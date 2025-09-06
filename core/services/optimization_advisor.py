"""
优化建议服务
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from core.services.cost_analytics import CostAnalyticsService
from core.ports.cost_analytics import TimeFrame


class OptimizationType(str, Enum):
    """优化类型"""
    MODEL_SELECTION = "model_selection"
    BATCH_PROCESSING = "batch_processing"
    CACHING = "caching"
    RATE_LIMITING = "rate_limiting"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    USAGE_PATTERN = "usage_pattern"


class Priority(str, Enum):
    """优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    id: str
    type: OptimizationType
    priority: Priority
    title: str
    description: str
    implementation_guide: List[str]
    potential_savings: Decimal
    effort_level: str  # easy, medium, hard
    estimated_time: str  # 预计实施时间
    metrics: Dict[str, Any]  # 相关指标


class OptimizationAdvisor:
    """优化建议服务
    
    分析使用模式并提供个性化的成本优化建议
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.cost_service = CostAnalyticsService(db_session)
    
    async def get_optimization_suggestions(
        self,
        user_id: str,
        time_frame: TimeFrame = TimeFrame.MONTHLY
    ) -> List[OptimizationSuggestion]:
        """获取优化建议"""
        suggestions = []
        
        # 获取使用数据
        summary = await self.cost_service.get_usage_summary(user_id, time_frame)
        model_stats = await self.cost_service.get_model_usage_stats(user_id, time_frame)
        trends = await self.cost_service.get_cost_trends(user_id, time_frame, TimeFrame.DAILY)
        
        # 分析模型选择
        model_suggestions = await self._analyze_model_selection(
            summary, model_stats
        )
        suggestions.extend(model_suggestions)
        
        # 分析使用模式
        pattern_suggestions = await self._analyze_usage_patterns(
            user_id, trends
        )
        suggestions.extend(pattern_suggestions)
        
        # 分析批处理机会
        batch_suggestions = await self._analyze_batch_opportunities(
            user_id, time_frame
        )
        suggestions.extend(batch_suggestions)
        
        # 缓存建议
        cache_suggestion = self._suggest_caching(summary)
        if cache_suggestion:
            suggestions.append(cache_suggestion)
        
        # 按优先级和节省潜力排序
        suggestions.sort(
            key=lambda x: (
                self._priority_value(x.priority),
                -float(x.potential_savings)
            )
        )
        
        return suggestions
    
    async def _analyze_model_selection(
        self,
        summary: Any,
        model_stats: List[Any]
    ) -> List[OptimizationSuggestion]:
        """分析模型选择优化机会"""
        suggestions = []
        
        # 检查是否过度使用昂贵模型
        for stat in model_stats:
            model_lower = stat.model_name.lower()
            
            # GPT-4 优化建议
            if "gpt-4" in model_lower and stat.total_requests > 50:
                # 计算如果使用 GPT-3.5 的潜在节省
                gpt35_cost_ratio = Decimal("0.05")  # GPT-3.5 大约是 GPT-4 成本的 5%
                potential_savings = stat.total_cost * (1 - gpt35_cost_ratio) * Decimal("0.6")  # 假设60%的任务可以用GPT-3.5
                
                suggestions.append(OptimizationSuggestion(
                    id="optimize-gpt4-usage",
                    type=OptimizationType.MODEL_SELECTION,
                    priority=Priority.HIGH if float(potential_savings) > 100 else Priority.MEDIUM,
                    title="优化 GPT-4 使用",
                    description=f"您在过去{self._get_timeframe_text(summary.time_frame)}使用了 {stat.total_requests} 次 {stat.model_name}。"
                               f"许多任务可能不需要 GPT-4 的能力。",
                    implementation_guide=[
                        "识别不需要高级推理的任务（如简单分类、格式化等）",
                        "为这些任务使用 GPT-3.5-Turbo",
                        "建立任务复杂度评估机制",
                        "实施自动模型选择逻辑"
                    ],
                    potential_savings=potential_savings,
                    effort_level="medium",
                    estimated_time="1-2天",
                    metrics={
                        "current_requests": stat.total_requests,
                        "current_cost": float(stat.total_cost),
                        "suggested_split": {"gpt-4": 0.4, "gpt-3.5-turbo": 0.6}
                    }
                ))
            
            # Claude Opus 优化建议
            elif "opus" in model_lower and stat.total_requests > 30:
                potential_savings = stat.total_cost * Decimal("0.5")
                
                suggestions.append(OptimizationSuggestion(
                    id="optimize-claude-opus",
                    type=OptimizationType.MODEL_SELECTION,
                    priority=Priority.MEDIUM,
                    title="考虑使用 Claude Sonnet",
                    description="Claude Sonnet 在大多数任务上表现接近 Opus，但成本更低。",
                    implementation_guide=[
                        "测试 Sonnet 在您的用例上的表现",
                        "识别真正需要 Opus 的任务",
                        "实施分级模型选择策略"
                    ],
                    potential_savings=potential_savings,
                    effort_level="easy",
                    estimated_time="几小时",
                    metrics={
                        "current_model": stat.model_name,
                        "current_requests": stat.total_requests
                    }
                ))
        
        return suggestions
    
    async def _analyze_usage_patterns(
        self,
        user_id: str,
        trends: List[Any]
    ) -> List[OptimizationSuggestion]:
        """分析使用模式"""
        suggestions = []
        
        if not trends:
            return suggestions
        
        # 检查是否有使用高峰
        daily_costs = [float(t.cost) for t in trends]
        avg_cost = sum(daily_costs) / len(daily_costs) if daily_costs else 0
        peak_days = [i for i, cost in enumerate(daily_costs) if cost > avg_cost * 2]
        
        if len(peak_days) >= 3:
            suggestions.append(OptimizationSuggestion(
                id="smooth-usage-peaks",
                type=OptimizationType.USAGE_PATTERN,
                priority=Priority.MEDIUM,
                title="平滑使用高峰",
                description="检测到使用量存在明显峰值，可能导致成本突增。",
                implementation_guide=[
                    "分析高峰时段的任务类型",
                    "考虑实施任务队列和延迟处理",
                    "使用速率限制避免突发请求",
                    "预先批量处理可预测的任务"
                ],
                potential_savings=Decimal(str(avg_cost * len(peak_days) * 0.3)),
                effort_level="medium",
                estimated_time="3-5天",
                metrics={
                    "peak_days_count": len(peak_days),
                    "average_daily_cost": avg_cost,
                    "peak_multiplier": 2.0
                }
            ))
        
        # 检查增长趋势
        if len(trends) >= 7:
            recent_avg = sum(float(t.cost) for t in trends[-7:]) / 7
            older_avg = sum(float(t.cost) for t in trends[:7]) / 7 if len(trends) >= 14 else recent_avg
            
            growth_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            
            if growth_rate > 0.5:  # 增长超过50%
                suggestions.append(OptimizationSuggestion(
                    id="control-cost-growth",
                    type=OptimizationType.USAGE_PATTERN,
                    priority=Priority.HIGH,
                    title="控制成本快速增长",
                    description=f"您的使用成本增长了 {growth_rate*100:.1f}%，需要关注。",
                    implementation_guide=[
                        "审查新增的使用场景",
                        "设置预算警报",
                        "实施成本监控仪表板",
                        "建立成本审批流程"
                    ],
                    potential_savings=Decimal(str(recent_avg * 7 * 0.2)),
                    effort_level="easy",
                    estimated_time="1天",
                    metrics={
                        "growth_rate": growth_rate,
                        "recent_average": recent_avg,
                        "older_average": older_avg
                    }
                ))
        
        return suggestions
    
    async def _analyze_batch_opportunities(
        self,
        user_id: str,
        time_frame: TimeFrame
    ) -> List[OptimizationSuggestion]:
        """分析批处理机会"""
        suggestions = []
        
        # 获取最近的使用详情
        recent_usages = await self.cost_service.get_usage_details(
            user_id=user_id,
            limit=500
        )
        
        if len(recent_usages) < 50:
            return suggestions
        
        # 分析请求时间间隔
        timestamps = [u.created_at for u in recent_usages]
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i-1] - timestamps[i]).total_seconds()
            if interval < 60:  # 1分钟内的请求
                intervals.append(interval)
        
        # 如果有很多短间隔请求，建议批处理
        if len(intervals) > len(timestamps) * 0.3:
            avg_requests_per_minute = len(intervals) / (len(timestamps) / 60) if len(timestamps) > 60 else len(intervals)
            
            suggestions.append(OptimizationSuggestion(
                id="enable-batch-processing",
                type=OptimizationType.BATCH_PROCESSING,
                priority=Priority.HIGH,
                title="启用批量处理",
                description=f"检测到大量短间隔请求（平均 {avg_requests_per_minute:.1f} 个/分钟）。批量处理可以减少开销。",
                implementation_guide=[
                    "实施请求队列系统",
                    "将相似请求合并处理",
                    "使用批量 API（如果可用）",
                    "设置合理的批处理窗口（如5-10秒）"
                ],
                potential_savings=Decimal(str(sum(float(u.cost) for u in recent_usages) * 0.15)),
                effort_level="hard",
                estimated_time="1周",
                metrics={
                    "short_interval_requests": len(intervals),
                    "total_requests": len(recent_usages),
                    "avg_requests_per_minute": avg_requests_per_minute
                }
            ))
        
        return suggestions
    
    def _suggest_caching(self, summary: Any) -> Optional[OptimizationSuggestion]:
        """缓存建议"""
        if summary.total_tokens < 500000:
            return None
        
        # 基于总使用量估算缓存可以节省的成本
        cache_hit_rate = 0.2  # 假设20%的缓存命中率
        potential_savings = summary.total_cost * Decimal(str(cache_hit_rate))
        
        return OptimizationSuggestion(
            id="implement-response-caching",
            type=OptimizationType.CACHING,
            priority=Priority.MEDIUM,
            title="实施智能缓存",
            description="您的使用量较大，实施缓存可以显著降低成本。",
            implementation_guide=[
                "识别可缓存的查询模式",
                "实施基于内容的缓存键生成",
                "设置合理的 TTL（如1-24小时）",
                "监控缓存命中率并优化"
            ],
            potential_savings=potential_savings,
            effort_level="medium",
            estimated_time="2-3天",
            metrics={
                "total_tokens": summary.total_tokens,
                "estimated_cache_hit_rate": cache_hit_rate,
                "current_total_cost": float(summary.total_cost)
            }
        )
    
    def _priority_value(self, priority: Priority) -> int:
        """优先级数值转换"""
        return {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3
        }[priority]
    
    def _get_timeframe_text(self, time_frame: TimeFrame) -> str:
        """时间框架文本"""
        return {
            TimeFrame.DAILY: "一天",
            TimeFrame.WEEKLY: "一周",
            TimeFrame.MONTHLY: "一个月",
            TimeFrame.YEARLY: "一年",
            TimeFrame.ALL_TIME: "所有时间"
        }.get(time_frame, "一段时间")
    
    async def apply_optimization(
        self,
        user_id: str,
        optimization_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """应用优化建议
        
        这是一个占位方法，实际实施需要根据具体优化类型进行
        """
        # 这里应该实现具体的优化逻辑
        # 例如更新用户偏好设置、配置缓存等
        
        result = {
            "success": True,
            "optimization_id": optimization_id,
            "message": f"优化建议 {optimization_id} 已标记为待实施",
            "next_steps": [
                "根据实施指南执行优化",
                "监控优化效果",
                "调整参数以获得最佳效果"
            ]
        }
        
        if parameters:
            result["parameters"] = parameters
        
        return result