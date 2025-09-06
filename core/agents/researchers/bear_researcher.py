from langchain_core.messages import AIMessage
import time
import json

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")

# 导入提示词加载器
from core.agents.prompt_loader import get_prompt_loader
# 导入i18n功能
from core.i18n.messages import get_language_name_for_prompt

# 导入消息处理工具 (Linus: use clean data structures)
from core.agents.utils.message_utils import (
    add_debate_turn,
    get_relevant_context,
    format_context_for_prompt,
    clean_content
)

# 导入轮次感知工具
from core.agents.utils.debate_utils import (
    is_first_round_analysis,
    get_analysis_context_for_prompt
)


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        debate_turns = investment_debate_state.get("debate_turns", [])
        
        # Get relevant context using the new structure (Linus: eliminate special cases)
        relevant_context = format_context_for_prompt(
            debate_turns, 
            "bear",
            max_context=3  # Only last 3 turns
        )
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]

        # 使用统一的股票类型检测
        company_name = state.get('company_of_interest', 'Unknown')
        from core.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(company_name)
        is_china = market_info['is_china']
        is_hk = market_info['is_hk']
        is_us = market_info['is_us']

        currency = market_info['currency_name']
        currency_symbol = market_info['currency_symbol']

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}"

        # 安全检查：确保memory不为None
        if memory is not None:
            past_memories = memory.get_memories(curr_situation, n_matches=2)
        else:
            logger.warning(f"⚠️ [DEBUG] memory为None，跳过历史记忆检索")
            past_memories = []

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # 使用提示词加载器获取配置
        prompt_loader = get_prompt_loader()
        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        
        prompt_config = prompt_loader.load_prompt("bear_researcher", language=language)
        
        # 获取系统消息模板
        system_message_template = prompt_config.get("system_message", "你是一位看跌分析师。")
        
        # 根据资产类型设置不同的分析要点
        is_crypto = any(ticker in company_name.upper() for ticker in ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'ADA', 'DOT', 'DOGE'])
        
        if is_crypto:
            risk_challenges_focus = "突出监管风险、技术漏洞、市场操纵、泡沫风险、极端波动性"
            competitive_weakness_focus = "强调扩展性问题、能源消耗、新公链竞争、技术落后风险"
            negative_indicators_focus = "使用链上数据下降、大户抛售、挖矿难度变化、DeFi锁仓量下降作为证据"
        else:
            risk_challenges_focus = "突出市场饱和、财务不稳定或宏观经济威胁等可能阻碍表现的因素"
            competitive_weakness_focus = "强调市场地位较弱、创新下降或来自竞争对手威胁等脆弱性"
            negative_indicators_focus = "使用财务数据、市场趋势或最近不利消息的证据来支持你的立场"
        
        # 使用轮次感知功能生成上下文
        analysis_context = get_analysis_context_for_prompt(
            debate_turns, 
            "bear",
            relevant_context  # 传入旧的上下文作为备用
        )
        
        # 根据分析模式调整提示词
        if analysis_context["analysis_mode"] == "independent":
            # 首轮分析：清空其他观点相关内容
            current_response_content = ""
            context_instruction = analysis_context["context_description"]
        else:
            # 后续轮次：可以参考其他观点
            current_response_content = analysis_context["other_views"]
            context_instruction = analysis_context["context_description"]
        
        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        language_name = get_language_name_for_prompt(language)
        
        # 格式化系统消息（替换占位符）
        prompt = system_message_template.format(
            company_name=company_name,
            market_type='加密货币',
            currency=currency,
            currency_symbol=currency_symbol,
            risk_challenges_focus=risk_challenges_focus,
            competitive_weakness_focus=competitive_weakness_focus,
            negative_indicators_focus=negative_indicators_focus,
            market_research_report=market_research_report,
            sentiment_report=sentiment_report,
            news_report=news_report,
            history=relevant_context,  # 保持兼容性
            current_response=current_response_content,  # 根据轮次动态设置
            past_memory_str=past_memory_str,
            language_name=language_name
        )
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("bear_researcher")
        logger.debug(f"🐻 [看跌研究员] 使用提示词版本: {prompt_version}")

        # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言
        language = state.get("language", "zh-CN")
        language_name = "English" if language == "en-US" else "简体中文"
        language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "
        
        logger.info(f"🌍 [bear_researcher] 语言设置: {language} -> {language_name}")
        logger.debug(f"🔴 [bear_researcher] 语言前缀: {language_prefix}")
        
        # 在prompt前添加语言强制前缀
        enhanced_prompt = language_prefix + prompt
        logger.info(f"✅ [bear_researcher] 已添加语言前缀到prompt")
        
        response = llm.invoke(enhanced_prompt)

        # 移除硬编码前缀，让内容纯粹
        argument = response.content
        
        # Clean the content
        argument = clean_content(argument)

        new_count = investment_debate_state["count"] + 1
        logger.info(f"🐻 [Bear Researcher] 计数递增: {investment_debate_state['count']} → {new_count}")
        
        # Add to debate turns using the new structure (Linus: single source of truth)
        updated_turns = add_debate_turn(
            debate_turns,
            speaker="bear",
            content=argument
        )
        
        new_investment_debate_state = {
            "debate_turns": updated_turns,  # Single source of truth
            "count": new_count,
            "judge_decision": investment_debate_state.get("judge_decision", ""),
            # Deprecated fields - kept for compatibility
            "history": "",  # No longer accumulate
            "bull_history": "",  # No longer accumulate
            "bear_history": "",  # No longer accumulate
            "current_response": argument  # Keep for compatibility
        }

        # Create clean AIMessage for message chain continuity
        clean_message = AIMessage(content=response.content)

        return {
            "messages": [clean_message],
            "investment_debate_state": new_investment_debate_state
        }

    return bear_node
