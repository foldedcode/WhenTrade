"""
数据处理模块
包含数据管道、统一适配器等数据处理组件
"""

from .pipeline import DataPipeline
from .unified_adapter import (
    global_unified_registry,
    initialize_unified_system,
    fetch_unified_data
)

__all__ = [
    "DataPipeline",
    "global_unified_registry",
    "initialize_unified_system",
    "fetch_unified_data"
]