"""
Cost Manager - 智能成本管理器
专为When.Trade交易时机分析优化的成本控制系统
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class CostItem:
    """成本项目"""
    service: str
    operation: str
    amount: float
    currency: str = "USD"
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class CostLimits:
    """成本限制配置"""
    daily_limit: float = 100.0
    weekly_limit: float = 500.0
    monthly_limit: float = 2000.0
    per_analysis_limit: float = 10.0
    currency: str = "USD"

class CostManager:
    """
    智能成本管理器
    
    功能:
    - 实时成本跟踪
    - 预算限制管理
    - 成本预测
    - 智能优化建议
    """
    
    def __init__(self, limits: Optional[CostLimits] = None):
        self.limits = limits or CostLimits()
        self.cost_history: List[CostItem] = []
        self.active_sessions: Dict[str, List[CostItem]] = {}
        self._lock = asyncio.Lock()
        
        logger.info("💰 Cost Manager initialized")
        logger.info(f"   Daily limit: ${self.limits.daily_limit}")
        logger.info(f"   Weekly limit: ${self.limits.weekly_limit}")
        logger.info(f"   Monthly limit: ${self.limits.monthly_limit}")
    
    async def record_cost(
        self, 
        service: str, 
        operation: str, 
        amount: float,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        记录成本
        
        Args:
            service: 服务名称 (e.g., "openai", "analysis_engine")
            operation: 操作类型 (e.g., "chat_completion", "market_analysis")
            amount: 成本金额
            session_id: 会话ID (可选)
            metadata: 额外元数据
            
        Returns:
            bool: 是否在预算范围内
        """
        async with self._lock:
            cost_item = CostItem(
                service=service,
                operation=operation,
                amount=amount,
                metadata=metadata or {}
            )
            
            # 记录到历史
            self.cost_history.append(cost_item)
            
            # 记录到会话
            if session_id:
                if session_id not in self.active_sessions:
                    self.active_sessions[session_id] = []
                self.active_sessions[session_id].append(cost_item)
            
            # 检查预算限制
            within_budget = await self._check_budget_limits()
            
            logger.info(f"💸 Cost recorded: {service}.{operation} = ${amount:.4f}")
            if not within_budget:
                logger.warning("⚠️ Budget limit exceeded!")
            
            return within_budget
    
    async def get_current_costs(self, period: str = "daily") -> Dict:
        """
        获取当前周期的成本统计
        
        Args:
            period: 统计周期 ("daily", "weekly", "monthly")
            
        Returns:
            Dict: 成本统计信息
        """
        now = datetime.now()
        
        if period == "daily":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_time = now - timedelta(days=7)
        elif period == "monthly":
            start_time = now - timedelta(days=30)
        else:
            raise ValueError(f"Invalid period: {period}")
        
        # 筛选时间范围内的成本
        period_costs = [
            cost for cost in self.cost_history
            if cost.timestamp >= start_time
        ]
        
        # 按服务分组统计
        service_costs = {}
        total_cost = 0.0
        
        for cost in period_costs:
            if cost.service not in service_costs:
                service_costs[cost.service] = {
                    "total": 0.0,
                    "operations": {},
                    "count": 0
                }
            
            service_costs[cost.service]["total"] += cost.amount
            service_costs[cost.service]["count"] += 1
            total_cost += cost.amount
            
            # 按操作类型统计
            op = cost.operation
            if op not in service_costs[cost.service]["operations"]:
                service_costs[cost.service]["operations"][op] = {
                    "total": 0.0,
                    "count": 0
                }
            service_costs[cost.service]["operations"][op]["total"] += cost.amount
            service_costs[cost.service]["operations"][op]["count"] += 1
        
        return {
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "total_cost": total_cost,
            "service_breakdown": service_costs,
            "transaction_count": len(period_costs),
            "limits": {
                "daily": self.limits.daily_limit,
                "weekly": self.limits.weekly_limit,
                "monthly": self.limits.monthly_limit
            },
            "remaining_budget": self._calculate_remaining_budget(period, total_cost)
        }
    
    async def predict_cost(
        self, 
        service: str, 
        operation: str, 
        estimated_usage: Dict
    ) -> Dict:
        """
        预测成本
        
        Args:
            service: 服务名称
            operation: 操作类型
            estimated_usage: 预估使用量
            
        Returns:
            Dict: 成本预测信息
        """
        # 基于历史数据计算平均成本
        historical_costs = [
            cost.amount for cost in self.cost_history
            if cost.service == service and cost.operation == operation
        ]
        
        if not historical_costs:
            # 如果没有历史数据，使用默认估算
            avg_cost = 0.01  # 默认每次操作1分钱
        else:
            avg_cost = sum(historical_costs) / len(historical_costs)
        
        # 预测总成本
        estimated_count = estimated_usage.get("count", 1)
        predicted_cost = avg_cost * estimated_count
        
        # 检查是否会超出预算
        current_daily = await self.get_current_costs("daily")
        remaining_budget = current_daily["remaining_budget"]
        
        return {
            "service": service,
            "operation": operation,
            "estimated_usage": estimated_usage,
            "avg_historical_cost": avg_cost,
            "predicted_total_cost": predicted_cost,
            "remaining_daily_budget": remaining_budget,
            "will_exceed_budget": predicted_cost > remaining_budget,
            "recommendation": self._get_cost_recommendation(
                predicted_cost, remaining_budget
            )
        }
    
    async def get_session_cost(self, session_id: str) -> Dict:
        """获取特定会话的成本统计"""
        if session_id not in self.active_sessions:
            return {
                "session_id": session_id,
                "total_cost": 0.0,
                "transaction_count": 0,
                "services": {}
            }
        
        session_costs = self.active_sessions[session_id]
        total_cost = sum(cost.amount for cost in session_costs)
        
        # 按服务分组
        services = {}
        for cost in session_costs:
            if cost.service not in services:
                services[cost.service] = {
                    "total": 0.0,
                    "count": 0,
                    "operations": {}
                }
            services[cost.service]["total"] += cost.amount
            services[cost.service]["count"] += 1
            
            if cost.operation not in services[cost.service]["operations"]:
                services[cost.service]["operations"][cost.operation] = {
                    "total": 0.0,
                    "count": 0
                }
            services[cost.service]["operations"][cost.operation]["total"] += cost.amount
            services[cost.service]["operations"][cost.operation]["count"] += 1
        
        return {
            "session_id": session_id,
            "total_cost": total_cost,
            "transaction_count": len(session_costs),
            "services": services,
            "start_time": session_costs[0].timestamp.isoformat() if session_costs else None,
            "last_activity": session_costs[-1].timestamp.isoformat() if session_costs else None
        }
    
    async def _check_budget_limits(self) -> bool:
        """检查预算限制"""
        daily_costs = await self.get_current_costs("daily")
        weekly_costs = await self.get_current_costs("weekly")
        monthly_costs = await self.get_current_costs("monthly")
        
        return (
            daily_costs["total_cost"] <= self.limits.daily_limit and
            weekly_costs["total_cost"] <= self.limits.weekly_limit and
            monthly_costs["total_cost"] <= self.limits.monthly_limit
        )
    
    def _calculate_remaining_budget(self, period: str, current_cost: float) -> float:
        """计算剩余预算"""
        if period == "daily":
            return max(0, self.limits.daily_limit - current_cost)
        elif period == "weekly":
            return max(0, self.limits.weekly_limit - current_cost)
        elif period == "monthly":
            return max(0, self.limits.monthly_limit - current_cost)
        return 0.0
    
    def _get_cost_recommendation(self, predicted_cost: float, remaining_budget: float) -> str:
        """获取成本优化建议"""
        if predicted_cost <= remaining_budget * 0.5:
            return "安全范围内，可以继续操作"
        elif predicted_cost <= remaining_budget * 0.8:
            return "成本适中，建议监控使用量"
        elif predicted_cost <= remaining_budget:
            return "接近预算限制，建议优化操作"
        else:
            return "将超出预算，建议减少操作或增加预算"
    
    async def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 清理历史记录
        initial_count = len(self.cost_history)
        self.cost_history = [
            cost for cost in self.cost_history
            if cost.timestamp >= cutoff_date
        ]
        
        # 清理会话记录
        for session_id in list(self.active_sessions.keys()):
            self.active_sessions[session_id] = [
                cost for cost in self.active_sessions[session_id]
                if cost.timestamp >= cutoff_date
            ]
            
            # 删除空会话
            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]
        
        cleaned_count = initial_count - len(self.cost_history)
        logger.info(f"🧹 Cleaned {cleaned_count} old cost records")
        
        return cleaned_count 