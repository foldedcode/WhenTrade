"""
数据适配器基础接口和类

提供统一的数据接入框架，支持多种数据源的插件式集成。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, AsyncIterator
from datetime import datetime, date
from enum import Enum
import asyncio
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class DataType(str, Enum):
    """数据类型枚举"""
    MARKET = "market"          # 市场数据（价格、成交量等）
    FUNDAMENTAL = "fundamental" # 基本面数据（财务报表等）
    NEWS = "news"              # 新闻数据
    SOCIAL = "social"          # 社交媒体数据
    ONCHAIN = "onchain"        # 链上数据
    ALTERNATIVE = "alternative" # 另类数据
    CUSTOM = "custom"          # 自定义数据


class DataFrequency(str, Enum):
    """数据频率枚举"""
    REALTIME = "realtime"  # 实时数据
    MINUTE = "1m"          # 分钟级
    MINUTE_5 = "5m"        # 5分钟级
    MINUTE_15 = "15m"      # 15分钟级
    MINUTE_30 = "30m"      # 30分钟级
    HOURLY = "1h"          # 小时级
    DAILY = "1d"           # 日级
    WEEKLY = "1w"          # 周级
    MONTHLY = "1M"         # 月级
    QUARTERLY = "1Q"       # 季度级
    YEARLY = "1Y"          # 年度级


@dataclass
class DataSourceInfo:
    """数据源信息"""
    id: str                        # 唯一标识
    name: str                      # 名称
    description: str               # 描述
    provider: str                  # 提供商
    version: str                   # 版本
    data_types: List[DataType]     # 支持的数据类型
    frequencies: List[DataFrequency] # 支持的数据频率
    markets: List[str]             # 支持的市场（如：US、CN、CRYPTO等）
    requires_auth: bool = False    # 是否需要认证
    rate_limits: Dict[str, int] = field(default_factory=dict)  # API限制
    metadata: Dict[str, Any] = field(default_factory=dict)      # 其他元数据


@dataclass
class DataRequest:
    """数据请求参数"""
    symbols: List[str]             # 标的列表
    data_type: DataType            # 数据类型
    start_date: Optional[date] = None    # 开始日期
    end_date: Optional[date] = None      # 结束日期
    frequency: Optional[DataFrequency] = None  # 数据频率
    fields: Optional[List[str]] = None   # 指定字段
    filters: Optional[Dict[str, Any]] = None  # 过滤条件
    options: Dict[str, Any] = field(default_factory=dict)  # 其他选项


@dataclass
class DataPoint:
    """单个数据点"""
    symbol: str                    # 标的
    timestamp: datetime            # 时间戳
    data: Dict[str, Any]          # 数据内容
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class DataResponse:
    """数据响应"""
    request: DataRequest           # 原始请求
    data_points: List[DataPoint]   # 数据点列表
    errors: List[str] = field(default_factory=list)  # 错误信息
    warnings: List[str] = field(default_factory=list)  # 警告信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 响应元数据
    
    @property
    def success(self) -> bool:
        """是否成功"""
        return len(self.errors) == 0
    
    @property
    def count(self) -> int:
        """数据点数量"""
        return len(self.data_points)


class DataQuality(BaseModel):
    """数据质量指标"""
    completeness: float = Field(ge=0, le=1)  # 完整性（0-1）
    accuracy: float = Field(ge=0, le=1)      # 准确性（0-1）
    timeliness: float = Field(ge=0, le=1)    # 时效性（0-1）
    consistency: float = Field(ge=0, le=1)    # 一致性（0-1）
    
    @property
    def overall_score(self) -> float:
        """综合质量分数"""
        return (self.completeness + self.accuracy + 
                self.timeliness + self.consistency) / 4


class IDataAdapter(ABC):
    """数据适配器接口"""
    
    @abstractmethod
    async def get_info(self) -> DataSourceInfo:
        """获取数据源信息"""
        pass
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """认证（如果需要）"""
        pass
    
    @abstractmethod
    async def fetch_data(self, request: DataRequest) -> DataResponse:
        """获取数据"""
        pass
    
    @abstractmethod
    async def validate_request(self, request: DataRequest) -> List[str]:
        """验证请求参数，返回错误列表"""
        pass
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            info = await self.get_info()
            return info is not None
        except Exception:
            return False
    
    async def get_available_symbols(self, market: Optional[str] = None) -> List[str]:
        """获取可用标的列表"""
        return []
    
    async def get_data_quality(self, 
                               symbol: str, 
                               data_type: DataType) -> Optional[DataQuality]:
        """获取数据质量指标"""
        return None
    
    async def batch_fetch(self, requests: List[DataRequest]) -> List[DataResponse]:
        """批量获取数据（默认串行执行）"""
        responses = []
        for request in requests:
            response = await self.fetch_data(request)
            responses.append(response)
        return responses
    
    async def stream_data(self, request: DataRequest) -> AsyncIterator[DataPoint]:
        """流式数据接口（用于实时数据）"""
        raise NotImplementedError("This adapter does not support streaming")


class BaseDataAdapter(IDataAdapter):
    """数据适配器基类，提供通用功能"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._authenticated = False
        self._rate_limiter = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def validate_request(self, request: DataRequest) -> List[str]:
        """基础请求验证"""
        errors = []
        
        # 验证标的列表
        if not request.symbols:
            errors.append("No symbols provided")
        
        # 验证日期范围
        if request.start_date and request.end_date:
            if request.start_date > request.end_date:
                errors.append("Start date must be before end date")
        
        # 验证数据类型
        info = await self.get_info()
        if request.data_type not in info.data_types:
            errors.append(f"Data type {request.data_type} not supported")
        
        # 验证频率
        if request.frequency and request.frequency not in info.frequencies:
            errors.append(f"Frequency {request.frequency} not supported")
        
        return errors
    
    async def _apply_rate_limit(self):
        """应用速率限制"""
        if self._rate_limiter:
            await self._rate_limiter.acquire()
    
    def _standardize_data(self, raw_data: Any) -> Dict[str, Any]:
        """标准化数据格式（子类可重写）"""
        return raw_data if isinstance(raw_data, dict) else {"value": raw_data}
    
    def _create_data_point(self, 
                          symbol: str, 
                          timestamp: datetime, 
                          data: Any) -> DataPoint:
        """创建标准数据点"""
        return DataPoint(
            symbol=symbol,
            timestamp=timestamp,
            data=self._standardize_data(data)
        )
    
    async def batch_fetch(self, requests: List[DataRequest]) -> List[DataResponse]:
        """批量获取数据（并发执行）"""
        tasks = [self.fetch_data(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常情况
        result = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                # 创建错误响应
                error_response = DataResponse(
                    request=requests[i],
                    data_points=[],
                    errors=[str(response)]
                )
                result.append(error_response)
            else:
                result.append(response)
        
        return result


class CompositeDataAdapter(IDataAdapter):
    """组合数据适配器，可以聚合多个数据源"""
    
    def __init__(self, adapters: List[IDataAdapter], strategy: str = "first"):
        """
        初始化组合适配器
        
        Args:
            adapters: 子适配器列表
            strategy: 数据获取策略
                - "first": 使用第一个可用的适配器
                - "merge": 合并所有适配器的数据
                - "fallback": 失败时尝试下一个
        """
        self.adapters = adapters
        self.strategy = strategy
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def get_info(self) -> DataSourceInfo:
        """聚合所有适配器信息"""
        all_data_types = set()
        all_frequencies = set()
        all_markets = set()
        requires_auth = False
        
        for adapter in self.adapters:
            try:
                info = await adapter.get_info()
                all_data_types.update(info.data_types)
                all_frequencies.update(info.frequencies)
                all_markets.update(info.markets)
                requires_auth = requires_auth or info.requires_auth
            except Exception as e:
                self.logger.error(f"Failed to get info from adapter: {e}")
        
        return DataSourceInfo(
            id="composite",
            name="Composite Data Source",
            description="Aggregates multiple data sources",
            provider="When.Trade",
            version="1.0.0",
            data_types=list(all_data_types),
            frequencies=list(all_frequencies),
            markets=list(all_markets),
            requires_auth=requires_auth
        )
    
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """认证所有需要认证的适配器"""
        results = await asyncio.gather(
            *[adapter.authenticate(credentials) for adapter in self.adapters],
            return_exceptions=True
        )
        
        # 检查所有非异常结果
        success_count = sum(1 for r in results if r is True)
        return success_count > 0
    
    async def fetch_data(self, request: DataRequest) -> DataResponse:
        """根据策略从适配器获取数据"""
        if self.strategy == "first":
            return await self._fetch_first_available(request)
        elif self.strategy == "merge":
            return await self._fetch_and_merge(request)
        elif self.strategy == "fallback":
            return await self._fetch_with_fallback(request)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
    
    async def _fetch_first_available(self, request: DataRequest) -> DataResponse:
        """使用第一个可用的适配器"""
        for adapter in self.adapters:
            errors = await adapter.validate_request(request)
            if not errors:
                try:
                    return await adapter.fetch_data(request)
                except Exception as e:
                    self.logger.error(f"Adapter failed: {e}")
                    continue
        
        return DataResponse(
            request=request,
            data_points=[],
            errors=["No adapter available for this request"]
        )
    
    async def _fetch_and_merge(self, request: DataRequest) -> DataResponse:
        """合并所有适配器的数据"""
        all_data_points = []
        all_errors = []
        all_warnings = []
        
        # 并发获取所有数据
        tasks = []
        valid_adapters = []
        
        for adapter in self.adapters:
            errors = await adapter.validate_request(request)
            if not errors:
                tasks.append(adapter.fetch_data(request))
                valid_adapters.append(adapter)
        
        if not tasks:
            return DataResponse(
                request=request,
                data_points=[],
                errors=["No adapter can handle this request"]
            )
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                all_errors.append(f"Adapter {i} failed: {str(response)}")
            else:
                all_data_points.extend(response.data_points)
                all_errors.extend(response.errors)
                all_warnings.extend(response.warnings)
        
        # 去重（基于symbol和timestamp）
        unique_points = {}
        for point in all_data_points:
            key = (point.symbol, point.timestamp)
            if key not in unique_points:
                unique_points[key] = point
        
        return DataResponse(
            request=request,
            data_points=list(unique_points.values()),
            errors=all_errors,
            warnings=all_warnings
        )
    
    async def _fetch_with_fallback(self, request: DataRequest) -> DataResponse:
        """失败时尝试下一个适配器"""
        for adapter in self.adapters:
            errors = await adapter.validate_request(request)
            if errors:
                continue
                
            try:
                response = await adapter.fetch_data(request)
                if response.success:
                    return response
            except Exception as e:
                self.logger.error(f"Adapter failed, trying next: {e}")
                continue
        
        return DataResponse(
            request=request,
            data_points=[],
            errors=["All adapters failed"]
        )
    
    async def validate_request(self, request: DataRequest) -> List[str]:
        """验证是否有适配器可以处理此请求"""
        for adapter in self.adapters:
            errors = await adapter.validate_request(request)
            if not errors:
                return []
        return ["No adapter can handle this request"]