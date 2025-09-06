import functools
import time
import json

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")

# 导入提示词加载器
from core.agents.prompt_loader import get_prompt_loader
# 导入i18n功能
from core.i18n.messages import get_language_name_for_prompt


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]

        # 使用统一的股票类型检测
        from core.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(company_name)
        is_china = market_info['is_china']
        is_hk = market_info['is_hk']
        is_us = market_info['is_us']

        # 根据股票类型确定货币单位
        currency = market_info['currency_name']
        currency_symbol = market_info['currency_symbol']

        logger.debug(f"💰 [DEBUG] ===== 交易员节点开始 =====")
        logger.debug(f"💰 [DEBUG] 交易员检测股票类型: {company_name} -> {market_info['market_name']}, 货币: {currency}")
        logger.debug(f"💰 [DEBUG] 货币符号: {currency_symbol}")
        logger.debug(f"💰 [DEBUG] 市场详情: 中国A股={is_china}, 港股={is_hk}, 美股={is_us}")
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}"

        # 检查memory是否可用
        if memory is not None:
            logger.warning(f"⚠️ [DEBUG] memory可用，获取历史记忆")
            past_memories = memory.get_memories(curr_situation, n_matches=2)
            past_memory_str = ""
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            logger.warning(f"⚠️ [DEBUG] memory为None，跳过历史记忆检索")
            past_memories = []
            past_memory_str = "暂无历史记忆数据可参考。"

        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        language_name = get_language_name_for_prompt(language)
        
        # 使用提示词加载器获取配置（支持多语言）
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt("trader", language=language)
        
        # 获取系统消息和用户消息模板
        system_message_template = prompt_config.get("system_message", "您是专业交易员。")
        user_message_template = prompt_config.get("user_message", "")
        
        # 格式化系统消息
        system_message = system_message_template.format(
            company_name=company_name,
            past_memory_str=past_memory_str,
            investment_plan=investment_plan
        )
        
        # 格式化用户消息
        user_message = user_message_template.format(
            company_name=company_name,
            investment_plan=investment_plan
        )
        
        messages = [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("trader")
        logger.debug(f"💰 [交易员] 使用提示词版本: {prompt_version}")

        logger.debug(f"💰 [DEBUG] 准备调用LLM，系统提示包含货币: {currency}")
        logger.debug(f"💰 [DEBUG] 系统提示中的关键部分: 目标价格({currency})")

        # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言
        language = state.get("language", "zh-CN")
        language_name = "English" if language == "en-US" else "简体中文"
        language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "
        
        logger.info(f"🌍 [交易员] 语言设置: {language} -> {language_name}")
        logger.debug(f"🔴 [交易员] 语言前缀: {language_prefix}")
        
        # 在调用LLM前添加语言前缀到messages
        try:
            if messages:
                # 创建带前缀的消息副本
                prefixed_messages = messages.copy()
                # 在第一个消息前添加系统级语言前缀
                from langchain_core.messages import SystemMessage
                language_system_msg = SystemMessage(content=language_prefix)
                prefixed_messages = [language_system_msg] + prefixed_messages
                logger.info(f"✅ [交易员] 已添加语言前缀，消息数: {len(prefixed_messages)}")
                result = llm.invoke(prefixed_messages)
            else:
                logger.warning(f"⚠️ [交易员] messages为空，使用原方法")
                result = llm.invoke(messages)
        except Exception as e:
            # 降级处理：直接调用原方法
            logger.warning(f"⚠️ [交易员] 语言前缀添加失败，使用原方法: {e}")
            result = llm.invoke(messages)

        logger.debug(f"💰 [DEBUG] LLM调用完成")
        logger.debug(f"💰 [DEBUG] 交易员回复长度: {len(result.content)}")
        logger.debug(f"💰 [DEBUG] 交易员回复前500字符: {result.content[:500]}...")
        logger.debug(f"💰 [DEBUG] ===== 交易员节点结束 =====")

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
