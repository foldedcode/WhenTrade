from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
import time
import json
import traceback
from datetime import datetime

# 导入分析模块日志装饰器
from core.utils.tool_logging import log_analyst_module

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")

# 导入提示词加载器
from core.agents.prompt_loader import get_prompt_loader

# 导入Redis发布器，用于发送工具执行事件
from core.services.redis_pubsub import redis_publisher


def _calculate_time_params(timeframe: str, current_date: str) -> dict:
    """
    智能计算时间参数，平衡数据充足性和数据量
    目标：60-100个数据点，足够计算技术指标，但不会过多
    
    Args:
        timeframe: 时间框架 ('1天', '1周', '1月', '1年' 或 '1d', '1w', '1m', '1y')  
        current_date: 当前日期字符串
        
    Returns:
        包含智能调整后的时间参数字典
    """
    from datetime import datetime, timedelta
    
    # 优化配置：控制数据点在60-120之间，平衡数据充足性和Token使用
    timeframe_config = {
        # 中文映射
        '1天': {
            'days': 1,         # 用户选择的显示范围
            'interval': '5m',  # 5分钟K线，提供足够精度计算技术指标
            'fetch_days': 2,   # 获取2天数据确保有足够数据点
            'points': 576      # 2天 × 288个5分钟 = 576个点
        },
        '1周': {
            'days': 7,
            'interval': '2h',  # 2小时K线，平衡精度和数据量
            'fetch_days': 7,   # 获取完整7天数据
            'points': 84       # 7天 × 12个2小时 = 84个点
        },
        '1月': {
            'days': 30,
            'interval': '6h',  # 6小时K线，适合中期分析
            'fetch_days': 30,  # 获取完整30天数据
            'points': 120      # 30天 × 4个6小时 = 120个点
        },
        '1年': {
            'days': 365,
            'interval': '1d',  # 日K线，经典长期分析
            'fetch_days': 90,  # 只获取90天（3个月），避免数据过多
            'points': 90       # 90天 = 90个点
        },
        # 英文映射
        '1d': {
            'days': 1,
            'interval': '5m',  # 修改为5分钟K线
            'fetch_days': 2,   # 获取2天数据
            'points': 576      # 2天 × 288个5分钟 = 576个点
        },
        '1w': {
            'days': 7,
            'interval': '2h',
            'fetch_days': 7,
            'points': 84
        },
        '1m': {
            'days': 30,
            'interval': '6h',
            'fetch_days': 30,
            'points': 120
        },
        '1y': {
            'days': 365,
            'interval': '1d',
            'fetch_days': 90,
            'points': 90
        },
        # 小时级映射
        '1h': {
            'days': 0.04,      # 1小时 = 0.04天（明确表示这是1小时而非1天）
            'interval': '1m',  # 1分钟K线，适合小时级分析
            'fetch_days': 1,   # 获取1天数据提供足够历史数据
            'points': 60       # 1小时 = 60个1分钟点
        },
        '4h': {
            'days': 1,
            'interval': '30m',
            'fetch_days': 2,   # 获取2天数据以确保足够点数
            'points': 96       # 2天 × 48个30分钟 = 96个点
        }
    }
    
    # 获取配置
    config = timeframe_config.get(timeframe)
    
    if not config:
        # 默认配置：中等时间范围
        logger.warning(f"未识别的timeframe: {timeframe}，使用默认配置")
        config = {
            'days': 30,
            'interval': '4h',
            'fetch_days': 30,
            'points': 180
        }
    
    # 解析当前日期
    try:
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
    except:
        current_dt = datetime.now()
        logger.warning(f"日期解析失败，使用当前时间: {current_dt}")
    
    # 计算日期范围
    start_date = (current_dt - timedelta(days=config['fetch_days'])).strftime('%Y-%m-%d')
    end_date = current_dt.strftime('%Y-%m-%d')
    
    result = {
        'start_date': start_date,
        'end_date': end_date,
        'period_days': config['fetch_days'],      # 实际获取的天数
        'display_days': config['days'],           # 用户选择的显示范围
        'interval': config['interval'],           # 动态K线间隔
        'expected_points': config['points'],      # 预期数据点数
        'days_back': config['days']               # 用于情绪分析工具
    }
    
    logger.info(f"📊 时间参数配置: {timeframe} → {config['interval']}间隔, {config['points']}个数据点")
    
    return result


def _construct_tool_args(tool_id: str, symbol: str, time_params: dict) -> dict:
    """
    根据工具ID和时间参数构造工具调用参数
    
    Args:
        tool_id: 工具ID (如 'crypto_price', 'indicators')
        symbol: 交易标的
        time_params: 时间参数字典
        
    Returns:
        工具调用参数字典
    """
    # 🔧 增强：严格的参数验证
    if not isinstance(tool_id, str) or not tool_id.strip():
        logger.error(f"❌ [参数验证] tool_id 必须是非空字符串，实际为: {type(tool_id).__name__} = {tool_id}")
        return {'symbol': symbol, 'error': 'invalid_tool_id'}
    
    if not isinstance(symbol, str) or not symbol.strip():
        logger.error(f"❌ [参数验证] symbol 必须是非空字符串，实际为: {type(symbol).__name__} = {symbol}")
        return {'error': 'invalid_symbol'}
    
    if not isinstance(time_params, dict):
        logger.error(f"❌ [参数验证] time_params 必须是字典，实际为: {type(time_params).__name__} = {time_params}")
        return {'symbol': symbol, 'error': 'invalid_time_params'}
    
    # 🔧 增强：验证time_params的必要字段
    required_fields = ['start_date', 'end_date', 'period_days', 'days_back', 'interval']
    missing_fields = [field for field in required_fields if field not in time_params]
    if missing_fields:
        logger.warning(f"⚠️ [参数验证] time_params 缺少字段: {missing_fields}")
        # 提供默认值
        defaults = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31', 
            'period_days': 30,
            'days_back': 7,
            'interval': '1d'
        }
        for field in missing_fields:
            time_params[field] = defaults.get(field, '1d')
        logger.info(f"🔧 [参数修复] 已添加默认值: {missing_fields}")
    
    try:
        # 🔧 修复：优先处理无参数工具
        no_param_tools = {
            'fear_greed': {},  # 恐惧贪婪指数不需要任何参数
            'market_overview': {},  # 市场概览不需要参数
            'global_market_cap': {}  # 全球市值不需要参数
        }
        
        # 如果是无参数工具，直接返回空字典
        if tool_id in no_param_tools:
            logger.debug(f"🔧 [无参数工具] {tool_id} 不需要参数")
            return no_param_tools[tool_id]
        
        # 技术分析工具参数 (使用正确的工具ID)
        technical_tools = {
            'crypto_price': {
                'symbol': symbol,
                'start_date': time_params['start_date'], 
                'end_date': time_params['end_date'],
                'interval': time_params['interval']
            },
            'indicators': {
                'symbol': symbol,
                'indicators': ['sma', 'ema', 'rsi', 'macd', 'bb'],  # 默认指标
                'period_days': time_params['period_days'],
                'interval': time_params.get('interval', '1d')  # 传递 interval 参数
            },
            'market_data': {
                'symbol': symbol,
                'vs_currency': 'usd'
            },
            'historical_data': {
                'symbol': symbol,
                'days': time_params['days_back'],
                'vs_currency': 'usd'
            },
        }
        
        # 情绪分析工具参数  
        sentiment_tools = {
            'finnhub_news': {
                'symbol': symbol,
                'days_back': time_params['days_back'],
                'max_results': 10
            },
            'reddit_sentiment': {
                'symbol': symbol,
                'days_back': time_params['days_back'],
                'max_results': 10
            },
            'sentiment_batch': {
                'symbol': symbol,
                'sources': ['finnhub', 'reddit'],
                'days_back': time_params['days_back']
            }
        }
        
        # 合并所有工具参数
        all_tools = {**technical_tools, **sentiment_tools}
        
        # 返回对应工具的参数，如果没找到则返回基本参数
        result = all_tools.get(tool_id, {'symbol': symbol})
        
        # 🔧 增强：记录构造的参数用于调试
        logger.debug(f"🔧 [参数构造] {tool_id} -> {result}")
        return result
        
    except Exception as e:
        # 🔧 增强：捕获构造参数时的异常
        logger.error(f"❌ [参数构造] 构造 {tool_id} 参数时发生异常: {e}")
        logger.debug(f"🔍 [参数构造调试] symbol={symbol}, time_params={time_params}")
        return {'symbol': symbol, 'error': f'construction_failed: {str(e)}'}


