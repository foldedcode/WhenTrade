"""
插件基础类和接口定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import logging
import asyncio

logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    """插件状态"""
    UNLOADED = "unloaded"      # 未加载
    LOADING = "loading"        # 加载中
    LOADED = "loaded"          # 已加载
    ACTIVE = "active"          # 已激活
    ERROR = "error"            # 错误状态
    DISABLED = "disabled"      # 已禁用


class PluginCapability(str, Enum):
    """插件能力类型"""
    DATA_SOURCE = "data_source"        # 数据源
    ANALYSIS = "analysis"              # 分析功能
    VISUALIZATION = "visualization"    # 可视化
    EXPORT = "export"                  # 导出功能
    NOTIFICATION = "notification"      # 通知功能
    INTEGRATION = "integration"        # 第三方集成
    CUSTOM = "custom"                  # 自定义功能


@dataclass
class PluginInfo:
    """插件信息"""
    id: str                           # 唯一标识
    name: str                         # 名称
    version: str                      # 版本
    description: str                  # 描述
    author: str                       # 作者
    capabilities: List[PluginCapability]  # 能力列表
    dependencies: List[str] = field(default_factory=list)  # 依赖
    config_schema: Dict[str, Any] = field(default_factory=dict)  # 配置模式
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def __post_init__(self):
        """验证插件信息"""
        if not self.id:
            raise ValueError("Plugin ID is required")
        if not self.name:
            raise ValueError("Plugin name is required")
        if not self.version:
            raise ValueError("Plugin version is required")


@dataclass
class PluginContext:
    """插件运行上下文"""
    plugin_id: str                    # 插件ID
    config: Dict[str, Any]            # 配置
    data_adapters: Dict[str, Any]     # 可用的数据适配器
    services: Dict[str, Any]          # 可用的服务
    logger: logging.Logger            # 日志记录器
    
    def get_service(self, service_name: str) -> Any:
        """获取服务"""
        return self.services.get(service_name)
    
    def get_adapter(self, adapter_id: str) -> Any:
        """获取数据适配器"""
        return self.data_adapters.get(adapter_id)


class PluginBase(ABC):
    """插件基类"""
    
    def __init__(self):
        self._status = PluginStatus.UNLOADED
        self._context: Optional[PluginContext] = None
        self._config: Dict[str, Any] = {}
        self._info: Optional[PluginInfo] = None
        
    @property
    def status(self) -> PluginStatus:
        """获取插件状态"""
        return self._status
    
    @property
    def info(self) -> Optional[PluginInfo]:
        """获取插件信息"""
        if not self._info:
            self._info = self.get_plugin_info()
        return self._info
    
    @property
    def context(self) -> Optional[PluginContext]:
        """获取插件上下文"""
        return self._context
    
    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（子类必须实现）"""
        pass
    
    async def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        try:
            self._status = PluginStatus.LOADING
            self._context = context
            self._config = context.config
            
            # 验证配置
            if not self.validate_config(self._config):
                raise ValueError("Invalid plugin configuration")
            
            # 执行初始化
            success = await self.on_initialize()
            
            if success:
                self._status = PluginStatus.LOADED
                logger.info(f"Plugin {self.info.id} initialized successfully")
            else:
                self._status = PluginStatus.ERROR
                logger.error(f"Plugin {self.info.id} initialization failed")
                
            return success
            
        except Exception as e:
            logger.error(f"Plugin {self.info.id} initialization error: {e}")
            self._status = PluginStatus.ERROR
            return False
    
    async def activate(self) -> bool:
        """激活插件"""
        if self._status != PluginStatus.LOADED:
            logger.error(f"Cannot activate plugin {self.info.id} in status {self._status}")
            return False
        
        try:
            success = await self.on_activate()
            if success:
                self._status = PluginStatus.ACTIVE
                logger.info(f"Plugin {self.info.id} activated")
            return success
        except Exception as e:
            logger.error(f"Plugin {self.info.id} activation error: {e}")
            return False
    
    async def deactivate(self) -> bool:
        """停用插件"""
        if self._status != PluginStatus.ACTIVE:
            return True
        
        try:
            success = await self.on_deactivate()
            if success:
                self._status = PluginStatus.LOADED
                logger.info(f"Plugin {self.info.id} deactivated")
            return success
        except Exception as e:
            logger.error(f"Plugin {self.info.id} deactivation error: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """清理插件"""
        try:
            # 先停用
            if self._status == PluginStatus.ACTIVE:
                await self.deactivate()
            
            # 执行清理
            success = await self.on_cleanup()
            
            if success:
                self._status = PluginStatus.UNLOADED
                self._context = None
                self._config = {}
                logger.info(f"Plugin {self.info.id} cleaned up")
                
            return success
        except Exception as e:
            logger.error(f"Plugin {self.info.id} cleanup error: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        # 基础验证，子类可以覆盖
        schema = self.info.config_schema
        if not schema:
            return True
        
        # 检查必需字段
        for key, spec in schema.items():
            if spec.get("required", False) and key not in config:
                logger.error(f"Missing required config field: {key}")
                return False
                
            # 类型检查
            if key in config and "type" in spec:
                expected_type = spec["type"]
                actual_type = type(config[key]).__name__
                if expected_type != actual_type:
                    logger.error(f"Config field {key} type mismatch: expected {expected_type}, got {actual_type}")
                    return False
        
        return True
    
    # 生命周期钩子（子类可以覆盖）
    async def on_initialize(self) -> bool:
        """初始化时调用"""
        return True
    
    async def on_activate(self) -> bool:
        """激活时调用"""
        return True
    
    async def on_deactivate(self) -> bool:
        """停用时调用"""
        return True
    
    async def on_cleanup(self) -> bool:
        """清理时调用"""
        return True
    
    # 插件能力接口（子类根据需要实现）
    async def execute(self, *args, **kwargs) -> Any:
        """执行插件主要功能"""
        raise NotImplementedError(f"Plugin {self.info.id} does not implement execute method")
    
    async def get_data(self, request: Dict[str, Any]) -> Any:
        """获取数据（数据源插件）"""
        raise NotImplementedError(f"Plugin {self.info.id} does not implement get_data method")
    
    async def analyze(self, data: Any) -> Any:
        """分析数据（分析插件）"""
        raise NotImplementedError(f"Plugin {self.info.id} does not implement analyze method")
    
    async def visualize(self, data: Any) -> Any:
        """可视化数据（可视化插件）"""
        raise NotImplementedError(f"Plugin {self.info.id} does not implement visualize method")
    
    async def export(self, data: Any, format: str) -> Any:
        """导出数据（导出插件）"""
        raise NotImplementedError(f"Plugin {self.info.id} does not implement export method")


class DataSourcePlugin(PluginBase):
    """数据源插件基类"""
    
    def get_plugin_info(self) -> PluginInfo:
        """默认信息，子类应该覆盖"""
        return PluginInfo(
            id="base_data_source",
            name="Base Data Source Plugin",
            version="1.0.0",
            description="Base class for data source plugins",
            author="When.Trade",
            capabilities=[PluginCapability.DATA_SOURCE]
        )
    
    @abstractmethod
    async def get_data(self, request: Dict[str, Any]) -> Any:
        """获取数据"""
        pass


class AnalysisPlugin(PluginBase):
    """分析插件基类"""
    
    def get_plugin_info(self) -> PluginInfo:
        """默认信息，子类应该覆盖"""
        return PluginInfo(
            id="base_analysis",
            name="Base Analysis Plugin",
            version="1.0.0",
            description="Base class for analysis plugins",
            author="When.Trade",
            capabilities=[PluginCapability.ANALYSIS]
        )
    
    @abstractmethod
    async def analyze(self, data: Any) -> Any:
        """分析数据"""
        pass


# 插件装饰器
def plugin(info: PluginInfo):
    """插件装饰器，用于注册插件信息"""
    def decorator(cls):
        # 添加get_plugin_info方法
        def get_plugin_info(self):
            return info
        
        cls.get_plugin_info = get_plugin_info
        # 添加插件信息作为类属性
        cls.plugin_info = info
        return cls
    
    return decorator