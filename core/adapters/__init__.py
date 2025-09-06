"""
数据适配器包

提供各种数据源的适配器实现
"""

from .base import (
    IDataAdapter,
    BaseDataAdapter,
    CompositeDataAdapter,
    DataType,
    DataFrequency,
    DataSourceInfo,
    DataRequest,
    DataResponse,
    DataPoint,
    DataQuality
)

from .yahoo_finance import YahooFinanceAdapter
from .alpha_vantage import AlphaVantageAdapter
from .coingecko import CoinGeckoAdapter
from .news_api import NewsAPIAdapter

__all__ = [
    # 基础类
    'IDataAdapter',
    'BaseDataAdapter',
    'CompositeDataAdapter',
    
    # 数据结构
    'DataType',
    'DataFrequency',
    'DataSourceInfo',
    'DataRequest',
    'DataResponse',
    'DataPoint',
    'DataQuality',
    
    # 具体实现
    'YahooFinanceAdapter',
    'AlphaVantageAdapter',
    'CoinGeckoAdapter',
    'NewsAPIAdapter'
]