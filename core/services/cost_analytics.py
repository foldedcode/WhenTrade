"""
成本分析服务
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.ports.cost_analytics import (
    CostAnalyticsPort,
    UsageSummary,
    UsageDetail,
    ModelUsageStats,
    CostTrend,
    TimeFrame
)
from core.adapters.database.cost_repository import CostAnalyticsAdapter
from core.adapters.ai_provider.usage_tracker import UsageTracker
from core.config import settings


class CostAnalyticsService:
    """成本分析服务
    
    组合使用 Port 和 Adapter 提供成本分析功能
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.repository = CostAnalyticsAdapter(db_session)
        self.usage_tracker = UsageTracker()
    
    async def get_usage_summary(
        self,
        user_id: str,
        time_frame: TimeFrame = TimeFrame.MONTHLY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageSummary:
        """获取使用量汇总
        
        直接委托给 repository
        """
        return await self.repository.get_usage_summary(
            user_id=user_id,
            time_frame=time_frame,
            start_date=start_date,
            end_date=end_date
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
        return await self.repository.get_usage_details(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            model=model,
            limit=limit,
            offset=offset
        )
    
    async def record_usage(
        self,
        user_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageDetail:
        """记录 AI 使用量
        
        使用 UsageTracker 计算成本，然后存储到数据库
        """
        # 计算成本
        cost = self.usage_tracker.calculate_cost(
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        # 记录到数据库
        return await self.repository.record_usage(
            user_id=user_id,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            metadata=metadata
        )
    
    async def get_model_usage_stats(
        self,
        user_id: str,
        time_frame: TimeFrame = TimeFrame.MONTHLY
    ) -> List[ModelUsageStats]:
        """获取各模型使用统计"""
        return await self.repository.get_model_usage_stats(
            user_id=user_id,
            time_frame=time_frame
        )
    
    async def get_cost_trends(
        self,
        user_id: str,
        time_frame: TimeFrame = TimeFrame.MONTHLY,
        granularity: TimeFrame = TimeFrame.DAILY
    ) -> List[CostTrend]:
        """获取成本趋势"""
        return await self.repository.get_cost_trends(
            user_id=user_id,
            time_frame=time_frame,
            granularity=granularity
        )
    
    async def get_model_comparison(
        self,
        user_id: str,
        models: List[str],
        time_frame: TimeFrame = TimeFrame.MONTHLY
    ) -> Dict[str, ModelUsageStats]:
        """比较不同模型的使用情况"""
        return await self.repository.get_model_comparison(
            user_id=user_id,
            models=models,
            time_frame=time_frame
        )
    
    async def estimate_cost(
        self,
        model_name: str,
        estimated_tokens: int,
        input_ratio: float = 0.3
    ) -> Dict[str, Any]:
        """估算成本
        
        使用 UsageTracker 进行成本估算
        """
        estimate = self.usage_tracker.estimate_cost(
            model_name=model_name,
            estimated_tokens=estimated_tokens,
            input_ratio=input_ratio
        )
        
        # 添加模型信息
        model_info = self.usage_tracker.get_model_info(model_name)
        estimate.update({
            "model_info": model_info
        })
        
        return estimate
    
    async def get_total_cost(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Decimal:
        """获取总成本"""
        return await self.repository.get_total_cost(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_model_pricing(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的定价信息"""
        return self.usage_tracker.get_all_model_pricing()
    
    async def get_cost_insights(
        self,
        user_id: str,
        time_frame: TimeFrame = TimeFrame.MONTHLY
    ) -> Dict[str, Any]:
        """获取成本洞察
        
        提供高级分析和建议
        """
        # 获取使用汇总
        summary = await self.get_usage_summary(user_id, time_frame)
        
        # 获取模型统计
        model_stats = await self.get_model_usage_stats(user_id, time_frame)
        
        # 获取成本趋势
        trends = await self.get_cost_trends(user_id, time_frame, TimeFrame.DAILY)
        
        # 分析数据
        insights = {
            "summary": {
                "total_cost": float(summary.total_cost),
                "daily_average": float(summary.daily_average),
                "total_tokens": summary.total_tokens
            },
            "top_models": [],
            "cost_trend": "stable",
            "recommendations": []
        }
        
        # 找出最常用的模型
        if model_stats:
            sorted_models = sorted(
                model_stats, 
                key=lambda x: x.total_cost, 
                reverse=True
            )[:3]
            insights["top_models"] = [
                {
                    "model": m.model_name,
                    "cost": float(m.total_cost),
                    "requests": m.total_requests
                }
                for m in sorted_models
            ]
        
        # 分析趋势
        if len(trends) >= 7:
            recent_avg = sum(t.cost for t in trends[-7:]) / 7
            previous_avg = sum(t.cost for t in trends[-14:-7]) / 7 if len(trends) >= 14 else recent_avg
            
            if recent_avg > previous_avg * 1.2:
                insights["cost_trend"] = "increasing"
            elif recent_avg < previous_avg * 0.8:
                insights["cost_trend"] = "decreasing"
        
        # 生成建议
        insights["recommendations"] = await self._generate_recommendations(
            summary, model_stats, insights["cost_trend"]
        )
        
        return insights
    
    async def _generate_recommendations(
        self,
        summary: UsageSummary,
        model_stats: List[ModelUsageStats],
        trend: str
    ) -> List[Dict[str, Any]]:
        """生成优化建议"""
        recommendations = []
        
        # 如果成本上升趋势
        if trend == "increasing":
            recommendations.append({
                "type": "trend_alert",
                "priority": "high",
                "title": "成本上升趋势",
                "description": "您的使用成本呈上升趋势，建议关注使用模式"
            })
        
        # 检查是否过度使用昂贵模型
        for stat in model_stats:
            if "gpt-4" in stat.model_name.lower() and stat.total_requests > 100:
                recommendations.append({
                    "type": "model_optimization",
                    "priority": "medium",
                    "title": "优化模型选择",
                    "description": f"您频繁使用 {stat.model_name}，考虑在简单任务中使用更经济的模型",
                    "potential_savings": float(stat.total_cost * 0.5)
                })
                break
        
        # 建议启用缓存
        if summary.total_tokens > 1000000:
            recommendations.append({
                "type": "enable_caching",
                "priority": "medium",
                "title": "启用响应缓存",
                "description": "您的使用量较大，启用缓存可以减少重复请求",
                "potential_savings": float(summary.total_cost * 0.15)
            })
        
        return recommendations