from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from datetime import datetime

# 导入统一日志系统和分析模块日志装饰器
from core.utils.logging_init import get_logger
from core.utils.tool_logging import log_analyst_module
# 导入提示词加载器
from core.agents.prompt_loader import get_prompt_loader
# 导入Redis发布器用于发送工具执行事件
from core.services.redis_pubsub import redis_publisher
# 导入多语言消息系统
from core.i18n.messages import get_message, get_tool_name, get_agent_name

logger = get_logger("analysts.social_media")

# 工具名称中文映射
TOOL_NAME_CN = {
    'finnhub_news': 'Finnhub新闻',
    'reddit_sentiment': 'Reddit情绪',
    'sentiment_batch': '批量情绪分析',
    'get_reddit_stock_info': 'Reddit股票信息',
    'get_reddit_news': 'Reddit新闻',
    'get_chinese_social_sentiment': '中国社交媒体情绪',
    'get_finnhub_company_insider_sentiment': '公司内部人员情绪',
    'get_stock_sentiment_unified': '统一情绪分析',
}


def _calculate_sentiment_time_params(timeframe: str, current_date: str) -> dict:
    """
    根据timeframe计算情绪分析的时间参数
    
    Args:
        timeframe: 时间框架 ('1天', '1周', '1月', '1年' 或 '1d', '1w', '1m', '1y')  
        current_date: 当前日期字符串
        
    Returns:
        包含days_back等参数的字典
    """
    from datetime import datetime, timedelta
    
    # timeframe映射（支持中文和英文）
    timeframe_mapping = {
        '1天': 3,    # 1天时间框架，查看3天情绪数据
        '1周': 7,    # 1周时间框架，查看7天情绪数据
        '1月': 14,   # 1月时间框架，查看14天情绪数据
        '1年': 30,   # 1年时间框架，查看30天情绪数据
        '1d': 3,
        '1w': 7,
        '1m': 14,
        '1y': 30,
        '1h': 1,     # 1小时图查看1天情绪
        '4h': 3,     # 4小时图查看3天情绪
    }
    
    # 获取天数，默认7天
    days_back = timeframe_mapping.get(timeframe, 7)
    
    return {
        'days_back': days_back,
        'max_results': min(20, days_back * 2)  # 结果数量与时间范围成正比
    }


def _construct_sentiment_tool_args(tool_id: str, symbol: str, time_params: dict) -> dict:
    """
    根据工具ID和时间参数构造情绪工具调用参数
    
    Args:
        tool_id: 工具ID (如 'finnhub_news', 'reddit_sentiment')
        symbol: 交易标的
        time_params: 时间参数字典
        
    Returns:
        工具调用参数字典
    """
    # 🔧 修复：无参数工具 - Linus式统一处理
    no_param_tools = ['fear_greed', 'market_overview', 'global_market_cap']
    if tool_id in no_param_tools:
        logger.debug(f"🔧 [无参数工具] {tool_id} 不需要参数")
        return {}
    
    # 情绪分析工具参数映射 (使用正确的工具ID)
    sentiment_tools = {
        'finnhub_news': {
            'symbol': symbol,
            'days_back': time_params['days_back'],
            'max_results': time_params['max_results']
        },
        'reddit_sentiment': {
            'symbol': symbol,
            'days_back': time_params['days_back'],
            'max_results': time_params['max_results']
        },
        'sentiment_batch': {
            'symbol': symbol,
            'sources': ['finnhub', 'reddit'],
            'days_back': time_params['days_back']
        }
    }
    
    # 返回对应工具的参数，如果没找到则返回基本参数
    return sentiment_tools.get(tool_id, {'symbol': symbol})


