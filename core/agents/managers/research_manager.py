import time
import json
from langchain_core.messages import AIMessage

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")

# 导入提示词加载器
from core.agents.prompt_loader import get_prompt_loader
# 导入i18n功能
from core.i18n.messages import get_language_name_for_prompt


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        # 获取辩论内容 - 使用新的debate_turns结构
        investment_debate_state = state["investment_debate_state"]
        debate_turns = investment_debate_state.get("debate_turns", [])
        
        # 将debate_turns转换为可读的历史记录
        history = ""
        for turn in debate_turns:
            speaker = turn.get("speaker", "").upper()
            content = turn.get("content", "")
            if speaker == "BULL":
                history += f"看涨分析师：{content}\n\n"
            elif speaker == "BEAR":
                history += f"看跌分析师：{content}\n\n"
        
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        
        # 获取资产类型
        company_name = state.get("company_of_interest", "Unknown")
        from core.utils.asset_utils import AssetUtils
        asset_type = AssetUtils.detect_asset_type(company_name)
        framework = AssetUtils.get_analysis_framework(asset_type)

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

        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        language_name = get_language_name_for_prompt(language)
        
        # 使用提示词加载器获取配置（支持多语言）
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt("research_manager", language=language)
        
        # 获取系统消息模板
        system_message_template = prompt_config.get("system_message", "您是投资组合经理。")
        
        # 根据资产类型添加额外指导
        asset_guidance = ""
        if asset_type == 'crypto':
            asset_guidance = "\n\n重要：当前分析的是加密货币，请关注链上数据、技术发展、监管风险等因素，而不是公司财务。"
        elif asset_type == 'stock':
            asset_guidance = "\n\n重要：当前分析的是股票，请关注公司财务、管理团队、行业竞争等因素。"
        
        # 格式化系统消息（替换占位符）
        prompt = system_message_template.format(
            past_memory_str=past_memory_str,
            market_research_report=market_research_report,
            sentiment_report=sentiment_report,
            news_report=news_report,
            history=history,
            language_name=language_name
        ) + asset_guidance
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("research_manager")
        logger.debug(f"📋 [研究经理] 使用提示词版本: {prompt_version}")
        # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言
        language = state.get("language", "zh-CN")
        language_name = "English" if language == "en-US" else "简体中文"
        language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "
        
        logger.info(f"🌍 [research_manager] 语言设置: {language} -> {language_name}")
        logger.debug(f"🔴 [research_manager] 语言前缀: {language_prefix}")
        
        # 在prompt前添加语言强制前缀
        enhanced_prompt = language_prefix + prompt
        logger.info(f"✅ [research_manager] 已添加语言前缀到prompt")
        
        response = llm.invoke(enhanced_prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        # Create clean AIMessage for message chain continuity
        clean_message = AIMessage(content=response.content)

        return {
            "messages": [clean_message],
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
