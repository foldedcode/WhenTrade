"""
插件管理器

负责插件的加载、管理、执行和生命周期控制
"""

import os
import sys
import importlib
import importlib.util
from typing import Dict, List, Any, Optional, Type, Set
from pathlib import Path
import asyncio
import logging
import json
import yaml
from datetime import datetime

from .plugin_base import (
    PluginBase,
    PluginInfo,
    PluginStatus,
    PluginContext,
    PluginCapability
)

logger = logging.getLogger(__name__)


class PluginManager:
    """插件管理器"""
    
    def __init__(self, 
                 plugin_dirs: Optional[List[str]] = None,
                 auto_discover: bool = True):
        """
        初始化插件管理器
        
        Args:
            plugin_dirs: 插件目录列表
            auto_discover: 是否自动发现插件
        """
        self.plugin_dirs = plugin_dirs or ["plugins"]
        self.auto_discover = auto_discover
        
        # 插件存储
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # 服务和适配器注册
        self.services: Dict[str, Any] = {}
        self.data_adapters: Dict[str, Any] = {}
        
        # 插件依赖图
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # 初始化 - 延迟异步发现到需要时
        self._discovered = False
    
    async def ensure_discovered(self):
        """确保插件已被发现"""
        if not self._discovered and self.auto_discover:
            await self.discover_plugins()
            self._discovered = True
    
    async def discover_plugins(self) -> List[str]:
        """发现所有可用的插件"""
        discovered = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue
            
            # 遍历插件目录
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                # 目录形式的插件
                if os.path.isdir(item_path):
                    plugin_file = os.path.join(item_path, "__init__.py")
                    if os.path.exists(plugin_file):
                        plugin_id = await self._load_plugin_module(plugin_file, item)
                        if plugin_id:
                            discovered.append(plugin_id)
                
                # 单文件插件
                elif item.endswith(".py") and not item.startswith("_"):
                    plugin_id = await self._load_plugin_module(
                        item_path, 
                        item[:-3]  # 去掉.py后缀
                    )
                    if plugin_id:
                        discovered.append(plugin_id)
        
        logger.info(f"Discovered {len(discovered)} plugins: {discovered}")
        return discovered
    
    async def _load_plugin_module(self, file_path: str, module_name: str) -> Optional[str]:
        """加载插件模块"""
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return None
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找插件类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase):
                    
                    # 获取插件信息
                    if hasattr(attr, 'plugin_info'):
                        plugin_info = attr.plugin_info
                    else:
                        # 创建临时实例获取信息
                        temp_instance = attr()
                        plugin_info = temp_instance.info
                    
                    if plugin_info:
                        # 注册插件类
                        self.plugin_classes[plugin_info.id] = attr
                        
                        # 加载配置
                        config = await self._load_plugin_config(
                            plugin_info.id, 
                            os.path.dirname(file_path)
                        )
                        self.plugin_configs[plugin_info.id] = config
                        
                        # 构建依赖图
                        self.dependency_graph[plugin_info.id] = set(plugin_info.dependencies)
                        
                        logger.info(f"Loaded plugin class: {plugin_info.id}")
                        return plugin_info.id
            
        except Exception as e:
            logger.error(f"Failed to load plugin module {module_name}: {e}")
            
        return None
    
    async def _load_plugin_config(self, plugin_id: str, plugin_dir: str) -> Dict[str, Any]:
        """加载插件配置"""
        config = {}
        
        # 尝试加载配置文件
        config_files = [
            os.path.join(plugin_dir, "config.json"),
            os.path.join(plugin_dir, "config.yaml"),
            os.path.join(plugin_dir, f"{plugin_id}.json"),
            os.path.join(plugin_dir, f"{plugin_id}.yaml")
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        if config_file.endswith('.json'):
                            config = json.load(f)
                        elif config_file.endswith('.yaml'):
                            config = yaml.safe_load(f)
                    logger.info(f"Loaded config for plugin {plugin_id} from {config_file}")
                    break
                except Exception as e:
                    logger.error(f"Failed to load config file {config_file}: {e}")
        
        return config
    
    async def install_plugin(self, plugin_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """安装并初始化插件"""
        await self.ensure_discovered()
        
        if plugin_id not in self.plugin_classes:
            logger.error(f"Plugin class not found: {plugin_id}")
            return False
        
        if plugin_id in self.plugins:
            logger.warning(f"Plugin already installed: {plugin_id}")
            return True
        
        try:
            # 检查依赖
            if not await self._check_dependencies(plugin_id):
                return False
            
            # 创建插件实例
            plugin_class = self.plugin_classes[plugin_id]
            plugin = plugin_class()
            
            # 合并配置
            final_config = self.plugin_configs.get(plugin_id, {})
            if config:
                final_config.update(config)
            
            # 创建上下文
            context = PluginContext(
                plugin_id=plugin_id,
                config=final_config,
                data_adapters=self.data_adapters,
                services=self.services,
                logger=logging.getLogger(f"plugin.{plugin_id}")
            )
            
            # 初始化插件
            if await plugin.initialize(context):
                self.plugins[plugin_id] = plugin
                logger.info(f"Plugin installed: {plugin_id}")
                return True
            else:
                logger.error(f"Plugin initialization failed: {plugin_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install plugin {plugin_id}: {e}")
            return False
    
    async def _check_dependencies(self, plugin_id: str) -> bool:
        """检查插件依赖"""
        dependencies = self.dependency_graph.get(plugin_id, set())
        
        for dep in dependencies:
            if dep not in self.plugins:
                # 尝试先安装依赖
                logger.info(f"Installing dependency {dep} for plugin {plugin_id}")
                if not await self.install_plugin(dep):
                    logger.error(f"Failed to install dependency {dep} for plugin {plugin_id}")
                    return False
        
        return True
    
    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin not installed: {plugin_id}")
            return True
        
        try:
            # 检查是否有其他插件依赖此插件
            for other_id, deps in self.dependency_graph.items():
                if plugin_id in deps and other_id in self.plugins:
                    logger.error(f"Cannot uninstall {plugin_id}: required by {other_id}")
                    return False
            
            # 清理插件
            plugin = self.plugins[plugin_id]
            if await plugin.cleanup():
                del self.plugins[plugin_id]
                logger.info(f"Plugin uninstalled: {plugin_id}")
                return True
            else:
                logger.error(f"Plugin cleanup failed: {plugin_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to uninstall plugin {plugin_id}: {e}")
            return False
    
    async def activate_plugin(self, plugin_id: str) -> bool:
        """激活插件"""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_id}")
            return False
        
        return await plugin.activate()
    
    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """停用插件"""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_id}")
            return False
        
        return await plugin.deactivate()
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """获取插件实例"""
        return self.plugins.get(plugin_id)
    
    def get_plugins_by_capability(self, capability: PluginCapability) -> List[PluginBase]:
        """根据能力获取插件"""
        result = []
        for plugin in self.plugins.values():
            if plugin.info and capability in plugin.info.capabilities:
                result.append(plugin)
        return result
    
    async def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件"""
        await self.ensure_discovered()
        plugins_info = []
        
        # 已安装的插件
        for plugin_id, plugin in self.plugins.items():
            info = plugin.info
            plugins_info.append({
                "id": plugin_id,
                "name": info.name if info else "Unknown",
                "version": info.version if info else "Unknown",
                "status": plugin.status.value,
                "installed": True,
                "capabilities": [cap.value for cap in info.capabilities] if info else []
            })
        
        # 未安装的插件
        for plugin_id in self.plugin_classes:
            if plugin_id not in self.plugins:
                # 获取插件信息
                plugin_class = self.plugin_classes[plugin_id]
                if hasattr(plugin_class, 'plugin_info'):
                    info = plugin_class.plugin_info
                else:
                    temp = plugin_class()
                    info = temp.info
                
                plugins_info.append({
                    "id": plugin_id,
                    "name": info.name if info else "Unknown",
                    "version": info.version if info else "Unknown",
                    "status": PluginStatus.UNLOADED.value,
                    "installed": False,
                    "capabilities": [cap.value for cap in info.capabilities] if info else []
                })
        
        return plugins_info
    
    def register_service(self, name: str, service: Any):
        """注册服务"""
        self.services[name] = service
        logger.info(f"Registered service: {name}")
    
    def register_data_adapter(self, adapter_id: str, adapter: Any):
        """注册数据适配器"""
        self.data_adapters[adapter_id] = adapter
        logger.info(f"Registered data adapter: {adapter_id}")
    
    async def execute_plugin(self, plugin_id: str, method: str, *args, **kwargs) -> Any:
        """执行插件方法"""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        if plugin.status != PluginStatus.ACTIVE:
            raise ValueError(f"Plugin not active: {plugin_id}")
        
        if not hasattr(plugin, method):
            raise ValueError(f"Plugin {plugin_id} does not have method {method}")
        
        method_func = getattr(plugin, method)
        if asyncio.iscoroutinefunction(method_func):
            return await method_func(*args, **kwargs)
        else:
            return method_func(*args, **kwargs)
    
    async def reload_plugin(self, plugin_id: str) -> bool:
        """重新加载插件"""
        # 先卸载
        if plugin_id in self.plugins:
            if not await self.uninstall_plugin(plugin_id):
                return False
        
        # 重新发现插件
        await self.discover_plugins()
        
        # 重新安装
        return await self.install_plugin(plugin_id)
    
    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """获取插件详细信息"""
        # 检查已安装的插件
        if plugin_id in self.plugins:
            plugin = self.plugins[plugin_id]
            info = plugin.info
            return {
                "id": plugin_id,
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "status": plugin.status.value,
                "installed": True,
                "capabilities": [cap.value for cap in info.capabilities],
                "dependencies": info.dependencies,
                "config_schema": info.config_schema,
                "metadata": info.metadata
            }
        
        # 检查未安装的插件
        elif plugin_id in self.plugin_classes:
            plugin_class = self.plugin_classes[plugin_id]
            if hasattr(plugin_class, 'plugin_info'):
                info = plugin_class.plugin_info
            else:
                temp = plugin_class()
                info = temp.info
            
            return {
                "id": plugin_id,
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "status": PluginStatus.UNLOADED.value,
                "installed": False,
                "capabilities": [cap.value for cap in info.capabilities],
                "dependencies": info.dependencies,
                "config_schema": info.config_schema,
                "metadata": info.metadata
            }
        
        return None