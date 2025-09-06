"""
插件注册表

全局插件注册和发现机制
"""

from typing import Dict, List, Any, Optional, Type
import logging
from datetime import datetime

from .plugin_base import PluginBase, PluginInfo, PluginCapability
from .plugin_manager import PluginManager

logger = logging.getLogger(__name__)


class PluginRegistry:
    """全局插件注册表"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.plugin_manager = PluginManager()
        self.registered_plugins: Dict[str, PluginInfo] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
        
    @classmethod
    def get_instance(cls) -> 'PluginRegistry':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_plugin_class(self, 
                             plugin_class: Type[PluginBase],
                             metadata: Optional[Dict[str, Any]] = None) -> bool:
        """注册插件类"""
        try:
            # 获取插件信息
            if hasattr(plugin_class, 'plugin_info'):
                info = plugin_class.plugin_info
            else:
                temp_instance = plugin_class()
                info = temp_instance.info
            
            if not info:
                logger.error(f"Cannot get plugin info for {plugin_class.__name__}")
                return False
            
            # 注册到管理器
            self.plugin_manager.plugin_classes[info.id] = plugin_class
            self.registered_plugins[info.id] = info
            
            # 保存元数据
            if metadata:
                self.plugin_metadata[info.id] = {
                    **metadata,
                    "registered_at": datetime.now().isoformat()
                }
            
            logger.info(f"Registered plugin: {info.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register plugin class: {e}")
            return False
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """注销插件"""
        if plugin_id in self.registered_plugins:
            del self.registered_plugins[plugin_id]
            
        if plugin_id in self.plugin_metadata:
            del self.plugin_metadata[plugin_id]
            
        if plugin_id in self.plugin_manager.plugin_classes:
            del self.plugin_manager.plugin_classes[plugin_id]
            
        logger.info(f"Unregistered plugin: {plugin_id}")
        return True
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.registered_plugins.get(plugin_id)
    
    def list_all_plugins(self) -> List[Dict[str, Any]]:
        """列出所有已注册的插件"""
        plugins = []
        
        for plugin_id, info in self.registered_plugins.items():
            plugin_data = {
                "id": plugin_id,
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "capabilities": [cap.value for cap in info.capabilities],
                "dependencies": info.dependencies
            }
            
            # 添加元数据
            if plugin_id in self.plugin_metadata:
                plugin_data["metadata"] = self.plugin_metadata[plugin_id]
            
            # 检查安装状态
            if plugin_id in self.plugin_manager.plugins:
                plugin = self.plugin_manager.plugins[plugin_id]
                plugin_data["status"] = plugin.status.value
                plugin_data["installed"] = True
            else:
                plugin_data["status"] = "unloaded"
                plugin_data["installed"] = False
            
            plugins.append(plugin_data)
        
        return plugins
    
    def find_plugins_by_capability(self, capability: PluginCapability) -> List[str]:
        """根据能力查找插件"""
        matching_plugins = []
        
        for plugin_id, info in self.registered_plugins.items():
            if capability in info.capabilities:
                matching_plugins.append(plugin_id)
        
        return matching_plugins
    
    def search_plugins(self, 
                      keyword: Optional[str] = None,
                      author: Optional[str] = None,
                      capability: Optional[PluginCapability] = None) -> List[Dict[str, Any]]:
        """搜索插件"""
        results = []
        
        for plugin_id, info in self.registered_plugins.items():
            # 关键词匹配
            if keyword:
                keyword_lower = keyword.lower()
                if (keyword_lower not in info.name.lower() and 
                    keyword_lower not in info.description.lower()):
                    continue
            
            # 作者匹配
            if author and info.author != author:
                continue
            
            # 能力匹配
            if capability and capability not in info.capabilities:
                continue
            
            # 添加到结果
            results.append({
                "id": plugin_id,
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "capabilities": [cap.value for cap in info.capabilities]
            })
        
        return results
    
    async def install_plugin(self, plugin_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """安装插件"""
        return await self.plugin_manager.install_plugin(plugin_id, config)
    
    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        return await self.plugin_manager.uninstall_plugin(plugin_id)
    
    async def activate_plugin(self, plugin_id: str) -> bool:
        """激活插件"""
        return await self.plugin_manager.activate_plugin(plugin_id)
    
    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """停用插件"""
        return await self.plugin_manager.deactivate_plugin(plugin_id)
    
    def get_plugin_instance(self, plugin_id: str) -> Optional[PluginBase]:
        """获取插件实例"""
        return self.plugin_manager.get_plugin(plugin_id)
    
    async def execute_plugin(self, plugin_id: str, method: str, *args, **kwargs) -> Any:
        """执行插件方法"""
        return await self.plugin_manager.execute_plugin(plugin_id, method, *args, **kwargs)
    
    def get_plugin_config_schema(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """获取插件配置模式"""
        info = self.registered_plugins.get(plugin_id)
        return info.config_schema if info else None
    
    def validate_plugin_config(self, plugin_id: str, config: Dict[str, Any]) -> List[str]:
        """验证插件配置"""
        errors = []
        schema = self.get_plugin_config_schema(plugin_id)
        
        if not schema:
            return errors
        
        # 检查必需字段
        for field, spec in schema.items():
            if spec.get("required", False) and field not in config:
                errors.append(f"Missing required field: {field}")
            
            # 类型检查
            if field in config and "type" in spec:
                expected_type = spec["type"]
                actual_type = type(config[field]).__name__
                if expected_type != actual_type:
                    errors.append(f"Field {field} type mismatch: expected {expected_type}, got {actual_type}")
        
        return errors


# 全局注册表实例
global_plugin_registry = PluginRegistry.get_instance()


# 便捷函数
def register_plugin(plugin_class: Type[PluginBase], metadata: Optional[Dict[str, Any]] = None) -> bool:
    """注册插件的便捷函数"""
    return global_plugin_registry.register_plugin_class(plugin_class, metadata)


def get_registry() -> PluginRegistry:
    """获取全局注册表"""
    return global_plugin_registry