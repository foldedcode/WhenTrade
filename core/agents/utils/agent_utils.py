from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List, Dict, Any, Callable
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import core.dataflows.interface as interface
from core.default_config import WHENTRADE_CONFIG
from langchain_core.messages import HumanMessage

# 导入统一日志系统和工具日志装饰器
from core.utils.tool_logging import log_tool_call, log_analysis_step

# 导入日志模块
from core.utils.logging_manager import get_logger
logger = get_logger('agents')


def timeframe_to_days(timeframe: str) -> int:
    """Convert timeframe string to number of days for data fetching"""
    timeframe_mapping = {
        '1h': 1,    # 1 hour = 1 day of data
        '4h': 1,    # 4 hours = 1 day of data  
        '1d': 7,    # 1 day = 1 week of data
        '1w': 30,   # 1 week = 1 month of data
        '1M': 180,  # 1 month = 6 months of data
    }
    return timeframe_mapping.get(timeframe, 7)  # Default to 7 days


def timeframe_to_reddit_time(timeframe: str) -> str:
    """Convert timeframe to Reddit API time parameter"""
    timeframe_mapping = {
        '1h': 'day',
        '4h': 'day',
        '1d': 'week', 
        '1w': 'month',
        '1M': 'year'
    }
    return timeframe_mapping.get(timeframe, 'week')  # Default to week


def create_msg_delete():
    def delete_messages(state):
        """Clear messages properly without adding garbage (Linus: if you don't need it, don't create it)"""
        # 导入日志系统
        from core.utils.logging_init import get_logger
        logger = get_logger("default")
        
        # 🔧 添加调试信息确认Msg Clear节点执行
        logger.info(f"🧹 [Msg Clear] 正在清理消息，当前状态包含字段: {list(state.keys())}")
        if "phase_1_complete" in state:
            logger.info(f"🧹 [Msg Clear] 检测到Phase 1完成标记: {state['phase_1_complete']}")
        if "ready_for_phase_2" in state:
            logger.info(f"🧹 [Msg Clear] 检测到Phase 2准备标记: {state['ready_for_phase_2']}")
        
        messages = state["messages"]
        logger.info(f"🧹 [Msg Clear] 即将删除 {len(messages)} 条消息")
        
        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]
        
        # Return clean state - no garbage placeholder
        # Sequence lock should be released by the analyst node after LLM analysis
        logger.info(f"🧹 [Msg Clear] 消息清理完成，即将转到下一节点")
        return {"messages": removal_operations}
    
    return delete_messages


def execute_tools_directly(
    tools: List[Callable],
    ticker: str,
    llm: Any,
    system_message: str,
    state: Dict[str, Any]
) -> AIMessage:
    """
    直接执行工具并生成分析报告（用于不支持工具调用的LLM）
    
    Args:
        tools: 工具函数列表
        ticker: 股票代码
        llm: LLM实例
        system_message: 系统消息
        state: Agent状态
    
    Returns:
        AIMessage: 包含分析结果的消息
    """
    logger.info(f"🔧 [直接执行模式] 开始执行{len(tools)}个工具")
    
    # 直接执行所有工具
    tool_results = []
    for tool in tools:
        try:
            tool_name = tool.__name__ if hasattr(tool, '__name__') else str(tool)
            logger.info(f"🎯 [直接执行] 正在执行工具: {tool_name}")
            
            # 执行工具
            if hasattr(tool, '__call__'):
                result_data = tool(ticker)
                tool_results.append({
                    "tool": tool_name,
                    "result": str(result_data)
                })
                logger.info(f"✅ [直接执行] 工具{tool_name}执行成功")
        except Exception as e:
            logger.error(f"❌ [直接执行] 工具{tool_name}执行失败: {str(e)}")
            tool_results.append({
                "tool": tool_name,
                "result": f"错误: {str(e)}"
            })
    
    # 构建工具结果文本
    tool_results_text = "\n\n".join([
        f"## {r['tool']}\n{r['result']}" for r in tool_results
    ])
    
    # 使用LLM分析工具结果
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "基于以下工具获取的数据进行分析。\n\n"
         "工具数据：\n{tool_results}\n\n"
         "{system_message}\n\n"
         "请基于以上数据进行综合分析，并提供明确的投资建议。"),
        MessagesPlaceholder(variable_name="messages")
    ])
    
    analysis_prompt = analysis_prompt.partial(tool_results=tool_results_text)
    analysis_prompt = analysis_prompt.partial(system_message=system_message)
    
    analysis_chain = analysis_prompt | llm
    result = analysis_chain.invoke(state["messages"])
    
    return result


