"""
加密货币技术指标工具
提供专门针对加密货币市场的技术分析指标
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CryptoIndicatorBase:
    """加密货币指标基类"""
    
    def __init__(self, symbol: str, timeframe: str = "1h"):
        self.symbol = symbol
        self.timeframe = timeframe
        
    async def get_market_data(self, period: int) -> Dict[str, Any]:
        """获取市场数据"""
        # TODO: 从DataGateway获取数据
        # 这里返回模拟数据
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period": period,
            "prices": self._generate_mock_prices(period),
            "volumes": self._generate_mock_volumes(period),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def _generate_mock_prices(self, period: int) -> List[float]:
        """生成模拟价格数据"""
        base_price = 50000 if "BTC" in self.symbol else 3000
        return [base_price + np.random.randn() * base_price * 0.02 for _ in range(period)]
        
    def _generate_mock_volumes(self, period: int) -> List[float]:
        """生成模拟成交量数据"""
        base_volume = 1000000
        return [base_volume + np.random.randn() * base_volume * 0.3 for _ in range(period)]


class RSIIndicator(CryptoIndicatorBase):
    """
    相对强弱指标 (RSI)
    专门针对加密货币的高波动性进行优化
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", period: int = 14):
        super().__init__(symbol, timeframe)
        self.period = period
        
    async def calculate(self) -> Dict[str, Any]:
        """计算RSI指标"""
        try:
            # 获取市场数据
            data = await self.get_market_data(self.period * 2)
            prices = data["prices"]
            
            # 计算价格变化
            deltas = np.diff(prices)
            gains = deltas.copy()
            losses = deltas.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = abs(losses)
            
            # 计算平均收益和损失
            avg_gain = np.mean(gains[:self.period])
            avg_loss = np.mean(losses[:self.period])
            
            # 计算RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
            # 加密货币特定的解释
            interpretation = self._interpret_rsi(rsi)
            
            return {
                "indicator": "RSI",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "period": self.period,
                "value": round(rsi, 2),
                "interpretation": interpretation,
                "signals": self._generate_signals(rsi),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            raise
            
    def _interpret_rsi(self, rsi: float) -> str:
        """解释RSI值（针对加密货币调整阈值）"""
        if rsi >= 80:
            return "极度超买 - 考虑到加密货币的高波动性，可能出现回调"
        elif rsi >= 70:
            return "超买 - 上涨动能强劲，但需要警惕"
        elif rsi <= 20:
            return "极度超卖 - 可能存在反弹机会"
        elif rsi <= 30:
            return "超卖 - 下跌动能减弱"
        else:
            return "中性区域 - 等待明确信号"
            
    def _generate_signals(self, rsi: float) -> List[str]:
        """生成交易信号"""
        signals = []
        
        if rsi >= 80:
            signals.append("卖出信号 - RSI极度超买")
        elif rsi <= 20:
            signals.append("买入信号 - RSI极度超卖")
            
        if 45 <= rsi <= 55:
            signals.append("观望 - RSI处于中性区域")
            
        return signals


class MACDIndicator(CryptoIndicatorBase):
    """
    MACD指标
    针对加密货币24/7交易特性优化
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", 
                 fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(symbol, timeframe)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
    async def calculate(self) -> Dict[str, Any]:
        """计算MACD指标"""
        try:
            # 获取足够的历史数据
            data = await self.get_market_data(self.slow_period * 2)
            prices = np.array(data["prices"])
            
            # 计算EMA
            ema_fast = self._calculate_ema(prices, self.fast_period)
            ema_slow = self._calculate_ema(prices, self.slow_period)
            
            # 计算MACD线
            macd_line = ema_fast - ema_slow
            
            # 计算信号线
            signal_line = self._calculate_ema(macd_line, self.signal_period)
            
            # 计算柱状图
            histogram = macd_line - signal_line
            
            # 获取最新值
            current_macd = macd_line[-1]
            current_signal = signal_line[-1]
            current_histogram = histogram[-1]
            
            return {
                "indicator": "MACD",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "macd": round(current_macd, 4),
                "signal": round(current_signal, 4),
                "histogram": round(current_histogram, 4),
                "interpretation": self._interpret_macd(current_macd, current_signal, current_histogram),
                "signals": self._generate_macd_signals(macd_line, signal_line, histogram),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            raise
            
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均"""
        multiplier = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]
            
        return ema
        
    def _interpret_macd(self, macd: float, signal: float, histogram: float) -> str:
        """解释MACD值"""
        if histogram > 0:
            if macd > signal and macd > 0:
                return "强势上涨 - MACD在零线上方且高于信号线"
            else:
                return "上涨动能增强"
        else:
            if macd < signal and macd < 0:
                return "强势下跌 - MACD在零线下方且低于信号线"
            else:
                return "下跌动能增强"
                
    def _generate_macd_signals(self, macd_line: np.ndarray, signal_line: np.ndarray, 
                              histogram: np.ndarray) -> List[str]:
        """生成MACD交易信号"""
        signals = []
        
        # 检查金叉/死叉
        if len(histogram) >= 2:
            if histogram[-2] < 0 and histogram[-1] > 0:
                signals.append("金叉信号 - MACD向上穿越信号线")
            elif histogram[-2] > 0 and histogram[-1] < 0:
                signals.append("死叉信号 - MACD向下穿越信号线")
                
        # 检查背离
        if len(macd_line) >= 5:
            if macd_line[-1] > macd_line[-3] and macd_line[-3] > macd_line[-5]:
                signals.append("MACD持续上升 - 上涨趋势确认")
            elif macd_line[-1] < macd_line[-3] and macd_line[-3] < macd_line[-5]:
                signals.append("MACD持续下降 - 下跌趋势确认")
                
        return signals


