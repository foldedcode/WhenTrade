"""
工具注册系统

提供统一的工具注册和执行接口
"""
from typing import Dict, List, Callable, Any, Optional
import logging
from .technical_tools import (
    get_crypto_price_data,
    calculate_technical_indicators
)
from .sentiment_tools import (
    get_finnhub_crypto_news,
    get_crypto_reddit_sentiment,
    analyze_sentiment_batch
)
from .coingecko_tools import (
    get_coin_market_data,
    get_historical_prices,
    get_market_metrics,
    get_trending_coins,
    get_fear_greed_index
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册中心"""
    
    # 工具映射表
    TOOL_REGISTRY = {
        'technical': {
            'crypto_price': {
                'function': get_crypto_price_data,
                'name': 'Crypto Price Data',
                'display_name': '加密货币价格',
                'description': 'Get cryptocurrency price data from Yahoo Finance',
                'parameters': ['symbol', 'start_date', 'end_date', 'interval'],
                'required': ['symbol', 'start_date', 'end_date'],
                'data_sources': ['yahoo_finance']
            },
            'indicators': {
                'function': calculate_technical_indicators,
                'name': 'Technical Indicators',
                'display_name': '技术指标',
                'description': 'Calculate technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)',
                'parameters': ['symbol', 'indicators', 'period_days'],
                'required': ['symbol', 'indicators'],
                'data_sources': ['yahoo_finance']
            },
            'market_data': {
                'function': get_coin_market_data,
                'name': 'Real-time Market Data',
                'display_name': '实时市场数据',
                'description': 'Get real-time cryptocurrency market data from CoinGecko',
                'parameters': ['symbol', 'vs_currency'],
                'required': ['symbol'],
                'data_sources': ['coingecko']
            },
            'historical_data': {
                'function': get_historical_prices,
                'name': 'Historical Price Data',
                'display_name': '历史价格数据',
                'description': 'Get historical price data from CoinGecko',
                'parameters': ['symbol', 'days', 'vs_currency'],
                'required': ['symbol'],
                'data_sources': ['coingecko']
            },
        },
        'sentiment': {
            'fear_greed': {
                'function': get_fear_greed_index,
                'name': 'Fear & Greed Index',
                'display_name': '恐惧贪婪指数',
                'description': 'Get cryptocurrency fear and greed index',
                'parameters': [],
                'required': [],
                'data_sources': ['alternative.me']
            },
            'finnhub_news': {
                'function': get_finnhub_crypto_news,
                'name': 'FinnHub Crypto News',
                'display_name': 'FinnHub新闻',
                'description': 'Get cryptocurrency news from FinnHub',
                'parameters': ['symbol', 'days_back', 'max_results'],
                'required': ['symbol'],
                'data_sources': ['finnhub']
            },
            'reddit_sentiment': {
                'function': get_crypto_reddit_sentiment,
                'name': 'Reddit Crypto Sentiment',
                'display_name': 'Reddit情绪分析',
                'description': 'Analyze cryptocurrency sentiment from Reddit',
                'parameters': ['symbol', 'days_back', 'max_results'],
                'required': ['symbol'],
                'data_sources': ['reddit']
            },
            'sentiment_batch': {
                'function': analyze_sentiment_batch,
                'name': 'Batch Sentiment Analysis',
                'display_name': '批量情绪分析',
                'description': 'Analyze sentiment from multiple sources',
                'parameters': ['symbol', 'sources', 'days_back'],
                'required': ['symbol'],
                'data_sources': ['finnhub', 'reddit']
            }
        }
    }
    
    # 默认工具配置（每个分析范围的推荐工具）
    DEFAULT_TOOLS = {
        'technical': ['crypto_price', 'indicators', 'market_data', 'historical_data'],
        'sentiment': ['finnhub_news', 'reddit_sentiment', 'sentiment_batch', 'fear_greed'],
        'onchain': [],  # 将来添加链上分析工具
        'defi': []      # 将来添加DeFi分析工具
    }
    
    @classmethod
    def get_tools_for_scope(cls, scope: str) -> List[str]:
        """
        获取指定分析范围的默认工具列表
        
        Args:
            scope: 分析范围 ('technical', 'sentiment', 'onchain', 'defi')
            
        Returns:
            工具ID列表
        """
        return cls.DEFAULT_TOOLS.get(scope, [])
    
    @classmethod
    def get_tool_info(cls, scope: str, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工具信息
        
        Args:
            scope: 分析范围
            tool_id: 工具ID
            
        Returns:
            工具信息字典
        """
        return cls.TOOL_REGISTRY.get(scope, {}).get(tool_id)
    
    @classmethod
    def execute_tool(
        cls,
        scope: str,
        tool_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            scope: 分析范围
            tool_id: 工具ID
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        try:
            tool_info = cls.get_tool_info(scope, tool_id)
            if not tool_info:
                return {
                    "error": f"Tool {tool_id} not found in scope {scope}",
                    "available_tools": list(cls.TOOL_REGISTRY.get(scope, {}).keys())
                }
            
            # 检查必需参数
            required_params = tool_info.get('required', [])
            missing_params = [param for param in required_params if param not in kwargs]
            if missing_params:
                return {
                    "error": f"Missing required parameters: {missing_params}",
                    "required": required_params,
                    "all_parameters": tool_info.get('parameters', [])
                }
            
            # 执行工具
            function = tool_info['function']
            result = function(**kwargs)
            
            # 添加执行元信息
            if isinstance(result, dict):
                result['_tool_info'] = {
                    'scope': scope,
                    'tool_id': tool_id,
                    'tool_name': tool_info.get('name', ''),
                    'execution_time': None  # 可以添加执行时间记录
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {scope}.{tool_id}: {e}")
            return {
                "error": str(e),
                "scope": scope,
                "tool_id": tool_id
            }
    
    @classmethod
    def execute_scope_tools(
        cls,
        scope: str,
        symbol: str,
        custom_tools: Optional[List[str]] = None,
        **common_kwargs
    ) -> Dict[str, Any]:
        """
        执行分析范围的所有默认工具
        
        Args:
            scope: 分析范围
            symbol: 加密货币符号
            custom_tools: 自定义工具列表（覆盖默认）
            **common_kwargs: 传递给所有工具的公共参数
            
        Returns:
            所有工具的执行结果
        """
        try:
            tools = custom_tools if custom_tools is not None else cls.get_tools_for_scope(scope)
            
            if not tools:
                return {
                    "error": f"No tools available for scope {scope}",
                    "scope": scope,
                    "available_scopes": list(cls.DEFAULT_TOOLS.keys())
                }
            
            results = {
                "scope": scope,
                "symbol": symbol,
                "tools_executed": [],
                "tools_failed": [],
                "results": {}
            }
            
            for tool_id in tools:
                try:
                    # 准备工具参数
                    tool_kwargs = {"symbol": symbol, **common_kwargs}
                    
                    # 为特定工具添加默认参数
                    if tool_id == 'crypto_price' and 'start_date' not in tool_kwargs:
                        from datetime import datetime, timedelta
                        end_date = datetime.now().strftime('%Y-%m-%d')
                        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                        tool_kwargs.update({
                            'start_date': start_date,
                            'end_date': end_date
                        })
                    
                    if tool_id == 'indicators' and 'indicators' not in tool_kwargs:
                        tool_kwargs['indicators'] = ['sma', 'rsi', 'macd']  # 默认指标
                    
                    # 过滤工具参数（只传递工具支持的参数）
                    tool_info = cls.get_tool_info(scope, tool_id)
                    if tool_info:
                        supported_params = tool_info.get('parameters', [])
                        filtered_kwargs = {
                            k: v for k, v in tool_kwargs.items() 
                            if k in supported_params
                        }
                    else:
                        filtered_kwargs = tool_kwargs
                    
                    # 执行工具
                    result = cls.execute_tool(scope, tool_id, **filtered_kwargs)
                    
                    if "error" in result:
                        results["tools_failed"].append(tool_id)
                        logger.warning(f"Tool {tool_id} failed: {result['error']}")
                    else:
                        results["tools_executed"].append(tool_id)
                    
                    results["results"][tool_id] = result
                    
                except Exception as e:
                    logger.error(f"Error executing tool {tool_id} in scope {scope}: {e}")
                    results["tools_failed"].append(tool_id)
                    results["results"][tool_id] = {"error": str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing scope tools for {scope}: {e}")
            return {
                "error": str(e),
                "scope": scope,
                "symbol": symbol
            }
    
    @classmethod
    def get_available_scopes(cls) -> List[str]:
        """获取所有可用的分析范围"""
        return list(cls.DEFAULT_TOOLS.keys())
    
    @classmethod
    def get_scope_tools(cls, scope: str) -> Dict[str, Dict[str, Any]]:
        """获取分析范围的所有工具信息"""
        return cls.TOOL_REGISTRY.get(scope, {})
    
    @classmethod
    def get_all_tools(cls) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """获取所有工具信息"""
        return cls.TOOL_REGISTRY
    
    @classmethod
    def get_scope_data_sources(cls, scope: str) -> List[str]:
        """
        获取分析范围的所有数据源（从工具定义中聚合）
        
        Args:
            scope: 分析范围 ('technical', 'sentiment', etc.)
            
        Returns:
            数据源列表（去重）
        """
        data_sources = set()
        scope_tools = cls.TOOL_REGISTRY.get(scope, {})
        
        for tool_id, tool_info in scope_tools.items():
            tool_data_sources = tool_info.get('data_sources', [])
            data_sources.update(tool_data_sources)
        
        return sorted(list(data_sources))


# 便捷函数接口
def execute_technical_analysis(symbol: str, **kwargs) -> Dict[str, Any]:
    """执行技术分析"""
    return ToolRegistry.execute_scope_tools('technical', symbol, **kwargs)


def execute_sentiment_analysis(symbol: str, **kwargs) -> Dict[str, Any]:
    """执行情绪分析"""
    return ToolRegistry.execute_scope_tools('sentiment', symbol, **kwargs)


def get_available_tools(scope: Optional[str] = None) -> Dict[str, Any]:
    """获取可用工具信息"""
    if scope:
        return {
            "scope": scope,
            "tools": ToolRegistry.get_scope_tools(scope)
        }
    else:
        return {
            "all_scopes": ToolRegistry.get_available_scopes(),
            "all_tools": ToolRegistry.get_all_tools()
        }