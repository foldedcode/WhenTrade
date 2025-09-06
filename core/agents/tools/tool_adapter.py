"""
工具适配器 - 为分析师提供统一的工具访问接口

将新的 services/tools 系统暴露给分析师使用，替代旧的 dataflows/interface 系统
"""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import asyncio

from core.services.tools.tool_registry import ToolRegistry
from core.services.tools.tool_optimizer import optimize_tool_call, get_tool_priority

logger = logging.getLogger(__name__)


class AnalystToolAdapter:
    """分析师工具适配器"""
    
    def __init__(self, agent_id: str = "unknown"):
        self.tool_registry = ToolRegistry
        self.agent_id = agent_id
        logger.info(f"🔧 AnalystToolAdapter initialized for agent: {agent_id}")
    
    # === 技术分析工具 ===
    
    def get_crypto_price_data(
        self, 
        symbol: str, 
        days_back: int = 30,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """获取加密货币价格数据"""
        try:
            # 尝试使用优化调用
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在已有事件循环中创建任务
                    task = asyncio.create_task(self._get_crypto_price_data_async(symbol, days_back, interval))
                    # 同步等待结果（这里可能需要优化）
                    return asyncio.run_coroutine_threadsafe(task, loop).result(timeout=30)
                else:
                    return asyncio.run(self._get_crypto_price_data_async(symbol, days_back, interval))
            except (RuntimeError, asyncio.TimeoutError):
                # 回退到直接调用
                return self._get_crypto_price_data_sync(symbol, days_back, interval)
            
        except Exception as e:
            logger.error(f"❌ 获取价格数据异常: {e}")
            return {"error": str(e), "symbol": symbol}
    
    async def _get_crypto_price_data_async(
        self, 
        symbol: str, 
        days_back: int = 30,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """异步获取加密货币价格数据"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        logger.info(f"📈 [异步] 获取 {symbol} 价格数据: {start_date} 到 {end_date}")
        
        # 使用优化器
        tool_func = lambda: self.tool_registry.execute_tool(
            scope='technical',
            tool_id='crypto_price',
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )
        
        result = await optimize_tool_call(
            tool_name='get_crypto_price_data',
            tool_func=tool_func,
            agent_id=self.agent_id,
            priority=get_tool_priority('get_crypto_price_data')
        )
        
        if 'error' in result:
            logger.warning(f"⚠️ 价格数据获取失败: {result['error']}")
        else:
            logger.info(f"✅ 成功获取 {result.get('total_records', 0)} 条价格记录")
        
        return result
    
    def _get_crypto_price_data_sync(
        self, 
        symbol: str, 
        days_back: int = 30,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """同步获取加密货币价格数据（回退方案）"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        logger.info(f"📈 [同步] 获取 {symbol} 价格数据: {start_date} 到 {end_date}")
        
        result = self.tool_registry.execute_tool(
            scope='technical',
            tool_id='crypto_price',
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )
        
        if 'error' in result:
            logger.warning(f"⚠️ 价格数据获取失败: {result['error']}")
        else:
            logger.info(f"✅ 成功获取 {result.get('total_records', 0)} 条价格记录")
        
        return result
    
    def get_technical_indicators(
        self, 
        symbol: str, 
        indicators: List[str] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """获取技术指标"""
        try:
            if indicators is None:
                indicators = ['sma', 'rsi', 'macd', 'bb']  # 默认指标
            
            logger.info(f"📊 计算 {symbol} 技术指标: {indicators}")
            
            result = self.tool_registry.execute_tool(
                scope='technical',
                tool_id='indicators',
                symbol=symbol,
                indicators=indicators,
                period_days=period_days
            )
            
            if 'error' in result:
                logger.warning(f"⚠️ 技术指标计算失败: {result['error']}")
            else:
                indicator_count = len(result.get('indicators', {}))
                logger.info(f"✅ 成功计算 {indicator_count} 个技术指标")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 技术指标计算异常: {e}")
            return {"error": str(e), "symbol": symbol}
    
    # === 情绪分析工具 ===
    
    def get_crypto_news(
        self, 
        symbol: str, 
        days_back: int = 7,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """获取加密货币新闻"""
        try:
            logger.info(f"📰 获取 {symbol} 新闻: 过去 {days_back} 天")
            
            result = self.tool_registry.execute_tool(
                scope='sentiment',
                tool_id='finnhub_news',
                symbol=symbol,
                days_back=days_back,
                max_results=max_results
            )
            
            if 'error' in result:
                logger.warning(f"⚠️ 新闻获取失败: {result['error']}")
            else:
                news_count = result.get('news_count', 0)
                logger.info(f"✅ 成功获取 {news_count} 条新闻")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 新闻获取异常: {e}")
            return {"error": str(e), "symbol": symbol}
    
    def get_sentiment_analysis(
        self, 
        symbol: str, 
        sources: List[str] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """获取综合情绪分析"""
        try:
            if sources is None:
                sources = ['finnhub', 'reddit']  # 默认数据源
            
            logger.info(f"🎭 分析 {symbol} 市场情绪: {sources}")
            
            result = self.tool_registry.execute_tool(
                scope='sentiment',
                tool_id='sentiment_batch',
                symbol=symbol,
                sources=sources,
                days_back=days_back
            )
            
            if 'error' in result:
                logger.warning(f"⚠️ 情绪分析失败: {result['error']}")
            else:
                total_articles = result.get('summary', {}).get('total_news_articles', 0)
                logger.info(f"✅ 情绪分析完成，共分析 {total_articles} 篇文章")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 情绪分析异常: {e}")
            return {"error": str(e), "symbol": symbol}
    
    # === 一站式工具方法 ===
    
    def execute_scope_analysis(
        self, 
        scope: str, 
        symbol: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """执行指定分析范围的所有工具"""
        try:
            logger.info(f"🔍 执行 {scope} 分析: {symbol}")
            
            result = self.tool_registry.execute_scope_tools(
                scope=scope,
                symbol=symbol,
                **kwargs
            )
            
            if result.get('tools_executed'):
                logger.info(f"✅ {scope} 分析完成，执行了 {len(result['tools_executed'])} 个工具")
            
            if result.get('tools_failed'):
                logger.warning(f"⚠️ {len(result['tools_failed'])} 个工具执行失败: {result['tools_failed']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 分析范围 {scope} 执行异常: {e}")
            return {"error": str(e), "scope": scope, "symbol": symbol}
    
    # === 兼容性方法 - 替代旧的dataflows接口 ===
    
    def get_finnhub_news(
        self, 
        ticker: str, 
        curr_date: str, 
        look_back_days: int
    ) -> str:
        """兼容旧的get_finnhub_news接口"""
        # 将旧接口调用转换为新工具调用
        result = self.get_crypto_news(ticker, look_back_days, max_results=20)
        
        if 'error' in result:
            return f"Error fetching news: {result['error']}"
        
        # 格式化为旧系统期望的字符串格式
        articles = result.get('articles', [])
        if not articles:
            return f"No news found for {ticker}"
        
        formatted_output = f"News for {ticker} (past {look_back_days} days):\n\n"
        for i, article in enumerate(articles[:10], 1):
            formatted_output += f"{i}. {article.get('headline', 'No headline')}\n"
            formatted_output += f"   Source: {article.get('source', 'Unknown')}\n"
            formatted_output += f"   Summary: {article.get('summary', 'No summary')[:200]}...\n\n"
        
        return formatted_output


# 全局适配器实例
analyst_tools = AnalystToolAdapter()