def _get_company_name(ticker: str, market_info: dict) -> str:
    """
    根据股票代码获取公司名称

    Args:
        ticker: 股票代码
        market_info: 市场信息字典

    Returns:
        str: 公司名称
    """
    try:
        if market_info['is_china']:
            # 中国A股：使用统一接口获取股票信息
            from core.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)

            # 解析股票名称
            if "股票名称:" in stock_info:
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                logger.debug(f"📊 [DEBUG] 从统一接口获取中国股票名称: {ticker} -> {company_name}")
                return company_name
            else:
                logger.warning(f"⚠️ [DEBUG] 无法从统一接口解析股票名称: {ticker}")
                return f"股票代码{ticker}"

        elif market_info['is_hk']:
            # 港股：使用改进的港股工具
            try:
                from core.dataflows.improved_hk_utils import get_hk_company_name_improved
                company_name = get_hk_company_name_improved(ticker)
                logger.debug(f"📊 [DEBUG] 使用改进港股工具获取名称: {ticker} -> {company_name}")
                return company_name
            except Exception as e:
                logger.debug(f"📊 [DEBUG] 改进港股工具获取名称失败: {e}")
                # 降级方案：生成友好的默认名称
                clean_ticker = ticker.replace('.HK', '').replace('.hk', '')
                return f"港股{clean_ticker}"

        elif market_info['is_us']:
            # 美股：使用简单映射或返回代码
            us_stock_names = {
                'AAPL': '苹果公司',
                'TSLA': '特斯拉',
                'NVDA': '英伟达',
                'MSFT': '微软',
                'GOOGL': '谷歌',
                'AMZN': '亚马逊',
                'META': 'Meta',
                'NFLX': '奈飞'
            }

            company_name = us_stock_names.get(ticker.upper(), f"美股{ticker}")
            logger.debug(f"📊 [DEBUG] 美股名称映射: {ticker} -> {company_name}")
            return company_name

        else:
            return f"股票{ticker}"

    except Exception as e:
        logger.error(f"❌ [DEBUG] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_market_analyst_react(llm, toolkit):
    """使用ReAct Agent模式的市场分析师（适用于通义千问）"""
    @log_analyst_module("market_react")
    def market_analyst_react_node(state):
        logger.debug(f"📈 [DEBUG] ===== ReAct市场分析师节点开始 =====")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        logger.debug(f"📈 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")

        # 检查是否为中国股票
        def is_china_stock(ticker_code):
            import re
            return re.match(r'^\d{6}$', str(ticker_code))

        is_china = is_china_stock(ticker)
        logger.debug(f"📈 [DEBUG] 股票类型检查: {ticker} -> 中国A股: {is_china}")

        if toolkit.config["online_tools"]:
            # 在线模式，使用ReAct Agent
            if is_china:
                logger.info(f"📈 [市场分析师] 使用ReAct Agent分析中国股票")

                # 创建中国股票数据工具
                from langchain_core.tools import BaseTool

                class ChinaStockDataTool(BaseTool):
                    name: str = "get_china_stock_data"
                    description: str = f"获取中国A股股票{ticker}的市场数据和技术指标（优化缓存版本）。直接调用，无需参数。"

                    def _run(self, query: str = "") -> str:
                        try:
                            logger.debug(f"📈 [DEBUG] ChinaStockDataTool调用，股票代码: {ticker}")
                            # 使用优化的缓存数据获取
                            from core.dataflows.optimized_china_data import get_china_stock_data_cached
                            return get_china_stock_data_cached(
                                symbol=ticker,
                                start_date='2025-05-28',
                                end_date=current_date,
                                force_refresh=False
                            )
                        except Exception as e:
                            logger.error(f"❌ 优化A股数据获取失败: {e}")
                            # 备用方案：使用原始API
                            try:
                                return toolkit.get_china_stock_data.invoke({
                                    'stock_code': ticker,
                                    'start_date': '2025-05-28',
                                    'end_date': current_date
                                })
                            except Exception as e2:
                                return f"获取股票数据失败: {str(e2)}"

                tools = [ChinaStockDataTool()]
                query = f"""请对中国A股股票{ticker}进行详细的技术分析。

执行步骤：
1. 使用get_china_stock_data工具获取股票市场数据
2. 基于获取的真实数据进行深入的技术指标分析
3. 直接输出完整的技术分析报告内容

重要要求：
- 必须输出完整的技术分析报告内容，不要只是描述报告已完成
- 报告必须基于工具获取的真实数据进行分析
- 报告长度不少于800字
- 包含具体的数据、指标数值和专业分析

报告格式应包含：
## 股票基本信息
## 技术指标分析
## 价格趋势分析
## 成交量分析
## 市场情绪分析
## 投资建议"""
            else:
                logger.info(f"📈 [市场分析师] 使用ReAct Agent分析美股/港股")

                # 创建美股数据工具
                from langchain_core.tools import BaseTool

                class RealTimeCryptoDataTool(BaseTool):
                    name: str = "get_crypto_data_realtime"
                    description: str = f"获取{ticker}的实时加密货币价格数据和技术指标。直接调用，无需参数。"

                    def _run(self, query: str = "") -> str:
                        try:
                            logger.info(f"📈 [实时数据] 获取{ticker}的实时价格数据和技术指标...")
                            
                            # 使用新的实时API工具
                            from core.agents.tools import analyst_tools
                            
                            # 获取价格数据
                            price_result = analyst_tools.get_crypto_price_data(ticker, days_back=30)
                            if 'error' in price_result:
                                return f"获取实时价格数据失败: {price_result['error']}"
                            
                            # 获取技术指标
                            indicators_result = analyst_tools.get_technical_indicators(
                                ticker, 
                                indicators=['sma', 'rsi', 'macd', 'bb']
                            )
                            
                            # 格式化数据
                            formatted_data = f"=== {ticker} 实时市场数据 ===\n\n"
                            
                            # 价格信息
                            formatted_data += f"当前价格: ${price_result.get('latest_price', 0):.2f}\n"
                            formatted_data += f"价格变化: {price_result.get('price_change_pct', 0):.2f}%\n"
                            formatted_data += f"价格变化金额: ${price_result.get('price_change', 0):.2f}\n"
                            formatted_data += f"数据记录: {price_result.get('total_records')}条\n"
                            formatted_data += f"分析周期: {price_result.get('start_date')} 到 {price_result.get('end_date')}\n\n"
                            
                            # 技术指标
                            if 'error' not in indicators_result:
                                indicators = indicators_result.get('indicators', {})
                                formatted_data += "=== 技术指标 ===\n"
                                
                                # RSI
                                rsi = indicators.get('rsi')
                                if rsi:
                                    status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "正常"
                                    formatted_data += f"RSI (14): {rsi:.2f} ({status})\n"
                                
                                # 移动平均线
                                sma_20 = indicators.get('sma_20')
                                sma_50 = indicators.get('sma_50')
                                if sma_20:
                                    formatted_data += f"SMA (20): ${sma_20:.2f}\n"
                                if sma_50:
                                    formatted_data += f"SMA (50): ${sma_50:.2f}\n"
                                
                                # MACD
                                macd = indicators.get('macd')
                                macd_signal = indicators.get('macd_signal')
                                if macd and macd_signal:
                                    formatted_data += f"MACD: {macd:.4f}\n"
                                    formatted_data += f"MACD信号线: {macd_signal:.4f}\n"
                                
                                # 布林带
                                bb_upper = indicators.get('bb_upper')
                                bb_lower = indicators.get('bb_lower')
                                if bb_upper and bb_lower:
                                    formatted_data += f"布林带上轨: ${bb_upper:.2f}\n"
                                    formatted_data += f"布林带下轨: ${bb_lower:.2f}\n"
                            
                            logger.info(f"✅ [实时数据] 成功获取{ticker}价格和技术指标")
                            return formatted_data
                            
                        except Exception as e:
                            logger.error(f"❌ [实时数据] 获取失败: {e}")
                            return f"获取实时加密货币数据失败: {str(e)}"

                class RealTimeCryptoNewsTool(BaseTool):
                    name: str = "get_crypto_news_realtime"
                    description: str = f"获取{ticker}的实时加密货币新闻和市场情绪（通过FinnHub API）。直接调用，无需参数。"

                    def _run(self, query: str = "") -> str:
                        try:
                            logger.info(f"📰 [实时新闻] 获取{ticker}的实时新闻数据...")
                            
                            # 使用新的实时API工具
                            from core.agents.tools import analyst_tools
                            result = analyst_tools.get_crypto_news(ticker, days_back=7, max_results=10)
                            
                            if 'error' in result:
                                return f"获取实时新闻失败: {result['error']}"
                            
                            # 格式化新闻数据
                            articles = result.get('articles', [])
                            news_count = result.get('news_count', 0)
                            
                            if not articles:
                                return f"暂时没有找到{ticker}相关的新闻数据"
                            
                            formatted_news = f"=== {ticker} 实时新闻 ({news_count}条) ===\n\n"
                            for i, article in enumerate(articles[:5], 1):
                                formatted_news += f"{i}. {article.get('headline', 'No headline')}\n"
                                formatted_news += f"   来源: {article.get('source', 'Unknown')}\n"
                                formatted_news += f"   时间: {article.get('datetime', 'N/A')}\n"
                                formatted_news += f"   摘要: {article.get('summary', 'No summary')[:150]}...\n\n"
                            
                            logger.info(f"✅ [实时新闻] 成功获取{news_count}条{ticker}新闻")
                            return formatted_news
                            
                        except Exception as e:
                            logger.error(f"❌ [实时新闻] 获取失败: {e}")
                            return f"获取实时新闻数据失败: {str(e)}"

                tools = [RealTimeCryptoDataTool(), RealTimeCryptoNewsTool()]
                query = f"""请对加密货币{ticker}进行详细的技术分析。

执行步骤：
1. 使用get_crypto_data_realtime工具获取{ticker}的实时价格数据和技术指标
2. 使用get_crypto_news_realtime工具获取最新加密货币新闻和市场情绪
3. 基于获取的真实数据进行深入的技术指标分析
4. 直接输出完整的技术分析报告内容

重要要求：
- 必须输出完整的技术分析报告内容，不要只是描述报告已完成
- 报告必须基于工具获取的真实数据进行分析
- 报告长度不少于800字
- 包含具体的数据、指标数值和专业分析
- 结合新闻信息分析市场情绪

报告格式应包含：
## 加密货币基本信息
## 技术指标分析
## 价格趋势分析
## 成交量分析
## 新闻和市场情绪分析
## 投资建议"""

            try:
                # 创建ReAct Agent
                prompt = hub.pull("hwchase17/react")
                agent = create_react_agent(llm, tools, prompt)
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    handle_parsing_errors=True,
                    max_iterations=10,  # 增加到10次迭代，确保有足够时间完成分析
                    max_execution_time=180  # 增加到3分钟，给更多时间生成详细报告
                )

                logger.debug(f"📈 [DEBUG] 执行ReAct Agent查询...")
                result = agent_executor.invoke({'input': query})

                report = result['output']
                logger.info(f"📈 [市场分析师] ReAct Agent完成，报告长度: {len(report)}")

            except Exception as e:
                logger.error(f"❌ [DEBUG] ReAct Agent失败: {str(e)}")
                report = f"ReAct Agent市场分析失败: {str(e)}"
        else:
            # 离线模式，使用原有逻辑
            report = "离线模式，暂不支持"

        logger.debug(f"📈 [DEBUG] ===== ReAct市场分析师节点结束 =====")

        return {
            "messages": [("assistant", report)],
            "market_report": report,
        }

    return market_analyst_react_node


