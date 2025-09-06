"""
统一的数据模型定义
整合来自 core/adapters/base.py 和 datagateway/base.py 的数据模型
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, field_validator


class DataType(str, Enum):
    """数据类型枚举"""
    # 市场数据
    PRICE = "price"              # 价格数据
    OHLCV = "ohlcv"             # OHLCV数据
    VOLUME = "volume"            # 成交量
    ORDERBOOK = "orderbook"      # 订单簿
    TRADES = "trades"            # 成交记录
    
    # 基本面数据
    FINANCIALS = "financials"    # 财务数据
    EARNINGS = "earnings"        # 收益数据
    METRICS = "metrics"          # 关键指标
    
    # 新闻和情绪
    NEWS = "news"                # 新闻数据
    SENTIMENT = "sentiment"      # 情绪数据
    SOCIAL = "social"            # 社交媒体数据
    
    # 技术指标
    TECHNICAL = "technical"      # 技术指标
    
    # 其他
    CUSTOM = "custom"            # 自定义数据


class DataFrequency(str, Enum):
    """数据频率枚举"""
    TICK = "tick"                # 逐笔
    SECOND = "1s"                # 秒级
    MINUTE = "1m"                # 分钟
    MINUTE_5 = "5m"              # 5分钟
    MINUTE_15 = "15m"            # 15分钟
    MINUTE_30 = "30m"            # 30分钟
    HOUR = "1h"                  # 小时
    HOUR_4 = "4h"                # 4小时
    DAILY = "1d"                 # 日线
    WEEKLY = "1w"                # 周线
    MONTHLY = "1M"               # 月线
    QUARTERLY = "1Q"             # 季度
    YEARLY = "1Y"                # 年线


@dataclass
class DataPoint:
    """单个数据点"""
    timestamp: datetime
    value: Union[float, Dict[str, Any], List[Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "metadata": self.metadata
        }


# 使用Pydantic版本（兼容API）
class DataRequest(BaseModel):
    """数据请求模型 - Pydantic版本"""
    symbol: str                              # 单个标的（兼容datagateway）
    symbols: Optional[List[str]] = None      # 标的列表（兼容adapters）
    data_type: Union[str, DataType]         # 数据类型
    start_date: Optional[Union[date, datetime]] = None
    end_date: Optional[Union[date, datetime]] = None
    frequency: Optional[Union[str, DataFrequency]] = None
    limit: Optional[int] = None
    extra_params: Dict[str, Any] = {}
    
    @field_validator('symbols')
    @classmethod
    def ensure_symbols(cls, v, info=None):
        """确保symbols字段始终有值"""
        if v is None and info and info.data and 'symbol' in info.data:
            return [info.data['symbol']]
        return v
    
    @field_validator('data_type')
    @classmethod
    def validate_data_type(cls, v):
        """验证数据类型"""
        if isinstance(v, str):
            try:
                return DataType(v)
            except ValueError:
                # 如果不是预定义的类型，返回原值（兼容自定义类型）
                return v
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }


class DataResponse(BaseModel):
    """数据响应模型 - Pydantic版本"""
    request: DataRequest
    data: Any                                # 灵活的数据格式
    data_points: Optional[List[DataPoint]] = None  # 结构化数据点
    metadata: Dict[str, Any] = {}
    timestamp: datetime = field(default_factory=datetime.utcnow)
    errors: List[str] = []
    warnings: List[str] = []
    success: bool = True
    
    @field_validator('success')
    @classmethod
    def check_success(cls, v, info=None):
        """根据错误列表自动设置成功状态"""
        if info and info.data and 'errors' in info.data and info.data['errors']:
            return False
        return v
    
    def to_dataframe(self):
        """转换为DataFrame（如果可能）"""
        try:
            import pandas as pd
            if self.data_points:
                data = [{"timestamp": dp.timestamp, **dp.value} 
                       if isinstance(dp.value, dict) else 
                       {"timestamp": dp.timestamp, "value": dp.value}
                       for dp in self.data_points]
                return pd.DataFrame(data)
            elif isinstance(self.data, list):
                return pd.DataFrame(self.data)
            elif isinstance(self.data, dict):
                return pd.DataFrame([self.data])
        except Exception:
            pass
        return None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            DataPoint: lambda v: v.to_dict()
        }


class DataValidationError(Exception):
    """数据验证错误"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)