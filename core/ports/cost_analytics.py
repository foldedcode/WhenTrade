"""
成本分析端口接口定义
"""
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class TimeFrame(str, Enum):
    """时间框架枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


@dataclass
class UsageSummary:
    """使用量汇总数据"""
    total_tokens: int
    total_cost: Decimal
    daily_average: Decimal
    model_breakdown: Dict[str, Dict[str, Any]]
    time_frame: TimeFrame
    start_date: datetime
    end_date: datetime


@dataclass
class UsageDetail:
    """使用量详细记录"""
    id: str
    user_id: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: Decimal
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelUsageStats:
    """模型使用统计"""
    model_name: str
    total_requests: int
    total_tokens: int
    total_cost: Decimal
    average_tokens_per_request: float
    cost_per_1k_tokens: Decimal


@dataclass
class CostTrend:
    """成本趋势数据"""
    date: datetime
    cost: Decimal
    token_count: int
    request_count: int
    trend_percentage: float  # 相对于前期的变化百分比


class CostAnalyticsPort(ABC):
    """成本分析端口接口"""
    
    @abstractmethod
    async def get_usage_summary(
        self,
        user_id: str,
        time_frame: TimeFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageSummary:
        """获取使用量汇总"""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_model_usage_stats(
        self,
        user_id: str,
        time_frame: TimeFrame
    ) -> List[ModelUsageStats]:
        """获取各模型使用统计"""
        pass
    
    @abstractmethod
    async def get_cost_trends(
        self,
        user_id: str,
        time_frame: TimeFrame,
        granularity: TimeFrame
    ) -> List[CostTrend]:
        """获取成本趋势
        
        Args:
            user_id: 用户ID
            time_frame: 查询的时间范围
            granularity: 数据粒度（日/周/月）
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_total_cost(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Decimal:
        """获取指定时间范围内的总成本"""
        pass
    
    @abstractmethod
    async def get_model_comparison(
        self,
        user_id: str,
        models: List[str],
        time_frame: TimeFrame
    ) -> Dict[str, ModelUsageStats]:
        """比较不同模型的使用情况"""
        pass