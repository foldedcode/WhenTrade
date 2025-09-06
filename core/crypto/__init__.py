"""
When.Trade Crypto Market Adapter
加密货币市场适配器

支持多个加密货币交易所和数据源的统一接口
专为When.Trade交易时机分析优化
"""

from .market_adapter import CryptoMarketAdapter
from .exchange_manager import ExchangeManager
from .data_aggregator import DataAggregator
from .price_feed import PriceFeedManager

__all__ = [
    "CryptoMarketAdapter",
    "ExchangeManager", 
    "DataAggregator",
    "PriceFeedManager"
]
