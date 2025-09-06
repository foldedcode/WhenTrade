"""
统一数据适配器系统

整合旧的 adapter_registry 和新的 data_source_registry 系统
保留最佳功能，提供统一接口
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Type, Set, Union
from datetime import datetime, date
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# 导入旧系统的类型定义 - 注释掉因为已经删除
# from core.data_adapter import DataAdapter as OldDataAdapter, DataSourceType, DataFormat
# from core.adapter_registry import AdapterRegistry as OldAdapterRegistry

# 临时定义，避免报错
class OldDataAdapter:
    pass

class OldAdapterRegistry:
    pass

class DataSourceType:
    pass

class DataFormat:
    pass

# 导入新系统的类型定义
from core.adapters.base import (
    IDataAdapter, BaseDataAdapter, DataSourceInfo, 
    DataType, DataFrequency, DataRequest, DataResponse, DataPoint
)

# 临时注释掉，因为文件不存在
# from core.data_source_registry import DataSourceRegistry, DataSourceRegistration
class DataSourceRegistry:
    pass

class DataSourceRegistration:
    pass

logger = logging.getLogger(__name__)


@dataclass
class UnifiedAdapterInfo:
    """统一适配器信息"""
    adapter_id: str
    name: str
    description: str
    version: str = "1.0.0"
    adapter_type: str = "unified"  # unified, legacy, new
    source_type: str = "api"
    data_types: List[str] = field(default_factory=list)
    markets: List[str] = field(default_factory=list)
    frequencies: List[str] = field(default_factory=list)
    requires_auth: bool = False
    supported_formats: List[str] = field(default_factory=list)
    priority: int = 0
    enabled: bool = True
    initialized: bool = False
    usage_count: int = 0
    error_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdapterWrapper:
    """适配器包装器，统一新旧适配器接口"""
    
    def __init__(self, adapter: Union[OldDataAdapter, IDataAdapter], adapter_type: str):
        self.adapter = adapter
        self.adapter_type = adapter_type  # "legacy" or "new"
        self.adapter_id = getattr(adapter, 'adapter_id', getattr(adapter, 'id', 'unknown'))
    
    async def get_info(self) -> UnifiedAdapterInfo:
        """获取统一的适配器信息"""
        if self.adapter_type == "legacy":
            # 处理旧系统适配器
            info = self.adapter.get_info()
            return UnifiedAdapterInfo(
                adapter_id=info.get('adapter_id', self.adapter_id),
                name=info.get('name', 'Unknown'),
                description="Legacy adapter",
                adapter_type="legacy",
                source_type=info.get('source_type', 'api'),
                supported_formats=info.get('supported_formats', []),
                enabled=True,
                config=getattr(self.adapter, 'config', {})
            )
        else:
            # 处理新系统适配器
            info = await self.adapter.get_info()
            return UnifiedAdapterInfo(
                adapter_id=getattr(self.adapter, 'id', self.adapter_id),
                name=info.name,
                description=info.description,
                adapter_type="new",
                source_type="api",
                data_types=[dt.value for dt in info.data_types],
                markets=info.markets,
                frequencies=[f.value for f in info.frequencies],
                requires_auth=info.requires_auth,
                enabled=True
            )
    
    async def fetch_data(self, request: Union[DataRequest, Dict[str, Any]]) -> Union[DataResponse, Dict[str, Any]]:
        """统一的数据获取接口"""
        if self.adapter_type == "legacy":
            # 转换新请求格式到旧格式
            if isinstance(request, DataRequest):
                target = request.symbols[0] if request.symbols else ""
                params = {
                    "symbols": request.symbols,
                    "start_date": request.start_date.isoformat() if request.start_date else None,
                    "end_date": request.end_date.isoformat() if request.end_date else None,
                    **request.extra_params
                }
            else:
                target = request.get("target", "")
                params = request.get("params", {})
            
            return await self.adapter.fetch_data(target, params)
        else:
            # 新系统适配器
            if isinstance(request, dict):
                # 转换旧请求格式到新格式
                data_request = DataRequest(
                    symbols=request.get("symbols", []),
                    data_type=DataType.MARKET,  # 默认类型
                    start_date=date.fromisoformat(request["start_date"]) if request.get("start_date") else None,
                    end_date=date.fromisoformat(request["end_date"]) if request.get("end_date") else None,
                    extra_params=request.get("params", {})
                )
                return await self.adapter.fetch_data(data_request)
            else:
                return await self.adapter.fetch_data(request)
    
    async def validate_request(self, request: Union[DataRequest, Dict[str, Any]]) -> List[str]:
        """验证请求"""
        if self.adapter_type == "new" and hasattr(self.adapter, 'validate_request'):
            if isinstance(request, dict):
                # 转换为 DataRequest
                data_request = DataRequest(
                    symbols=request.get("symbols", []),
                    data_type=DataType.MARKET,
                    extra_params=request.get("params", {})
                )
                return await self.adapter.validate_request(data_request)
            else:
                return await self.adapter.validate_request(request)
        return []  # 旧系统不支持验证
    
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """认证"""
        if self.adapter_type == "new" and hasattr(self.adapter, 'authenticate'):
            return await self.adapter.authenticate(credentials)
        elif self.adapter_type == "legacy" and hasattr(self.adapter, 'connect'):
            return await self.adapter.connect(credentials)
        return True


class UnifiedAdapterRegistry:
    """统一适配器注册表"""
    
    def __init__(self):
        # 存储统一的适配器包装器
        self.adapters: Dict[str, AdapterWrapper] = {}
        self.adapter_info: Dict[str, UnifiedAdapterInfo] = {}
        
        # 索引
        self.by_data_type: Dict[str, Set[str]] = {}
        self.by_market: Dict[str, Set[str]] = {}
        self.by_source_type: Dict[str, Set[str]] = {}
        
        # 兼容性：保持对旧注册表的引用
        self.legacy_registry: Optional[OldAdapterRegistry] = None
        self.new_registry: Optional[DataSourceRegistry] = None
        
        # 初始化锁
        self._lock = asyncio.Lock()
    
    async def initialize_with_legacy(self, legacy_registry: OldAdapterRegistry):
        """使用旧注册表初始化"""
        self.legacy_registry = legacy_registry
        
        # 迁移旧适配器
        legacy_adapters = legacy_registry.list_adapters()
        for adapter_info in legacy_adapters:
            adapter_id = adapter_info["id"]
            legacy_adapter = legacy_registry.get_adapter(adapter_id)
            if legacy_adapter:
                wrapped_adapter = AdapterWrapper(legacy_adapter, "legacy")
                await self.register_wrapper(adapter_id, wrapped_adapter)
    
    async def initialize_with_new(self, new_registry: DataSourceRegistry):
        """使用新注册表初始化"""
        self.new_registry = new_registry
        
        # 迁移新适配器
        for adapter_id, registration in new_registry.registrations.items():
            if registration.adapter_instance:
                wrapped_adapter = AdapterWrapper(registration.adapter_instance, "new")
                await self.register_wrapper(adapter_id, wrapped_adapter)
    
    async def register_wrapper(self, adapter_id: str, wrapper: AdapterWrapper):
        """注册适配器包装器"""
        async with self._lock:
            self.adapters[adapter_id] = wrapper
            
            # 获取并缓存适配器信息
            info = await wrapper.get_info()
            self.adapter_info[adapter_id] = info
            
            # 更新索引
            await self._update_indexes(adapter_id, info)
            
            logger.info(f"Registered unified adapter: {adapter_id}")
    
    async def register_legacy_adapter(self, adapter_id: str, adapter: OldDataAdapter):
        """注册旧系统适配器"""
        wrapper = AdapterWrapper(adapter, "legacy")
        await self.register_wrapper(adapter_id, wrapper)
    
    async def register_new_adapter(self, adapter_id: str, adapter: IDataAdapter):
        """注册新系统适配器"""
        wrapper = AdapterWrapper(adapter, "new")
        await self.register_wrapper(adapter_id, wrapper)
    
    async def get_adapter(self, adapter_id: str) -> Optional[AdapterWrapper]:
        """获取适配器包装器"""
        return self.adapters.get(adapter_id)
    
    async def list_adapters(self) -> List[UnifiedAdapterInfo]:
        """列出所有适配器信息"""
        return list(self.adapter_info.values())
    
    async def find_adapters(self, 
                           data_type: Optional[str] = None,
                           market: Optional[str] = None,
                           source_type: Optional[str] = None,
                           enabled_only: bool = True) -> List[str]:
        """查找符合条件的适配器"""
        candidates = set(self.adapters.keys())
        
        # 按数据类型过滤
        if data_type and data_type in self.by_data_type:
            candidates &= self.by_data_type[data_type]
        
        # 按市场过滤
        if market and market in self.by_market:
            candidates &= self.by_market[market]
        
        # 按源类型过滤
        if source_type and source_type in self.by_source_type:
            candidates &= self.by_source_type[source_type]
        
        # 过滤启用状态
        if enabled_only:
            candidates = {
                aid for aid in candidates
                if self.adapter_info[aid].enabled
            }
        
        # 按优先级排序
        sorted_adapters = sorted(
            candidates,
            key=lambda x: (
                -self.adapter_info[x].priority,
                self.adapter_info[x].error_count
            )
        )
        
        return sorted_adapters
    
    async def get_best_adapter(self, 
                              request: Union[DataRequest, Dict[str, Any]]) -> Optional[AdapterWrapper]:
        """获取最适合的适配器"""
        # 确定搜索条件
        if isinstance(request, DataRequest):
            data_type = request.data_type.value if request.data_type else None
        else:
            data_type = request.get("data_type")
        
        # 查找适配器
        adapter_ids = await self.find_adapters(data_type=data_type)
        
        # 验证并选择最佳适配器
        for adapter_id in adapter_ids:
            wrapper = await self.get_adapter(adapter_id)
            if not wrapper:
                continue
            
            # 验证请求
            try:
                errors = await wrapper.validate_request(request)
                if not errors:
                    return wrapper
            except Exception as e:
                logger.warning(f"Adapter {adapter_id} validation failed: {e}")
                continue
        
        return None
    
    async def fetch_data(self, 
                        request: Union[DataRequest, Dict[str, Any]],
                        adapter_id: Optional[str] = None) -> Union[DataResponse, Dict[str, Any]]:
        """统一数据获取接口"""
        try:
            # 获取适配器
            if adapter_id:
                wrapper = await self.get_adapter(adapter_id)
                if not wrapper:
                    raise ValueError(f"Adapter {adapter_id} not found")
            else:
                wrapper = await self.get_best_adapter(request)
                if not wrapper:
                    raise ValueError("No suitable adapter found")
            
            # 获取数据
            result = await wrapper.fetch_data(request)
            
            # 更新统计
            if adapter_id and adapter_id in self.adapter_info:
                self.adapter_info[adapter_id].usage_count += 1
            
            return result
            
        except Exception as e:
            # 更新错误统计
            if adapter_id and adapter_id in self.adapter_info:
                self.adapter_info[adapter_id].error_count += 1
            
            logger.error(f"Failed to fetch data: {e}")
            raise
    
    async def _update_indexes(self, adapter_id: str, info: UnifiedAdapterInfo):
        """更新索引"""
        # 数据类型索引
        for data_type in info.data_types:
            if data_type not in self.by_data_type:
                self.by_data_type[data_type] = set()
            self.by_data_type[data_type].add(adapter_id)
        
        # 市场索引
        for market in info.markets:
            if market not in self.by_market:
                self.by_market[market] = set()
            self.by_market[market].add(adapter_id)
        
        # 源类型索引
        if info.source_type not in self.by_source_type:
            self.by_source_type[info.source_type] = set()
        self.by_source_type[info.source_type].add(adapter_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_adapters = len(self.adapter_info)
        enabled_adapters = sum(1 for info in self.adapter_info.values() if info.enabled)
        legacy_adapters = sum(1 for info in self.adapter_info.values() if info.adapter_type == "legacy")
        new_adapters = sum(1 for info in self.adapter_info.values() if info.adapter_type == "new")
        
        total_usage = sum(info.usage_count for info in self.adapter_info.values())
        total_errors = sum(info.error_count for info in self.adapter_info.values())
        
        return {
            "total_adapters": total_adapters,
            "enabled_adapters": enabled_adapters,
            "legacy_adapters": legacy_adapters,
            "new_adapters": new_adapters,
            "total_usage_count": total_usage,
            "total_error_count": total_errors,
            "adapters_by_data_type": {
                dt: len(adapters) 
                for dt, adapters in self.by_data_type.items()
            },
            "adapters_by_market": {
                market: len(adapters) 
                for market, adapters in self.by_market.items()
            },
            "adapters_by_source_type": {
                st: len(adapters)
                for st, adapters in self.by_source_type.items()
            }
        }


# 全局统一注册表实例
global_unified_registry = UnifiedAdapterRegistry()


# 便捷函数
async def initialize_unified_system():
    """初始化统一适配器系统"""
    # TODO: 需要创建或修复 adapter_registry 和 data_source_registry
    # 临时跳过初始化，避免导入错误
    logger.warning("统一适配器系统初始化被跳过 - 需要修复缺失的依赖")
    
    # from core.adapter_registry import adapter_registry
    # from core.data_source_registry import global_data_source_registry
    
    # # 初始化旧系统
    # await global_unified_registry.initialize_with_legacy(adapter_registry)
    
    # # 初始化新系统
    # await global_unified_registry.initialize_with_new(global_data_source_registry)
    
    # logger.info("Unified adapter system initialized")


async def get_unified_adapter(adapter_id: str) -> Optional[AdapterWrapper]:
    """获取统一适配器的便捷函数"""
    return await global_unified_registry.get_adapter(adapter_id)


async def fetch_unified_data(request: Union[DataRequest, Dict[str, Any]], 
                           adapter_id: Optional[str] = None) -> Union[DataResponse, Dict[str, Any]]:
    """统一数据获取的便捷函数"""
    return await global_unified_registry.fetch_data(request, adapter_id)