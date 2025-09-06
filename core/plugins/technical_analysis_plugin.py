"""
技术分析领域插件
提供通用的技术分析能力
"""

from typing import Dict, Any, List, Type
import logging

from core.domain_plugin import DomainPlugin
from core.business.market_config import AnalysisDomain
from core.agents.base import BaseAnalyst, TechnicalAnalyst

logger = logging.getLogger(__name__)


class TechnicalAnalysisPlugin(DomainPlugin):
    """技术分析插件 - 支持多种市场"""
    
    def __init__(self):
        super().__init__(
            plugin_id="technical_analysis",
            name="Technical Analysis Suite",
            version="2.0.0"
        )
        self.indicators = {}
        self.pattern_recognizers = {}
        
    def get_domain(self) -> AnalysisDomain:
        """获取插件对应的分析领域"""
        return AnalysisDomain.TECHNICAL
        
    def get_supported_markets(self) -> List[str]:
        """获取支持的市场类型"""
        # 技术分析适用于所有市场
        return ["stock_us", "stock_cn", "crypto", "forex", "commodity", "prediction"]
        
    def get_agents(self) -> List[Type[BaseAnalyst]]:
        """获取插件提供的分析师类型"""
        return [TechnicalAnalyst]
        
    def get_data_requirements(self) -> Dict[str, Any]:
        """获取数据需求描述"""
        return {
            "required": {
                "price_data": {
                    "current_price": "Current price",
                    "change_24h": "24-hour change percentage",
                    "change_7d": "7-day change percentage",
                    "change_30d": "30-day change percentage",
                    "volume_24h": "24-hour trading volume"
                }
            },
            "optional": {
                "ohlcv": {
                    "open": "Opening price",
                    "high": "Highest price",
                    "low": "Lowest price",
                    "close": "Closing price",
                    "volume": "Trading volume"
                },
                "indicators": {
                    "rsi": "Relative Strength Index",
                    "macd": "Moving Average Convergence Divergence",
                    "bollinger_bands": "Bollinger Bands",
                    "moving_averages": "Various moving averages"
                },
                "historical_data": "Historical price data for backtesting"
            }
        }
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self.config = config
            
            # 初始化技术指标计算器
            self._initialize_indicators(config.get("indicators", {}))
            
            # 初始化图表形态识别器
            self._initialize_pattern_recognizers(config.get("patterns", {}))
            
            # 设置默认参数
            self._set_default_parameters(config.get("defaults", {}))
            
            logger.info(f"技术分析插件初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"技术分析插件初始化失败: {e}")
            return False
            
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证输入数据是否满足要求"""
        # 检查必需的价格数据
        if "price_data" not in data:
            logger.warning("缺少价格数据")
            return False
            
        price_data = data["price_data"]
        required_fields = ["current_price", "volume_24h"]
        
        for field in required_fields:
            if field not in price_data:
                logger.warning(f"缺少必需的价格数据字段: {field}")
                return False
                
        return True
        
    def _initialize_indicators(self, indicator_config: Dict[str, Any]):
        """初始化技术指标"""
        # RSI配置
        self.indicators["rsi"] = {
            "period": indicator_config.get("rsi_period", 14),
            "overbought": indicator_config.get("rsi_overbought", 70),
            "oversold": indicator_config.get("rsi_oversold", 30)
        }
        
        # MACD配置
        self.indicators["macd"] = {
            "fast_period": indicator_config.get("macd_fast", 12),
            "slow_period": indicator_config.get("macd_slow", 26),
            "signal_period": indicator_config.get("macd_signal", 9)
        }
        
        # 移动平均线配置
        self.indicators["ma"] = {
            "periods": indicator_config.get("ma_periods", [20, 50, 200])
        }
        
    def _initialize_pattern_recognizers(self, pattern_config: Dict[str, Any]):
        """初始化图表形态识别器"""
        self.pattern_recognizers = {
            "head_and_shoulders": pattern_config.get("head_and_shoulders", True),
            "double_top": pattern_config.get("double_top", True),
            "double_bottom": pattern_config.get("double_bottom", True),
            "triangle": pattern_config.get("triangle", True),
            "flag": pattern_config.get("flag", True),
            "wedge": pattern_config.get("wedge", True)
        }
        
    def _set_default_parameters(self, defaults: Dict[str, Any]):
        """设置默认参数"""
        self.config["timeframe"] = defaults.get("timeframe", "1d")
        self.config["lookback_period"] = defaults.get("lookback_period", 100)
        self.config["signal_threshold"] = defaults.get("signal_threshold", 0.7)
        
    def calculate_indicators(self, price_data: List[float]) -> Dict[str, Any]:
        """计算技术指标（扩展功能）"""
        results = {}
        
        # RSI计算
        if len(price_data) >= self.indicators["rsi"]["period"]:
            results["rsi"] = self._calculate_rsi(price_data)
            
        # MACD计算
        if len(price_data) >= self.indicators["macd"]["slow_period"]:
            results["macd"] = self._calculate_macd(price_data)
            
        # 移动平均线计算
        results["moving_averages"] = self._calculate_moving_averages(price_data)
        
        return results
        
    def identify_patterns(self, ohlcv_data: List[Dict[str, float]]) -> List[Dict[str, Any]]:
        """识别图表形态（扩展功能）"""
        patterns = []
        
        # 这里实现各种图表形态的识别逻辑
        # 示例：检测双顶形态
        if self.pattern_recognizers.get("double_top") and len(ohlcv_data) >= 50:
            double_top = self._detect_double_top(ohlcv_data)
            if double_top:
                patterns.append(double_top)
                
        return patterns
        
    def _calculate_rsi(self, prices: List[float]) -> float:
        """计算RSI指标 - 使用Wilder's平滑方法"""
        period = self.indicators["rsi"]["period"]
        if len(prices) < period + 1:
            return 50.0
            
        # 计算价格变化
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
            
        # 初始平均值（简单移动平均）
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Wilder's平滑方法
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        # 计算RSI
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
        
    def _calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """计算MACD指标 - 使用真实的EMA计算"""
        fast = self.indicators["macd"]["fast_period"]
        slow = self.indicators["macd"]["slow_period"]
        signal = self.indicators["macd"]["signal_period"]
        
        if len(prices) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
        # 计算快速和慢速EMA
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        # 计算MACD线
        macd_values = []
        for i in range(len(ema_slow)):
            macd = ema_fast[i + (len(ema_fast) - len(ema_slow))] - ema_slow[i]
            macd_values.append(macd)
        
        # 计算信号线（MACD的EMA）
        if len(macd_values) >= signal:
            signal_line = self._calculate_ema(macd_values, signal)
            current_signal = signal_line[-1]
        else:
            current_signal = 0
        
        current_macd = macd_values[-1] if macd_values else 0
        histogram = current_macd - current_signal
        
        return {
            "macd": round(current_macd, 4),
            "signal": round(current_signal, 4),
            "histogram": round(histogram, 4)
        }
        
    def _calculate_moving_averages(self, prices: List[float]) -> Dict[int, float]:
        """计算移动平均线"""
        mas = {}
        for period in self.indicators["ma"]["periods"]:
            if len(prices) >= period:
                mas[period] = sum(prices[-period:]) / period
        return mas
        
    def _detect_double_top(self, ohlcv_data: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """检测双顶形态"""
        # 简化的双顶检测逻辑
        # 实际实现需要更复杂的算法
        return None
        
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """计算指数移动平均（EMA）"""
        if len(prices) < period:
            return []
            
        multiplier = 2 / (period + 1)
        
        # 初始值使用简单移动平均
        sma = sum(prices[:period]) / period
        ema_values = [sma]
        
        # 计算后续的EMA值
        for i in range(period, len(prices)):
            ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)
            
        return ema_values