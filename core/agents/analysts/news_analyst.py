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

logger = get_logger("analysts.news")

# 工具名称中文映射
TOOL_NAME_CN = {
    'finnhub_news': 'Finnhub新闻',
    'get_stock_news_openai': '股票新闻',
    'get_global_news_openai': '全球新闻',
    'get_finnhub_crypto_news': '加密货币新闻',
}


def create_news_analyst(llm, toolkit):
    @log_analyst_module("news")
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 获取语言设置
        language = state.get("language", "zh-CN")

        # 🛠 使用Toolkit中已有的工具，避免工具不匹配错误
        logger.info(f"[新闻分析师] 使用Toolkit中的标准工具获取{ticker}的新闻资讯")
        
        # 使用ToolNode中已有的工具（无需自定义工具）
        # 可用工具：get_stock_news_openai, get_finnhub_crypto_news
        
        # Phase 2: 根据用户选择动态构建工具列表
        selected_tools = state.get("selected_tools", [])
        
        # 区分"用户选择了0个工具"和"用户没有进行工具配置"两种情况
        if "selected_tools" in state and selected_tools is not None:
            # 用户有具体的工具选择，使用用户选择的工具
            logger.info(f"📰 [Phase 2] 新闻分析师使用用户选择的工具: {selected_tools} (共{len(selected_tools)}个)")
            
            # 工具ID映射表（正确的工具ID -> 实际工具方法）
            tool_mapping = {
                'finnhub_news': getattr(toolkit, 'finnhub_news', None),
                # 添加其他新闻相关工具ID
            }
            
            # 根据用户选择构建工具列表
            tools = []
            for tool_id in selected_tools:
                tool_method = tool_mapping.get(tool_id)
                if tool_method is not None:
                    tools.append(tool_method)
                    logger.info(f"✅ [Phase 2] 已添加用户选择的新闻工具: {tool_id}")
                else:
                    logger.warning(f"⚠️ [Phase 2] 未找到新闻工具: {tool_id}")
            
            # 如果用户明确选择了0个工具，跳过工具执行
            if len(selected_tools) == 0:
                logger.info(f"📰 [Phase 2] 用户选择了0个新闻工具，跳过工具执行")
                tools = []  # 空工具列表
            # 如果没有找到任何有效工具，使用默认工具
            elif not tools:
                logger.warning("⚠️ [Phase 2] 用户选择的新闻工具都无效，回退到默认工具")
                default_tool = getattr(toolkit, 'finnhub_news', None)
                if default_tool:
                    tools = [default_tool]  # 使用finnhub_news作为默认工具
                
        else:
            # 用户没有具体选择，使用默认的新闻分析工具
            logger.info(f"📰 [新闻分析师] 使用默认的新闻分析工具")
            default_tool = getattr(toolkit, 'finnhub_news', None)
            tools = [default_tool] if default_tool else []

        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        
        # 使用提示词加载器获取配置（支持多语言）
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt("news_analyst", language=language)
        
        # 获取系统消息
        system_message = prompt_config.get("system_message", "您是一位专业的新闻分析师。")
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("news_analyst", language=language)
        logger.debug(f"📰 [DEBUG] 使用提示词版本: {prompt_version} (语言: {language})")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    system_message
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        tool_names_str = ", ".join(tool_names)
        
        # 绑定提示词参数
        prompt = prompt.partial(
            system_message=system_message,
            tool_names=tool_names_str,
            current_date=current_date,
            ticker=ticker
        )

        # Linus原则：统一使用直接执行模式，消除特殊情况
        logger.info(f"🛠 [新闻分析师] 使用统一的直接执行模式")
        
        # 获取analysis_id用于发送WebSocket事件
        analysis_id = state.get("analysis_id")
        
        # 如果没有analysis_id，记录警告
        if not analysis_id:
            logger.warning(f"⚠️ [新闻分析师] 没有analysis_id，工具执行消息将无法发送")
        else:
            logger.info(f"✅ [新闻分析师] 使用analysis_id: {analysis_id}")
        
        # 获取用户选择的工具列表和时间参数
        selected_tools = state.get("selected_tools", [])
        timeframe = state.get("timeframe", "1d")
        
        # 新闻工具映射 (使用正确的工具ID)
        news_tool_ids = ['finnhub_news']  # 新闻相关的工具ID
        selected_news_tools = [tool_id for tool_id in selected_tools if tool_id in news_tool_ids]
        logger.info(f"🛠 [直接执行] 新闻工具: {selected_news_tools} (共{len(selected_news_tools)}个)")
        
        # 计算时间参数
        from datetime import timedelta
        current_dt = datetime.now()
        days_back = 7 if timeframe in ['1h', '1d'] else 14
        
        # 获取语言设置（修复作用域问题）
        language = state.get("language", "zh-CN")
        
        # 发送工具执行开始聚合消息
        start_time = datetime.utcnow()
        if analysis_id and redis_publisher and selected_news_tools and len(selected_news_tools) > 0:
            try:
                # 使用本地化工具名称（与市场分析师保持一致）
                tools_localized_list = [get_tool_name(tool_id, language) for tool_id in selected_news_tools]
                tools_list = ", ".join(tools_localized_list)
                
                # 手动构建消息（与市场分析师一致）
                start_msg = get_message('tool_execution_start', language)
                tools_count_label = get_message('tools_count', language)
                total_count_label = get_message('total_count', language)
                colon = get_message('colon', language)
                agent_name = get_agent_name('news', language)
                message = f"{start_msg}{colon} {tools_list} ({total_count_label} {len(selected_news_tools)} {tools_count_label})"
                
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
                logger.debug(f"📡 [聚合消息] 已发送新闻工具批量执行开始事件: {len(selected_news_tools)}个工具")
            except Exception as e:
                logger.warning(f"⚠️ [聚合消息] 发送工具开始事件失败: {e}")

        # 直接执行新闻工具
        tool_results = []
        successful_tools = 0
        failed_tools = 0
        
        for tool_id in selected_news_tools:
            try:
                tool_cn_name = TOOL_NAME_CN.get(tool_id, tool_id)
                logger.info(f"🎯 [直接执行] 正在执行新闻工具: {tool_cn_name} ({tool_id})")
                
                # 从toolkit获取工具方法
                tool_method = getattr(toolkit, tool_id, None)
                if tool_method is None:
                    logger.warning(f"⚠️ [直接执行] 未找到新闻工具: {tool_id}")
                    tool_results.append({
                        "tool": tool_id,
                        "result": f"错误: 未找到工具 {tool_id}"
                    })
                    failed_tools += 1
                    continue
                
                # 构造工具参数
                tool_args = {
                    'symbol': ticker,
                    'days_back': days_back,
                    'max_results': 10
                }
                
                # 执行工具
                result_data = tool_method(**tool_args)
                tool_results.append({
                    "tool": tool_id,
                    "result": str(result_data)
                })
                logger.info(f"✅ [直接执行] 工具{tool_cn_name}执行成功")
                successful_tools += 1
                
            except Exception as e:
                logger.error(f"❌ [直接执行] 工具{tool_id}执行失败: {str(e)}")
                tool_results.append({
                    "tool": tool_id,
                    "result": f"错误: {str(e)}"
                })
                failed_tools += 1

        # 发送工具执行完成聚合消息
        if analysis_id and redis_publisher and selected_news_tools:
            try:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                # 手动构建完成消息（与市场分析师一致）
                complete_msg = get_message('tool_execution_complete', language)
                tools_label = get_message('tools_count', language)
                success_label = get_message('success_count', language)
                failed_label = get_message('failed_count', language)
                time_label = get_message('time_spent', language)
                agent_name = get_agent_name('news', language)
                
                comma = get_message('comma', language)
                total_count_label = get_message('total_count', language)
                message = f"{complete_msg}{comma} {total_count_label} {len(selected_news_tools)} {tools_label}{comma} {successful_tools} {success_label}{comma} {failed_tools} {failed_label}{comma} {time_label} {duration:.1f}s"
                
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
                logger.debug(f"📡 [聚合消息] 已发送新闻工具批量执行完成事件: 耗时{duration:.1f}s")
            except Exception as e:
                logger.warning(f"⚠️ [聚合消息] 发送工具完成事件失败: {e}")
        
        # 构建工具结果文本
        if tool_results:
            tool_results_text = "\n\n".join([
                f"## {r['tool']}\n{r['result']}" for r in tool_results
            ])
            system_content = (
                "你是一位专业的新闻分析师。基于以下工具获取的新闻数据进行分析。\n\n"
                "新闻数据：\n{tool_results}\n\n"
                "{system_message}\n\n"
                "请基于以上数据进行综合新闻分析，评估新闻对股价的影响。"
            )
        else:
            tool_results_text = "用户选择跳过工具调用，无实时新闻数据。"
            system_content = (
                "你是一位专业的新闻分析师。\n\n"
                "{system_message}\n\n"
                "注意：用户选择跳过工具调用，请基于一般市场知识进行新闻影响分析。\n"
                "请分析当前可能影响该股票/资产的一般新闻类型和趋势，并明确说明这是基于一般市场知识的分析。"
            )
            
        # 使用LLM分析新闻数据
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", system_content),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        analysis_prompt = analysis_prompt.partial(tool_results=tool_results_text)
        analysis_prompt = analysis_prompt.partial(system_message=system_message)
        
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

                    result = analysis_chain.invoke(state["messages"])

            except Exception as e:

                # 降级处理：直接调用原方法

                logger.warning(f"⚠️ 语言前缀添加失败，使用原方法: {e}")

                result = analysis_chain.invoke(state["messages"])
        except Exception as e:
            logger.error(f"❌ [新闻分析师] LLM调用失败: {str(e)}")
            # 创建降级响应，确保流程继续
            from langchain_core.messages import AIMessage
            result = AIMessage(content=f"新闻分析暂时不可用：{str(e)}。请检查LLM配置或token限制。")
        
        # 返回分析结果
        report = result.content if hasattr(result, 'content') else str(result)
        logger.info(f"📰 [新闻分析师] 直接执行模式分析完成，报告长度: {len(report)}")
        
        # 释放序列锁，允许下一个分析师开始执行
        logger.info(f"🔓 [新闻分析师] 释放序列锁，完成执行")
        
        # 添加小延迟确保消息已发送完成
        import time
        time.sleep(0.5)
        
        return {
            "messages": [result],
            "news_report": report,
            "current_sequence": None,  # 释放当前序列
            "sequence_lock": False,    # 释放锁
            # 🔧 添加明确的阶段转换标记，确保流程继续到Phase 2
            "phase_1_complete": True,  # 标记Phase 1完成
            "ready_for_phase_2": True,  # 准备进入Phase 2投资辩论
        }


    return news_analyst_node