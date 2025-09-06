"""
预算管理端口接口定义
"""
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class BudgetType(str, Enum):
    """预算类型枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    TOTAL = "total"  # 总预算，不限时间


class AlertLevel(str, Enum):
    """预警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class BudgetConfig:
    """预算配置"""
    id: str
    user_id: str
    budget_type: BudgetType
    amount: Decimal
    currency: str = "USD"
    alert_threshold: float = 0.8  # 达到预算的80%时预警
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class BudgetStatus:
    """预算状态"""
    budget_config: BudgetConfig
    current_usage: Decimal
    remaining_budget: Decimal
    usage_percentage: float
    alert_level: AlertLevel
    days_remaining: Optional[int] = None  # 对于有时间限制的预算
    projected_overage: Optional[Decimal] = None  # 预计超支金额


@dataclass
class BudgetAlert:
    """预算预警"""
    id: str
    user_id: str
    budget_id: str
    alert_level: AlertLevel
    message: str
    current_usage: Decimal
    budget_limit: Decimal
    created_at: datetime
    is_acknowledged: bool = False


@dataclass
class SpendingForecast:
    """支出预测"""
    forecast_date: datetime
    predicted_amount: Decimal
    confidence_level: float  # 0-1之间的置信度
    based_on_days: int  # 基于多少天的历史数据


class BudgetManagementPort(ABC):
    """预算管理端口接口"""
    
    @abstractmethod
    async def create_budget(
        self,
        user_id: str,
        budget_type: BudgetType,
        amount: Decimal,
        currency: str = "USD",
        alert_threshold: float = 0.8
    ) -> BudgetConfig:
        """创建预算配置"""
        pass
    
    @abstractmethod
    async def update_budget(
        self,
        budget_id: str,
        amount: Optional[Decimal] = None,
        alert_threshold: Optional[float] = None,
        is_active: Optional[bool] = None
    ) -> BudgetConfig:
        """更新预算配置"""
        pass
    
    @abstractmethod
    async def delete_budget(self, budget_id: str) -> bool:
        """删除预算配置"""
        pass
    
    @abstractmethod
    async def get_budget_by_id(self, budget_id: str) -> Optional[BudgetConfig]:
        """根据ID获取预算配置"""
        pass
    
    @abstractmethod
    async def get_user_budgets(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[BudgetConfig]:
        """获取用户的所有预算配置"""
        pass
    
    @abstractmethod
    async def get_budget_status(
        self,
        user_id: str,
        budget_type: Optional[BudgetType] = None
    ) -> List[BudgetStatus]:
        """获取预算状态"""
        pass
    
    @abstractmethod
    async def check_budget_exceeded(
        self,
        user_id: str,
        additional_cost: Decimal
    ) -> Dict[BudgetType, bool]:
        """检查是否会超出预算
        
        Returns:
            各预算类型是否会超支的字典
        """
        pass
    
    @abstractmethod
    async def get_budget_alerts(
        self,
        user_id: str,
        unacknowledged_only: bool = True,
        limit: int = 50
    ) -> List[BudgetAlert]:
        """获取预算预警"""
        pass
    
    @abstractmethod
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """确认预警"""
        pass
    
    @abstractmethod
    async def create_alert(
        self,
        user_id: str,
        budget_id: str,
        alert_level: AlertLevel,
        message: str,
        current_usage: Decimal,
        budget_limit: Decimal
    ) -> BudgetAlert:
        """创建预警"""
        pass
    
    @abstractmethod
    async def get_spending_forecast(
        self,
        user_id: str,
        budget_type: BudgetType,
        days_ahead: int = 30
    ) -> List[SpendingForecast]:
        """获取支出预测"""
        pass
    
    @abstractmethod
    async def get_budget_recommendations(
        self,
        user_id: str
    ) -> Dict[BudgetType, Decimal]:
        """获取预算建议
        
        基于用户的历史使用模式推荐合理的预算设置
        """
        pass