def create_social_media_analyst(llm, toolkit):
    @log_analyst_module("social_media")
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 🛠 使用Toolkit中已有的工具，避免工具不匹配错误
        logger.info(f"[社交媒体分析师] 使用Toolkit中的标准工具获取{ticker}的市场情绪")
        
        # Linus原则：统一使用直接执行模式，消除特殊情况
        logger.info(f"🛠 [社交媒体分析师] 使用统一的直接执行模式")
        
        # 获取analysis_id用于发送WebSocket事件
        analysis_id = state.get("analysis_id")
        
        # 如果没有analysis_id，记录警告
        if not analysis_id:
            logger.warning(f"⚠️ [社交媒体分析师] 没有analysis_id，工具执行消息将无法发送")
        else:
            logger.info(f"✅ [社交媒体分析师] 使用analysis_id: {analysis_id}")
        
        # 获取用户选择的时间框架并计算时间参数
        timeframe = state.get("timeframe", "1d")
        time_params = _calculate_sentiment_time_params(timeframe, current_date)
        logger.info(f"📅 [直接执行] 基于timeframe '{timeframe}' 计算情绪时间参数: {time_params}")
        
        # 🛠 修复核心问题：正确的工具分类逻辑
        selected_tools = state.get("selected_tools", [])
        logger.info(f"🔍 [工具分类] 用户原始选择: {selected_tools}")
        
        # 🛠 Linus式解决方案：重新设计数据结构
        # 定义情绪分析师真正需要的工具
        SENTIMENT_TOOL_MAPPING = {
            # 用户可能选择的工具ID -> 实际的情绪工具方法
            'finnhub_news': 'get_finnhub_crypto_news',
            'reddit_sentiment': 'get_crypto_reddit_sentiment', 
            'sentiment_batch': 'analyze_sentiment_batch',
            'fear_greed': 'get_fear_greed_index',
            # 技术工具无法用于情绪分析，但不报错，直接忽略
            'crypto_price': None,
            'indicators': None,
            'market_data': None,
            'historical_data': None,
        }
        
        # 从用户选择中筛选出真正可用的情绪工具
        available_sentiment_tools = []
        for tool_id in selected_tools:
            mapped_method = SENTIMENT_TOOL_MAPPING.get(tool_id)
            if mapped_method:  # 不是None
                # 检查toolkit中是否有对应的工具ID（而非方法名）- Linus式简化
                if hasattr(toolkit, tool_id):
                    available_sentiment_tools.append(tool_id)
                    logger.info(f"✅ [工具映射] {tool_id} (存在)")
                else:
                    logger.warning(f"⚠️ [工具映射] {tool_id} (不存在)")
            elif mapped_method is None and tool_id in SENTIMENT_TOOL_MAPPING:
                # 技术工具，直接忽略，不报错
                logger.debug(f"🛠 [工具过滤] {tool_id} 是技术工具，跳过")
            else:
                # 未知工具
                logger.warning(f"❓ [工具映射] 未知工具: {tool_id}")
        
        logger.info(f"🎯 [工具分类结果] 可用情绪工具: {available_sentiment_tools}")
        
        # 如果没有可用的情绪工具，使用默认配置
        if not available_sentiment_tools:
            logger.info(f"🔄 [默认配置] 用户未选择情绪工具，使用默认的Reddit情绪分析")
            # 检查是否有基础的情绪分析工具可用 - Linus式简化
            default_tools = []
            if hasattr(toolkit, 'reddit_sentiment'):
                default_tools.append('reddit_sentiment')
            if hasattr(toolkit, 'fear_greed'):
                default_tools.append('fear_greed')
            
            available_sentiment_tools = default_tools
            logger.info(f"🔄 [默认配置] 使用默认工具: {available_sentiment_tools}")
        
        # 获取语言设置（修复作用域问题）
        language = state.get("language", "zh-CN")
        
        # 发送工具执行开始聚合消息
        start_time = datetime.utcnow()
        if analysis_id and redis_publisher and available_sentiment_tools:
            try:
                # 使用本地化工具名称（与市场分析师保持一致）
                tools_localized_list = [get_tool_name(tool_id, language) for tool_id in available_sentiment_tools]
                tools_list = ", ".join(tools_localized_list)
                
                # 手动构建消息（与市场分析师一致）
                start_msg = get_message('tool_execution_start', language)
                tools_count_label = get_message('tools_count', language)
                total_count_label = get_message('total_count', language)
                colon = get_message('colon', language)
                agent_name = get_agent_name('social_media', language)
                message = f"{start_msg}{colon} {tools_list} ({total_count_label} {len(available_sentiment_tools)} {tools_count_label})"
                
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
                logger.debug(f"📡 [聚合消息] 已发送情绪工具批量执行开始事件: {len(available_sentiment_tools)}个工具")
            except Exception as e:
                logger.warning(f"⚠️ [聚合消息] 发送工具开始事件失败: {e}")

        # 直接执行所有可用的情绪工具
        tool_results = []
        successful_tools = 0
        failed_tools = 0
        
        for tool_id in available_sentiment_tools:
            try:
                tool_cn_name = TOOL_NAME_CN.get(tool_id, tool_id)
                logger.info(f"🎯 [直接执行] 正在执行情绪工具: {tool_cn_name} ({tool_id})")
                
                # 🛠 修复：直接使用tool_id查找工具 - Linus式简化
                # Toolkit注册的是tool_id，不是method_name
                tool_method = getattr(toolkit, tool_id, None)
                method_name = SENTIMENT_TOOL_MAPPING.get(tool_id)  # 仅用于日志显示
                
                if tool_method is None:
                    # 🛠 增强：添加详细的调试信息
                    available_methods = [attr for attr in dir(toolkit) if not attr.startswith('_') and callable(getattr(toolkit, attr, None))]
                    toolkit_selected_tools = getattr(toolkit, 'selected_tools', [])
                    
                    logger.error(f"❌ [直接执行] 情绪工具方法未找到: {method_name or tool_id}")
                    logger.error(f"   📊 Toolkit注册的工具: {toolkit_selected_tools}")
                    logger.error(f"   🔍 Toolkit可用方法(前20个): {available_methods[:20]}")
                    logger.error(f"   🛠 预期方法名: {method_name}")
                    
                    tool_results.append({
                        "tool": tool_id,
                        "result": {
                            "error": f"情绪工具方法未找到: {method_name or tool_id}",
                            "symbol": ticker,
                            "tool_id": tool_id,
                            "method_name": method_name,
                            "available_methods": available_methods[:10]  # 只显示前10个避免日志过长
                        }
                    })
                    failed_tools += 1
                    continue
                
                # 根据工具ID构造参数
                tool_args = _construct_sentiment_tool_args(tool_id, ticker, time_params)
                logger.debug(f"🛠 [直接执行] 工具参数: {tool_args}")
                
                # 执行工具
                result_data = tool_method(**tool_args)
                tool_results.append({
                    "tool": tool_id,
                    "result": result_data
                })
                logger.info(f"✅ [直接执行] 工具{tool_cn_name}执行成功")
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
        if analysis_id and redis_publisher and available_sentiment_tools:
            try:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                # 手动构建完成消息（与市场分析师一致）
                complete_msg = get_message('tool_execution_complete', language)
                tools_label = get_message('tools_count', language)
                success_label = get_message('success_count', language)
                failed_label = get_message('failed_count', language)
                time_label = get_message('time_spent', language)
                agent_name = get_agent_name('social_media', language)
                
                comma = get_message('comma', language)
                total_count_label = get_message('total_count', language)
                message = f"{complete_msg}{comma} {total_count_label} {len(available_sentiment_tools)} {tools_label}{comma} {successful_tools} {success_label}{comma} {failed_tools} {failed_label}{comma} {time_label} {duration:.1f}s"
                
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
                logger.debug(f"📡 [聚合消息] 已发送情绪工具批量执行完成事件: 耗时{duration:.1f}s")
            except Exception as e:
                logger.warning(f"⚠️ [聚合消息] 发送工具完成事件失败: {e}")
        
        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        
        # 使用提示词加载器获取配置（支持多语言）
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt("social_media_analyst", language=language)
        
        # 获取系统消息
        system_message = prompt_config.get("system_message", "您是一位专业的社交媒体分析师。")
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("social_media_analyst", language=language)
        logger.debug(f"🎭 [DEBUG] 使用提示词版本: {prompt_version} (语言: {language})")
        
        # 🛠 修复：正确处理工具结果，避免"数据中没有提供"的误导
        if tool_results:
            # 过滤掉失败的工具结果，只保留成功的
            successful_results = [r for r in tool_results if 'error' not in str(r['result'])]
            failed_results = [r for r in tool_results if 'error' in str(r['result'])]
            
            if successful_results:
                tool_results_text = "\n\n".join([
                    f"## {r['tool']}\n{r['result']}" for r in successful_results
                ])
                system_content = (
                    "你是一位专业的社交媒体情绪分析师。基于以下工具获取的真实数据进行分析。\n\n"
                    "工具数据：\n{tool_results}\n\n"
                    "{system_message}\n\n"
                    "重要：请直接基于上述真实数据进行分析，不要说'数据中没有提供'之类的话。"
                    "如果某个平台的数据不可用，请专注于分析可用的数据。"
                )
                if failed_results:
                    logger.info(f"📊 成功工具: {len(successful_results)}, 失败工具: {len(failed_results)}")
            else:
                # 所有工具都失败了
                tool_results_text = "所有情绪工具调用失败，无法获取实时数据。"
                system_content = (
                    "你是一位专业的社交媒体情绪分析师。\n\n"
                    "{system_message}\n\n"
                    "注意：无法获取实时社交媒体数据，请基于一般市场知识进行情绪分析。\n"
                    "请分析当前市场对该加密货币的一般情绪趋势，并明确说明这是基于一般市场知识的分析。"
                )
        else:
            tool_results_text = "未执行情绪工具调用。"
            system_content = (
                "你是一位专业的社交媒体情绪分析师。\n\n"
                "{system_message}\n\n"
                "注意：未执行情绪工具调用，请基于一般市场知识进行情绪分析。\n"
                "请分析当前市场对该加密货币的一般情绪趋势，并明确说明这是基于一般市场知识的分析。"
            )
            
        # 使用LLM分析工具结果
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", system_content),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        analysis_prompt = analysis_prompt.partial(tool_results=tool_results_text)
        analysis_prompt = analysis_prompt.partial(system_message=system_message)
        
        # 🛠 Token控制：智能压缩消息避免32768限制
        from core.utils.token_manager import compress_messages_smart
        
        original_messages = state.get("messages", [])
        logger.debug(f"🔍 [TokenManager] 原始消息数量: {len(original_messages)}")
        
        # 智能压缩消息
        compressed_messages, token_usage = compress_messages_smart(original_messages, max_tokens=32768)
        
        if len(compressed_messages) < len(original_messages):
            logger.info(f"📦 [TokenManager] 消息压缩: {len(original_messages)} -> {len(compressed_messages)}, tokens: ~{token_usage.estimated_tokens}")
        else:
            logger.debug(f"✅ [TokenManager] 消息无需压缩, tokens: ~{token_usage.estimated_tokens}")
        
        # 🛠 Linus式修复：统一错误处理，消除崩溃特殊情况
        try:
            analysis_chain = analysis_prompt | llm
            # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言

            language = state.get("language", "zh-CN")

            language_name = "English" if language == "en-US" else "简体中文"

            language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "

            

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

                    result = analysis_chain.invoke(prefixed_messages)

                else:

                    # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言


                    language = state.get("language", "zh-CN")


                    language_name = "English" if language == "en-US" else "简体中文"


                    language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "


                    


                    # 在调用LLM前添加语言前缀到compressed_messages


                    try:


                        if compressed_messages:


                            # 创建带前缀的消息副本


                            prefixed_compressed_messages = compressed_messages.copy()


                            # 在第一个消息前添加系统级语言前缀


                            from langchain_core.messages import SystemMessage


                            language_system_msg = SystemMessage(content=language_prefix)


                            prefixed_compressed_messages = [language_system_msg] + prefixed_compressed_messages


                            result = analysis_chain.invoke(prefixed_compressed_messages)


                        else:


                            result = analysis_chain.invoke(compressed_messages)


                    except Exception as e:


                        # 降级处理：直接调用原方法


                        logger.warning(f"⚠️ 语言前缀添加失败，使用原方法: {e}")


                        result = analysis_chain.invoke(compressed_messages)

            except Exception as e:

                # 降级处理：直接调用原方法

                logger.warning(f"⚠️ 语言前缀添加失败，使用原方法: {e}")

                # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言


                language = state.get("language", "zh-CN")


                language_name = "English" if language == "en-US" else "简体中文"


                language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "


                


                # 在调用LLM前添加语言前缀到compressed_messages


                try:


                    if compressed_messages:


                        # 创建带前缀的消息副本


                        prefixed_compressed_messages = compressed_messages.copy()


                        # 在第一个消息前添加系统级语言前缀


                        from langchain_core.messages import SystemMessage


                        language_system_msg = SystemMessage(content=language_prefix)


                        prefixed_compressed_messages = [language_system_msg] + prefixed_compressed_messages


                        result = analysis_chain.invoke(prefixed_compressed_messages)


                    else:


                        result = analysis_chain.invoke(compressed_messages)


                except Exception as e:


                    # 降级处理：直接调用原方法


                    logger.warning(f"⚠️ 语言前缀添加失败，使用原方法: {e}")


                    result = analysis_chain.invoke(compressed_messages)
        except Exception as e:
            logger.error(f"❌ [社交媒体分析师] LLM调用失败: {str(e)}")
            # 创建降级响应，确保流程继续
            from langchain_core.messages import AIMessage
            result = AIMessage(content=f"社交媒体分析暂时不可用：{str(e)}。请检查LLM配置或token限制。")
        
        # 返回分析结果
        report = result.content if hasattr(result, 'content') else str(result)
        logger.info(f"🎭 [社交媒体分析师] 直接执行模式分析完成，报告长度: {len(report)}")
        
        # 释放序列锁，允许下一个分析师开始执行
        logger.info(f"🔓 [社交媒体分析师] 释放序列锁，完成执行")
        
        # 添加小延迟确保消息已发送完成
        import time
        time.sleep(0.5)
        
        return {
            "messages": [result],
            "sentiment_report": report,
            "current_sequence": None,  # 释放当前序列
            "sequence_lock": False,    # 释放锁
        }


    return social_media_analyst_node
