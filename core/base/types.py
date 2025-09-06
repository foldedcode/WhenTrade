"""
通用类型定义
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime


class Status(str, Enum):
    """通用状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"


class Priority(int, Enum):
    """优先级枚举"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    TRIVIAL = 4


@dataclass
class Result:
    """通用结果类"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
            
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
        
    @classmethod
    def success_result(cls, data: Any = None, **kwargs) -> "Result":
        """创建成功结果"""
        return cls(success=True, data=data, **kwargs)
        
    @classmethod
    def error_result(cls, error: str, **kwargs) -> "Result":
        """创建错误结果"""
        return cls(success=False, error=error, **kwargs)