class Toolkit:
    _config = WHENTRADE_CONFIG.copy()
    _current_timeframe = "1d"  # Default timeframe

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)
    
    @classmethod
    def set_timeframe(cls, timeframe: str):
        """Set the current timeframe for all tools"""
        cls._current_timeframe = timeframe

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None, selected_tools=None, selected_data_sources=None, stop_event=None, websocket=None):
        if config:
            self.update_config(config)
        
        # Phase 2: 存储用户选择的工具配置
        self.selected_tools = selected_tools or []
        self.selected_data_sources = selected_data_sources or []
        
        # 添加WebSocket通知支持
        self.stop_event = stop_event
        self.websocket = websocket
        
        # 如果有选择的工具，记录一下
        if self.selected_tools:
            logger.info(f"🔧 [Toolkit] 初始化，包含用户选择的 {len(self.selected_tools)} 个工具")
            logger.debug(f"   工具列表: {self.selected_tools}")
        
        # 动态注册用户选择的工具
        self._register_selected_tools()
    
    def _send_tool_status_sync(self, tool_name: str, status: str, **kwargs):
        """同步发送工具状态通知（兼容同步工具方法）"""
        if self.websocket:
            import asyncio
            import json
            
            message = {
                "type": "tool.status",
                "data": {
                    "tool_name": tool_name,
                    "status": status,
                    **kwargs
                }
            }
            
            try:
                # 检查是否在异步环境中
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在运行的事件循环中使用create_task
                        asyncio.create_task(self.websocket.send_text(json.dumps(message)))
                    else:
                        # 创建新的事件循环
                        asyncio.run(self.websocket.send_text(json.dumps(message)))
                except RuntimeError:
                    # 如果没有事件循环，创建新的
                    asyncio.run(self.websocket.send_text(json.dumps(message)))
            except Exception as e:
                logger.debug(f"WebSocket通知发送失败: {e}")
    
    def _register_selected_tools(self):
        """Phase 2: 根据用户选择动态注册工具"""
        if not self.selected_tools:
            logger.debug("🔧 [Toolkit] 没有用户选择的工具，使用默认工具集")
            return
        
        logger.info(f"🔍 [Toolkit] 开始注册工具，selected_tools = {self.selected_tools}")
        
        # 导入工具注册表和实际工具
        from core.services.tools.tool_registry import ToolRegistry
        from core.services.tools.technical_tools import TechnicalAnalysisTools
        from core.services.tools.coingecko_tools import CoinGeckoTools
        from core.services.tools.sentiment_tools import SentimentAnalysisTools
        
        # 工具ID到实际方法的映射
        tool_method_mapping = {
            # 技术分析工具
            'crypto_price': TechnicalAnalysisTools.get_crypto_price_data,
            'indicators': TechnicalAnalysisTools.calculate_technical_indicators,
            'market_data': CoinGeckoTools.get_coin_market_data,
            'historical_data': CoinGeckoTools.get_historical_prices,
            
            # 情绪分析工具
            'finnhub_news': SentimentAnalysisTools.get_finnhub_crypto_news,
            'reddit_sentiment': SentimentAnalysisTools.get_crypto_reddit_sentiment,
            'sentiment_batch': SentimentAnalysisTools.analyze_sentiment_batch,
            'fear_greed': CoinGeckoTools.get_fear_greed_index,
        }
        
        # 遍历所有选择的工具并注册
        registered_count = 0
        for tool_id in self.selected_tools:
            logger.debug(f"🔍 [Toolkit] 查找工具: {tool_id}")
            # 在所有分类中查找工具
            found = False
            for category, tools in ToolRegistry.TOOL_REGISTRY.items():
                logger.debug(f"🔍 [Toolkit] 检查分类 {category}，包含工具: {list(tools.keys())[:5]}...")
                if tool_id in tools:
                    tool_info = tools[tool_id]
                    logger.info(f"✅ [Toolkit] 注册工具: {tool_id} ({tool_info.get('display_name', tool_info['name'])})")
                    
                    # 获取实际的工具方法
                    tool_method = tool_method_mapping.get(tool_id, tool_info['function'])
                    logger.debug(f"🔍 [Toolkit] 工具方法: {tool_method}")
                    
                    # 动态创建工具方法并绑定到self
                    # 使用tool_id作为属性名，这样market_analyst可以通过getattr获取
                    setattr(self, tool_id, tool_method)
                    
                    # 也创建tool_前缀的版本以保持兼容性
                    setattr(self, f"tool_{tool_id}", tool_method)
                    
                    registered_count += 1
                    found = True
                    break
            
            if not found:
                logger.warning(f"⚠️ [Toolkit] 未找到工具: {tool_id}")
        
        logger.info(f"🎯 [Toolkit] 工具注册完成，成功注册 {registered_count}/{len(self.selected_tools)} 个工具")

    @staticmethod
    @tool
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """
        
        global_news_result = interface.get_reddit_global_news(curr_date, 7, 5)

        return global_news_result

    @staticmethod
    @tool
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    def get_reddit_stock_info(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        Retrieve the latest Reddit sentiment about a given stock using Reddit public API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: Formatted Reddit sentiment analysis data
        """
        import requests
        import json
        from datetime import datetime, timedelta
        
        try:
            # 根据股票类型选择相关subreddit
            if ticker.upper() in ['BTC', 'BITCOIN']:
                subreddits = ['Bitcoin', 'CryptoCurrency', 'btc']
                search_terms = ['BTC', 'Bitcoin', 'bitcoin']
            elif ticker.upper() in ['ETH', 'ETHEREUM']:
                subreddits = ['ethereum', 'CryptoCurrency', 'ethfinance']
                search_terms = ['ETH', 'Ethereum', 'ethereum']
            else:
                subreddits = ['wallstreetbets', 'stocks', 'investing']
                search_terms = [ticker.upper(), ticker.lower()]
            
            sentiment_data = {
                'total_posts': 0,
                'total_score': 0,
                'total_comments': 0,
                'positive_posts': 0,
                'negative_posts': 0,
                'neutral_posts': 0,
                'top_posts': []
            }
            
            headers = {'User-Agent': 'WhenTrade-Analysis/1.0'}
            
            # 搜索每个subreddit
            for subreddit in subreddits:
                for search_term in search_terms:
                    try:
                        url = f"https://www.reddit.com/r/{subreddit}/search.json"
                        params = {
                            'q': search_term,
                            'sort': 'relevance',
                            'time': timeframe_to_reddit_time(Toolkit._current_timeframe),
                            'limit': 15,
                            'restrict_sr': 'true'
                        }
                        
                        response = requests.get(url, params=params, headers=headers, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            if 'data' in data and 'children' in data['data']:
                                posts = data['data']['children']
                                
                                for post in posts:
                                    if 'data' not in post:
                                        continue
                                        
                                    post_data = post['data']
                                    score = post_data.get('score', 0)
                                    title = post_data.get('title', '').lower()
                                    num_comments = post_data.get('num_comments', 0)
                                    
                                    sentiment_data['total_posts'] += 1
                                    sentiment_data['total_score'] += score
                                    sentiment_data['total_comments'] += num_comments
                                    
                                    # 保存高分帖子
                                    if score > 50:
                                        sentiment_data['top_posts'].append({
                                            'title': post_data.get('title', ''),
                                            'score': score,
                                            'comments': num_comments,
                                            'subreddit': subreddit
                                        })
                                    
                                    # 简单情绪分析
                                    positive_keywords = ['bullish', 'moon', 'buy', 'long', 'pump', 'hodl', 'rally', 'breakout']
                                    negative_keywords = ['bearish', 'crash', 'sell', 'short', 'dump', 'drop', 'fall', 'dip']
                                    
                                    if any(word in title for word in positive_keywords) or score > 100:
                                        sentiment_data['positive_posts'] += 1
                                    elif any(word in title for word in negative_keywords) or score < 0:
                                        sentiment_data['negative_posts'] += 1
                                    else:
                                        sentiment_data['neutral_posts'] += 1
                                        
                    except requests.RequestException as req_e:
                        logger.warning(f"⚠️ Reddit请求失败 ({subreddit}): {req_e}")
                        continue
                    except Exception as parse_e:
                        logger.warning(f"⚠️ Reddit数据解析失败: {parse_e}")
                        continue
            
            # 计算情绪指标
            total_posts = sentiment_data['total_posts']
            if total_posts == 0:
                return f"## {ticker} Reddit情绪分析\n\n暂无找到相关讨论数据"
            
            avg_score = sentiment_data['total_score'] / total_posts if total_posts > 0 else 0
            sentiment_score = (sentiment_data['positive_posts'] - sentiment_data['negative_posts']) / total_posts * 100
            
            # 格式化结果
            result_lines = [
                f"## {ticker} Reddit情绪分析",
                f"**分析帖子数**: {total_posts}",
                f"**平均得分**: {avg_score:.1f}",
                f"**总评论数**: {sentiment_data['total_comments']}",
                f"**正面帖子**: {sentiment_data['positive_posts']} ({sentiment_data['positive_posts']/total_posts*100:.1f}%)",
                f"**负面帖子**: {sentiment_data['negative_posts']} ({sentiment_data['negative_posts']/total_posts*100:.1f}%)",
                f"**中性帖子**: {sentiment_data['neutral_posts']} ({sentiment_data['neutral_posts']/total_posts*100:.1f}%)",
                f"**情绪评分**: {sentiment_score:.1f}% ({'积极' if sentiment_score > 10 else '消极' if sentiment_score < -10 else '中性'})",
            ]
            
            # 添加热门讨论
            if sentiment_data['top_posts']:
                result_lines.append(f"\n### 热门讨论")
                top_posts = sorted(sentiment_data['top_posts'], key=lambda x: x['score'], reverse=True)[:3]
                for i, post in enumerate(top_posts, 1):
                    result_lines.append(f"{i}. **{post['title'][:80]}...** ({post['score']} 👍, {post['comments']} 💬)")
            
            result_lines.append(f"\n*数据来源: Reddit公开API, 分析时间: {curr_date}*")
            
            return "\n".join(result_lines)
            
        except Exception as e:
            logger.error(f"❌ Reddit情绪获取失败: {e}")
            return f"## {ticker} Reddit情绪分析\n\nReddit情绪分析暂时不可用: {str(e)}\n\n*建议：请稍后重试或检查网络连接*"

    @staticmethod
    @tool
    def get_chinese_social_sentiment(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        获取中国社交媒体和财经平台上关于特定股票的情绪分析和讨论热度。
        整合雪球、东方财富股吧、新浪财经等中国本土平台的数据。
        Args:
            ticker (str): 股票代码，如 AAPL, TSM
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含中国投资者情绪分析、讨论热度、关键观点的格式化报告
        """
        try:
            # 这里可以集成多个中国平台的数据
            chinese_sentiment_results = interface.get_chinese_social_sentiment(ticker, curr_date)
            return chinese_sentiment_results
        except Exception as e:
            # 如果中国平台数据获取失败，回退到原有的Reddit数据
            return interface.get_reddit_company_news(ticker, curr_date, 7, 5)

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_china_stock_data(
        stock_code: Annotated[str, "中国股票代码，如 000001(平安银行), 600519(贵州茅台)"],
        start_date: Annotated[str, "开始日期，格式 yyyy-mm-dd"],
        end_date: Annotated[str, "结束日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        获取中国A股实时和历史数据，通过Tushare等高质量数据源提供专业的股票数据。
        支持实时行情、历史K线、技术指标等全面数据，自动使用最佳数据源。
        Args:
            stock_code (str): 中国股票代码，如 000001(平安银行), 600519(贵州茅台)
            start_date (str): 开始日期，格式 yyyy-mm-dd
            end_date (str): 结束日期，格式 yyyy-mm-dd
        Returns:
            str: 包含实时行情、历史数据、技术指标的完整股票分析报告
        """
        try:
            logger.debug(f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 开始调用 =====")
            logger.debug(f"📊 [DEBUG] 参数: stock_code={stock_code}, start_date={start_date}, end_date={end_date}")

            from core.dataflows.interface import get_china_stock_data_unified
            logger.debug(f"📊 [DEBUG] 成功导入统一数据源接口")

            logger.debug(f"📊 [DEBUG] 正在调用统一数据源接口...")
            result = get_china_stock_data_unified(stock_code, start_date, end_date)

            logger.debug(f"📊 [DEBUG] 统一数据源接口调用完成")
            logger.debug(f"📊 [DEBUG] 返回结果类型: {type(result)}")
            logger.debug(f"📊 [DEBUG] 返回结果长度: {len(result) if result else 0}")
            logger.debug(f"📊 [DEBUG] 返回结果前200字符: {str(result)[:200]}...")
            logger.debug(f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 调用结束 =====")

            return result
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] ===== agent_utils.get_china_stock_data 异常 =====")
            logger.error(f"❌ [DEBUG] 错误类型: {type(e).__name__}")
            logger.error(f"❌ [DEBUG] 错误信息: {str(e)}")
            logger.error(f"❌ [DEBUG] 详细堆栈:")
            print(error_details)
            logger.error(f"❌ [DEBUG] ===== 异常处理结束 =====")
            return f"中国股票数据获取失败: {str(e)}。建议安装pytdx库: pip install pytdx"

    @staticmethod
    @tool
    def get_china_market_overview(
        curr_date: Annotated[str, "当前日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        获取中国股市整体概览，包括主要指数的实时行情。
        涵盖上证指数、深证成指、创业板指、科创50等主要指数。
        Args:
            curr_date (str): 当前日期，格式 yyyy-mm-dd
        Returns:
            str: 包含主要指数实时行情的市场概览报告
        """
        try:
            # 使用Tushare获取主要指数数据
            from core.dataflows.tushare_adapter import get_tushare_adapter

            adapter = get_tushare_adapter()
            if not adapter.provider or not adapter.provider.connected:
                # 如果Tushare不可用，回退到TDX
                logger.warning(f"⚠️ Tushare不可用，回退到TDX获取市场概览")
                from core.dataflows.tdx_utils import get_china_market_overview
                return get_china_market_overview()

            # 使用Tushare获取主要指数信息
            # 这里可以扩展为获取具体的指数数据
            return f"""# 中国股市概览 - {curr_date}

## 📊 主要指数
- 上证指数: 数据获取中...
- 深证成指: 数据获取中...
- 创业板指: 数据获取中...
- 科创50: 数据获取中...

## 💡 说明
市场概览功能正在从TDX迁移到Tushare，完整功能即将推出。
当前可以使用股票数据获取功能分析个股。

数据来源: Tushare专业数据源
更新时间: {curr_date}
"""

        except Exception as e:
            return f"中国市场概览获取失败: {str(e)}。正在从TDX迁移到Tushare数据源。"

    @tool
    def get_YFin_data(
        self,
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """
        logger.info(f"📊 [YFin工具] 获取股票数据: {symbol}")
        
        # 发送开始通知
        self._send_tool_status_sync(
            tool_name="get_YFin_data",
            status="starting",
            symbol=symbol,
            message=f"开始获取 {symbol} Yahoo Finance数据"
        )
        
        try:
            result_data = interface.get_YFin_data(symbol, start_date, end_date)
            
            # 发送成功通知
            self._send_tool_status_sync(
                tool_name="get_YFin_data",
                status="completed",
                symbol=symbol,
                message=f"成功获取 {symbol} Yahoo Finance数据"
            )
            
            logger.info(f"✅ [YFin工具] 数据获取成功: {symbol}")
            return result_data
            
        except Exception as e:
            error_msg = f"Yahoo Finance数据获取失败: {str(e)}"
            logger.error(f"❌ [YFin工具] {error_msg}")
            
            # 发送错误通知
            self._send_tool_status_sync(
                tool_name="get_YFin_data",
                status="failed",
                symbol=symbol,
                message=error_msg
            )
            
            return error_msg

    @staticmethod
    @tool
    def get_YFin_data_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data_online(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, False
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_stockstats_indicators_report_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, True
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[
            str,
            "current date of you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider sentiment information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the sentiment in the past 30 days starting at curr_date
        """

        data_sentiment = interface.get_finnhub_company_insider_sentiment(
            ticker, curr_date, 30
        )

        return data_sentiment

    @staticmethod
    @tool
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[
            str,
            "current date you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider transaction information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's insider transactions/trading information in the past 30 days
        """

        data_trans = interface.get_finnhub_company_insider_transactions(
            ticker, curr_date, 30
        )

        return data_trans

    @staticmethod
    @tool
    def get_simfin_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent balance sheet of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's most recent balance sheet
        """

        data_balance_sheet = interface.get_simfin_balance_sheet(ticker, freq, curr_date)

        return data_balance_sheet

    @staticmethod
    @tool
    def get_simfin_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent cash flow statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent cash flow statement
        """

        data_cashflow = interface.get_simfin_cashflow(ticker, freq, curr_date)

        return data_cashflow

    @staticmethod
    @tool
    def get_simfin_income_stmt(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent income statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent income statement
        """

        data_income_stmt = interface.get_simfin_income_statements(
            ticker, freq, curr_date
        )

        return data_income_stmt

    @staticmethod
    @tool
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): How many days to look back
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    @tool
    def get_realtime_stock_news(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        获取股票的实时新闻分析，解决传统新闻源的滞后性问题。
        整合多个专业财经API，提供15-30分钟内的最新新闻。
        支持多种新闻源轮询机制，优先使用实时新闻聚合器，失败时自动尝试备用新闻源。
        对于A股和港股，会优先使用中文财经新闻源（如东方财富）。
        
        Args:
            ticker (str): 股票代码，如 AAPL, TSM, 600036.SH
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含实时新闻分析、紧急程度评估、时效性说明的格式化报告
        """
        from core.dataflows.realtime_news_utils import get_realtime_stock_news
        return get_realtime_stock_news(ticker, curr_date, hours_back=6)

    @tool
    def get_stock_news_openai(
        self,
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news about the company on the given date.
        """
        logger.info(f"📰 [OpenAI新闻工具] 获取 {ticker} 股票新闻")
        
        # 发送开始通知
        self._send_tool_status_sync(
            tool_name="get_stock_news_openai",
            status="starting",
            symbol=ticker,
            message=f"开始获取 {ticker} OpenAI股票新闻"
        )
        
        try:
            openai_news_results = interface.get_stock_news_openai(ticker, curr_date, Toolkit._current_timeframe)
            
            # 发送成功通知
            self._send_tool_status_sync(
                tool_name="get_stock_news_openai",
                status="completed",
                symbol=ticker,
                message=f"成功获取 {ticker} OpenAI股票新闻"
            )
            
            logger.info(f"✅ [OpenAI新闻工具] 新闻获取成功: {ticker}")
            return openai_news_results
            
        except Exception as e:
            error_msg = f"OpenAI股票新闻获取失败: {str(e)}"
            logger.error(f"❌ [OpenAI新闻工具] {error_msg}")
            
            # 发送错误通知
            self._send_tool_status_sync(
                tool_name="get_stock_news_openai",
                status="failed",
                symbol=ticker,
                message=error_msg
            )
            
            return error_msg

    @staticmethod
    @tool
    def get_global_news_openai(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest macroeconomics news on a given date using OpenAI's macroeconomics news API.
        Args:
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest macroeconomic news on the given date.
        """

        openai_news_results = interface.get_global_news_openai(curr_date)

        return openai_news_results

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest fundamental information about a given stock on a given date by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest fundamental information about the company on the given date.
        """
        logger.debug(f"📊 [DEBUG] get_fundamentals_openai 被调用: ticker={ticker}, date={curr_date}")

        # 检查是否为中国股票
        import re
        if re.match(r'^\d{6}$', str(ticker)):
            logger.debug(f"📊 [DEBUG] 检测到中国A股代码: {ticker}")
            # 使用统一接口获取中国股票名称
            try:
                from core.dataflows.interface import get_china_stock_info_unified
                stock_info = get_china_stock_info_unified(ticker)

                # 解析股票名称
                if "股票名称:" in stock_info:
                    company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                else:
                    company_name = f"股票代码{ticker}"

                logger.debug(f"📊 [DEBUG] 中国股票名称映射: {ticker} -> {company_name}")
            except Exception as e:
                logger.error(f"⚠️ [DEBUG] 从统一接口获取股票名称失败: {e}")
                company_name = f"股票代码{ticker}"

            # 修改查询以包含正确的公司名称
            modified_query = f"{company_name}({ticker})"
            logger.debug(f"📊 [DEBUG] 修改后的查询: {modified_query}")
        else:
            logger.debug(f"📊 [DEBUG] 检测到非中国股票: {ticker}")
            modified_query = ticker

        try:
            openai_fundamentals_results = interface.get_fundamentals_openai(
                modified_query, curr_date
            )
            logger.debug(f"📊 [DEBUG] OpenAI基本面分析结果长度: {len(openai_fundamentals_results) if openai_fundamentals_results else 0}")
            return openai_fundamentals_results
        except Exception as e:
            logger.error(f"❌ [DEBUG] OpenAI基本面分析失败: {str(e)}")
            return f"基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_china_fundamentals(
        ticker: Annotated[str, "中国A股股票代码，如600036"],
        curr_date: Annotated[str, "当前日期，格式为yyyy-mm-dd"],
    ):
        """
        获取中国A股股票的基本面信息，使用中国股票数据源。
        Args:
            ticker (str): 中国A股股票代码，如600036, 000001
            curr_date (str): 当前日期，格式为yyyy-mm-dd
        Returns:
            str: 包含股票基本面信息的格式化字符串
        """
        logger.debug(f"📊 [DEBUG] get_china_fundamentals 被调用: ticker={ticker}, date={curr_date}")

        # 检查是否为中国股票
        import re
        if not re.match(r'^\d{6}$', str(ticker)):
            return f"错误：{ticker} 不是有效的中国A股代码格式"

        try:
            # 使用统一数据源接口获取股票数据（默认Tushare，支持备用数据源）
            from core.dataflows.interface import get_china_stock_data_unified
            logger.debug(f"📊 [DEBUG] 正在获取 {ticker} 的股票数据...")

            # 获取最近30天的数据用于基本面分析
            from datetime import datetime, timedelta
            end_date = datetime.strptime(curr_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=30)

            stock_data = get_china_stock_data_unified(
                ticker,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            logger.debug(f"📊 [DEBUG] 股票数据获取完成，长度: {len(stock_data) if stock_data else 0}")

            if not stock_data or "获取失败" in stock_data or "❌" in stock_data:
                return f"无法获取股票 {ticker} 的基本面数据：{stock_data}"

            # 调用真正的基本面分析
            from core.dataflows.optimized_china_data import OptimizedChinaDataProvider

            # 创建分析器实例
            analyzer = OptimizedChinaDataProvider()

            # 生成真正的基本面分析报告
            fundamentals_report = analyzer._generate_fundamentals_report(ticker, stock_data)

            logger.debug(f"📊 [DEBUG] 中国基本面分析报告生成完成")
            logger.debug(f"📊 [DEBUG] get_china_fundamentals 结果长度: {len(fundamentals_report)}")

            return fundamentals_report

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_china_fundamentals 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"中国股票基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_hk_stock_data_unified(
        symbol: Annotated[str, "港股代码，如：0700.HK、9988.HK等"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        获取港股数据的统一接口，优先使用AKShare数据源，备用Yahoo Finance

        Args:
            symbol: 港股代码 (如: 0700.HK)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            str: 格式化的港股数据
        """
        logger.debug(f"🇭🇰 [DEBUG] get_hk_stock_data_unified 被调用: symbol={symbol}, start_date={start_date}, end_date={end_date}")

        try:
            from core.dataflows.interface import get_hk_stock_data_unified

            result = get_hk_stock_data_unified(symbol, start_date, end_date)

            logger.debug(f"🇭🇰 [DEBUG] 港股数据获取完成，长度: {len(result) if result else 0}")

            return result

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_hk_stock_data_unified 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"港股数据获取失败: {str(e)}"

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_fundamentals_unified", log_args=True)
    def get_stock_fundamentals_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"] = None,
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"] = None,
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None
    ) -> str:
        """
        统一的股票基本面分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 基本面分析数据和报告
        """
        logger.info(f"📊 [统一基本面工具] 分析股票: {ticker}")

        # 添加详细的股票代码追踪日志
        logger.info(f"🔍 [股票代码追踪] 统一基本面工具接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})")
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(ticker))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(ticker))}")

        # 保存原始ticker用于对比
        original_ticker = ticker

        try:
            from core.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"🔍 [股票代码追踪] StockUtils.get_market_info 返回的市场信息: {market_info}")
            logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
            logger.info(f"📊 [统一基本面工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']})")

            # 检查ticker是否在处理过程中发生了变化
            if str(ticker) != str(original_ticker):
                logger.warning(f"🔍 [股票代码追踪] 警告：股票代码发生了变化！原始: '{original_ticker}' -> 当前: '{ticker}'")

            # 设置默认日期
            if not curr_date:
                curr_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = curr_date

            result_data = []

            if is_china:
                # 中国A股：获取股票数据 + 基本面数据
                logger.info(f"🇨🇳 [统一基本面工具] 处理A股数据...")
                logger.info(f"🔍 [股票代码追踪] 进入A股处理分支，ticker: '{ticker}'")

                try:
                    # 获取股票价格数据
                    from core.dataflows.interface import get_china_stock_data_unified
                    logger.info(f"🔍 [股票代码追踪] 调用 get_china_stock_data_unified，传入参数: ticker='{ticker}', start_date='{start_date}', end_date='{end_date}'")
                    stock_data = get_china_stock_data_unified(ticker, start_date, end_date)
                    logger.info(f"🔍 [股票代码追踪] get_china_stock_data_unified 返回结果前200字符: {stock_data[:200] if stock_data else 'None'}")
                    result_data.append(f"## A股价格数据\n{stock_data}")
                except Exception as e:
                    logger.error(f"🔍 [股票代码追踪] get_china_stock_data_unified 调用失败: {e}")
                    result_data.append(f"## A股价格数据\n获取失败: {e}")

                try:
                    # 获取基本面数据
                    from core.dataflows.optimized_china_data import OptimizedChinaDataProvider
                    analyzer = OptimizedChinaDataProvider()
                    logger.info(f"🔍 [股票代码追踪] 调用 OptimizedChinaDataProvider._generate_fundamentals_report，传入参数: ticker='{ticker}'")
                    fundamentals_data = analyzer._generate_fundamentals_report(ticker, stock_data if 'stock_data' in locals() else "")
                    logger.info(f"🔍 [股票代码追踪] _generate_fundamentals_report 返回结果前200字符: {fundamentals_data[:200] if fundamentals_data else 'None'}")
                    result_data.append(f"## A股基本面数据\n{fundamentals_data}")
                except Exception as e:
                    logger.error(f"🔍 [股票代码追踪] _generate_fundamentals_report 调用失败: {e}")
                    result_data.append(f"## A股基本面数据\n获取失败: {e}")

            elif is_hk:
                # 港股：使用AKShare数据源，支持多重备用方案
                logger.info(f"🇭🇰 [统一基本面工具] 处理港股数据...")

                hk_data_success = False

                # 主要数据源：AKShare
                try:
                    from core.dataflows.interface import get_hk_stock_data_unified
                    hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                    # 检查数据质量
                    if hk_data and len(hk_data) > 100 and "❌" not in hk_data:
                        result_data.append(f"## 港股数据\n{hk_data}")
                        hk_data_success = True
                        logger.info(f"✅ [统一基本面工具] 港股主要数据源成功")
                    else:
                        logger.warning(f"⚠️ [统一基本面工具] 港股主要数据源质量不佳")

                except Exception as e:
                    logger.error(f"⚠️ [统一基本面工具] 港股主要数据源失败: {e}")

                # 备用方案：基础港股信息
                if not hk_data_success:
                    try:
                        from core.dataflows.interface import get_hk_stock_info_unified
                        hk_info = get_hk_stock_info_unified(ticker)

                        basic_info = f"""## 港股基础信息

**股票代码**: {ticker}
**股票名称**: {hk_info.get('name', f'港股{ticker}')}
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)
**数据源**: {hk_info.get('source', '基础信息')}

⚠️ 注意：详细的价格和财务数据暂时无法获取，建议稍后重试或使用其他数据源。

**基本面分析建议**：
- 建议查看公司最新财报
- 关注港股市场整体走势
- 考虑汇率因素对投资的影响
"""
                        result_data.append(basic_info)
                        logger.info(f"✅ [统一基本面工具] 港股备用信息成功")

                    except Exception as e2:
                        # 最终备用方案
                        fallback_info = f"""## 港股信息（备用）

**股票代码**: {ticker}
**股票类型**: 港股
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)

❌ 数据获取遇到问题: {str(e2)}

**建议**：
1. 检查网络连接
2. 稍后重试分析
3. 使用其他港股数据源
4. 查看公司官方财报
"""
                        result_data.append(fallback_info)
                        logger.warning(f"⚠️ [统一基本面工具] 港股使用最终备用方案")

            else:
                # 美股：使用OpenAI/Finnhub数据源
                logger.info(f"🇺🇸 [统一基本面工具] 处理美股数据...")

                try:
                    from core.dataflows.interface import get_fundamentals_openai
                    us_data = get_fundamentals_openai(ticker, curr_date)
                    result_data.append(f"## 美股基本面数据\n{us_data}")
                except Exception as e:
                    result_data.append(f"## 美股基本面数据\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 基本面分析数据

**股票类型**: {market_info['market_name']}
**货币**: {market_info['currency_name']} ({market_info['currency_symbol']})
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            logger.info(f"📊 [统一基本面工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一基本面分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一基本面工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_market_data_unified", log_args=True)
    def get_stock_market_data_unified(
        ticker: Annotated[str, "代币符号（如BTC、ETH等）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        统一的市场数据工具 - 支持加密货币
        自动识别资产类型并调用相应的数据源获取价格和技术指标数据

        Args:
            ticker: 代币符号（如：BTC、ETH、USDT）
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）

        Returns:
            str: 市场数据和技术分析报告
        """
        logger.info(f"📈 [统一市场工具] 分析: {ticker}")

        try:
            from core.utils.stock_utils import StockUtils

            # 自动识别资产类型
            market_info = StockUtils.get_market_info(ticker)
            
            logger.info(f"📈 [统一市场工具] 资产类型: {market_info['market_name']}")
            
            # 如果是加密货币，使用加密货币API
            if market_info['is_crypto']:
                logger.info(f"🪙 [统一市场工具] 处理加密货币数据...")
                
                try:
                    from core.agents.tools import analyst_tools
                    
                    # 获取价格数据
                    price_data = analyst_tools.get_crypto_price_data(ticker, days_back=30)
                    
                    if 'error' in price_data:
                        return f"加密货币数据获取失败: {price_data['error']}"
                    
                    # 获取技术指标
                    indicators_data = analyst_tools.get_technical_indicators(ticker)
                    
                    # 返回格式化的加密货币数据
                    result = f"""# {ticker} 市场数据分析

**类型**: 加密货币
**当前价格**: ${price_data.get('latest_price', 0):.2f}
**价格变化**: {price_data.get('price_change_pct', 0):.2f}%
**分析期间**: {start_date} 至 {end_date}
**数据记录**: {price_data.get('total_records', 0)}条

## 技术指标
"""
                    
                    if 'error' not in indicators_data:
                        indicators = indicators_data.get('indicators', {})
                        
                        # RSI
                        rsi = indicators.get('rsi')
                        if rsi:
                            status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "正常"
                            result += f"- RSI (14): {rsi:.2f} ({status})\n"
                        
                        # 移动平均线
                        sma_20 = indicators.get('sma_20')
                        sma_50 = indicators.get('sma_50')
                        if sma_20:
                            result += f"- SMA (20): ${sma_20:.2f}\n"
                        if sma_50:
                            result += f"- SMA (50): ${sma_50:.2f}\n"
                        
                        # MACD
                        macd = indicators.get('macd')
                        macd_signal = indicators.get('macd_signal')
                        if macd and macd_signal:
                            result += f"- MACD: {macd:.4f}\n"
                            result += f"- MACD信号线: {macd_signal:.4f}\n"
                        
                        # 布林带
                        bb_upper = indicators.get('bb_upper')
                        bb_lower = indicators.get('bb_lower')
                        if bb_upper and bb_lower:
                            result += f"- 布林带上轨: ${bb_upper:.2f}\n"
                            result += f"- 布林带下轨: ${bb_lower:.2f}\n"
                    else:
                        result += "技术指标计算失败\n"
                    
                    result += "\n---\n*数据来源: 实时加密货币API*"
                    
                    logger.info(f"✅ [统一市场工具] 加密货币数据获取完成")
                    return result
                    
                except Exception as e:
                    error_msg = f"加密货币数据获取失败: {str(e)}"
                    logger.error(f"❌ [统一市场工具] {error_msg}")
                    return error_msg
            else:
                # 非加密货币资产暂不支持
                return f"暂不支持非加密货币资产: {ticker}"
                
        except Exception as e:
            error_msg = f"统一市场数据工具执行失败: {str(e)}"
            logger.error(f"❌ [统一市场工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_news_unified", log_args=True)
    def get_stock_news_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        统一的股票新闻工具
        自动识别股票类型（A股、港股、美股）并调用相应的新闻数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 新闻分析报告
        """
        logger.info(f"📰 [统一新闻工具] 分析股票: {ticker}")

        try:
            from core.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"📰 [统一新闻工具] 股票类型: {market_info['market_name']}")

            # 计算新闻查询的日期范围
            end_date = datetime.strptime(curr_date, '%Y-%m-%d')
            days_back = timeframe_to_days(Toolkit._current_timeframe)
            start_date = end_date - timedelta(days=days_back)
            start_date_str = start_date.strftime('%Y-%m-%d')

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用AKShare东方财富新闻和Google新闻（中文搜索）
                logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 处理中文新闻...")

                # 1. 尝试获取AKShare东方财富新闻
                try:
                    # 处理股票代码
                    clean_ticker = ticker.replace('.SH', '').replace('.SZ', '').replace('.SS', '')\
                                   .replace('.HK', '').replace('.XSHE', '').replace('.XSHG', '')
                    
                    logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 尝试获取东方财富新闻: {clean_ticker}")
                    
                    # 导入AKShare新闻获取函数
                    from core.dataflows.akshare_utils import get_stock_news_em
                    
                    # 获取东方财富新闻
                    news_df = get_stock_news_em(clean_ticker)
                    
                    if not news_df.empty:
                        # 格式化东方财富新闻
                        em_news_items = []
                        for _, row in news_df.iterrows():
                            news_title = row.get('标题', '')
                            news_time = row.get('时间', '')
                            news_url = row.get('链接', '')
                            
                            news_item = f"- **{news_title}** [{news_time}]({news_url})"
                            em_news_items.append(news_item)
                        
                        # 添加到结果中
                        if em_news_items:
                            em_news_text = "\n".join(em_news_items)
                            result_data.append(f"## 东方财富新闻\n{em_news_text}")
                            logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 成功获取{len(em_news_items)}条东方财富新闻")
                except Exception as em_e:
                    logger.error(f"❌ [统一新闻工具] 东方财富新闻获取失败: {em_e}")
                    result_data.append(f"## 东方财富新闻\n获取失败: {em_e}")

                # 2. 获取Google新闻作为补充
                try:
                    # 获取公司中文名称用于搜索
                    if is_china:
                        # A股使用股票代码搜索，添加更多中文关键词
                        clean_ticker = ticker.replace('.SH', '').replace('.SZ', '').replace('.SS', '')\
                                       .replace('.XSHE', '').replace('.XSHG', '')
                        search_query = f"{clean_ticker} 股票 公司 财报 新闻"
                        logger.info(f"🇨🇳 [统一新闻工具] A股Google新闻搜索关键词: {search_query}")
                    else:
                        # 港股使用代码搜索
                        search_query = f"{ticker} 港股"
                        logger.info(f"🇭🇰 [统一新闻工具] 港股Google新闻搜索关键词: {search_query}")

                    from core.dataflows.interface import get_google_news
                    news_data = get_google_news(search_query, curr_date)
                    result_data.append(f"## Google新闻\n{news_data}")
                    logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 成功获取Google新闻")
                except Exception as google_e:
                    logger.error(f"❌ [统一新闻工具] Google新闻获取失败: {google_e}")
                    result_data.append(f"## Google新闻\n获取失败: {google_e}")

            else:
                # 美股：使用Finnhub新闻
                logger.info(f"🇺🇸 [统一新闻工具] 处理美股新闻...")

                try:
                    from core.dataflows.interface import get_finnhub_news
                    news_data = get_finnhub_news(ticker, start_date_str, curr_date)
                    result_data.append(f"## 美股新闻\n{news_data}")
                except Exception as e:
                    result_data.append(f"## 美股新闻\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 新闻分析

**股票类型**: {market_info['market_name']}
**分析日期**: {curr_date}
**新闻时间范围**: {start_date_str} 至 {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的新闻源*
"""

            logger.info(f"📰 [统一新闻工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一新闻工具执行失败: {str(e)}"
            logger.error(f"❌ [统一新闻工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_sentiment_unified", log_args=True)
    def get_stock_sentiment_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        统一的股票情绪分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的情绪数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 情绪分析报告
        """
        logger.info(f"😊 [统一情绪工具] 分析股票: {ticker}")

        try:
            from core.utils.stock_utils import StockUtils

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"😊 [统一情绪工具] 股票类型: {market_info['market_name']}")

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用社交媒体情绪分析
                logger.info(f"🇨🇳🇭🇰 [统一情绪工具] 处理中文市场情绪...")

                try:
                    # 可以集成微博、雪球、东方财富等中文社交媒体情绪
                    # 目前使用基础的情绪分析
                    sentiment_summary = f"""
## 中文市场情绪分析

**股票**: {ticker} ({market_info['market_name']})
**分析日期**: {curr_date}

### 市场情绪概况
- 由于中文社交媒体情绪数据源暂未完全集成，当前提供基础分析
- 建议关注雪球、东方财富、同花顺等平台的讨论热度
- 港股市场还需关注香港本地财经媒体情绪

### 情绪指标
- 整体情绪: 中性
- 讨论热度: 待分析
- 投资者信心: 待评估

*注：完整的中文社交媒体情绪分析功能正在开发中*
"""
                    result_data.append(sentiment_summary)
                except Exception as e:
                    result_data.append(f"## 中文市场情绪\n获取失败: {e}")

            else:
                # 美股：使用Reddit情绪分析
                logger.info(f"🇺🇸 [统一情绪工具] 处理美股情绪...")

                try:
                    from core.dataflows.interface import get_reddit_sentiment

                    sentiment_data = get_reddit_sentiment(ticker, curr_date)
                    result_data.append(f"## 美股Reddit情绪\n{sentiment_data}")
                except Exception as e:
                    result_data.append(f"## 美股Reddit情绪\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 情绪分析

**股票类型**: {market_info['market_name']}
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的情绪数据源*
"""

            logger.info(f"😊 [统一情绪工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一情绪分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一情绪工具] {error_msg}")
            return error_msg
