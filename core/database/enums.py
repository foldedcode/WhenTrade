"""
数据库通用枚举定义
"""

import enum


class TaskStatus(str, enum.Enum):
    """任务/分析状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"  # 额外的暂停状态


class MarketType(str, enum.Enum):
    """市场类型"""
    STOCK = "stock"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    FOREX = "forex"
    FUTURES = "futures"


class TaskType(str, enum.Enum):
    """任务类型"""
    RESEARCH = "research"
    CHAT = "chat"
    ANALYSIS = "analysis"
    PREDICTION = "prediction"
    MONITORING = "monitoring"


class UserRole(str, enum.Enum):
    """用户角色"""
    USER = "user"
    ADMIN = "admin"
    VIP = "vip"
    PREMIUM = "premium"


class SubscriptionStatus(str, enum.Enum):
    """订阅状态"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"
    SUSPENDED = "suspended"


class SubscriptionTier(str, enum.Enum):
    """订阅等级"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class ReportType(str, enum.Enum):
    """报告类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"
    ANALYSIS = "analysis"


class ReportFormat(str, enum.Enum):
    """报告格式"""
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"
    EXCEL = "excel"


# 为了向后兼容，创建别名
AnalysisStatus = TaskStatus