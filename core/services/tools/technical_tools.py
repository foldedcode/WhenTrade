"""
技术分析工具服务

提供加密货币价格数据获取和技术指标计算功能
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class TechnicalAnalysisTools:
    """技术分析工具类"""
    
    # 加密货币符号映射（与Yahoo Finance兼容）
    CRYPTO_SYMBOLS = {
        'BTC': 'BTC-USD',
        'ETH': 'ETH-USD', 
        'ADA': 'ADA-USD',
        'SOL': 'SOL-USD',
        'DOT': 'DOT-USD',
        'AVAX': 'AVAX-USD',
        'MATIC': 'MATIC-USD',
        'LINK': 'LINK-USD',
        'UNI': 'UNI-USD',
        'ATOM': 'ATOM-USD',
    }
    
    @classmethod
    def get_crypto_price_from_coingecko(
        cls,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        使用 CoinGecko API 获取加密货币价格数据
        注意：CoinGecko免费API不支持自定义interval，数据粒度自动决定
        
        Args:
            symbol: 加密货币符号 (如 'BTC', 'ETH')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            interval: 时间间隔 (CoinGecko不支持指定，自动决定)
            
        Returns:
            包含价格数据的字典，格式与YFinance兼容
        """
        from .coingecko_tools import CoinGeckoTools
        from datetime import datetime, timedelta
        
        try:
            # 检查是否需要分钟级数据
            if interval in ['5m', '15m', '30m']:
                # CoinGecko只能为"最近1天"提供5分钟数据
                # 检查请求的时间跨度
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                date_range_days = (end_dt - start_dt).days
                
                # 🔧 Linus式修复：允许1天范围的5分钟数据请求
                # CoinGecko可以提供"从现在开始往前1天"的5分钟数据
                logger.info(f"🔍 CoinGecko判断：{start_date}到{end_date}，跨度{date_range_days}天，interval={interval}")
                if date_range_days > 1:  # 修复：只有超过1天才返回错误
                    return {
                        "error": "CoinGecko cannot provide minute-level data for multi-day ranges",
                        "symbol": symbol,
                        "data_source": "coingecko",
                        "fallback_reason": "multi_day_minute_data_not_supported"
                    }
                
                # 对于1天范围的5分钟数据，让CoinGecko处理
                logger.info(f"📊 CoinGecko处理5分钟数据请求：{symbol}，范围{date_range_days}天")
            
            # 检查是否需要小时级数据
            if interval in ['1h', '2h', '4h', '6h']:
                # CoinGecko免费版不支持指定interval，让YFinance处理
                return {
                    "error": "CoinGecko cannot specify hourly intervals",
                    "symbol": symbol,
                    "data_source": "coingecko",
                    "fallback_reason": "specific_interval_not_supported"
                }
            
            # 计算需要获取的天数
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # CoinGecko的days参数是"从现在往前多少天"
            days_from_now = (datetime.now().date() - start_dt.date()).days
            days = min(days_from_now + 1, 365)  # 最多365天
            
            # 获取 CoinGecko 数据
            cg_data = CoinGeckoTools.get_historical_prices(
                symbol=symbol,
                days=days,
                vs_currency='usd'
            )
            
            if 'error' in cg_data:
                return {
                    "error": cg_data['error'],
                    "symbol": symbol,
                    "data_source": "coingecko"
                }
            
            # 获取价格和成交量数据
            prices_data = cg_data.get('prices', [])
            volumes_data = cg_data.get('volumes', [])
            
            if not prices_data:
                return {
                    "error": f"No price data found for {symbol}",
                    "symbol": symbol,
                    "data_source": "coingecko"
                }
            
            # 创建成交量映射
            volume_map = {}
            for vol in volumes_data:
                if isinstance(vol, dict) and 'timestamp' in vol:
                    date_str = datetime.fromtimestamp(vol['timestamp']/1000).strftime('%Y-%m-%d %H:%M')
                    volume_map[date_str] = vol.get('volume', 0)
            
            # 构造 OHLC 数据（不过滤日期，使用所有数据点）
            records = []
            for timestamp, price in prices_data:
                date_obj = datetime.fromtimestamp(timestamp / 1000)
                date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                
                records.append({
                    'Date': date_str,
                    'Open': round(price, 2),
                    'High': round(price, 2),  # CoinGecko只有单价格点，用同一价格填充
                    'Low': round(price, 2),
                    'Close': round(price, 2),
                    'Adj Close': round(price, 2),
                    'Volume': volume_map.get(date_str, 0)  # 使用真实成交量
                })
            
            # 返回所有数据点
            if records:
                logger.info(f"✅ CoinGecko成功获取{symbol}数据：{len(records)}个数据点，间隔{interval}")
                return {
                    "symbol": symbol,
                    "coin_id": cg_data.get('coin_id'),
                    "start_date": start_date,
                    "end_date": end_date,
                    "interval": interval,
                    "actual_interval": "auto",  # CoinGecko自动决定
                    "total_records": len(records),
                    "data": records,
                    "latest_price": records[-1]['Close'],
                    "price_change": round(records[-1]['Close'] - records[0]['Close'], 2),
                    "price_change_pct": round((records[-1]['Close'] / records[0]['Close'] - 1) * 100, 2),
                    "data_source": "coingecko"
                }
            else:
                return {
                    "error": f"No data processed for {symbol}",
                    "symbol": symbol,
                    "data_source": "coingecko"
                }
            
        except Exception as e:
            logger.error(f"Error fetching CoinGecko price data for {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "data_source": "coingecko"
            }

    @classmethod
    def get_crypto_price_from_yfinance(
        cls,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        使用 YFinance API 获取加密货币价格数据
        增强：智能降级功能，当5分钟数据不足时自动降级到更大间隔
        
        Args:
            symbol: 加密货币符号 (如 'BTC', 'ETH')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            interval: 时间间隔 ('1d', '1h', '5m' 等)
            
        Returns:
            包含价格数据的字典
        """
        from .retry_handler import retry_on_error
        from .rate_limiter import rate_limit
        from datetime import datetime, timedelta
        
        @rate_limit(api_name='yfinance')
        @retry_on_error(api_name='yfinance')
        def _fetch_price_data(actual_interval, actual_start_date, actual_end_date):
            # 转换符号格式
            yf_symbol = cls.CRYPTO_SYMBOLS.get(symbol.upper(), f"{symbol.upper()}-USD")
            
            # 获取数据
            ticker = yf.Ticker(yf_symbol)
            data = ticker.history(start=actual_start_date, end=actual_end_date, interval=actual_interval)
            
            if data.empty:
                return {
                    "error": f"No data found for {symbol} with {actual_interval} interval",
                    "symbol": symbol,
                    "yf_symbol": yf_symbol,
                    "attempted_interval": actual_interval
                }
            
            # 清理数据
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            
            # 🔧 Linus式修复：包含Volume列在数值处理中
            numeric_columns = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
            for col in numeric_columns:
                if col in data.columns:
                    if col == "Volume":
                        # Volume保持整数，不需要小数位
                        data[col] = data[col].round(0).astype('int64')
                        logger.debug(f"🔧 Volume列已处理: {data[col].head(3).tolist()}")
                    else:
                        # 价格数据保留2位小数
                        data[col] = data[col].round(2)
            
            # 转换为字典格式
            result = {
                "symbol": symbol,
                "yf_symbol": yf_symbol,
                "start_date": actual_start_date,
                "end_date": actual_end_date,
                "interval": actual_interval,
                "original_interval": interval,  # 记录原始请求的间隔
                "total_records": len(data),
                "data": data.to_dict('records'),
                "latest_price": float(data['Close'].iloc[-1]) if not data.empty else None,
                "price_change": float(data['Close'].iloc[-1] - data['Close'].iloc[0]) if len(data) > 1 else 0,
                "price_change_pct": float((data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100) if len(data) > 1 else 0,
                "data_source": "yfinance"
            }
            
            # 🔧 日志记录Volume数据状态
            if 'Volume' in data.columns and not data['Volume'].isna().all():
                avg_volume = data['Volume'].mean()
                logger.info(f"✅ YFinance Volume数据获取成功，平均成交量: {avg_volume:,.0f}")
            else:
                logger.warning("⚠️ YFinance Volume数据缺失或全为NaN")
            
            return result
        
        try:
            # 🔧 Linus式智能降级：消除5分钟数据不足的特殊情况
            min_required_points = 200
            
            # 定义降级序列
            downgrade_sequence = [
                {'interval': interval, 'days_extend': 0},
                {'interval': '15m', 'days_extend': 3},   # 15分钟，扩展3天
                {'interval': '30m', 'days_extend': 7},   # 30分钟，扩展7天  
                {'interval': '1h', 'days_extend': 10},   # 1小时，扩展10天
                {'interval': '2h', 'days_extend': 20}    # 2小时，扩展20天
            ]
            
            logger.info(f"📊 YFinance获取{symbol}数据，原始间隔：{interval}")
            
            for attempt, config in enumerate(downgrade_sequence):
                current_interval = config['interval']
                days_extend = config['days_extend']
                
                # 计算扩展后的开始日期
                if days_extend > 0:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=days_extend)
                    extended_start_date = start_dt.strftime('%Y-%m-%d')
                else:
                    extended_start_date = start_date
                
                logger.info(f"🔄 尝试{attempt+1}: {current_interval}间隔，时间范围{extended_start_date}到{end_date}")
                
                result = _fetch_price_data(current_interval, extended_start_date, end_date)
                
                if 'error' not in result:
                    data_points = result['total_records']
                    logger.info(f"📈 获得{data_points}个数据点")
                    
                    # 🔧 Linus式修复：所有尝试都必须检查数据点充足性
                    if data_points >= min_required_points:
                        if attempt > 0:
                            result['downgraded_from'] = interval
                            result['downgrade_reason'] = f"原始{interval}间隔数据不足"
                            logger.warning(f"⚠️ YFinance降级：{interval} → {current_interval}，数据点：{data_points}")
                        else:
                            logger.info(f"✅ YFinance原始间隔成功：{current_interval}，数据点：{data_points}")
                        return result
                    else:
                        # 如果是最后一次尝试，即使数据点不足也要返回
                        if attempt == len(downgrade_sequence) - 1:
                            logger.warning(f"⚠️ 最后一次尝试{current_interval}，数据点({data_points})不足{min_required_points}，但仍返回结果")
                            result['insufficient_data_warning'] = f"数据点不足：{data_points}/{min_required_points}"
                            return result
                        else:
                            logger.info(f"⏭️ {current_interval}数据点({data_points})仍不足{min_required_points}，继续降级")
                else:
                    logger.warning(f"⚠️ {current_interval}间隔获取失败：{result.get('error', 'unknown error')}")
            
            # 所有尝试都失败
            logger.error(f"❌ YFinance所有降级尝试均失败")
            return {
                "error": f"YFinance unable to fetch sufficient data for {symbol}",
                "symbol": symbol,
                "data_source": "yfinance",
                "attempted_intervals": [config['interval'] for config in downgrade_sequence]
            }
            
        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "data_source": "yfinance"
            }

    @classmethod
    def get_crypto_price_data(
        cls,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        获取加密货币价格数据，使用CoinGecko作为主要数据源，YFinance作为备用
        
        Args:
            symbol: 加密货币符号 (如 'BTC', 'ETH')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            interval: 时间间隔 ('1d', '1h', '5m' 等)
            
        Returns:
            包含价格数据的字典
        """
        from .api_executor import APIExecutor
        
        # 使用现有的 API 执行器和故障转移机制
        executor = APIExecutor()
        
        def coingecko_call():
            return cls.get_crypto_price_from_coingecko(symbol, start_date, end_date, interval)
        
        def yfinance_call():
            return cls.get_crypto_price_from_yfinance(symbol, start_date, end_date, interval)
        
        # 使用故障转移机制：CoinGecko 主要，YFinance 备用
        result = executor.call_with_fallback(
            tool_name=f'get_crypto_price_data_{symbol}',
            primary_func=coingecko_call,
            fallback_func=yfinance_call,
            primary_api='coingecko',
            fallback_api='yfinance'
        )
        
        return result
    
    @classmethod
    def calculate_technical_indicators(
        cls,
        symbol: str,
        indicators: List[str],
        period_days: int = 30,
        price_data: Optional[Dict] = None,
        interval: str = None
    ) -> Dict[str, Any]:
        """
        计算技术指标
        
        Args:
            symbol: 加密货币符号
            indicators: 指标列表 ['sma', 'ema', 'rsi', 'macd', 'bb']
            period_days: 计算周期（天数）
            price_data: 可选的价格数据，如果提供则不会重复请求API
            interval: 数据间隔，用于智能选择K线周期
            
        Returns:
            包含技术指标的字典
        """
        try:
            # 如果没有提供价格数据，才调用API获取
            if price_data is None:
                logger.info(f"📊 获取{symbol}价格数据用于技术指标计算")
                
                # 智能计算所需数据点数
                required_points = cls._calculate_required_points(indicators)
                logger.info(f"🔢 指标 {indicators} 需要 {required_points} 个数据点")
                
                # 根据 period_days 智能选择数据间隔和获取天数
                if period_days <= 2:
                    # 1-2天：需要5分钟K线数据
                    interval = interval or '5m'
                    # 获取今天+昨天的数据，确保有足够数据点计算指标
                    fetch_days = max(2, period_days)  # 至少2天数据
                    logger.info(f"📅 短期分析(1-2天)：使用{interval}间隔，获取{fetch_days}天数据")
                    
                elif period_days <= 7:
                    # 1周：使用15分钟或30分钟K线
                    interval = interval or '15m'
                    # 获取足够的历史数据
                    fetch_days = max(7, required_points // 96 + 1)  # 15分钟K线每天96个点
                    logger.info(f"📅 短期分析(1周)：使用{interval}间隔，获取{fetch_days}天数据")
                    
                elif period_days <= 30:
                    # 1月：使用1小时K线
                    interval = interval or '1h'
                    # 获取足够的历史数据
                    fetch_days = max(30, required_points // 24 + 1)  # 1小时K线每天24个点
                    logger.info(f"📅 中期分析(1月)：使用{interval}间隔，获取{fetch_days}天数据")
                    
                else:
                    # 长期（1年及以上）：使用日K线
                    interval = interval or '1d'
                    # 获取充足的历史数据
                    fetch_days = max(365, required_points + 50)
                    logger.info(f"📅 长期分析(1年+)：使用{interval}间隔，获取{fetch_days}天数据")
                
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=fetch_days)).strftime('%Y-%m-%d')
                
                # 传递正确的 interval 参数
                price_data = cls.get_crypto_price_data(symbol, start_date, end_date, interval)
                logger.info(f"📊 实际获取数据：从{start_date}到{end_date}，间隔{interval}")
            else:
                logger.info(f"♻️ 使用已获取的{symbol}价格数据计算技术指标")
            
            if not price_data:
                return {"error": "No price data available", "symbol": symbol}
            
            if 'error' in price_data:
                return price_data
            
            # 🔧 调试：记录实际数据格式和来源
            logger.info(f"📊 price_data格式检查: data字段={bool('data' in price_data)}, prices字段={bool('prices' in price_data)}, 数据源={price_data.get('data_source', 'unknown')}")
            if 'data' in price_data:
                logger.info(f"📊 YFinance数据长度: {len(price_data['data']) if isinstance(price_data.get('data'), list) else 'Not List'}")
            if 'prices' in price_data:
                logger.info(f"📊 CoinGecko数据长度: {len(price_data['prices']) if isinstance(price_data.get('prices'), list) else 'Not List'}")
            
            # 灵活处理不同格式的价格数据
            if 'data' in price_data and isinstance(price_data['data'], list):
                # YFinance格式：有data字段
                logger.warning(f"⚠️ 使用YFinance数据，数据点：{len(price_data['data'])}")
                df = pd.DataFrame(price_data['data'])
                df.index = pd.to_datetime(df.index) if 'index' in df.columns else pd.date_range(start=datetime.now() - timedelta(days=len(df)), periods=len(df), freq='D')
            elif 'prices' in price_data and isinstance(price_data['prices'], list):
                # CoinGecko格式：有prices字段
                prices = price_data['prices']
                volumes = price_data.get('volumes', [])  # 获取成交量数据
                
                # 🔧 Linus式修复：检测数据格式，字典列表 vs 嵌套列表
                if prices and isinstance(prices[0], dict):
                    # CoinGecko新格式：[{'timestamp': xxx, 'price': yyy}, ...]
                    logger.info(f"📊 检测到CoinGecko字典格式数据：{len(prices)}个数据点")
                    df = pd.DataFrame(prices)
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('timestamp', inplace=True)
                    if 'price' in df.columns:
                        df['Close'] = df['price']
                else:
                    # 原始格式：[[timestamp, price], ...]
                    logger.info(f"📊 检测到CoinGecko嵌套列表格式数据：{len(prices)}个数据点")
                    df = pd.DataFrame(prices, columns=['timestamp', 'Close'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                
                # 🔧 修复成交量数据：使用CoinGecko实际返回的成交量
                if volumes:
                    logger.info(f"📊 检测到成交量数据：{len(volumes)}个数据点")
                    if isinstance(volumes[0], dict):
                        # 字典格式：[{'timestamp': xxx, 'volume': yyy}]
                        volume_df = pd.DataFrame(volumes)
                        if 'timestamp' in volume_df.columns and 'volume' in volume_df.columns:
                            volume_df['timestamp'] = pd.to_datetime(volume_df['timestamp'], unit='ms')
                            volume_df.set_index('timestamp', inplace=True)
                            df = df.join(volume_df[['volume']].rename(columns={'volume': 'Volume'}), how='left')
                    elif isinstance(volumes[0], list):
                        # 嵌套列表格式：[[timestamp, volume]]
                        volume_df = pd.DataFrame(volumes, columns=['timestamp', 'Volume'])
                        volume_df['timestamp'] = pd.to_datetime(volume_df['timestamp'], unit='ms')
                        volume_df.set_index('timestamp', inplace=True)
                        df = df.join(volume_df[['Volume']], how='left')
                
                # 如果没有成交量数据或合并失败，设置为0
                if 'Volume' not in df.columns or df['Volume'].isna().all():
                    df['Volume'] = 0
                    logger.warning("⚠️ 未获取到有效成交量数据，设置为0")
                else:
                    logger.info(f"✅ 成功获取成交量数据，平均成交量: {df['Volume'].mean():.0f}")
                
                # 为技术指标计算添加必要的列（使用Close价格）
                df['Open'] = df['Close']
                df['High'] = df['Close'] 
                df['Low'] = df['Close']
            else:
                # 尝试直接转换为DataFrame
                df = pd.DataFrame(price_data)
            
            if df.empty:
                return {"error": "No data available for technical analysis"}
            
            # 确保有Close列用于技术指标计算
            if 'Close' not in df.columns and 'close' in df.columns:
                df['Close'] = df['close']
            elif 'Close' not in df.columns:
                return {"error": "Price data missing Close column for technical analysis"}
            
            # 🔧 Linus式数据清洗：消除NaN/Inf特殊情况，确保计算质量
            original_count = len(df)
            
            # 诊断数据质量问题
            nan_count = df['Close'].isna().sum()
            inf_count = (np.isinf(df['Close']).sum() if df['Close'].dtype in ['float64', 'float32'] else 0)
            
            if nan_count > 0 or inf_count > 0:
                logger.warning(f"📊 数据质量问题：{nan_count}个NaN值，{inf_count}个Inf值（总共{original_count}个数据点）")
                # 检查数据样本
                logger.debug(f"Close列前5个值: {df['Close'].head().tolist()}")
                logger.debug(f"Close列后5个值: {df['Close'].tail().tolist()}")
            
            # 清理无穷值和NaN值
            df = df.replace([np.inf, -np.inf], np.nan)  # 无穷值转为NaN
            df = df.dropna(subset=['Close'])  # 移除Close列为NaN的行
            
            cleaned_count = len(df)
            if cleaned_count != original_count:
                logger.warning(f"🧹 数据清洗：移除{original_count - cleaned_count}个无效数据点，剩余{cleaned_count}个")
                if cleaned_count == 0:
                    logger.error("❌ 致命错误：所有数据点都被清洗掉了，可能是数据格式问题")
            
            if df.empty:
                return {"error": "No valid price data after cleaning", "original_count": original_count}
            
            results = {
                "symbol": symbol,
                "calculation_date": datetime.now().strftime('%Y-%m-%d'),
                "period_days": period_days,
                "indicators": {},
                "data_source": price_data.get('data_source', 'unknown'),
                "data_points": cleaned_count,  # 使用清洗后的数据量
                "original_data_points": original_count,  # 记录原始数据量
                "warnings": []
            }
            
            logger.info(f"📊 清洗后数据点: {cleaned_count}（原始:{original_count}），开始计算技术指标")
            
            # 计算各种技术指标，带数据充足性验证
            for indicator in indicators:
                try:
                    if indicator.lower() == 'sma':
                        # SMA 降级处理：优先计算更高期数的指标
                        if len(df) >= 200:
                            results["indicators"]["sma_200"] = cls._calculate_sma(df['Close'], 200)
                        elif len(df) < 200:
                            results["warnings"].append(f"SMA200需要200个数据点，实际只有{len(df)}个，无法计算")
                            
                        if len(df) >= 50:
                            results["indicators"]["sma_50"] = cls._calculate_sma(df['Close'], 50)
                        elif len(df) < 50:
                            results["warnings"].append(f"SMA50需要50个数据点，实际只有{len(df)}个，无法计算")
                            
                        # 🔧 Linus式修复：诚实的日志，不要撒谎
                        results["indicators"]["sma_20"] = cls._calculate_sma(df['Close'], 20)
                        if results["indicators"]["sma_20"] == 0.0:
                            logger.warning(f"⚠️ SMA20计算失败：数据不足({len(df)}/20个点)")
                            results["warnings"].append(f"SMA20需要20个数据点，实际只有{len(df)}个，返回默认值0")
                        else:
                            logger.info(f"✅ SMA20计算成功: {results['indicators']['sma_20']:.2f}")
                    
                    elif indicator.lower() == 'ema':
                        # 🔧 Linus式修复：诚实的日志，不要撒谎
                        results["indicators"]["ema_26"] = cls._calculate_ema(df['Close'], 26)
                        if results["indicators"]["ema_26"] == 0.0:
                            logger.warning(f"⚠️ EMA26计算失败：数据不足({len(df)}/26个点)")
                            results["warnings"].append(f"EMA26需要26个数据点，实际只有{len(df)}个，返回默认值0")
                        else:
                            logger.info(f"✅ EMA26计算成功: {results['indicators']['ema_26']:.2f}")
                            
                        results["indicators"]["ema_12"] = cls._calculate_ema(df['Close'], 12)
                        if results["indicators"]["ema_12"] == 0.0:
                            logger.warning(f"⚠️ EMA12计算失败：数据不足({len(df)}/12个点)")
                            results["warnings"].append(f"EMA12需要12个数据点，实际只有{len(df)}个，返回默认值0")
                        else:
                            logger.info(f"✅ EMA12计算成功: {results['indicators']['ema_12']:.2f}")
                    
                    elif indicator.lower() == 'rsi':
                        # 🔧 Linus式修复：诚实的日志，不要撒谎  
                        results["indicators"]["rsi"] = cls._calculate_rsi(df['Close'], 14)
                        if results["indicators"]["rsi"] == 50.0:
                            logger.warning(f"⚠️ RSI计算失败：数据不足({len(df)}/15个点)")
                            results["warnings"].append(f"RSI需要15个数据点，实际只有{len(df)}个，返回中性值50")
                        else:
                            logger.info(f"✅ RSI计算成功: {results['indicators']['rsi']:.2f}")
                    
                    elif indicator.lower() == 'macd':
                        # 🔧 Linus式修复：诚实的日志，不要撒谎
                        macd_data = cls._calculate_macd(df['Close'])
                        results["indicators"].update(macd_data)
                        if macd_data["macd"] == 0.0:
                            logger.warning(f"⚠️ MACD计算失败：数据不足({len(df)}/35个点)")
                            results["warnings"].append(f"MACD需要35个数据点，实际只有{len(df)}个，返回默认值0")
                        else:
                            logger.info(f"✅ MACD计算成功: {macd_data['macd']:.4f}")
                    
                    elif indicator.lower() == 'bb':
                        # 🔧 Linus式修复：诚实的日志，不要撒谎
                        bb_data = cls._calculate_bollinger_bands(df['Close'], 20, 2)
                        results["indicators"].update(bb_data)
                        if bb_data["bb_upper"] == 0.0:
                            logger.warning(f"⚠️ 布林带计算失败：数据不足({len(df)}/20个点)")
                            results["warnings"].append(f"布林带需要20个数据点，实际只有{len(df)}个，返回默认值0")
                        else:
                            logger.info(f"✅ 布林带计算成功: 上轨{bb_data['bb_upper']:.2f}, 下轨{bb_data['bb_lower']:.2f}")
                        
                except Exception as e:
                    logger.warning(f"Error calculating {indicator} for {symbol}: {e}")
                    results["indicators"][indicator] = f"Error: {str(e)}"
            
            # 记录警告信息
            if results["warnings"]:
                logger.warning(f"⚠️ 技术指标计算警告: {'; '.join(results['warnings'])}")
            
            # 🔧 Linus式修复：统一处理成交量数据，支持YFinance和CoinGecko
            if price_data:
                # YFinance数据：从data字段的Volume列获取成交量
                if 'data' in price_data and isinstance(price_data['data'], list):
                    volumes_from_data = []
                    for record in price_data['data']:
                        if isinstance(record, dict) and 'Volume' in record and record['Volume'] > 0:
                            volumes_from_data.append(record['Volume'])
                    
                    if volumes_from_data:
                        total_volume = sum(volumes_from_data)
                        latest_volume = volumes_from_data[-1]
                        
                        results["indicators"]["total_volume_period"] = float(total_volume)
                        results["indicators"]["latest_volume_24h"] = float(latest_volume)
                        results["indicators"]["volume_data_points"] = len(volumes_from_data)
                        
                        logger.info(f"✅ YFinance成交量数据已添加: 总量{total_volume:.0f}, 最新24h{latest_volume:.0f}, 数据点{len(volumes_from_data)}个")
                    else:
                        logger.warning("⚠️ YFinance数据中Volume列为空或全为0")
                
                # CoinGecko数据：从volumes字段获取成交量
                elif 'volumes' in price_data:
                    volumes = price_data['volumes']
                    if volumes:
                        # 计算时间范围内的总成交量
                        total_volume = sum(vol['volume'] if isinstance(vol, dict) else vol[1] for vol in volumes)
                        latest_volume = volumes[-1]['volume'] if isinstance(volumes[-1], dict) else volumes[-1][1]
                        
                        results["indicators"]["total_volume_period"] = float(total_volume)
                        results["indicators"]["latest_volume_24h"] = float(latest_volume)
                        results["indicators"]["volume_data_points"] = len(volumes)
                        
                        logger.info(f"✅ CoinGecko成交量数据已添加: 总量{total_volume:.0f}, 最新24h{latest_volume:.0f}, 数据点{len(volumes)}个")
                    else:
                        logger.warning("⚠️ CoinGecko成交量数据为空")
                else:
                    logger.warning("⚠️ price_data中既没有volumes字段也没有data字段中的Volume列")
            else:
                logger.warning("⚠️ price_data为空")
            
            # 记录成功计算的指标
            calculated_indicators = [k for k, v in results["indicators"].items() if v is not None and not str(v).startswith("Error")]
            logger.info(f"✅ 成功计算 {len(calculated_indicators)} 个技术指标: {calculated_indicators}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators for {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol
            }
    
    @staticmethod
    def _calculate_required_points(indicators: List[str]) -> int:
        """计算指标所需的最小数据点数"""
        requirements = {
            'sma': 200,  # SMA200 需要200个点
            'ema': 26,   # EMA26 需要26个点  
            'rsi': 15,   # RSI14 需要15个点
            'macd': 35,  # MACD(26+9) 需要35个点
            'bb': 20     # BB20 需要20个点
        }
        
        max_points = 50  # 默认最小值
        for indicator in indicators:
            max_points = max(max_points, requirements.get(indicator.lower(), 50))
        
        return max_points

    @staticmethod
    def _calculate_sma(prices: pd.Series, window: int) -> float:
        """计算简单移动平均线"""
        if len(prices) < window:
            # 🔧 Linus式修复：返回0而非None，消除特殊情况
            return 0.0
        return float(prices.rolling(window=window).mean().iloc[-1])
    
    @staticmethod
    def _calculate_ema(prices: pd.Series, span: int) -> float:
        """计算指数移动平均线"""
        if len(prices) < span:
            # 🔧 Linus式修复：返回0而非None，消除特殊情况
            return 0.0
        return float(prices.ewm(span=span).mean().iloc[-1])
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, window: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < window + 1:
            # 🔧 Linus式修复：返回50（中性值）而非None，消除特殊情况
            return 50.0
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1])
    
    @staticmethod
    def _calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """计算MACD指标"""
        if len(prices) < slow + signal:
            # 🔧 Linus式修复：返回零值而非None，消除特殊情况
            return {"macd": 0.0, "macd_signal": 0.0, "macd_histogram": 0.0}
        
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        
        return {
            "macd": float(macd.iloc[-1]),
            "macd_signal": float(macd_signal.iloc[-1]),
            "macd_histogram": float(macd_histogram.iloc[-1])
        }
    
    @staticmethod
    def _calculate_bollinger_bands(prices: pd.Series, window: int = 20, num_std: int = 2) -> Dict[str, float]:
        """计算布林带指标"""
        if len(prices) < window:
            # 🔧 修复：返回0而非None，避免前端显示NaN - Linus式消除特殊情况
            return {"bb_upper": 0, "bb_middle": 0, "bb_lower": 0}
        
        rolling_mean = prices.rolling(window=window).mean()
        rolling_std = prices.rolling(window=window).std()
        
        bb_upper = rolling_mean + (rolling_std * num_std)
        bb_lower = rolling_mean - (rolling_std * num_std)
        
        return {
            "bb_upper": float(bb_upper.iloc[-1]),
            "bb_middle": float(rolling_mean.iloc[-1]),
            "bb_lower": float(bb_lower.iloc[-1])
        }


# 便捷函数接口
def get_crypto_price_data(symbol: str, start_date: str, end_date: str, interval: str = "1d") -> Dict[str, Any]:
    """获取加密货币价格数据"""
    return TechnicalAnalysisTools.get_crypto_price_data(symbol, start_date, end_date, interval)


def calculate_technical_indicators(
    symbol: str, 
    indicators: List[str], 
    period_days: int = 30,
    price_data: Optional[Dict] = None,
    interval: str = None
) -> Dict[str, Any]:
    """计算技术指标"""
    return TechnicalAnalysisTools.calculate_technical_indicators(
        symbol, 
        indicators, 
        period_days,
        price_data,
        interval
    )