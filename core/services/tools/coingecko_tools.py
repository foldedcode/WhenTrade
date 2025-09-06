"""
CoinGecko加密货币数据工具

提供专业的加密货币市场数据、价格历史和市场指标
"""
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CoinGeckoTools:
    """CoinGecko API工具类"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    _session = None
    
    # 常用币种ID映射
    COIN_IDS = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'ADA': 'cardano',
        'SOL': 'solana',
        'DOT': 'polkadot',
        'AVAX': 'avalanche-2',
        'MATIC': 'matic-network',
        'LINK': 'chainlink',
        'UNI': 'uniswap',
        'ATOM': 'cosmos',
        'XRP': 'ripple',
        'DOGE': 'dogecoin',
        'SHIB': 'shiba-inu',
    }
    
    @classmethod 
    def _get_session(cls) -> requests.Session:
        """获取配置了重试机制的Session"""
        if cls._session is None:
            cls._session = requests.Session()
            
            # 配置重试策略 - 专门处理SSL和网络问题
            retry_strategy = Retry(
                total=3,  # 最多重试3次
                status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
                allowed_methods=["GET"],  # 只对GET请求重试
                backoff_factor=1,  # 指数退避系数
                raise_on_status=False  # 不要因为状态码抛出异常
            )
            
            # 为HTTPS请求配置适配器
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=10,  # 连接池大小
                pool_maxsize=10,      # 最大连接数
                pool_block=True       # 连接池满时阻塞而不是抛异常
            )
            
            cls._session.mount("https://", adapter)
            logger.debug("🔧 CoinGecko Session initialized with retry strategy")
            
        return cls._session

    @classmethod
    def _get_headers(cls) -> Dict[str, str]:
        """获取API请求头"""
        api_key = os.getenv('COINGECKO_API_KEY')
        if api_key and api_key != 'your-coingecko-api-key':
            return {
                'x-cg-demo-api-key': api_key,
                'accept': 'application/json'
            }
        return {'accept': 'application/json'}
    
    @classmethod
    def _get_coin_id(cls, symbol: str) -> str:
        """转换币种符号为CoinGecko ID"""
        symbol = symbol.upper().replace('-USD', '').replace('USDT', '')
        return cls.COIN_IDS.get(symbol, symbol.lower())
    
    @classmethod
    def get_coin_market_data(
        cls,
        symbol: str,
        vs_currency: str = 'usd'
    ) -> Dict[str, Any]:
        """
        获取加密货币实时市场数据
        
        Args:
            symbol: 币种符号 (如 'BTC', 'ETH')
            vs_currency: 计价货币 (默认 'usd')
            
        Returns:
            包含价格、市值、24h变化等数据
        """
        from .retry_handler import retry_on_error
        from .rate_limiter import rate_limit
        
        @rate_limit(api_name='coingecko')
        @retry_on_error(api_name='coingecko')
        def _fetch_market_data():
            coin_id = cls._get_coin_id(symbol)
            
            # 获取市场数据
            url = f"{cls.BASE_URL}/coins/markets"
            params = {
                'vs_currency': vs_currency,
                'ids': coin_id,
                'order': 'market_cap_desc',
                'per_page': 1,
                'page': 1,
                'sparkline': True,
                'price_change_percentage': '1h,24h,7d,30d'
            }
            
            response = requests.get(url, headers=cls._get_headers(), params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                return {
                    "error": f"No data found for {symbol}",
                    "symbol": symbol
                }
            
            coin_data = data[0]
            
            return {
                "symbol": symbol,
                "coin_id": coin_id,
                "name": coin_data.get('name'),
                "current_price": coin_data.get('current_price'),
                "market_cap": coin_data.get('market_cap'),
                "market_cap_rank": coin_data.get('market_cap_rank'),
                "total_volume": coin_data.get('total_volume'),
                "high_24h": coin_data.get('high_24h'),
                "low_24h": coin_data.get('low_24h'),
                "price_change_24h": coin_data.get('price_change_24h'),
                "price_change_percentage_24h": coin_data.get('price_change_percentage_24h'),
                "price_change_percentage_1h": coin_data.get('price_change_percentage_1h_in_currency'),
                "price_change_percentage_7d": coin_data.get('price_change_percentage_7d_in_currency'),
                "price_change_percentage_30d": coin_data.get('price_change_percentage_30d_in_currency'),
                "circulating_supply": coin_data.get('circulating_supply'),
                "total_supply": coin_data.get('total_supply'),
                "max_supply": coin_data.get('max_supply'),
                "ath": coin_data.get('ath'),
                "ath_change_percentage": coin_data.get('ath_change_percentage'),
                "ath_date": coin_data.get('ath_date'),
                "atl": coin_data.get('atl'),
                "atl_change_percentage": coin_data.get('atl_change_percentage'),
                "atl_date": coin_data.get('atl_date'),
                "sparkline_7d": coin_data.get('sparkline_in_7d', {}).get('price', []),
                "last_updated": coin_data.get('last_updated'),
                "data_source": "coingecko"
            }
        
        try:
            return _fetch_market_data()
        except requests.exceptions.SSLError as e:
            logger.error(f"🔐 SSL Error for {symbol}: {e}", exc_info=True)
            return {
                "error": f"SSL connection failed: {str(e)}",
                "symbol": symbol,
                "data_source": "coingecko",
                "error_type": "ssl_error"
            }
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "data_source": "coingecko"
            }
    
    @classmethod
    def get_historical_prices(
        cls,
        symbol: str,
        days: int = 30,
        vs_currency: str = 'usd'
    ) -> Dict[str, Any]:
        """
        获取历史价格数据
        
        Args:
            symbol: 币种符号
            days: 历史天数 (1, 7, 14, 30, 90, 180, 365, max)
            vs_currency: 计价货币
            
        Returns:
            历史价格数据
        """
        from .retry_handler import retry_on_error
        from .rate_limiter import rate_limit
        
        @rate_limit(api_name='coingecko')
        @retry_on_error(api_name='coingecko')
        def _fetch_historical_data():
            coin_id = cls._get_coin_id(symbol)
            
            url = f"{cls.BASE_URL}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': vs_currency,
                'days': days
                # 删除interval参数：让API根据days自动选择最佳间隔
                # 避免使用企业版专属的'hourly'参数
            }
            
            response = requests.get(url, headers=cls._get_headers(), params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 格式化数据
            prices = []
            volumes = []
            market_caps = []
            
            for price_point in data.get('prices', []):
                prices.append({
                    'timestamp': price_point[0],
                    'date': datetime.fromtimestamp(price_point[0]/1000).isoformat(),
                    'price': price_point[1]
                })
            
            for volume_point in data.get('total_volumes', []):
                volumes.append({
                    'timestamp': volume_point[0],
                    'date': datetime.fromtimestamp(volume_point[0]/1000).isoformat(),
                    'volume': volume_point[1]
                })
            
            for cap_point in data.get('market_caps', []):
                market_caps.append({
                    'timestamp': cap_point[0],
                    'date': datetime.fromtimestamp(cap_point[0]/1000).isoformat(),
                    'market_cap': cap_point[1]
                })
            
            # 🔧 Linus式修复：转换为嵌套列表格式，确保与technical_tools.py兼容
            prices_nested = [[p['timestamp'], p['price']] for p in prices]
            
            return {
                "symbol": symbol,
                "coin_id": coin_id,
                "days": days,
                "vs_currency": vs_currency,
                "prices": prices_nested,  # 统一使用嵌套列表格式
                "volumes": volumes,
                "market_caps": market_caps,
                "data_points": len(prices_nested),
                "data_source": "coingecko"
            }
        
        try:
            return _fetch_historical_data()
        except requests.exceptions.SSLError as e:
            logger.error(f"🔐 SSL Error (historical) for {symbol}: {e}", exc_info=True)
            return {
                "error": f"SSL connection failed: {str(e)}",
                "symbol": symbol,
                "data_source": "coingecko",
                "error_type": "ssl_error"
            }
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "data_source": "coingecko"
            }
    
    @classmethod
    def get_market_metrics(cls) -> Dict[str, Any]:
        """
        获取全球加密货币市场指标
        
        Returns:
            市场总览数据
        """
        try:
            url = f"{cls.BASE_URL}/global"
            
            response = requests.get(url, headers=cls._get_headers(), timeout=10)
            response.raise_for_status()
            
            data = response.json().get('data', {})
            
            return {
                "total_market_cap": data.get('total_market_cap', {}).get('usd'),
                "total_volume_24h": data.get('total_volume', {}).get('usd'),
                "bitcoin_dominance": data.get('market_cap_percentage', {}).get('btc'),
                "ethereum_dominance": data.get('market_cap_percentage', {}).get('eth'),
                "active_cryptocurrencies": data.get('active_cryptocurrencies'),
                "upcoming_icos": data.get('upcoming_icos'),
                "ongoing_icos": data.get('ongoing_icos'),
                "ended_icos": data.get('ended_icos'),
                "markets": data.get('markets'),
                "market_cap_change_24h": data.get('market_cap_change_percentage_24h_usd'),
                "updated_at": data.get('updated_at'),
                "data_source": "coingecko"
            }
            
        except Exception as e:
            logger.error(f"Error getting market metrics: {e}")
            return {
                "error": str(e),
                "data_source": "coingecko"
            }
    
    @classmethod
    def get_trending_coins(cls) -> Dict[str, Any]:
        """
        获取热门币种
        
        Returns:
            热门币种列表
        """
        try:
            url = f"{cls.BASE_URL}/search/trending"
            
            response = requests.get(url, headers=cls._get_headers(), timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 格式化热门币种数据
            trending = []
            for coin in data.get('coins', []):
                item = coin.get('item', {})
                trending.append({
                    'id': item.get('id'),
                    'symbol': item.get('symbol'),
                    'name': item.get('name'),
                    'market_cap_rank': item.get('market_cap_rank'),
                    'price_btc': item.get('price_btc'),
                    'score': item.get('score'),
                    'thumb': item.get('thumb'),
                    'data': item.get('data', {})
                })
            
            return {
                "trending_coins": trending,
                "count": len(trending),
                "data_source": "coingecko"
            }
            
        except Exception as e:
            logger.error(f"Error getting trending coins: {e}")
            return {
                "error": str(e),
                "data_source": "coingecko"
            }
    
    @classmethod
    def get_fear_greed_index(cls) -> Dict[str, Any]:
        """
        获取恐惧贪婪指数（来自alternative.me）
        
        Returns:
            恐惧贪婪指数数据
        """
        try:
            # 注意：这个API不是CoinGecko的，但常与CoinGecko数据配合使用
            url = "https://api.alternative.me/fng/"
            params = {'limit': 1}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json().get('data', [])
            if data:
                current = data[0]
                return {
                    "value": int(current.get('value')),
                    "classification": current.get('value_classification'),
                    "timestamp": current.get('timestamp'),
                    "time_until_update": current.get('time_until_update'),
                    "data_source": "alternative.me"
                }
            
            return {
                "error": "No fear & greed index data available",
                "data_source": "alternative.me"
            }
            
        except Exception as e:
            logger.error(f"Error getting fear & greed index: {e}")
            return {
                "error": str(e),
                "data_source": "alternative.me"
            }


# 便捷函数接口
def get_coin_market_data(symbol: str, **kwargs) -> Dict[str, Any]:
    """获取实时市场数据"""
    return CoinGeckoTools.get_coin_market_data(symbol, **kwargs)


def get_historical_prices(symbol: str, days: int = 30, **kwargs) -> Dict[str, Any]:
    """获取历史价格"""
    return CoinGeckoTools.get_historical_prices(symbol, days, **kwargs)


def get_market_metrics() -> Dict[str, Any]:
    """获取市场指标"""
    return CoinGeckoTools.get_market_metrics()


def get_trending_coins() -> Dict[str, Any]:
    """获取热门币种"""
    return CoinGeckoTools.get_trending_coins()


def get_fear_greed_index() -> Dict[str, Any]:
    """获取恐惧贪婪指数"""
    return CoinGeckoTools.get_fear_greed_index()