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


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

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
        prompt_config = prompt_loader.load_prompt("risk_manager", language=language)
        
        # 获取系统消息模板
        system_message_template = prompt_config.get("system_message", "您是风险管理委员会主席。")
        
        # 格式化系统消息（替换占位符）
        prompt = system_message_template.format(
            trader_plan=trader_plan,
            past_memory_str=past_memory_str,
            history=history,
            language_name=language_name
        )
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("risk_manager", language=language)
        logger.debug(f"🛡️ [风险管理经理] 使用提示词版本: {prompt_version} (语言: {language})")
        
        # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言
        language = state.get("language", "zh-CN")
        language_name = "English" if language == "en-US" else "简体中文"
        language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "
        
        logger.info(f"🌍 [risk_manager] 语言设置: {language} -> {language_name}")
        logger.debug(f"🔴 [risk_manager] 语言前缀: {language_prefix}")
        
        # 在prompt前添加语言强制前缀
        enhanced_prompt = language_prefix + prompt
        logger.info(f"✅ [risk_manager] 已添加语言前缀到prompt")
        
        response = llm.invoke(enhanced_prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "risky_history": risk_debate_state["risky_history"],
            "safe_history": risk_debate_state["safe_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_risky_response": risk_debate_state["current_risky_response"],
            "current_safe_response": risk_debate_state["current_safe_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        # Create clean AIMessage for message chain continuity
        clean_message = AIMessage(content=response.content)

        return {
            "messages": [clean_message],
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return risk_manager_node
