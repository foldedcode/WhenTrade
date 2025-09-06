import time
import json
from langchain_core.messages import AIMessage

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")

# 导入提示词加载器
from core.agents.prompt_loader import get_prompt_loader

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


def get_latest_response(full_response):
    """提取最新的核心观点，跳过复述部分"""
    if not full_response:
        return ""
    
    # 按段落分割
    paragraphs = full_response.split('\n')
    
    # 过滤掉复述性的段落（包含这些关键词的段落可能是在复述他人观点）
    restatement_keywords = [
        "你说", "您说", "他说", "提到", "认为", "觉得",
        "指出", "表示", "强调", "刚才", "之前",
        "你的观点", "您的观点", "他的观点"
    ]
    
    # 找到核心观点段落（从后往前找，跳过复述）
    core_paragraphs = []
    for p in reversed(paragraphs):
        p_clean = p.strip()
        if not p_clean:
            continue
            
        # 检查是否是复述段落
        is_restatement = any(keyword in p_clean[:50] for keyword in restatement_keywords)
        
        if not is_restatement:
            core_paragraphs.append(p_clean)
            if len('\n'.join(core_paragraphs)) > 300:  # 收集足够的核心内容
                break
    
    # 反转顺序（因为是从后往前收集的）
    core_paragraphs.reverse()
    
    # 组合并截取
    result = '\n'.join(core_paragraphs)
    return result[:500] if len(result) > 500 else result


def create_risky_debator(llm):
    def risky_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        debate_turns = risk_debate_state.get("debate_turns", [])
        
        # Get relevant context using the new structure (Linus: eliminate special cases)
        relevant_context = format_context_for_prompt(
            debate_turns, 
            "risky",
            max_context=3  # Only last 3 turns
        )

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]

        trader_decision = state.get("investment_plan", "")
        
        # 使用轮次感知功能生成上下文
        analysis_context = get_analysis_context_for_prompt(
            debate_turns, 
            "risky",  # aggressive 在系统中是 risky
            relevant_context
        )
        
        # 获取其他分析师的观点内容
        safe_response = ""
        neutral_response = ""
        
        if analysis_context["analysis_mode"] != "independent":
            # 从debate_turns中提取safe和neutral的观点
            for turn in debate_turns:
                if turn.get("speaker") == "safe":
                    safe_response = turn.get("content", "")[:200] + "..."
                elif turn.get("speaker") == "neutral":
                    neutral_response = turn.get("content", "")[:200] + "..."

        # 使用提示词加载器获取配置
        prompt_loader = get_prompt_loader()
        # 获取语言参数（从state中提取，如果没有则使用默认中文）
        language = state.get("language", "zh-CN")
        
        prompt_config = prompt_loader.load_prompt("aggressive_debator", language=language)
        
        # 获取系统消息模板
        system_message_template = prompt_config.get("system_message", "您是激进风险分析师。")
        
        # 格式化系统消息（替换占位符）
        prompt = system_message_template.format(
            trader_decision=trader_decision,
            market_research_report=market_research_report,
            sentiment_report=sentiment_report,
            news_report=news_report,
            history=relevant_context,  # 保持兼容性
            current_safe_response=safe_response,  # 根据轮次动态设置
            current_neutral_response=neutral_response  # 根据轮次动态设置
        )
        
        # 记录提示词版本
        prompt_version = prompt_loader.get_prompt_version("aggressive_debator")
        logger.debug(f"🔥 [激进风险分析师] 使用提示词版本: {prompt_version}")
        
        # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言

        
        language = state.get("language", "zh-CN")

        
        language_name = "English" if language == "en-US" else "简体中文"

        
        language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "

        
        

        
        # 在prompt前添加语言强制前缀

        
        enhanced_prompt = language_prefix + prompt

        
        

        
        response = llm.invoke(enhanced_prompt)

        # 检查角色混淆
        argument = response.content
        if "保守" in argument[:100] or "谨慎" in argument[:100]:
            logger.warning("⚠️ 激进分析师角色混淆，重新生成...")
            # 如果检测到角色混淆，使用默认回应
            argument = "我坚持认为应该积极把握这个高风险高回报的机会。虽然市场存在波动，但长期增长潜力巨大。通过合理的风险管理，我们可以在控制风险的前提下获得高额回报。"
        
        # Clean the content
        argument = clean_content(argument)
        
        # Add to debate turns using the new structure (Linus: single source of truth)
        updated_turns = add_debate_turn(
            debate_turns,
            speaker="risky",
            content=argument
        )
        
        new_risk_debate_state = {
            "debate_turns": updated_turns,  # Single source of truth
            "latest_speaker": "Risky",
            "count": risk_debate_state["count"] + 1,
            "judge_decision": risk_debate_state.get("judge_decision", ""),
            # Deprecated fields - kept for compatibility
            "history": "",  # No longer accumulate
            "risky_history": "",  # No longer accumulate
            "safe_history": "",  # No longer accumulate
            "neutral_history": "",  # No longer accumulate
            "current_risky_response": argument,  # Keep for compatibility
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", "")
        }

        # Create clean AIMessage for message chain continuity
        clean_message = AIMessage(content=response.content)

        return {
            "messages": [clean_message],
            "risk_debate_state": new_risk_debate_state
        }

    return risky_node
