"""
CoinGecko 数据适配器

提供加密货币市场数据、价格、市值和其他指标
"""

import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
import logging

from .base import (
    BaseDataAdapter,
    DataType,
    DataFrequency,
    DataSourceInfo,
    DataRequest,
    DataResponse,
    DataPoint
)

logger = logging.getLogger(__name__)


class CoinGeckoAdapter(BaseDataAdapter):
    """CoinGecko 数据适配器"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "CoinGecko"
        self.session = None
        self._coin_list = None  # 缓存币种列表
        
    async def get_info(self) -> DataSourceInfo:
        """获取数据源信息"""
        return DataSourceInfo(
            id="coingecko",
            name="CoinGecko",
            description="Comprehensive cryptocurrency data API",
            provider="CoinGecko",
            version="3.0.0",
            data_types=[
                DataType.MARKET,
                DataType.ONCHAIN
            ],
            frequencies=[
                DataFrequency.REALTIME,
                DataFrequency.MINUTE,
                DataFrequency.HOURLY,
                DataFrequency.DAILY
            ],
            markets=["CRYPTO"],
            requires_auth=False,
            rate_limits={
                "requests_per_minute": 50,  # 免费版
                "requests_per_minute_pro": 500  # Pro版
            },
            metadata={
                "api_docs": "https://www.coingecko.com/en/api/documentation",
                "supported_vs_currencies": ["usd", "eur", "gbp", "jpy", "cny", "btc", "eth"]
            }
        )
    
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """CoinGecko 免费版不需要认证，Pro版需要API密钥"""
        # 如果提供了API密钥，则使用Pro版本
        self.api_key = credentials.get("api_key") if credentials else None
        self._authenticated = True
        return True
    
    async def fetch_data(self, request: DataRequest) -> DataResponse:
        """获取数据"""
        try:
            # 验证请求
            errors = await self.validate_request(request)
            if errors:
                return DataResponse(
                    request=request,
                    data_points=[],
                    errors=errors
                )
            
            # 创建会话
            if not self.session:
                headers = {}
                if self.api_key:
                    headers["x-cg-pro-api-key"] = self.api_key
                self.session = aiohttp.ClientSession(headers=headers)
            
            data_points = []
            warnings = []
            
            # 转换币种符号（如BTC -> bitcoin）
            coin_ids = await self._convert_symbols_to_ids(request.symbols)
            
            if request.data_type == DataType.MARKET:
                if request.frequency == DataFrequency.REALTIME:
                    # 获取实时价格
                    points = await self._fetch_current_prices(coin_ids)
                    data_points.extend(points)
                else:
                    # 获取历史数据
                    for coin_id in coin_ids:
                        try:
                            points = await self._fetch_historical_data(
                                coin_id,
                                request.start_date,
                                request.end_date,
                                request.frequency
                            )
                            data_points.extend(points)
                        except Exception as e:
                            warnings.append(f"Failed to fetch {coin_id}: {str(e)}")
            
            elif request.data_type == DataType.ONCHAIN:
                # 获取链上数据
                for coin_id in coin_ids:
                    try:
                        points = await self._fetch_onchain_data(coin_id)
                        data_points.extend(points)
                    except Exception as e:
                        warnings.append(f"Failed to fetch onchain data for {coin_id}: {str(e)}")
            
            return DataResponse(
                request=request,
                data_points=data_points,
                warnings=warnings,
                metadata={
                    "source": "coingecko",
                    "fetch_time": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"CoinGecko fetch error: {e}")
            return DataResponse(
                request=request,
                data_points=[],
                errors=[str(e)]
            )
    
    async def _convert_symbols_to_ids(self, symbols: List[str]) -> List[str]:
        """转换交易符号到CoinGecko ID"""
        # 获取币种列表
        if not self._coin_list:
            await self._fetch_coin_list()
        
        # 创建符号到ID的映射
        symbol_to_id = {}
        for coin in self._coin_list:
            symbol_to_id[coin['symbol'].upper()] = coin['id']
        
        # 转换符号
        coin_ids = []
        for symbol in symbols:
            # 移除USD后缀（如BTC-USD -> BTC）
            clean_symbol = symbol.upper().replace('-USD', '').replace('USDT', '')
            
            if clean_symbol in symbol_to_id:
                coin_ids.append(symbol_to_id[clean_symbol])
            else:
                # 如果找不到，尝试使用小写作为ID
                coin_ids.append(clean_symbol.lower())
        
        return coin_ids
    
    async def _fetch_coin_list(self):
        """获取所有支持的币种列表"""
        url = f"{self.BASE_URL}/coins/list"
        async with self.session.get(url) as response:
            if response.status == 200:
                self._coin_list = await response.json()
            else:
                self._coin_list = []
    
    async def _fetch_current_prices(self, coin_ids: List[str]) -> List[DataPoint]:
        """获取当前价格"""
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true"
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"API request failed with status {response.status}")
            
            data = await response.json()
            
        data_points = []
        timestamp = datetime.now()
        
        for coin_id, price_data in data.items():
            data_point = DataPoint(
                symbol=coin_id.upper(),
                timestamp=timestamp,
                data={
                    "price": price_data.get("usd", 0),
                    "market_cap": price_data.get("usd_market_cap", 0),
                    "volume_24h": price_data.get("usd_24h_vol", 0),
                    "change_24h": price_data.get("usd_24h_change", 0),
                    "last_updated": datetime.fromtimestamp(
                        price_data.get("last_updated_at", 0)
                    ).isoformat() if price_data.get("last_updated_at") else None
                },
                metadata={
                    "source": "coingecko",
                    "data_type": "realtime"
                }
            )
            data_points.append(data_point)
        
        return data_points
    
    async def _fetch_historical_data(self,
                                   coin_id: str,
                                   start_date: Optional[date],
                                   end_date: Optional[date],
                                   frequency: Optional[DataFrequency]) -> List[DataPoint]:
        """获取历史数据"""
        # 确定时间范围
        end = end_date or date.today()
        
        if frequency == DataFrequency.MINUTE:
            # 分钟数据只能获取最近1天
            start = end - timedelta(days=1)
            url = f"{self.BASE_URL}/coins/{coin_id}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": "1",
                "interval": "minute"
            }
        elif frequency == DataFrequency.HOURLY:
            # 小时数据可以获取最近90天
            if not start_date:
                start = end - timedelta(days=30)
            else:
                start = start_date
            days = (end - start).days
            url = f"{self.BASE_URL}/coins/{coin_id}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": str(min(days, 90)),
                "interval": "hourly"
            }
        else:  # DAILY
            # 日数据可以获取所有历史
            if not start_date:
                start = end - timedelta(days=365)
            else:
                start = start_date
            
            url = f"{self.BASE_URL}/coins/{coin_id}/market_chart/range"
            params = {
                "vs_currency": "usd",
                "from": int(start.timestamp()),
                "to": int(end.timestamp())
            }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"API request failed with status {response.status}")
            
            data = await response.json()
        
        # 解析数据
        data_points = []
        
        prices = data.get("prices", [])
        market_caps = data.get("market_caps", [])
        volumes = data.get("total_volumes", [])
        
        for i in range(len(prices)):
            timestamp = datetime.fromtimestamp(prices[i][0] / 1000)  # 毫秒转秒
            
            data_point = DataPoint(
                symbol=coin_id.upper(),
                timestamp=timestamp,
                data={
                    "price": prices[i][1] if i < len(prices) else 0,
                    "market_cap": market_caps[i][1] if i < len(market_caps) else 0,
                    "volume": volumes[i][1] if i < len(volumes) else 0
                },
                metadata={
                    "source": "coingecko",
                    "frequency": frequency.value if frequency else "daily"
                }
            )
            data_points.append(data_point)
        
        return data_points
    
    async def _fetch_onchain_data(self, coin_id: str) -> List[DataPoint]:
        """获取链上数据和详细信息"""
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false"
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"API request failed with status {response.status}")
            
            data = await response.json()
        
        # 提取市场数据
        market_data = data.get("market_data", {})
        
        data_point = DataPoint(
            symbol=coin_id.upper(),
            timestamp=datetime.now(),
            data={
                # 基本信息
                "name": data.get("name", ""),
                "symbol": data.get("symbol", "").upper(),
                "market_cap_rank": data.get("market_cap_rank", 0),
                
                # 价格数据
                "current_price": market_data.get("current_price", {}).get("usd", 0),
                "ath": market_data.get("ath", {}).get("usd", 0),
                "ath_date": market_data.get("ath_date", {}).get("usd", ""),
                "atl": market_data.get("atl", {}).get("usd", 0),
                "atl_date": market_data.get("atl_date", {}).get("usd", ""),
                
                # 市场数据
                "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                "fully_diluted_valuation": market_data.get("fully_diluted_valuation", {}).get("usd", 0),
                "total_volume": market_data.get("total_volume", {}).get("usd", 0),
                "circulating_supply": market_data.get("circulating_supply", 0),
                "total_supply": market_data.get("total_supply", 0),
                "max_supply": market_data.get("max_supply", 0),
                
                # 价格变化
                "price_change_24h": market_data.get("price_change_24h", 0),
                "price_change_percentage_24h": market_data.get("price_change_percentage_24h", 0),
                "price_change_percentage_7d": market_data.get("price_change_percentage_7d", 0),
                "price_change_percentage_30d": market_data.get("price_change_percentage_30d", 0),
                "price_change_percentage_1y": market_data.get("price_change_percentage_1y", 0),
                
                # 社区数据
                "twitter_followers": data.get("community_data", {}).get("twitter_followers", 0),
                "reddit_subscribers": data.get("community_data", {}).get("reddit_subscribers", 0),
                
                # 开发活动
                "github_stars": data.get("developer_data", {}).get("stars", 0),
                "github_forks": data.get("developer_data", {}).get("forks", 0),
                "github_commits_4_weeks": data.get("developer_data", {}).get("commit_count_4_weeks", 0)
            },
            metadata={
                "source": "coingecko",
                "data_type": "onchain",
                "last_updated": data.get("last_updated", "")
            }
        )
        
        return [data_point]
    
    async def get_available_symbols(self, market: Optional[str] = None) -> List[str]:
        """获取可用的加密货币符号"""
        if not self._coin_list:
            await self._fetch_coin_list()
        
        # 返回前100个币种的符号
        symbols = []
        for coin in self._coin_list[:100]:
            symbols.append(coin['symbol'].upper())
        
        return symbols
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None