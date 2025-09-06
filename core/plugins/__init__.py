"""
插件系统包

提供插件加载、管理和执行功能
"""

from .plugin_base import (
    PluginBase,
    PluginInfo,
    PluginStatus,
    PluginCapability
)

from .plugin_manager import PluginManager
from .plugin_registry import PluginRegistry

__all__ = [
    'PluginBase',
    'PluginInfo',
    'PluginStatus',
    'PluginCapability',
    'PluginManager',
    'PluginRegistry'
]