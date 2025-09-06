"""
股票工具函数
提供股票代码识别、分类和处理功能
"""

import re
from typing import Dict, Tuple, Optional
from enum import Enum

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")


class StockMarket(Enum):
    """股票市场枚举"""
    CHINA_A = "china_a"      # 中国A股
    HONG_KONG = "hong_kong"  # 港股
    US = "us"                # 美股
    CRYPTO = "crypto"        # 加密货币
    UNKNOWN = "unknown"      # 未知


class StockUtils:
    """股票工具类"""
    
    @staticmethod
    def identify_stock_market(ticker: str) -> StockMarket:
        """
        识别股票代码所属市场
        
        Args:
            ticker: 股票代码，可能是交易对格式（如BTC/USDT）或单个代码
            
        Returns:
            StockMarket: 股票市场类型
        """
        if not ticker:
            return StockMarket.UNKNOWN
            
        ticker_original = str(ticker).strip()
        ticker = ticker_original.upper()
        
        # 加密货币交易对：包含"/"的格式（如BTC/USDT, ETH/USDT等）
        if "/" in ticker:
            return StockMarket.CRYPTO
        
        # 常见加密货币代码：特定的加密货币符号
        crypto_symbols = {
            'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE', 'MATIC', 'AVAX',
            'DOT', 'LINK', 'UNI', 'LTC', 'ATOM', 'ICP', 'NEAR', 'FTM', 'ALGO', 'MANA',
            'SAND', 'CRV', 'AAVE', 'COMP', 'MKR', 'SUSHI', 'YFI', 'SNX', '1INCH'
        }
        
        if ticker in crypto_symbols:
            logger.info(f"🪙 识别为加密货币: {ticker}")
            return StockMarket.CRYPTO
        
        # 中国A股：6位数字
        if re.match(r'^\d{6}$', ticker):
            return StockMarket.CHINA_A

        # 港股：4-5位数字.HK（支持0700.HK和09988.HK格式）
        if re.match(r'^\d{4,5}\.HK$', ticker):
            return StockMarket.HONG_KONG

        # 美股：1-5位字母（但排除已知的加密货币代码）
        if re.match(r'^[A-Z]{1,5}$', ticker) and ticker not in crypto_symbols:
            return StockMarket.US
            
        return StockMarket.UNKNOWN
    
    @staticmethod
    def is_china_stock(ticker: str) -> bool:
        """
        判断是否为中国A股
        
        Args:
            ticker: 股票代码
            
        Returns:
            bool: 是否为中国A股
        """
        return StockUtils.identify_stock_market(ticker) == StockMarket.CHINA_A
    
    @staticmethod
    def is_hk_stock(ticker: str) -> bool:
        """
        判断是否为港股
        
        Args:
            ticker: 股票代码
            
        Returns:
            bool: 是否为港股
        """
        return StockUtils.identify_stock_market(ticker) == StockMarket.HONG_KONG
    
    @staticmethod
    def is_us_stock(ticker: str) -> bool:
        """
        判断是否为美股
        
        Args:
            ticker: 股票代码
            
        Returns:
            bool: 是否为美股
        """
        return StockUtils.identify_stock_market(ticker) == StockMarket.US
    
    @staticmethod
    def is_crypto(ticker: str) -> bool:
        """
        判断是否为加密货币
        
        Args:
            ticker: 股票代码或交易对
            
        Returns:
            bool: 是否为加密货币
        """
        return StockUtils.identify_stock_market(ticker) == StockMarket.CRYPTO
    
    @staticmethod
    def get_currency_info(ticker: str) -> Tuple[str, str]:
        """
        根据股票代码获取货币信息
        
        Args:
            ticker: 股票代码或加密货币交易对
            
        Returns:
            Tuple[str, str]: (货币名称, 货币符号)
        """
        market = StockUtils.identify_stock_market(ticker)
        
        if market == StockMarket.CHINA_A:
            return "人民币", "¥"
        elif market == StockMarket.HONG_KONG:
            return "港币", "HK$"
        elif market == StockMarket.US:
            return "美元", "$"
        elif market == StockMarket.CRYPTO:
            # 加密货币：根据交易对确定计价货币
            if "/" in ticker.upper():
                quote_currency = ticker.upper().split("/")[1]
                if quote_currency == "USDT":
                    return "Tether", "₮"
                elif quote_currency == "USDC":
                    return "USD Coin", "USDC"
                elif quote_currency == "BTC":
                    return "Bitcoin", "₿"
                elif quote_currency == "ETH":
                    return "Ethereum", "Ξ"
                else:
                    return quote_currency, quote_currency
            else:
                return "加密货币", "₿"
        else:
            return "未知", "?"
    
    @staticmethod
    def get_data_source(ticker: str) -> str:
        """
        根据股票代码获取推荐的数据源
        
        Args:
            ticker: 股票代码或加密货币交易对
            
        Returns:
            str: 数据源名称
        """
        market = StockUtils.identify_stock_market(ticker)
        
        if market == StockMarket.CHINA_A:
            return "china_unified"  # 使用统一的中国股票数据源
        elif market == StockMarket.HONG_KONG:
            return "yahoo_finance"  # 港股使用Yahoo Finance
        elif market == StockMarket.US:
            return "yahoo_finance"  # 美股使用Yahoo Finance
        elif market == StockMarket.CRYPTO:
            return "crypto_unified"  # 加密货币使用统一的加密货币数据源
        else:
            return "unknown"
    
    @staticmethod
    def normalize_hk_ticker(ticker: str) -> str:
        """
        标准化港股代码格式
        
        Args:
            ticker: 原始港股代码
            
        Returns:
            str: 标准化后的港股代码
        """
        if not ticker:
            return ticker
            
        ticker = str(ticker).strip().upper()
        
        # 如果是纯4-5位数字，添加.HK后缀
        if re.match(r'^\d{4,5}$', ticker):
            return f"{ticker}.HK"

        # 如果已经是正确格式，直接返回
        if re.match(r'^\d{4,5}\.HK$', ticker):
            return ticker
            
        return ticker
    
    @staticmethod
    def get_market_info(ticker: str) -> Dict:
        """
        获取股票市场的详细信息
        
        Args:
            ticker: 股票代码
            
        Returns:
            Dict: 市场信息字典
        """
        market = StockUtils.identify_stock_market(ticker)
        currency_name, currency_symbol = StockUtils.get_currency_info(ticker)
        data_source = StockUtils.get_data_source(ticker)
        
        market_names = {
            StockMarket.CHINA_A: "中国A股",
            StockMarket.HONG_KONG: "港股",
            StockMarket.US: "美股",
            StockMarket.CRYPTO: "加密货币",
            StockMarket.UNKNOWN: "未知市场"
        }
        
        return {
            "ticker": ticker,
            "market": market.value,
            "market_name": market_names[market],
            "currency_name": currency_name,
            "currency_symbol": currency_symbol,
            "data_source": data_source,
            "is_china": market == StockMarket.CHINA_A,
            "is_hk": market == StockMarket.HONG_KONG,
            "is_us": market == StockMarket.US,
            "is_crypto": market == StockMarket.CRYPTO
        }


# 便捷函数，保持向后兼容
def is_china_stock(ticker: str) -> bool:
    """判断是否为中国A股（向后兼容）"""
    return StockUtils.is_china_stock(ticker)


def is_hk_stock(ticker: str) -> bool:
    """判断是否为港股"""
    return StockUtils.is_hk_stock(ticker)


def is_us_stock(ticker: str) -> bool:
    """判断是否为美股"""
    return StockUtils.is_us_stock(ticker)


def is_crypto(ticker: str) -> bool:
    """判断是否为加密货币"""
    return StockUtils.is_crypto(ticker)


def get_stock_market_info(ticker: str) -> Dict:
    """获取股票市场信息"""
    return StockUtils.get_market_info(ticker)
