"""
依赖注入
"""

from typing import AsyncGenerator
from functools import lru_cache

# 数据网关依赖注入（已删除未实现功能）

from core.config import settings
from core.infrastructure.logger import logger


# @lru_cache()
# def get_cache_manager() -> CacheManager:
#     """获取缓存管理器单例"""
#     config = CacheConfig(
#         redis_url=settings.REDIS_URL,
#         default_ttl=3600,
#         namespace="datagateway"
#     )
#     return CacheManager(config)


# @lru_cache()
# def get_data_gateway() -> DataGateway:
#     """获取数据网关单例"""
#     # 创建数据网关
#     gateway = DataGateway(cache_manager=get_cache_manager())
    
#     # 注册数据提供者
#     # Yahoo Finance
#     yfinance_config = {
#         "api_key": settings.YFINANCE_API_KEY if hasattr(settings, 'YFINANCE_API_KEY') else None
#     }
#     gateway.register_provider("yfinance", YFinanceProvider(yfinance_config))
    
#     # Binance
#     binance_config = {
#         "api_key": settings.BINANCE_API_KEY if hasattr(settings, 'BINANCE_API_KEY') else None,
#         "api_secret": settings.BINANCE_API_SECRET if hasattr(settings, 'BINANCE_API_SECRET') else None
#     }
#     gateway.register_provider("binance", BinanceProvider(binance_config))
#     
#     # Mock Provider (用于开发和测试)
#     gateway.register_provider("mock", MockProvider())
#     
#     logger.info("Data gateway initialized with providers")
#     
#     return gateway


# async def startup_event():
#     """应用启动事件"""
#     # 连接缓存
#     cache_manager = get_cache_manager()
#     await cache_manager.connect()
#     logger.info("Cache manager connected")
#     
#     # 注册工具
#     from core.tools.legacy.registry import tool_registry
#     from core.tools.legacy.technical import RSITool, MACDTool, MovingAverageTool, BollingerBandsTool
#     from core.tools.legacy.sentiment import NewsSentimentTool
#     
#     # 注册技术分析工具
#     tool_registry.register(RSITool())
#     tool_registry.register(MACDTool())
#     tool_registry.register(MovingAverageTool())
#     tool_registry.register(BollingerBandsTool())
#     
#     # 注册情绪分析工具
#     tool_registry.register(NewsSentimentTool())
#     
#     logger.info(f"Registered {len(tool_registry._tools)} tools in registry")
    
    
# async def shutdown_event():
#     """应用关闭事件"""
#     # 断开缓存连接
#     cache_manager = get_cache_manager()
#     await cache_manager.disconnect()
#     logger.info("Cache manager disconnected")