"""
Billing service with idempotency and distributed locking
"""

import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from core.database.models.user import User
from core.database.models.billing import (
    UserBalance, WalletTopup, StripePayment,
    StripeEvent, UsageLog, TransactionLedger
)
from core.cache.redis_client import RedisClient
from core.database.session import get_db


logger = logging.getLogger(__name__)


class BillingService:
    """Service for handling billing operations with idempotency"""
    
    def __init__(self, db: AsyncSession, redis: RedisClient):
        self.db = db
        self.redis = redis
    
    async def _acquire_user_lock(
        self, 
        user_id: str, 
        operation: str = "balance",
        ttl: int = 30
    ) -> Optional[str]:
        """
        Acquire distributed lock for user operations
        
        Returns:
            Lock ID if acquired, None otherwise
        """
        lock_key = f"billing:lock:user:{user_id}:{operation}"
        lock_id = str(uuid.uuid4())
        
        if await self.redis.acquire_lock(lock_key, lock_id, ttl):
            return lock_id
        return None
    
    async def _release_user_lock(
        self, 
        user_id: str, 
        lock_id: str,
        operation: str = "balance"
    ):
        """Release user lock"""
        lock_key = f"billing:lock:user:{user_id}:{operation}"
        await self.redis.release_lock(lock_key, lock_id)
    
    async def update_user_balance(
        self,
        user_id: str,
        amount: Decimal,
        transaction_type: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update user balance with transaction ledger
        
        Args:
            user_id: User ID
            amount: Amount to add (positive) or subtract (negative)
            transaction_type: Type of transaction
            reference_type: Reference table name
            reference_id: Reference record ID
            description: Transaction description
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        lock_id = await self._acquire_user_lock(user_id)
        if not lock_id:
            logger.error(f"Failed to acquire lock for user {user_id}")
            return False
        
        try:
            # Get current balance with row lock
            balance_stmt = select(UserBalance).where(
                UserBalance.user_id == user_id
            ).with_for_update()
            
            result = await self.db.execute(balance_stmt)
            balance = result.scalar_one_or_none()
            
            if not balance:
                # Create balance record if not exists
                balance = UserBalance(user_id=user_id, credits=Decimal("0"))
                self.db.add(balance)
                await self.db.flush()
            
            # Calculate new balance
            balance_before = balance.credits
            balance_after = balance_before + amount
            
            # Check for sufficient balance (for debits)
            if balance_after < 0:
                logger.warning(f"Insufficient balance for user {user_id}")
                return False
            
            # Update balance
            balance.credits = balance_after
            balance.version += 1
            
            # Create ledger entry
            ledger_entry = TransactionLedger(
                user_id=user_id,
                transaction_type=transaction_type,
                reference_type=reference_type,
                reference_id=uuid.UUID(reference_id) if reference_id else None,
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                description=description,
                metadata=metadata or {}
            )
            self.db.add(ledger_entry)
            
            # Commit transaction
            await self.db.commit()
            
            # Update cache
            await self._update_balance_cache(user_id, balance_after)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            await self.db.rollback()
            return False
            
        finally:
            await self._release_user_lock(user_id, lock_id)
    
    async def process_wallet_topup(
        self,
        tx_hash: str,
        confirmations: int
    ) -> bool:
        """
        Process wallet topup with idempotency
        
        Args:
            tx_hash: Transaction hash (idempotency key)
            confirmations: Number of confirmations
            
        Returns:
            True if processed, False otherwise
        """
        lock_key = f"billing:lock:topup:{tx_hash}"
        lock_id = str(uuid.uuid4())
        
        if not await self.redis.acquire_lock(lock_key, lock_id, ttl=60):
            logger.warning(f"Failed to acquire lock for topup {tx_hash}")
            return False
        
        try:
            # Get topup record
            stmt = select(WalletTopup).where(
                WalletTopup.tx_hash == tx_hash
            ).with_for_update()
            
            result = await self.db.execute(stmt)
            topup = result.scalar_one_or_none()
            
            if not topup:
                logger.error(f"Topup not found: {tx_hash}")
                return False
            
            # Check if already processed (idempotent)
            if topup.status == "confirmed":
                return True
            
            # Update confirmations
            topup.confirmations = confirmations
            
            # Process if enough confirmations
            if confirmations >= 6:  # 6 confirmations for safety
                # Add credits to user balance
                success = await self.update_user_balance(
                    user_id=str(topup.user_id),
                    amount=topup.credits_added,
                    transaction_type="topup",
                    reference_type="wallet_topup",
                    reference_id=str(topup.id),
                    description=f"Wallet topup: {topup.amount} USDC",
                    metadata={
                        "tx_hash": topup.tx_hash,
                        "chain_id": topup.chain_id,
                        "token_address": topup.token_address
                    }
                )
                
                if success:
                    topup.status = "confirmed"
                    topup.confirmed_at = datetime.utcnow()
                    await self.db.commit()
                    return True
                else:
                    await self.db.rollback()
                    return False
            
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error processing topup {tx_hash}: {e}")
            await self.db.rollback()
            return False
            
        finally:
            await self.redis.release_lock(lock_key, lock_id)
    
    async def process_stripe_event(
        self,
        event_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Process Stripe webhook event with idempotency
        
        Args:
            event_id: Stripe event ID (idempotency key)
            event_type: Event type
            event_data: Event data
            
        Returns:
            True if processed, False otherwise
        """
        try:
            # Check if event already processed (idempotent)
            stmt = select(StripeEvent).where(
                StripeEvent.stripe_event_id == event_id
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing and existing.processed:
                return True
            
            # Create or update event record
            if not existing:
                event = StripeEvent(
                    stripe_event_id=event_id,
                    event_type=event_type,
                    raw_data=event_data
                )
                self.db.add(event)
            else:
                event = existing
            
            # Process based on event type
            if event_type == "payment_intent.succeeded":
                success = await self._process_payment_intent(event_data)
            elif event_type == "invoice.payment_succeeded":
                success = await self._process_invoice_payment(event_data)
            else:
                # Mark as processed for unsupported events
                success = True
            
            if success:
                event.processed = True
                event.processed_at = datetime.utcnow()
            else:
                event.error = "Processing failed"
            
            await self.db.commit()
            return success
            
        except IntegrityError:
            # Event already exists (race condition)
            await self.db.rollback()
            return True
        except Exception as e:
            logger.error(f"Error processing Stripe event {event_id}: {e}")
            await self.db.rollback()
            return False
    
    async def record_usage(
        self,
        user_id: str,
        request_id: str,
        service_type: str,
        credits_used: Decimal,
        service_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        execution_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record usage and deduct credits
        
        Args:
            user_id: User ID
            request_id: Unique request ID (idempotency key)
            service_type: Type of service used
            credits_used: Credits to deduct
            service_id: Specific service identifier
            input_tokens: Input token count
            output_tokens: Output token count
            execution_time_ms: Execution time in milliseconds
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check for duplicate request (idempotent)
            stmt = select(UsageLog).where(
                UsageLog.request_id == request_id
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                return True  # Already processed
            
            # Create usage log
            usage_log = UsageLog(
                user_id=user_id,
                request_id=request_id,
                service_type=service_type,
                service_id=service_id,
                credits_used=credits_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                execution_time_ms=execution_time_ms,
                metadata=metadata or {}
            )
            self.db.add(usage_log)
            await self.db.flush()
            
            # Deduct credits
            success = await self.update_user_balance(
                user_id=user_id,
                amount=-credits_used,  # Negative for deduction
                transaction_type="usage",
                reference_type="usage_log",
                reference_id=str(usage_log.id),
                description=f"Usage: {service_type}",
                metadata={
                    "service_type": service_type,
                    "service_id": service_id,
                    "tokens": input_tokens + output_tokens
                }
            )
            
            if not success:
                await self.db.rollback()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            await self.db.rollback()
            return False
    
    async def get_user_balance(self, user_id: str) -> Optional[Decimal]:
        """Get user's current balance with caching"""
        # Try cache first
        cached = await self.redis.get(f"cache:balance:{user_id}")
        if cached:
            return Decimal(cached)
        
        # Get from database
        stmt = select(UserBalance).where(UserBalance.user_id == user_id)
        result = await self.db.execute(stmt)
        balance = result.scalar_one_or_none()
        
        if balance:
            # Update cache
            await self._update_balance_cache(user_id, balance.credits)
            return balance.credits
        
        return Decimal("0")
    
    async def _update_balance_cache(self, user_id: str, balance: Decimal):
        """Update balance cache"""
        await self.redis.set(
            f"cache:balance:{user_id}",
            str(balance),
            ttl=60  # 60 seconds TTL
        )
    
    async def _process_payment_intent(self, data: Dict[str, Any]) -> bool:
        """Process successful payment intent"""
        # Implementation depends on Stripe webhook structure
        # This is a placeholder
        return True
    
    async def _process_invoice_payment(self, data: Dict[str, Any]) -> bool:
        """Process successful invoice payment"""
        # Implementation depends on Stripe webhook structure
        # This is a placeholder
        return True