"""
CoinGecko API适配器

提供CoinGecko API的统一访问接口
"""
import os
import requests
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CoinGeckoAdapter:
    """CoinGecko API适配器"""
    
    def __init__(self):
        self.api_key = os.getenv('COINGECKO_API_KEY')
        self.base_url = "https://api.coingecko.com/api/v3"
        self.headers = self._get_headers()
        
    def _get_headers(self) -> Dict[str, str]:
        """构建请求头"""
        if self.api_key and self.api_key != 'your-coingecko-api-key':
            return {
                'x-cg-demo-api-key': self.api_key,
                'accept': 'application/json'
            }
        return {'accept': 'application/json'}
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """发送API请求"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGecko API request failed: {e}")
            raise
    
    def get_price(self, coin_ids: List[str], vs_currencies: List[str] = ['usd']) -> Dict[str, Any]:
        """获取简单价格"""
        params = {
            'ids': ','.join(coin_ids),
            'vs_currencies': ','.join(vs_currencies),
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        return self._make_request('simple/price', params)
    
    def get_coin_markets(self, vs_currency: str = 'usd', **kwargs) -> List[Dict[str, Any]]:
        """获取市场数据"""
        params = {
            'vs_currency': vs_currency,
            'order': kwargs.get('order', 'market_cap_desc'),
            'per_page': kwargs.get('per_page', 100),
            'page': kwargs.get('page', 1),
            'sparkline': kwargs.get('sparkline', False),
            'price_change_percentage': kwargs.get('price_change_percentage', '24h')
        }
        
        if 'ids' in kwargs:
            params['ids'] = kwargs['ids']
        
        return self._make_request('coins/markets', params)
    
    def get_coin_history(self, coin_id: str, date: str) -> Dict[str, Any]:
        """获取历史数据"""
        params = {'date': date}
        return self._make_request(f'coins/{coin_id}/history', params)
    
    def get_coin_market_chart(self, coin_id: str, vs_currency: str = 'usd', days: int = 30) -> Dict[str, Any]:
        """获取市场图表数据"""
        params = {
            'vs_currency': vs_currency,
            'days': days
        }
        return self._make_request(f'coins/{coin_id}/market_chart', params)
    
    def get_coin_market_chart_range(
        self, 
        coin_id: str, 
        vs_currency: str,
        from_timestamp: int,
        to_timestamp: int
    ) -> Dict[str, Any]:
        """获取指定时间范围的市场数据"""
        params = {
            'vs_currency': vs_currency,
            'from': from_timestamp,
            'to': to_timestamp
        }
        return self._make_request(f'coins/{coin_id}/market_chart/range', params)
    
    def get_coin_ohlc(self, coin_id: str, vs_currency: str = 'usd', days: int = 7) -> List[List[float]]:
        """获取OHLC数据"""
        params = {
            'vs_currency': vs_currency,
            'days': days
        }
        return self._make_request(f'coins/{coin_id}/ohlc', params)
    
    def get_global_data(self) -> Dict[str, Any]:
        """获取全球数据"""
        return self._make_request('global')
    
    def get_global_defi_data(self) -> Dict[str, Any]:
        """获取全球DeFi数据"""
        return self._make_request('global/decentralized_finance_defi')
    
    def get_trending(self) -> Dict[str, Any]:
        """获取热门搜索"""
        return self._make_request('search/trending')
    
    def get_exchanges(self, per_page: int = 100, page: int = 1) -> List[Dict[str, Any]]:
        """获取交易所列表"""
        params = {
            'per_page': per_page,
            'page': page
        }
        return self._make_request('exchanges', params)
    
    def get_exchange_volume_chart(self, exchange_id: str, days: int = 30) -> List[List[float]]:
        """获取交易所交易量图表"""
        return self._make_request(f'exchanges/{exchange_id}/volume_chart', {'days': days})
    
    def search(self, query: str) -> Dict[str, Any]:
        """搜索币种、交易所、ICO等"""
        return self._make_request('search', {'query': query})
    
    def get_coin_info(self, coin_id: str) -> Dict[str, Any]:
        """获取币种详细信息"""
        params = {
            'localization': 'false',
            'tickers': 'true',
            'market_data': 'true',
            'community_data': 'true',
            'developer_data': 'true',
            'sparkline': 'true'
        }
        return self._make_request(f'coins/{coin_id}', params)
    
    def get_supported_vs_currencies(self) -> List[str]:
        """获取支持的计价货币列表"""
        return self._make_request('simple/supported_vs_currencies')
    
    def ping(self) -> Dict[str, Any]:
        """测试API连接"""
        return self._make_request('ping')
    
    def get_api_usage(self) -> Optional[Dict[str, Any]]:
        """获取API使用情况（需要Pro API key）"""
        if not self.api_key:
            return None
        
        try:
            # CoinGecko Pro API endpoint
            url = "https://pro-api.coingecko.com/api/v3/key"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except:
            return None


# 单例实例
_adapter_instance = None

def get_coingecko_adapter() -> CoinGeckoAdapter:
    """获取CoinGecko适配器单例"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = CoinGeckoAdapter()
    return _adapter_instance