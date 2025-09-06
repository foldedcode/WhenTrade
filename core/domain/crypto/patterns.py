"""
加密货币图表模式识别
识别常见的技术分析图表模式
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PatternRecognizer:
    """图表模式识别基类"""
    
    def __init__(self, symbol: str, timeframe: str = "1h"):
        self.symbol = symbol
        self.timeframe = timeframe
        
    async def get_price_data(self, period: int = 100) -> List[float]:
        """获取价格数据"""
        # TODO: 从DataGateway获取数据
        # 模拟价格数据
        base_price = 50000 if "BTC" in self.symbol else 3000
        trend = np.random.choice([-1, 0, 1])
        prices = []
        
        for i in range(period):
            noise = np.random.randn() * base_price * 0.02
            trend_effect = trend * i * base_price * 0.001
            prices.append(base_price + noise + trend_effect)
            
        return prices


class SupportResistanceDetector(PatternRecognizer):
    """
    支撑阻力位检测器
    识别关键价格水平
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", sensitivity: float = 0.02):
        super().__init__(symbol, timeframe)
        self.sensitivity = sensitivity  # 价格水平的敏感度
        
    async def detect_levels(self) -> Dict[str, Any]:
        """检测支撑和阻力位"""
        try:
            prices = await self.get_price_data(200)
            
            # 找出局部高点和低点
            highs, lows = self._find_pivot_points(prices)
            
            # 聚类相似的价格水平
            resistance_levels = self._cluster_levels(highs)
            support_levels = self._cluster_levels(lows)
            
            # 评估强度
            resistance_strength = self._evaluate_level_strength(resistance_levels, prices)
            support_strength = self._evaluate_level_strength(support_levels, prices)
            
            # 当前价格
            current_price = prices[-1]
            
            # 找出最近的支撑和阻力
            nearest_support = self._find_nearest_level(support_levels, current_price, "below")
            nearest_resistance = self._find_nearest_level(resistance_levels, current_price, "above")
            
            return {
                "analyzer": "SupportResistanceDetector",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "current_price": round(current_price, 2),
                "resistance_levels": [
                    {
                        "price": round(level, 2),
                        "strength": strength,
                        "touches": self._count_touches(level, prices)
                    }
                    for level, strength in zip(resistance_levels, resistance_strength)
                ],
                "support_levels": [
                    {
                        "price": round(level, 2),
                        "strength": strength,
                        "touches": self._count_touches(level, prices)
                    }
                    for level, strength in zip(support_levels, support_strength)
                ],
                "nearest_support": round(nearest_support, 2) if nearest_support else None,
                "nearest_resistance": round(nearest_resistance, 2) if nearest_resistance else None,
                "recommendation": self._generate_sr_recommendation(
                    current_price, nearest_support, nearest_resistance
                ),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting support/resistance: {e}")
            raise
            
    def _find_pivot_points(self, prices: List[float]) -> Tuple[List[float], List[float]]:
        """找出局部高点和低点"""
        highs = []
        lows = []
        
        for i in range(2, len(prices) - 2):
            # 局部高点
            if (prices[i] > prices[i-1] and prices[i] > prices[i-2] and
                prices[i] > prices[i+1] and prices[i] > prices[i+2]):
                highs.append(prices[i])
                
            # 局部低点
            if (prices[i] < prices[i-1] and prices[i] < prices[i-2] and
                prices[i] < prices[i+1] and prices[i] < prices[i+2]):
                lows.append(prices[i])
                
        return highs, lows
        
    def _cluster_levels(self, levels: List[float]) -> List[float]:
        """聚类相似的价格水平"""
        if not levels:
            return []
            
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < self.sensitivity:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
                
        clusters.append(np.mean(current_cluster))
        return clusters
        
    def _evaluate_level_strength(self, levels: List[float], prices: List[float]) -> List[str]:
        """评估支撑/阻力位的强度"""
        strengths = []
        
        for level in levels:
            touches = self._count_touches(level, prices)
            if touches >= 5:
                strengths.append("强")
            elif touches >= 3:
                strengths.append("中")
            else:
                strengths.append("弱")
                
        return strengths
        
    def _count_touches(self, level: float, prices: List[float]) -> int:
        """计算价格触及某个水平的次数"""
        touches = 0
        threshold = level * self.sensitivity
        
        for price in prices:
            if abs(price - level) <= threshold:
                touches += 1
                
        return touches
        
    def _find_nearest_level(self, levels: List[float], current_price: float, 
                           direction: str) -> Optional[float]:
        """找出最近的支撑或阻力位"""
        if not levels:
            return None
            
        if direction == "below":
            below_levels = [l for l in levels if l < current_price]
            return max(below_levels) if below_levels else None
        else:
            above_levels = [l for l in levels if l > current_price]
            return min(above_levels) if above_levels else None
            
    def _generate_sr_recommendation(self, current: float, support: float, 
                                   resistance: float) -> str:
        """生成支撑阻力建议"""
        if support and resistance:
            range_size = resistance - support
            position = (current - support) / range_size
            
            if position < 0.2:
                return "价格接近支撑位，可能反弹"
            elif position > 0.8:
                return "价格接近阻力位，上涨压力增大"
            else:
                return "价格在支撑阻力区间中部，等待突破方向"
        else:
            return "缺少明确的支撑阻力位，谨慎交易"


class TrendPatternDetector(PatternRecognizer):
    """
    趋势模式检测器
    识别上升/下降趋势和通道
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h"):
        super().__init__(symbol, timeframe)
        
    async def detect_trend_patterns(self) -> Dict[str, Any]:
        """检测趋势模式"""
        try:
            prices = await self.get_price_data(100)
            
            # 计算趋势线
            trend_line = self._calculate_trend_line(prices)
            
            # 识别趋势类型
            trend_type = self._identify_trend_type(trend_line["slope"])
            
            # 检测通道
            channel = self._detect_channel(prices, trend_line)
            
            # 计算趋势强度
            trend_strength = self._calculate_trend_strength(prices, trend_line)
            
            # 检测趋势突破
            breakout = self._detect_breakout(prices, channel)
            
            return {
                "analyzer": "TrendPatternDetector",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "trend_type": trend_type,
                "trend_strength": trend_strength,
                "trend_line": {
                    "slope": round(trend_line["slope"], 4),
                    "current_value": round(trend_line["current_value"], 2)
                },
                "channel": {
                    "upper": round(channel["upper"], 2),
                    "lower": round(channel["lower"], 2),
                    "width": round(channel["width"], 2)
                },
                "breakout": breakout,
                "signals": self._generate_trend_signals(trend_type, trend_strength, breakout),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting trend patterns: {e}")
            raise
            
    def _calculate_trend_line(self, prices: List[float]) -> Dict[str, Any]:
        """计算趋势线（最小二乘法）"""
        x = np.arange(len(prices))
        y = np.array(prices)
        
        # 线性回归
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        intercept = coeffs[1]
        
        # 当前趋势线值
        current_value = slope * (len(prices) - 1) + intercept
        
        return {
            "slope": slope,
            "intercept": intercept,
            "current_value": current_value
        }
        
    def _identify_trend_type(self, slope: float) -> str:
        """识别趋势类型"""
        if slope > 0.1:
            return "强势上涨"
        elif slope > 0.01:
            return "温和上涨"
        elif slope < -0.1:
            return "强势下跌"
        elif slope < -0.01:
            return "温和下跌"
        else:
            return "横盘整理"
            
    def _detect_channel(self, prices: List[float], trend_line: Dict[str, Any]) -> Dict[str, Any]:
        """检测价格通道"""
        x = np.arange(len(prices))
        trend_values = trend_line["slope"] * x + trend_line["intercept"]
        
        # 计算价格与趋势线的偏差
        deviations = prices - trend_values
        
        # 找出上下边界
        upper_dev = np.percentile(deviations, 90)
        lower_dev = np.percentile(deviations, 10)
        
        current_upper = trend_line["current_value"] + upper_dev
        current_lower = trend_line["current_value"] + lower_dev
        
        return {
            "upper": current_upper,
            "lower": current_lower,
            "width": current_upper - current_lower
        }
        
    def _calculate_trend_strength(self, prices: List[float], trend_line: Dict[str, Any]) -> str:
        """计算趋势强度"""
        x = np.arange(len(prices))
        trend_values = trend_line["slope"] * x + trend_line["intercept"]
        
        # 计算R²值
        ss_res = np.sum((prices - trend_values) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        if r_squared > 0.8:
            return "非常强"
        elif r_squared > 0.6:
            return "强"
        elif r_squared > 0.4:
            return "中等"
        else:
            return "弱"
            
    def _detect_breakout(self, prices: List[float], channel: Dict[str, Any]) -> Optional[str]:
        """检测突破"""
        current_price = prices[-1]
        
        if current_price > channel["upper"]:
            return "向上突破"
        elif current_price < channel["lower"]:
            return "向下突破"
        else:
            return None
            
    def _generate_trend_signals(self, trend_type: str, strength: str, 
                               breakout: Optional[str]) -> List[str]:
        """生成趋势信号"""
        signals = []
        
        if "上涨" in trend_type and strength in ["强", "非常强"]:
            signals.append("强势上涨趋势，考虑做多")
        elif "下跌" in trend_type and strength in ["强", "非常强"]:
            signals.append("强势下跌趋势，考虑做空或观望")
            
        if breakout == "向上突破":
            signals.append("突破上轨，可能加速上涨")
        elif breakout == "向下突破":
            signals.append("突破下轨，可能加速下跌")
            
        if trend_type == "横盘整理":
            signals.append("等待明确的方向选择")
            
        return signals


class CandlePatternRecognizer(PatternRecognizer):
    """
    K线形态识别器
    识别经典的K线组合形态
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h"):
        super().__init__(symbol, timeframe)
        
    async def recognize_patterns(self) -> Dict[str, Any]:
        """识别K线形态"""
        try:
            # 获取OHLC数据
            candles = await self._get_ohlc_data(50)
            
            # 识别各种形态
            patterns = []
            
            # 锤子线/上吊线
            hammer = self._detect_hammer(candles)
            if hammer:
                patterns.append(hammer)
                
            # 吞没形态
            engulfing = self._detect_engulfing(candles)
            if engulfing:
                patterns.append(engulfing)
                
            # 十字星
            doji = self._detect_doji(candles)
            if doji:
                patterns.append(doji)
                
            # 三只乌鸦/三个白兵
            three_pattern = self._detect_three_pattern(candles)
            if three_pattern:
                patterns.append(three_pattern)
                
            # 晨星/暮星
            star = self._detect_star_pattern(candles)
            if star:
                patterns.append(star)
                
            return {
                "analyzer": "CandlePatternRecognizer",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "patterns_detected": len(patterns),
                "patterns": patterns,
                "current_candle": self._describe_current_candle(candles[-1]),
                "recommendation": self._generate_pattern_recommendation(patterns),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recognizing candle patterns: {e}")
            raise
            
    async def _get_ohlc_data(self, period: int) -> List[Dict[str, float]]:
        """获取OHLC数据"""
        # 模拟OHLC数据
        prices = await self.get_price_data(period)
        candles = []
        
        for i in range(len(prices)):
            base = prices[i]
            candles.append({
                "open": base + np.random.randn() * base * 0.005,
                "high": base + abs(np.random.randn()) * base * 0.01,
                "low": base - abs(np.random.randn()) * base * 0.01,
                "close": base + np.random.randn() * base * 0.005,
                "volume": 1000000 + np.random.randn() * 200000
            })
            
        return candles
        
    def _detect_hammer(self, candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """检测锤子线/上吊线"""
        if len(candles) < 2:
            return None
            
        current = candles[-1]
        prev = candles[-2]
        
        body = abs(current["close"] - current["open"])
        lower_shadow = min(current["open"], current["close"]) - current["low"]
        upper_shadow = current["high"] - max(current["open"], current["close"])
        
        # 锤子线特征：下影线长，实体小
        if lower_shadow > body * 2 and upper_shadow < body * 0.1:
            if prev["close"] < prev["open"]:  # 下跌趋势中
                return {
                    "pattern": "锤子线",
                    "type": "反转信号",
                    "direction": "看涨",
                    "reliability": "中等"
                }
            else:  # 上涨趋势中
                return {
                    "pattern": "上吊线",
                    "type": "反转信号",
                    "direction": "看跌",
                    "reliability": "中等"
                }
                
        return None
        
    def _detect_engulfing(self, candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """检测吞没形态"""
        if len(candles) < 2:
            return None
            
        current = candles[-1]
        prev = candles[-2]
        
        # 看涨吞没
        if (prev["close"] < prev["open"] and  # 前一根阴线
            current["close"] > current["open"] and  # 当前阳线
            current["open"] < prev["close"] and  # 开盘价低于前收盘
            current["close"] > prev["open"]):  # 收盘价高于前开盘
            return {
                "pattern": "看涨吞没",
                "type": "反转信号",
                "direction": "看涨",
                "reliability": "高"
            }
            
        # 看跌吞没
        if (prev["close"] > prev["open"] and  # 前一根阳线
            current["close"] < current["open"] and  # 当前阴线
            current["open"] > prev["close"] and  # 开盘价高于前收盘
            current["close"] < prev["open"]):  # 收盘价低于前开盘
            return {
                "pattern": "看跌吞没",
                "type": "反转信号",
                "direction": "看跌",
                "reliability": "高"
            }
            
        return None
        
    def _detect_doji(self, candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """检测十字星"""
        if not candles:
            return None
            
        current = candles[-1]
        body = abs(current["close"] - current["open"])
        total_range = current["high"] - current["low"]
        
        # 十字星特征：实体极小
        if total_range > 0 and body / total_range < 0.1:
            return {
                "pattern": "十字星",
                "type": "犹豫信号",
                "direction": "中性",
                "reliability": "需要确认"
            }
            
        return None
        
    def _detect_three_pattern(self, candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """检测三只乌鸦/三个白兵"""
        if len(candles) < 3:
            return None
            
        last_three = candles[-3:]
        
        # 三个白兵
        if all(c["close"] > c["open"] for c in last_three):  # 都是阳线
            if (last_three[1]["close"] > last_three[0]["close"] and
                last_three[2]["close"] > last_three[1]["close"]):  # 逐步走高
                return {
                    "pattern": "三个白兵",
                    "type": "持续信号",
                    "direction": "看涨",
                    "reliability": "高"
                }
                
        # 三只乌鸦
        if all(c["close"] < c["open"] for c in last_three):  # 都是阴线
            if (last_three[1]["close"] < last_three[0]["close"] and
                last_three[2]["close"] < last_three[1]["close"]):  # 逐步走低
                return {
                    "pattern": "三只乌鸦",
                    "type": "持续信号",
                    "direction": "看跌",
                    "reliability": "高"
                }
                
        return None
        
    def _detect_star_pattern(self, candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """检测晨星/暮星形态"""
        if len(candles) < 3:
            return None
            
        first = candles[-3]
        middle = candles[-2]
        last = candles[-1]
        
        # 晨星（底部反转）
        if (first["close"] < first["open"] and  # 第一根阴线
            abs(middle["close"] - middle["open"]) < abs(first["close"] - first["open"]) * 0.3 and  # 中间小实体
            last["close"] > last["open"] and  # 第三根阳线
            last["close"] > (first["open"] + first["close"]) / 2):  # 收盘价超过第一根中点
            return {
                "pattern": "晨星",
                "type": "反转信号",
                "direction": "看涨",
                "reliability": "高"
            }
            
        # 暮星（顶部反转）
        if (first["close"] > first["open"] and  # 第一根阳线
            abs(middle["close"] - middle["open"]) < abs(first["close"] - first["open"]) * 0.3 and  # 中间小实体
            last["close"] < last["open"] and  # 第三根阴线
            last["close"] < (first["open"] + first["close"]) / 2):  # 收盘价低于第一根中点
            return {
                "pattern": "暮星",
                "type": "反转信号",
                "direction": "看跌",
                "reliability": "高"
            }
            
        return None
        
    def _describe_current_candle(self, candle: Dict[str, float]) -> Dict[str, Any]:
        """描述当前K线"""
        body = candle["close"] - candle["open"]
        body_size = abs(body)
        total_range = candle["high"] - candle["low"]
        
        return {
            "type": "阳线" if body > 0 else "阴线",
            "body_size": "大" if body_size / total_range > 0.7 else "中" if body_size / total_range > 0.3 else "小",
            "shadows": {
                "upper": "长" if (candle["high"] - max(candle["open"], candle["close"])) / total_range > 0.3 else "短",
                "lower": "长" if (min(candle["open"], candle["close"]) - candle["low"]) / total_range > 0.3 else "短"
            }
        }
        
    def _generate_pattern_recommendation(self, patterns: List[Dict[str, Any]]) -> str:
        """生成形态分析建议"""
        if not patterns:
            return "未检测到明显的K线形态，继续观察"
            
        bullish_signals = sum(1 for p in patterns if p["direction"] == "看涨")
        bearish_signals = sum(1 for p in patterns if p["direction"] == "看跌")
        
        if bullish_signals > bearish_signals:
            return f"检测到{bullish_signals}个看涨信号，市场可能上涨"
        elif bearish_signals > bullish_signals:
            return f"检测到{bearish_signals}个看跌信号，市场可能下跌"
        else:
            return "多空信号平衡，等待更明确的方向"