# 工具ID到中文名称的映射（已弃用：请使用 get_tool_name() 进行多语言支持）
TOOL_NAME_CN = {
    # 技术分析工具
    'crypto_price': '加密货币价格',
    'indicators': '技术指标',
    'market_data': '实时市场数据',
    'historical_data': '历史数据',
    # 情绪分析工具
    'finnhub_news': 'Finnhub新闻',
    'reddit_sentiment': 'Reddit情绪',
    'sentiment_batch': '批量情绪分析',
    'fear_greed': '恐惧贪婪指数',
    # 传统工具
    'get_stock_market_data_unified': '统一市场数据',
    'get_china_stock_data': '中国股票数据',
    'get_YFin_data_online': 'Yahoo财经数据',
    'get_stockstats_indicators_report_online': '技术指标报告',
    'get_hk_stock_data_unified': '港股数据',
    'get_stock_news_openai': '股票新闻',
    'get_reddit_stock_info': 'Reddit股票信息'
}


def create_market_analyst(llm, toolkit):

    def market_analyst_node(state):
        logger.debug(f"📈 [DEBUG] ===== 市场分析师节点开始 =====")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        logger.debug(f"📈 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")
        logger.debug(f"📈 [DEBUG] 当前状态中的消息数量: {len(state.get('messages', []))}")
        logger.debug(f"📈 [DEBUG] 现有市场报告: {state.get('market_report', 'None')}")
        
        # 获取序列锁 - 确保顺序执行
        logger.info(f"🔒 [市场分析师] 获取序列锁，开始执行")

        # 根据股票代码格式选择数据源
        from core.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)

        logger.debug(f"📈 [DEBUG] 股票类型检查: {ticker} -> {market_info['market_name']} ({market_info['currency_name']})")

        # 获取公司名称
        company_name = _get_company_name(ticker, market_info)
        logger.debug(f"📈 [DEBUG] 公司名称: {ticker} -> {company_name}")

        if toolkit.config["online_tools"]:
            # Phase 2: 根据用户选择动态构建工具列表
            selected_tools = state.get("selected_tools", [])
            
            # 区分"用户选择了0个工具"和"用户没有进行工具配置"两种情况
            # 如果selected_tools在state中且不为None，表示用户进行了工具配置
            if "selected_tools" in state and selected_tools is not None:
                # 用户有具体的工具选择，使用用户选择的工具
                logger.info(f"📊 [Phase 2] 市场分析师使用用户选择的工具: {selected_tools} (共{len(selected_tools)}个)")
                
                # 导入实际的工具函数
                from core.services.tools.technical_tools import TechnicalAnalysisTools
                from core.services.tools.coingecko_tools import CoinGeckoTools
                from core.services.tools.sentiment_tools import SentimentAnalysisTools
                
                # 工具名称映射表（前端工具ID -> 实际工具方法）
                tool_mapping = {
                    # 技术分析工具 (Technical Analysis)
                    'crypto_price': TechnicalAnalysisTools.get_crypto_price_data,
                    'indicators': TechnicalAnalysisTools.calculate_technical_indicators,
                    'market_data': CoinGeckoTools.get_coin_market_data,
                    'historical_data': CoinGeckoTools.get_historical_prices,
                    'market_metrics': CoinGeckoTools.get_market_metrics,
                    'trending': CoinGeckoTools.get_trending_coins,
                    'fear_greed': CoinGeckoTools.get_fear_greed_index,
                    
                    # 情绪分析工具 (Sentiment Analysis)
                    'finnhub_news': SentimentAnalysisTools.get_finnhub_crypto_news,
                    'reddit_sentiment': SentimentAnalysisTools.get_crypto_reddit_sentiment,
                    'sentiment_batch': SentimentAnalysisTools.analyze_sentiment_batch,
                    
                    # 保留原有的工具映射以向后兼容
                    'get_stock_market_data_unified': toolkit.get_stock_market_data_unified,
                    'get_china_stock_data': toolkit.get_china_stock_data,
                    'get_YFin_data_online': toolkit.get_YFin_data_online,
                    'get_stockstats_indicators_report_online': toolkit.get_stockstats_indicators_report_online,
                    'get_hk_stock_data_unified': toolkit.get_hk_stock_data_unified,
                    'get_stock_news_openai': getattr(toolkit, 'get_stock_news_openai', None),
                    'get_reddit_stock_info': getattr(toolkit, 'get_reddit_stock_info', None),
                }
                
                # 根据用户选择构建工具列表
                tools = []
                for tool_name in selected_tools:
                    # 首先尝试从映射表获取
                    tool_method = tool_mapping.get(tool_name)
                    
                    # 如果映射表没有，尝试从toolkit动态属性获取
                    if tool_method is None:
                        tool_method = getattr(toolkit, tool_name, None)
                    
                    # 如果还是没有，尝试添加tool_前缀
                    if tool_method is None:
                        tool_method = getattr(toolkit, f"tool_{tool_name}", None)
                    
                    if tool_method is not None:
                        tools.append(tool_method)
                        logger.info(f"✅ [Phase 2] 已添加用户选择的工具: {tool_name}")
                    else:
                        logger.warning(f"⚠️ [Phase 2] 未找到工具: {tool_name}")
                
                # 如果用户明确选择了0个工具，跳过工具执行
                if len(selected_tools) == 0:
                    logger.info(f"📊 [Phase 2] 用户选择了0个工具，跳过工具执行")
                    tools = []  # 空工具列表
                # 如果没有找到任何有效工具，使用默认工具
                elif not tools:
                    logger.warning("⚠️ [Phase 2] 用户选择的工具都无效，回退到默认工具")
                    tools = [toolkit.get_stock_market_data_unified]  # 最小默认工具
                    
            else:
                # 用户没有具体选择，使用默认的多工具配置
                logger.info(f"📊 [市场分析师] 使用默认的多个市场分析工具，提供全面市场分析")
                tools = [
                    toolkit.get_stock_market_data_unified,  # 统一市场数据工具
                    toolkit.get_china_stock_data,           # 中国股票数据
                    toolkit.get_YFin_data_online,          # Yahoo Finance在线数据
                    toolkit.get_stockstats_indicators_report_online,  # 在线技术指标
                    toolkit.get_hk_stock_data_unified      # 港股统一数据
                ]
            # 安全地获取工具名称用于调试
            tool_names_debug = []
            for tool in tools:
                if hasattr(tool, 'name'):
                    tool_names_debug.append(tool.name)
                elif hasattr(tool, '__name__'):
                    tool_names_debug.append(tool.__name__)
                else:
                    tool_names_debug.append(str(tool))
            logger.debug(f"📊 [DEBUG] 选择的工具: {tool_names_debug}")
            logger.debug(f"📊 [DEBUG] 🔧 统一工具将自动处理: {market_info['market_name']}")
        else:
            tools = [
                toolkit.get_YFin_data,
                toolkit.get_stockstats_indicators_report,
            ]

        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        
        # 使用提示词加载器获取配置（支持多语言）
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt("market/market_analyst", language=language)
        
        # 获取系统消息模板
        system_message_template = prompt_config.get("system_message", "你是一位专业的股票技术分析师。")
        
        # 导入i18n功能
        from core.i18n.messages import get_language_name_for_prompt, get_message, get_tool_name, get_agent_name
        
        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        language_name = get_language_name_for_prompt(language)
        
        # 格式化系统消息（替换占位符）
        system_message = system_message_template.format(
            company_name=company_name,
            ticker=ticker,
            market_name=market_info['market_name'],
            currency_name=market_info['currency_name'],
            currency_symbol=market_info['currency_symbol'],
            language_name=language_name
        )
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("market")
        logger.debug(f"📈 [DEBUG] 使用提示词版本: {prompt_version}")

        # Phase 2: 根据用户选择的工具动态生成调用指令
        tool_instructions = ""
        tool_steps = []  # 移到外面以便后续使用
        if "selected_tools" in state and selected_tools is not None and len(selected_tools) > 0:
            # 用户选择了特定工具，生成调用所有选中工具的指令
            for i, tool_name in enumerate(selected_tools, 1):  # 移除[:10]限制，用户选几个就生成几个
                tool_steps.append(f"{i}. 调用 {tool_name} 获取相关数据")
            tool_instructions = "\n".join(tool_steps)
            logger.info(f"📋 [Phase 2] 生成了{len(tool_steps)}个工具调用指令")
        elif "selected_tools" in state and selected_tools is not None and len(selected_tools) == 0:
            # 用户明确选择了0个工具，不需要调用任何工具
            tool_instructions = "用户已选择跳过工具调用，请基于已有知识和上下文进行分析。"
            logger.info(f"📋 [Phase 2] 用户选择不使用工具，将进行纯分析模式")
        else:
            # 默认情况：调用基础工具
            tool_instructions = "1. 调用 get_stock_market_data_unified 获取{company_name}({ticker})的真实数据"

        # 根据是否有工具动态生成prompt内容
        if "selected_tools" in state and selected_tools is not None and len(selected_tools) == 0:
            # 用户选择不使用工具的情况
            system_prompt = (
                "你是一位专业的股票技术分析师。\n\n"
                "⚠️ 重要规则：\n"
                "1. 用户已选择跳过工具调用\n"
                "2. 请基于已有的市场知识和上下文信息进行分析\n"
                "3. 可以参考历史趋势和一般市场规律\n"
                "4. 在分析中明确说明这是基于一般市场知识的分析\n\n"
                "📋 执行步骤：\n"
                f"{tool_instructions}\n"
                "1. 基于市场知识进行分析\n"
                "2. 提供投资建议：**买入/持有/卖出**\n\n"
                "{system_message}\n\n"
                "当前日期：{current_date}\n"
                "分析标的：{company_name}（{ticker}）\n\n"
                "注意：本次分析基于一般市场知识，未获取实时数据。"
            )
        else:
            # 有工具的情况
            system_prompt = (
                "你是一位专业的股票技术分析师，必须基于真实数据进行分析。\n\n"
                "⚠️ 重要规则 - 必须严格遵守：\n"
                "1. 你必须调用所有可用的工具获取全面的数据\n"
                "2. 禁止使用假设、可能、如果等词汇\n"
                "3. 禁止编造或假设任何数据\n"
                "4. 必须先获取数据，后进行分析\n\n"
                "📋 强制执行步骤：\n"
                f"{tool_instructions}\n"
                f"{len(tool_steps) + 1 if tool_steps else 2}. 基于获取的所有数据进行综合技术分析\n"
                f"{len(tool_steps) + 2 if tool_steps else 3}. 提供明确的投资建议：**买入/持有/卖出**\n\n"
                "可用工具：{tool_names}\n"
                "{system_message}\n\n"
                "当前日期：{current_date}\n"
                "分析标的：{company_name}（{ticker}）\n\n"
                "注意：你必须调用所有列出的工具来获取全面的数据。"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(company_name=company_name)

        # Linus原则：统一使用直接执行模式，消除特殊情况
        # 第一阶段是数据收集，按用户选择执行工具，不需要LLM决策
        logger.info(f"🔧 [市场分析师] 使用统一的直接执行模式")
        
        # 获取用户选择的工具
        selected_tools = state.get("selected_tools", [])
        logger.info(f"🔍 [市场分析师] 用户选择的工具: {selected_tools} (共{len(selected_tools)}个)")
        
        # 获取用户选择的时间框架并计算时间参数
        timeframe = state.get("timeframe", "1d")
        time_params = _calculate_time_params(timeframe, current_date)
        logger.info(f"📅 [直接执行] 基于timeframe '{timeframe}' 计算时间参数: {time_params}")
        
        # 过滤出技术相关工具（消除特殊情况）
        technical_tool_ids = ['crypto_price', 'indicators', 'market_data', 'historical_data']
        selected_technical_tools = [tool_id for tool_id in selected_tools if tool_id in technical_tool_ids]
        logger.info(f"🔧 [直接执行] 技术工具: {selected_technical_tools} (共{len(selected_technical_tools)}个)")
        
        # 获取analysis_id用于发送WebSocket事件
        analysis_id = state.get("analysis_id")
        
        # 如果没有analysis_id，记录警告
        if not analysis_id:
            logger.warning(f"⚠️ [市场分析师] 没有analysis_id，工具执行消息将无法发送")
        else:
            logger.info(f"✅ [市场分析师] 使用analysis_id: {analysis_id}")
        
        # 发送工具执行开始聚合消息
        start_time = datetime.utcnow()
        if analysis_id and redis_publisher and selected_technical_tools:
            try:
                # 动态获取工具名称列表
                tools_localized_list = [get_tool_name(tool_id, language) for tool_id in selected_technical_tools]
                tools_list = ", ".join(tools_localized_list)
                
                # 构建动态消息
                start_msg = get_message('tool_execution_start', language)
                tools_count_label = get_message('tools_count', language)
                total_count_label = get_message('total_count', language)
                colon = get_message('colon', language)
                agent_name = get_agent_name('market', language)
                message = f"{start_msg}{colon} {tools_list} ({total_count_label} {len(selected_technical_tools)} {tools_count_label})"
                
                redis_publisher.client.publish(
                    f"analysis:{analysis_id}",
                    json.dumps({
                        "type": "agent.tool",
                        "data": {
                            "analysisId": analysis_id,
                            "agent": agent_name,
                            "tool": "batch_execution",
                            "status": "executing",
                            "message": message,
                            "timestamp": start_time.isoformat()
                        }
                    })
                )
                logger.debug(f"📡 [聚合消息] 已发送工具批量执行开始事件: {len(selected_technical_tools)}个工具")
            except Exception as e:
                logger.warning(f"⚠️ [聚合消息] 发送工具开始事件失败: {e}")

        # 直接执行所有选择的技术工具，优化数据共享
        tool_results = []
        successful_tools = 0
        failed_tools = 0
        price_data = None  # 存储价格数据，供indicators工具使用
        
        # 重新排序工具执行顺序：先执行crypto_price，再执行indicators
        execution_order = []
        if 'crypto_price' in selected_technical_tools:
            execution_order.append('crypto_price')
        if 'indicators' in selected_technical_tools:
            execution_order.append('indicators')
        # 添加其他工具
        for tool_id in selected_technical_tools:
            if tool_id not in ['crypto_price', 'indicators']:
                execution_order.append(tool_id)
        
        logger.info(f"🔄 [直接执行] 工具执行顺序: {execution_order}")
        
        for tool_id in execution_order:
            try:
                tool_localized_name = get_tool_name(tool_id, language)
                logger.info(f"🎯 [直接执行] 正在执行工具: {tool_localized_name} ({tool_id})")
                
                # 从toolkit获取工具方法 - Linus式简化：快速失败
                tool_method = getattr(toolkit, tool_id, None)
                if tool_method is None:
                    logger.warning(f"⚠️ [直接执行] 工具 {tool_id} 未找到，跳过")
                    failed_tools += 1
                    continue  # 直接跳过，不添加错误结果
                
                # 根据工具ID构造参数
                tool_args = _construct_tool_args(tool_id, ticker, time_params)
                
                # 特殊处理indicators工具，传递价格数据
                if tool_id == 'indicators' and price_data is not None:
                    # 使用已获取的价格数据，避免重复API调用
                    tool_args['price_data'] = price_data
                    logger.info(f"♻️ [直接执行] indicators工具使用crypto_price数据，避免重复获取")
                
                logger.debug(f"🔧 [直接执行] 工具参数: {tool_args}")
                
                # 执行工具
                result_data = tool_method(**tool_args)
                
                # 🔧 增强：严格验证工具返回结果 - Linus式防护
                if result_data is None:
                    logger.error(f"❌ [直接执行] {tool_id} 返回了None")
                    result_data = {
                        "error": f"工具{tool_id}返回了None",
                        "tool_id": tool_id,
                        "tool_name": tool_localized_name
                    }
                elif isinstance(result_data, (int, float, str, bool)):
                    logger.error(f"❌ [直接执行] {tool_id} 返回了原始类型: {type(result_data).__name__} = {result_data}")
                    result_data = {
                        "error": f"工具{tool_id}返回了原始类型而非字典",
                        "invalid_result": result_data,
                        "result_type": type(result_data).__name__,
                        "tool_id": tool_id,
                        "tool_name": tool_localized_name
                    }
                elif not isinstance(result_data, dict):
                    logger.error(f"❌ [直接执行] {tool_id} 返回了非字典类型: {type(result_data).__name__} = {result_data}")
                    result_data = {
                        "error": f"工具{tool_id}返回了非法类型 {type(result_data).__name__}",
                        "invalid_result": str(result_data),
                        "tool_id": tool_id,
                        "tool_name": tool_localized_name
                    }
                
                # 如果是crypto_price工具，保存价格数据
                if tool_id == 'crypto_price' and result_data and 'error' not in result_data:
                    price_data = result_data
                    logger.info(f"💾 [直接执行] 已保存crypto_price数据供indicators工具使用")
                
                tool_results.append({
                    "tool": tool_id,
                    "result": result_data
                })
                logger.info(f"✅ [直接执行] 工具{tool_localized_name}执行成功")
                successful_tools += 1
                
            except Exception as e:
                logger.error(f"❌ [直接执行] 工具{tool_id}执行失败: {str(e)}")
                tool_results.append({
                    "tool": tool_id,
                    "result": {
                        "error": str(e),
                        "symbol": ticker,
                        "tool_id": tool_id
                    }
                })
                failed_tools += 1

        # 发送工具执行完成聚合消息
        if analysis_id and redis_publisher and selected_technical_tools:
            try:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                # 构建动态完成消息
                complete_msg = get_message('tool_execution_complete', language)
                tools_label = get_message('tools_count', language)
                success_label = get_message('success_count', language)
                failed_label = get_message('failed_count', language)
                time_label = get_message('time_spent', language)
                agent_name = get_agent_name('market', language)
                
                comma = get_message('comma', language)
                total_count_label = get_message('total_count', language)
                message = f"{complete_msg}{comma} {total_count_label} {len(selected_technical_tools)} {tools_label}{comma} {successful_tools} {success_label}{comma} {failed_tools} {failed_label}{comma} {time_label} {duration:.1f}s"
                
                redis_publisher.client.publish(
                    f"analysis:{analysis_id}",
                    json.dumps({
                        "type": "agent.tool",
                        "data": {
                            "analysisId": analysis_id,
                            "agent": agent_name,
                            "tool": "batch_execution",
                            "status": "completed",
                            "message": message,
                            "timestamp": end_time.isoformat()
                        }
                    })
                )
                logger.debug(f"📡 [聚合消息] 已发送工具批量执行完成事件: 耗时{duration:.1f}s")
            except Exception as e:
                logger.warning(f"⚠️ [聚合消息] 发送工具完成事件失败: {e}")
        
        # 数值格式化辅助函数
        def format_number(value, value_type="default"):
            """智能格式化数值，提升可读性"""
            if value is None:
                return "N/A"
            
            try:
                num_value = float(value)
                
                if value_type == "price":
                    # 价格格式：大于1000加逗号，保留2位小数
                    if abs(num_value) >= 1000:
                        return f"{num_value:,.2f}"
                    else:
                        return f"{num_value:.2f}"
                        
                elif value_type == "percentage":
                    # 百分比格式：带符号，2位小数
                    return f"{num_value:+.2f}%"
                    
                elif value_type == "macd":
                    # MACD格式：根据大小自动调整精度
                    if abs(num_value) < 0.001:
                        return f"{num_value:.6f}"
                    elif abs(num_value) < 0.1:
                        return f"{num_value:.4f}"
                    else:
                        return f"{num_value:.2f}"
                        
                elif value_type == "rsi":
                    # RSI格式：1位小数即可
                    return f"{num_value:.1f}"
                    
                else:
                    # 默认格式：2位小数
                    return f"{num_value:.2f}"
                    
            except (ValueError, TypeError):
                return str(value)
        
        # 解析和格式化技术指标数据
        def estimate_token_count(text: str) -> int:
            """估算文本的token数量（粗略估计：1 token ≈ 4字符）"""
            return len(text) // 4
        
        def format_tool_results_summary(tool_results: list, language="zh-CN") -> str:
            """智能格式化工具结果摘要，避免token超限"""
            summary_parts = []
            
            for result in tool_results:
                try:
                    tool_name = result.get('tool', 'Unknown')
                    result_data = result.get('result', {})
                    
                    # 跳过包含错误的结果
                    if isinstance(result_data, dict) and 'error' in result_data:
                        error_msg = get_message('error', language)
                        summary_parts.append(f"## {tool_name}\n❌ {error_msg}: {result_data['error']}")
                        continue
                    
                    # 格式化不同类型的工具结果
                    if tool_name == 'crypto_price':
                        if isinstance(result_data, dict):
                            latest_price = result_data.get('latest_price')
                            price_change_pct = result_data.get('price_change_pct')
                            total_records = result_data.get('total_records', 0)
                            interval = result_data.get('interval', '1d')  # 获取K线间隔
                            
                            crypto_price_title = get_message('crypto_price', language)
                            summary = f"## {crypto_price_title}\n"
                            if latest_price:
                                latest_price_label = get_message('latest_price', language)
                                summary += f"- {latest_price_label}: **{format_number(latest_price, 'price')}**\n"
                            if price_change_pct is not None:
                                direction_key = "upward" if price_change_pct > 0 else "downward" if price_change_pct < 0 else "sideways"
                                direction = get_message(direction_key, language)
                                price_change_label = get_message('price_change', language)
                                summary += f"- {price_change_label}: **{format_number(price_change_pct, 'percentage')}** ({direction})\n"
                            data_interval_label = get_message('data_interval', language)
                            data_points_label = get_message('data_points', language)
                            summary += f"- {data_interval_label}: {interval}\n"
                            summary += f"- {data_points_label}: {total_records}个"
                            
                            # 数据量提示
                            if total_records < 50:
                                warning_msg = get_message('data_points_few_warning', language)
                                summary += f" ⚠️ {warning_msg}"
                            elif total_records > 200:
                                compressed_msg = get_message('data_compressed', language)
                                summary += f" {compressed_msg}"
                            
                            summary_parts.append(summary)
                    
                    elif tool_name == 'market_data':
                        if isinstance(result_data, dict):
                            realtime_data_title = get_message('market_data_realtime', language)
                            summary = f"## {realtime_data_title}\n"
                            for key in ['current_price', 'market_cap', 'volume_24h', 'price_change_24h']:
                                if key in result_data:
                                    value = result_data[key]
                                    if key == 'price_change_24h':
                                        summary += f"- 24小时变化: **{format_number(value, 'percentage')}**\n"
                                    elif key == 'current_price':
                                        current_price_label = get_message('current_price', language)
                                        summary += f"- {current_price_label}: **{format_number(value, 'price')}**\n"
                                    else:
                                        summary += f"- {key}: **{format_number(value)}**\n"
                            summary_parts.append(summary)
                    
                    elif tool_name == 'historical_data':
                        # 🔧 修复：添加严格的类型检查
                        if isinstance(result_data, dict):
                            prices = result_data.get('prices', [])
                            historical_data_title = get_message('historical_data', language)
                            data_points_count_label = get_message('data_points_count', language)
                            summary = f"## {historical_data_title}\n- {data_points_count_label}: {len(prices)}个\n"
                            if prices:
                                # 🔧 修复：检测数据格式，支持嵌套列表和字典格式
                                if isinstance(prices[0], list):
                                    # 嵌套列表格式：[[timestamp, price]]
                                    first_price = prices[0][1] if len(prices[0]) > 1 else None
                                    last_price = prices[-1][1] if len(prices[-1]) > 1 else None
                                elif isinstance(prices[0], dict):
                                    # 字典格式：[{'timestamp': xxx, 'price': yyy}]
                                    first_price = prices[0].get('price')
                                    last_price = prices[-1].get('price')
                                else:
                                    first_price = None
                                    last_price = None
                                
                                if first_price and last_price:
                                    change_pct = ((last_price - first_price) / first_price) * 100
                                    direction_key = "upward" if change_pct > 0 else "downward" if change_pct < 0 else "sideways"
                                    direction = get_message(direction_key, language)
                                    period_change_label = get_message('period_change', language)
                                    summary += f"- {period_change_label}: **{format_number(change_pct, 'percentage')}** ({direction})"
                            summary_parts.append(summary)
                        else:
                            # 🔧 修复：非字典类型的错误处理
                            logger.warning(f"⚠️ [格式化] {tool_name} 返回了非字典类型的数据: {type(result_data).__name__} = {result_data}")
                            format_error_msg = get_message('data_format_error', language)
                            expected_dict_msg = get_message('expected_dict_got', language)
                            summary_parts.append(f"## {tool_name}\n⚠️ {format_error_msg}: {expected_dict_msg} {type(result_data).__name__}")
                    
                    else:
                        # 对于其他工具，尝试提取关键信息
                        if isinstance(result_data, dict):
                            summary = f"## {tool_name}\n"
                            # 只保留关键字段，避免完整数据
                            key_fields = ['symbol', 'sentiment', 'score', 'summary', 'count']
                            for field in key_fields:
                                if field in result_data:
                                    summary += f"- {field}: {result_data[field]}\n"
                            summary_parts.append(summary)
                        else:
                            # 非字典类型，截断处理
                            text = str(result_data)[:500]  # 限制500字符
                            summary_parts.append(f"## {tool_name}\n{text}")
                            
                except Exception as e:
                    logger.warning(f"格式化工具结果失败 {result.get('tool', 'Unknown')}: {e}")
                    # 🔧 修复：添加更详细的错误信息
                    logger.debug(f"🔍 [格式化调试] 工具数据详情: {result}")
                    continue
            
            return "\n\n".join(summary_parts)
        
        def check_data_size_and_format(tool_results: list, language="zh-CN") -> tuple[str, bool]:
            """检查数据量并格式化，返回(格式化文本, 是否需要警告)"""
            # 先尝试摘要格式
            summary_text = format_tool_results_summary(tool_results, language)
            estimated_tokens = estimate_token_count(summary_text)
            
            # Token限制检查（保守估计，留20%缓冲）
            MAX_SAFE_TOKENS = 25000  # 32768 * 0.8
            
            if estimated_tokens <= MAX_SAFE_TOKENS:
                logger.info(f"📊 数据量检查: {estimated_tokens} tokens (安全范围)")
                return summary_text, False
            else:
                # 数据量过大，进一步压缩
                logger.warning(f"⚠️ 数据量过大: {estimated_tokens} tokens，启用压缩模式")
                
                # 压缩策略：只保留最关键的信息
                compressed_parts = []
                for result in tool_results:
                    tool_name = result.get('tool', 'Unknown')
                    result_data = result.get('result', {})
                    
                    if isinstance(result_data, dict) and 'error' not in result_data:
                        if tool_name == 'crypto_price' and 'latest_price' in result_data:
                            latest_price_label = get_message('latest_price', language)
                            compressed_parts.append(f"**{tool_name}**: {latest_price_label} {format_number(result_data['latest_price'], 'price')}")
                        elif tool_name == 'indicators' and 'indicators' in result_data:
                            indicators = result_data['indicators']
                            key_indicators = []
                            if 'rsi' in indicators:
                                key_indicators.append(f"RSI: {format_number(indicators['rsi'], 'rsi')}")
                            if 'sma_20' in indicators:
                                key_indicators.append(f"SMA20: {format_number(indicators['sma_20'], 'price')}")
                            compressed_parts.append(f"**{tool_name}**: {', '.join(key_indicators)}")
                        else:
                            data_obtained_msg = get_message('data_obtained', language)
                            compressed_parts.append(f"**{tool_name}**: {data_obtained_msg}")
                
                summary_compressed_title = get_message('data_summary_compressed', language)
                compressed_text = f"# {summary_compressed_title}\n\n" + "\n".join(compressed_parts)
                final_tokens = estimate_token_count(compressed_text)
                
                if final_tokens > MAX_SAFE_TOKENS:
                    # 即使压缩后仍然过大
                    error_msg = (f"❌ 数据量过大无法处理\n\n"
                               f"估算Token数: {estimated_tokens:,} (压缩后: {final_tokens:,})\n"
                               f"系统限制: {MAX_SAFE_TOKENS:,} tokens\n\n"
                               f"建议：\n"
                               f"1. 减少时间范围（当前可能选择了过长的时间段）\n" 
                               f"2. 减少工具数量\n"
                               f"3. 选择更短的时间框架进行分析")
                    return error_msg, True
                else:
                    logger.info(f"📊 数据压缩完成: {final_tokens} tokens")
                    return compressed_text, False

        def extract_technical_indicators(tool_results, language="zh-CN"):
            """从工具结果中提取技术指标数值"""
            indicators_summary = []
            
            for result in tool_results:
                try:
                    # Linus: 初始化indicators变量，消除特殊情况
                    indicators = None
                    
                    if isinstance(result['result'], dict):
                        data = result['result']
                        
                        # 跳过包含错误的结果
                        if 'error' in data:
                            logger.warning(f"工具 {result.get('tool')} 返回错误: {data['error']}")
                            continue
                        
                        # 如果是技术指标工具的结果
                        if 'indicators' in data and isinstance(data['indicators'], dict):
                            indicators = data['indicators']
                            tech_analysis_title = get_message('technical_analysis', language)
                            indicators_summary.append(f"## {tech_analysis_title}\n")
                            
                            # 移动平均线分析
                            if 'sma_20' in indicators or 'sma_50' in indicators:
                                ma_analysis_title = get_message('moving_average_analysis', language)
                                indicators_summary.append(f"### {ma_analysis_title}")
                                if 'sma_20' in indicators and indicators['sma_20']:
                                    indicators_summary.append(f"- 20日简单移动平均线(SMA20): **{format_number(indicators['sma_20'], 'price')}**")
                                if 'sma_50' in indicators and indicators['sma_50']:
                                    indicators_summary.append(f"- 50日简单移动平均线(SMA50): **{format_number(indicators['sma_50'], 'price')}**")
                            
                            # EMA分析
                            if 'ema_12' in indicators or 'ema_26' in indicators:
                                ma_analysis_title = get_message('moving_average_analysis', language)
                                if not any(ma_analysis_title in item for item in indicators_summary):
                                    indicators_summary.append(f"### {ma_analysis_title}")
                                if 'ema_12' in indicators and indicators['ema_12']:
                                    indicators_summary.append(f"- 12日指数移动平均线(EMA12): **{format_number(indicators['ema_12'], 'price')}**")
                                if 'ema_26' in indicators and indicators['ema_26']:
                                    indicators_summary.append(f"- 26日指数移动平均线(EMA26): **{format_number(indicators['ema_26'], 'price')}**")
                            
                            # MACD分析
                            if any(k.startswith('macd') for k in indicators.keys()):
                                macd_analysis_title = get_message('macd_analysis', language)
                                indicators_summary.append(f"\n### {macd_analysis_title}")
                                if 'macd' in indicators and indicators['macd']:
                                    indicators_summary.append(f"- MACD值: **{format_number(indicators['macd'], 'macd')}**")
                                if 'macd_signal' in indicators and indicators['macd_signal']:
                                    indicators_summary.append(f"- MACD信号线: **{format_number(indicators['macd_signal'], 'macd')}**")
                                if 'macd_histogram' in indicators and indicators['macd_histogram']:
                                    indicators_summary.append(f"- MACD柱状图: **{format_number(indicators['macd_histogram'], 'macd')}**")
                            
                            # RSI分析
                            if 'rsi' in indicators and indicators['rsi']:
                                momentum_title = get_message('momentum_strength_analysis', language)
                                indicators_summary.append(f"\n### {momentum_title}")
                                rsi_value = indicators['rsi']
                                rsi_level_key = "overbought" if rsi_value > 70 else "oversold" if rsi_value < 30 else "neutral"
                                rsi_level = get_message(rsi_level_key, language)
                                area_label = get_message('area', language)
                                indicators_summary.append(f"- RSI(14): **{format_number(rsi_value, 'rsi')}** ({rsi_level}{area_label})")
                            
                            # 布林带分析
                            if any(k.startswith('bb_') for k in indicators.keys()):
                                volatility_title = get_message('volatility_analysis', language)
                                indicators_summary.append(f"\n### {volatility_title}")
                                if 'bb_upper' in indicators and indicators['bb_upper']:
                                    bb_upper_label = get_message('bb_upper', language)
                                    indicators_summary.append(f"- {bb_upper_label}: **{format_number(indicators['bb_upper'], 'price')}**")
                                if 'bb_middle' in indicators and indicators['bb_middle']:
                                    bb_middle_label = get_message('bb_middle', language)
                                    indicators_summary.append(f"- {bb_middle_label}: **{format_number(indicators['bb_middle'], 'price')}**")
                                if 'bb_lower' in indicators and indicators['bb_lower']:
                                    bb_lower_label = get_message('bb_lower', language)
                                    indicators_summary.append(f"- {bb_lower_label}: **{format_number(indicators['bb_lower'], 'price')}**")
                        
                        # 如果是价格数据
                        if 'latest_price' in data and data['latest_price']:
                            price_info_title = get_message('price_info', language)
                            latest_price_label = get_message('latest_price', language)
                            indicators_summary.append(f"\n### {price_info_title}")
                            indicators_summary.append(f"- {latest_price_label}: **{format_number(data['latest_price'], 'price')}**")
                            if 'price_change_pct' in data:
                                change_pct = data['price_change_pct']
                                direction_key = "upward" if change_pct > 0 else "downward" if change_pct < 0 else "sideways"
                                direction = get_message(direction_key, language)
                                price_change_label = get_message('price_change', language)
                                indicators_summary.append(f"- {price_change_label}: **{format_number(change_pct, 'percentage')}** ({direction})")
                        
                        # 成交量数据提取（Linus: 安全检查，避免未初始化变量）
                        if indicators and 'total_volume_period' in indicators:
                            volume_analysis_title = get_message('volume_analysis', language)
                            indicators_summary.append(f"\n### {volume_analysis_title}")
                            total_volume = indicators['total_volume_period']
                            latest_volume = indicators.get('latest_volume_24h', 0)
                            data_points = indicators.get('volume_data_points', 0)
                            
                            total_volume_label = get_message('total_volume_period', language)
                            latest_volume_label = get_message('latest_24h_volume', language)
                            volume_data_points_label = get_message('volume_data_points', language)
                            indicators_summary.append(f"- {total_volume_label}: **{format_number(total_volume)}**")
                            indicators_summary.append(f"- {latest_volume_label}: **{format_number(latest_volume)}**")
                            indicators_summary.append(f"- {volume_data_points_label}: **{data_points}个**")
                            
                            # 成交量活跃度判断
                            if latest_volume > 0:
                                volume_activity_key = "active" if latest_volume > total_volume / data_points else "sluggish"
                                volume_activity = get_message(volume_activity_key, language)
                                volume_status_label = get_message('volume_status', language)
                                indicators_summary.append(f"- {volume_status_label}: **{volume_activity}**")
                        
                except Exception as e:
                    logger.warning(f"解析技术指标数据失败: {e}")
                    continue
            
            return "\n".join(indicators_summary) if indicators_summary else ""
        
        # 智能数据量检查和格式化（避免token超限）
        tool_results_text, has_error = check_data_size_and_format(tool_results, language)
        
        # 如果数据量过大，直接返回错误信息
        if has_error:
            logger.error("❌ 数据量过大，无法继续分析")
            return {
                "messages": [("assistant", tool_results_text)],
                "market_report": tool_results_text,
            }
        
        # 提取技术指标数值
        indicators_data = extract_technical_indicators(tool_results, language)
        
        # 使用LLM分析工具结果
        professional_analyst_msg = get_message('professional_stock_analyst', language)
        tech_indicators_label = get_message('technical_indicators_values', language)
        tool_data_label = get_message('tool_data', language)
        comprehensive_analysis_msg = get_message('comprehensive_analysis_request', language)
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             f"{professional_analyst_msg}\n\n"
             f"{tech_indicators_label}\n{{indicators_data}}\n\n"
             f"{tool_data_label}\n{{tool_results}}\n\n"
             "{{system_message}}\n\n"
             f"{comprehensive_analysis_msg}"),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        analysis_prompt = analysis_prompt.partial(indicators_data=indicators_data)
        analysis_prompt = analysis_prompt.partial(tool_results=tool_results_text)
        analysis_prompt = analysis_prompt.partial(system_message=system_message)
        
        # 🛠 Linus式修复：统一错误处理，消除崩溃特殊情况
        try:
            analysis_chain = analysis_prompt | llm
            
            # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言
            language = state.get("language", "zh-CN")
            language_name = "English" if language == "en-US" else "简体中文"
            language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "
            
            logger.info(f"🌍 [市场分析师] 语言设置: {language} -> {language_name}")
            logger.debug(f"🔴 [市场分析师] 语言前缀: {language_prefix}")
            
            # 在调用LLM前添加语言前缀到messages
            try:
                messages = state["messages"]
                if messages:
                    # 创建带前缀的消息副本
                    prefixed_messages = messages.copy()
                    # 在第一个消息前添加系统级语言前缀
                    from langchain_core.messages import SystemMessage
                    language_system_msg = SystemMessage(content=language_prefix)
                    prefixed_messages = [language_system_msg] + prefixed_messages
                    logger.info(f"✅ [市场分析师] 已添加语言前缀，消息数: {len(prefixed_messages)}")
                    result = analysis_chain.invoke(prefixed_messages)
                else:
                    logger.warning(f"⚠️ [市场分析师] messages为空，使用原方法")
                    result = analysis_chain.invoke(state["messages"])
            except Exception as e:
                # 降级处理：直接调用原方法
                logger.warning(f"⚠️ [市场分析师] 语言前缀添加失败，使用原方法: {e}")
                result = analysis_chain.invoke(state["messages"])
        except Exception as e:
            logger.error(f"❌ [市场分析师] LLM调用失败: {str(e)}")
            # 创建降级响应，确保流程继续
            from langchain_core.messages import AIMessage
            result = AIMessage(content=f"市场分析暂时不可用：{str(e)}。请检查LLM配置或token限制。")
        
        # 返回结果
        report = result.content if hasattr(result, 'content') else ""
        logger.info(f"📊 [市场分析师] 生成完整分析报告，长度: {len(report)}")
        
        # 释放序列锁，允许下一个分析师开始执行
        logger.info(f"🔓 [市场分析师] 释放序列锁，完成执行")
        
        # 添加小延迟确保消息已发送完成
        import time
        time.sleep(0.5)
        
        return {
            "messages": [result],
            "market_report": report,
            "current_sequence": None,  # 释放当前序列
            "sequence_lock": False,    # 释放锁
        }

    return market_analyst_node
