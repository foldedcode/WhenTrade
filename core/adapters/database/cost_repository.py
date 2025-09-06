"""
成本数据存储适配器实现
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database.models.ai_usage import AIUsage
from core.database.models.user import User
from core.ports.cost_analytics import (
    CostAnalyticsPort,
    UsageSummary,
    UsageDetail,
    ModelUsageStats,
    CostTrend,
    TimeFrame
)
from core.ports.budget_management import (
    BudgetManagementPort,
    BudgetConfig,
    BudgetStatus,
    BudgetAlert,
    SpendingForecast,
    BudgetType,
    AlertLevel
)
from core.ports.achievement_system import (
    AchievementSystemPort,
    Achievement,
    UserAchievement,
    AchievementProgress,
    Leaderboard,
    LeaderboardEntry,
    AchievementCategory,
    AchievementRarity
)


class CostAnalyticsAdapter(CostAnalyticsPort):
    """成本分析适配器实现"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    def _get_date_range(self, time_frame: TimeFrame, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> tuple[datetime, datetime]:
        """获取时间范围"""
        if start_date and end_date:
            return start_date, end_date
            
        now = datetime.now(timezone.utc)
        if time_frame == TimeFrame.DAILY:
            start = now - timedelta(days=1)
        elif time_frame == TimeFrame.WEEKLY:
            start = now - timedelta(weeks=1)
        elif time_frame == TimeFrame.MONTHLY:
            start = now - timedelta(days=30)
        elif time_frame == TimeFrame.YEARLY:
            start = now - timedelta(days=365)
        else:  # ALL_TIME
            start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        
        return start, now
    
    async def get_usage_summary(
        self,
        user_id: str,
        time_frame: TimeFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageSummary:
        """获取使用量汇总"""
        start, end = self._get_date_range(time_frame, start_date, end_date)
        
        # 查询使用记录
        result = await self.db.execute(
            select(AIUsage).filter(
                AIUsage.user_id == user_id,
                AIUsage.created_at >= start,
                AIUsage.created_at <= end
            )
        )
        records = result.scalars().all()
        
        if not records:
            return UsageSummary(
                total_tokens=0,
                total_cost=Decimal("0.00"),
                daily_average=Decimal("0.00"),
                model_breakdown={},
                time_frame=time_frame,
                start_date=start,
                end_date=end
            )
        
        # 计算汇总数据
        total_tokens = sum(r.total_tokens for r in records)
        total_cost = sum(r.cost_amount for r in records)
        days = max((end - start).days, 1)
        daily_average = total_cost / days
        
        # 按模型分组统计
        model_breakdown = {}
        for record in records:
            if record.model_name not in model_breakdown:
                model_breakdown[record.model_name] = {
                    "tokens": 0,
                    "cost": Decimal("0.00"),
                    "requests": 0,
                    "percentage": 0.0
                }
            model_breakdown[record.model_name]["tokens"] += record.total_tokens
            model_breakdown[record.model_name]["cost"] += record.cost_amount
            model_breakdown[record.model_name]["requests"] += 1
        
        # 计算百分比
        for model in model_breakdown:
            model_breakdown[model]["percentage"] = float(
                model_breakdown[model]["cost"] / total_cost * 100
            ) if total_cost > 0 else 0.0
        
        return UsageSummary(
            total_tokens=total_tokens,
            total_cost=total_cost,
            daily_average=daily_average,
            model_breakdown=model_breakdown,
            time_frame=time_frame,
            start_date=start,
            end_date=end
        )
    
    async def get_usage_details(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UsageDetail]:
        """获取使用量详细记录"""
        query = select(AIUsage).filter(AIUsage.user_id == user_id)
        
        if start_date:
            query = query.filter(AIUsage.created_at >= start_date)
        if end_date:
            query = query.filter(AIUsage.created_at <= end_date)
        if model:
            query = query.filter(AIUsage.model_name == model)
        
        result = await self.db.execute(
            query.order_by(desc(AIUsage.created_at))
            .limit(limit)
            .offset(offset)
        )
        records = result.scalars().all()
        
        return [
            UsageDetail(
                id=str(record.id),
                user_id=record.user_id,
                model_name=record.model_name,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                total_tokens=record.total_tokens,
                cost=record.cost_amount,
                created_at=record.created_at,
                metadata=record.metadata
            )
            for record in records
        ]
    
    async def get_model_usage_stats(
        self,
        user_id: str,
        time_frame: TimeFrame
    ) -> List[ModelUsageStats]:
        """获取各模型使用统计"""
        start, end = self._get_date_range(time_frame)
        
        # 使用聚合查询
        result = await self.db.execute(
            select(
                AIUsage.model_name,
                func.count(AIUsage.id).label('request_count'),
                func.sum(AIUsage.total_tokens).label('total_tokens'),
                func.sum(AIUsage.cost_amount).label('total_cost'),
                func.avg(AIUsage.total_tokens).label('avg_tokens')
            ).filter(
                AIUsage.user_id == user_id,
                AIUsage.created_at >= start,
                AIUsage.created_at <= end
            ).group_by(AIUsage.model_name)
        )
        
        stats = []
        for row in result:
            stats.append(ModelUsageStats(
                model_name=row.model_name,
                total_requests=row.request_count,
                total_tokens=row.total_tokens or 0,
                total_cost=row.total_cost or Decimal("0.00"),
                average_tokens_per_request=float(row.avg_tokens or 0),
                cost_per_1k_tokens=Decimal(str(
                    float(row.total_cost) / (row.total_tokens / 1000)
                )) if row.total_tokens else Decimal("0.00")
            ))
        
        return stats
    
    async def get_cost_trends(
        self,
        user_id: str,
        time_frame: TimeFrame,
        granularity: TimeFrame
    ) -> List[CostTrend]:
        """获取成本趋势"""
        start, end = self._get_date_range(time_frame)
        
        # 根据粒度确定分组方式
        if granularity == TimeFrame.DAILY:
            date_trunc = func.date_trunc('day', AIUsage.created_at)
        elif granularity == TimeFrame.WEEKLY:
            date_trunc = func.date_trunc('week', AIUsage.created_at)
        else:  # MONTHLY
            date_trunc = func.date_trunc('month', AIUsage.created_at)
        
        # 查询趋势数据
        result = await self.db.execute(
            select(
                date_trunc.label('period'),
                func.sum(AIUsage.cost_amount).label('total_cost'),
                func.sum(AIUsage.total_tokens).label('total_tokens'),
                func.count(AIUsage.id).label('request_count')
            ).filter(
                AIUsage.user_id == user_id,
                AIUsage.created_at >= start,
                AIUsage.created_at <= end
            ).group_by('period').order_by('period')
        )
        
        trends = []
        prev_cost = None
        
        for row in result:
            trend_percentage = 0.0
            if prev_cost and prev_cost > 0:
                trend_percentage = float((row.total_cost - prev_cost) / prev_cost * 100)
            
            trends.append(CostTrend(
                date=row.period,
                cost=row.total_cost or Decimal("0.00"),
                token_count=row.total_tokens or 0,
                request_count=row.request_count or 0,
                trend_percentage=trend_percentage
            ))
            
            prev_cost = row.total_cost
        
        return trends
    
    async def record_usage(
        self,
        user_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: Decimal,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageDetail:
        """记录新的使用量"""
        usage = AIUsage(
            id=uuid4(),
            user_id=user_id,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_amount=cost,
            cost_currency="USD",
            metadata=metadata or {}
        )
        
        self.db.add(usage)
        await self.db.commit()
        await self.db.refresh(usage)
        
        return UsageDetail(
            id=str(usage.id),
            user_id=usage.user_id,
            model_name=usage.model_name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cost=usage.cost_amount,
            created_at=usage.created_at,
            metadata=usage.metadata
        )
    
    async def get_total_cost(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Decimal:
        """获取指定时间范围内的总成本"""
        query = select(func.sum(AIUsage.cost_amount)).filter(
            AIUsage.user_id == user_id
        )
        
        if start_date:
            query = query.filter(AIUsage.created_at >= start_date)
        if end_date:
            query = query.filter(AIUsage.created_at <= end_date)
        
        result = await self.db.execute(query)
        total = result.scalar()
        
        return total or Decimal("0.00")
    
    async def get_model_comparison(
        self,
        user_id: str,
        models: List[str],
        time_frame: TimeFrame
    ) -> Dict[str, ModelUsageStats]:
        """比较不同模型的使用情况"""
        stats = await self.get_model_usage_stats(user_id, time_frame)
        
        comparison = {}
        for stat in stats:
            if stat.model_name in models:
                comparison[stat.model_name] = stat
        
        # 为未使用的模型添加空数据
        for model in models:
            if model not in comparison:
                comparison[model] = ModelUsageStats(
                    model_name=model,
                    total_requests=0,
                    total_tokens=0,
                    total_cost=Decimal("0.00"),
                    average_tokens_per_request=0.0,
                    cost_per_1k_tokens=Decimal("0.00")
                )
        
        return comparison