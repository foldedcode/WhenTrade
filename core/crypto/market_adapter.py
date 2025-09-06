"""
Crypto Market Adapter - 加密货币市场适配器
统一的加密货币市场数据接口
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """市场数据结构"""
    symbol: str
    price: float
    volume: float
    change_24h: float
    change_percent_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime
    exchange: str = "binance"
    
@dataclass
class OrderBookData:
    """订单簿数据"""
    symbol: str
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    timestamp: datetime
    exchange: str = "binance"

@dataclass
class TradeData:
    """交易数据"""
    symbol: str
    price: float
    quantity: float
    side: str  # "buy" or "sell"
    timestamp: datetime
    trade_id: str
    exchange: str = "binance"

class CryptoMarketAdapter:
    """
    加密货币市场适配器
    
    功能:
    - 多交易所数据统一
    - 实时价格获取
    - 历史数据查询
    - 订单簿分析
    - 交易流分析
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.supported_exchanges = ["binance", "coinbase", "kraken", "huobi"]
        self.active_connections = {}
        self.price_cache = {}
        self.cache_ttl = 5  # 缓存5秒
        
        logger.info("📈 Crypto Market Adapter initialized")
        logger.info(f"   Supported exchanges: {', '.join(self.supported_exchanges)}")
    
    async def get_price(
        self, 
        symbol: str, 
        exchange: str = "binance"
    ) -> Optional[MarketData]:
        """
        获取实时价格
        
        Args:
            symbol: 交易对符号 (e.g., "BTCUSDT")
            exchange: 交易所名称
            
        Returns:
            MarketData: 市场数据对象
        """
        cache_key = f"{exchange}:{symbol}"
        
        # 检查缓存
        if cache_key in self.price_cache:
            cached_data, cache_time = self.price_cache[cache_key]
            if (datetime.now() - cache_time).seconds < self.cache_ttl:
                return cached_data
        
        try:
            # 模拟获取实时数据
            price_data = await self._fetch_price_data(symbol, exchange)
            
            # 缓存数据
            self.price_cache[cache_key] = (price_data, datetime.now())
            
            logger.debug(f"💰 Price fetched: {symbol} = ${price_data.price:.4f}")
            return price_data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch price for {symbol}: {e}")
            return None
    
    async def get_multiple_prices(
        self, 
        symbols: List[str], 
        exchange: str = "binance"
    ) -> Dict[str, Optional[MarketData]]:
        """批量获取价格"""
        tasks = [
            self.get_price(symbol, exchange) 
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: result if not isinstance(result, Exception) else None
            for symbol, result in zip(symbols, results)
        }
    
    async def get_orderbook(
        self, 
        symbol: str, 
        depth: int = 20,
        exchange: str = "binance"
    ) -> Optional[OrderBookData]:
        """
        获取订单簿数据
        
        Args:
            symbol: 交易对符号
            depth: 深度级别
            exchange: 交易所名称
            
        Returns:
            OrderBookData: 订单簿数据
        """
        try:
            # 模拟订单簿数据
            base_price = 50000.0  # 假设BTC价格
            
            # 生成买单 (bids)
            bids = []
            for i in range(depth):
                price = base_price - (i * 10)
                quantity = 0.5 + (i * 0.1)
                bids.append([price, quantity])
            
            # 生成卖单 (asks)
            asks = []
            for i in range(depth):
                price = base_price + (i * 10)
                quantity = 0.5 + (i * 0.1)
                asks.append([price, quantity])
            
            orderbook = OrderBookData(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(),
                exchange=exchange
            )
            
            logger.debug(f"📊 Orderbook fetched: {symbol} ({len(bids)} bids, {len(asks)} asks)")
            return orderbook
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch orderbook for {symbol}: {e}")
            return None
    
    async def get_recent_trades(
        self, 
        symbol: str, 
        limit: int = 100,
        exchange: str = "binance"
    ) -> List[TradeData]:
        """
        获取最近交易记录
        
        Args:
            symbol: 交易对符号
            limit: 记录数量限制
            exchange: 交易所名称
            
        Returns:
            List[TradeData]: 交易数据列表
        """
        try:
            trades = []
            base_price = 50000.0
            
            for i in range(limit):
                price = base_price + (i % 20 - 10) * 5
                quantity = 0.1 + (i % 10) * 0.05
                side = "buy" if i % 2 == 0 else "sell"
                timestamp = datetime.now() - timedelta(minutes=i)
                
                trade = TradeData(
                    symbol=symbol,
                    price=price,
                    quantity=quantity,
                    side=side,
                    timestamp=timestamp,
                    trade_id=f"trade_{i}",
                    exchange=exchange
                )
                trades.append(trade)
            
            logger.debug(f"📈 Recent trades fetched: {symbol} ({len(trades)} trades)")
            return trades
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch recent trades for {symbol}: {e}")
            return []
    
    async def get_historical_data(
        self, 
        symbol: str, 
        interval: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        exchange: str = "binance"
    ) -> List[Dict]:
        """
        获取历史K线数据
        
        Args:
            symbol: 交易对符号
            interval: 时间间隔 ("1m", "5m", "15m", "1h", "4h", "1d")
            start_time: 开始时间
            end_time: 结束时间
            exchange: 交易所名称
            
        Returns:
            List[Dict]: K线数据列表
        """
        try:
            if end_time is None:
                end_time = datetime.now()
            if start_time is None:
                start_time = end_time - timedelta(days=30)
            
            # 计算时间间隔
            interval_minutes = {
                "1m": 1, "5m": 5, "15m": 15, "30m": 30,
                "1h": 60, "4h": 240, "1d": 1440
            }.get(interval, 60)
            
            # 生成模拟K线数据
            klines = []
            current_time = start_time
            base_price = 50000.0
            
            while current_time <= end_time:
                # 模拟价格波动
                price_change = (hash(str(current_time)) % 1000 - 500) / 100
                open_price = base_price + price_change
                close_price = open_price + (hash(str(current_time + timedelta(1))) % 200 - 100) / 50
                high_price = max(open_price, close_price) + abs(hash(str(current_time + timedelta(2))) % 100) / 100
                low_price = min(open_price, close_price) - abs(hash(str(current_time + timedelta(3))) % 100) / 100
                volume = 1000 + abs(hash(str(current_time + timedelta(4))) % 50000)
                
                kline = {
                    "timestamp": current_time.isoformat(),
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 2),
                    "symbol": symbol,
                    "exchange": exchange
                }
                klines.append(kline)
                
                current_time += timedelta(minutes=interval_minutes)
                base_price = close_price  # 下一个K线的基础价格
            
            logger.debug(f"📊 Historical data fetched: {symbol} ({len(klines)} klines)")
            return klines
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch historical data for {symbol}: {e}")
            return []
    
    async def get_market_summary(self, exchange: str = "binance") -> Dict:
        """获取市场概览"""
        try:
            # 主要加密货币
            major_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
            
            # 批量获取价格
            price_data = await self.get_multiple_prices(major_symbols, exchange)
            
            # 计算市场统计
            total_volume = 0
            price_changes = []
            
            market_data = {}
            for symbol, data in price_data.items():
                if data:
                    market_data[symbol] = {
                        "price": data.price,
                        "change_24h": data.change_24h,
                        "change_percent_24h": data.change_percent_24h,
                        "volume": data.volume
                    }
                    total_volume += data.volume
                    price_changes.append(data.change_percent_24h)
            
            # 市场趋势分析
            avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
            market_sentiment = "BULLISH" if avg_change > 1 else "BEARISH" if avg_change < -1 else "NEUTRAL"
            
            return {
                "exchange": exchange,
                "timestamp": datetime.now().isoformat(),
                "market_data": market_data,
                "market_summary": {
                    "total_volume": total_volume,
                    "average_change_24h": avg_change,
                    "market_sentiment": market_sentiment,
                    "active_symbols": len(market_data)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch market summary: {e}")
            return {}
    
    async def _fetch_price_data(self, symbol: str, exchange: str) -> MarketData:
        """模拟获取价格数据"""
        # 在实际实现中，这里会调用具体交易所的API
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        # 模拟数据
        base_price = 50000.0 if "BTC" in symbol else 3000.0 if "ETH" in symbol else 1.0
        price_change = (hash(symbol + str(datetime.now().minute)) % 1000 - 500) / 100
        current_price = base_price + price_change
        
        return MarketData(
            symbol=symbol,
            price=current_price,
            volume=1000000 + abs(hash(symbol) % 500000),
            change_24h=price_change,
            change_percent_24h=price_change / base_price * 100,
            high_24h=current_price + 500,
            low_24h=current_price - 300,
            timestamp=datetime.now(),
            exchange=exchange
        )
    
    async def cleanup_cache(self):
        """清理过期缓存"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, (data, cache_time) in self.price_cache.items():
            if (current_time - cache_time).seconds > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.price_cache[key]
        
        logger.debug(f"🧹 Cleaned {len(expired_keys)} expired cache entries") 