class BollingerBandsIndicator(CryptoIndicatorBase):
    """
    布林带指标
    针对加密货币的高波动性调整参数
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", period: int = 20, std_dev: float = 2.0):
        super().__init__(symbol, timeframe)
        self.period = period
        self.std_dev = std_dev
        
    async def calculate(self) -> Dict[str, Any]:
        """计算布林带"""
        try:
            data = await self.get_market_data(self.period * 2)
            prices = np.array(data["prices"])
            
            # 计算移动平均
            sma = np.mean(prices[-self.period:])
            
            # 计算标准差
            std = np.std(prices[-self.period:])
            
            # 计算布林带
            upper_band = sma + (self.std_dev * std)
            lower_band = sma - (self.std_dev * std)
            
            # 当前价格
            current_price = prices[-1]
            
            # 计算带宽
            band_width = (upper_band - lower_band) / sma * 100
            
            # 计算%B指标
            percent_b = (current_price - lower_band) / (upper_band - lower_band)
            
            return {
                "indicator": "BollingerBands",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "period": self.period,
                "upper_band": round(upper_band, 2),
                "middle_band": round(sma, 2),
                "lower_band": round(lower_band, 2),
                "current_price": round(current_price, 2),
                "band_width": round(band_width, 2),
                "percent_b": round(percent_b, 3),
                "interpretation": self._interpret_bb(current_price, upper_band, lower_band, percent_b),
                "signals": self._generate_bb_signals(current_price, upper_band, lower_band, band_width),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            raise
            
    def _interpret_bb(self, price: float, upper: float, lower: float, percent_b: float) -> str:
        """解释布林带指标"""
        if percent_b > 1:
            return "价格突破上轨 - 强势上涨，但可能超买"
        elif percent_b > 0.8:
            return "价格接近上轨 - 上涨压力增大"
        elif percent_b < 0:
            return "价格突破下轨 - 强势下跌，但可能超卖"
        elif percent_b < 0.2:
            return "价格接近下轨 - 下跌支撑增强"
        else:
            return "价格在布林带中间区域 - 震荡整理"
            
    def _generate_bb_signals(self, price: float, upper: float, lower: float, band_width: float) -> List[str]:
        """生成布林带交易信号"""
        signals = []
        
        if price > upper:
            signals.append("卖出信号 - 价格突破上轨")
        elif price < lower:
            signals.append("买入信号 - 价格突破下轨")
            
        if band_width < 10:
            signals.append("波动率收缩 - 可能出现大幅变动")
        elif band_width > 40:
            signals.append("波动率扩张 - 市场处于高波动期")
            
        return signals


class VolumeProfileIndicator(CryptoIndicatorBase):
    """
    成交量分布指标
    分析加密货币的成交量特征
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", period: int = 24):
        super().__init__(symbol, timeframe)
        self.period = period
        
    async def calculate(self) -> Dict[str, Any]:
        """计算成交量分布"""
        try:
            data = await self.get_market_data(self.period)
            prices = np.array(data["prices"])
            volumes = np.array(data["volumes"])
            
            # 计算价格区间
            price_min = np.min(prices)
            price_max = np.max(prices)
            price_range = price_max - price_min
            
            # 创建价格区间
            num_bins = 10
            bins = np.linspace(price_min, price_max, num_bins + 1)
            
            # 计算每个价格区间的成交量
            volume_profile = {}
            for i in range(num_bins):
                bin_mask = (prices >= bins[i]) & (prices < bins[i + 1])
                bin_volume = np.sum(volumes[bin_mask])
                bin_center = (bins[i] + bins[i + 1]) / 2
                volume_profile[f"{bins[i]:.2f}-{bins[i+1]:.2f}"] = {
                    "volume": float(bin_volume),
                    "percentage": float(bin_volume / np.sum(volumes) * 100)
                }
                
            # 找出成交量最大的价格区间（POC - Point of Control）
            poc_range = max(volume_profile.items(), key=lambda x: x[1]["volume"])[0]
            
            # 计算成交量加权平均价格（VWAP）
            vwap = np.sum(prices * volumes) / np.sum(volumes)
            
            # 分析买卖压力
            current_price = prices[-1]
            above_current = np.sum(volumes[prices > current_price])
            below_current = np.sum(volumes[prices < current_price])
            
            return {
                "indicator": "VolumeProfile",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "period": self.period,
                "volume_profile": volume_profile,
                "poc_range": poc_range,
                "vwap": round(vwap, 2),
                "current_price": round(current_price, 2),
                "buy_pressure": round(below_current / np.sum(volumes) * 100, 2),
                "sell_pressure": round(above_current / np.sum(volumes) * 100, 2),
                "interpretation": self._interpret_volume_profile(current_price, vwap, above_current, below_current),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating Volume Profile: {e}")
            raise
            
    def _interpret_volume_profile(self, price: float, vwap: float, above: float, below: float) -> str:
        """解释成交量分布"""
        if price > vwap:
            if above > below:
                return "价格高于VWAP，上方存在较大卖压"
            else:
                return "价格高于VWAP，下方支撑较强"
        else:
            if below > above:
                return "价格低于VWAP，下方存在较大买压"
            else:
                return "价格低于VWAP，上方阻力较强"