# WhenTrade/graph/conditional_logic.py

from core.agents.utils.agent_states import WTAgentState

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: WTAgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🛠️ [市场分析师] 执行工具: {len(last_message.tool_calls)}个工具")
            return "tools_market"
        
        logger.info(f"✅ [市场分析师] 完成分析")
        return "Msg Clear Market"

    def should_continue_social(self, state: WTAgentState):
        """Determine if social media analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🛠️ [社交分析师] 执行工具: {len(last_message.tool_calls)}个工具")
            return "tools_social"
        
        logger.info(f"✅ [社交分析师] 完成分析")
        return "Msg Clear Social"

    def should_continue_news(self, state: WTAgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            logger.info(f"🛠️ [新闻分析师] 执行工具: {len(last_message.tool_calls)}个工具")
            return "tools_news"
        
        logger.info(f"✅ [新闻分析师] 完成分析")
        return "Msg Clear News"



    def should_continue_bull(self, state: WTAgentState) -> str:
        """Determine if Bull Researcher should continue debate or finish.
        Pure function: only reads state, no side effects."""
        # Read current count (Bull node already incremented it)
        current_count = state["investment_debate_state"]["count"]
        
        logger.info(f"🐂 [Bull条件判断] count={current_count}, max_rounds={self.max_debate_rounds}, threshold={2 * self.max_debate_rounds}")
        
        # 统一架构：总是路由到Msg Clear节点
        if current_count >= 2 * self.max_debate_rounds:
            logger.info(f"🐂 [Bull条件判断] 辩论结束 (count={current_count} >= {2 * self.max_debate_rounds}) → Msg Clear Bull")
        else:
            logger.info(f"🐂 [Bull条件判断] 继续辩论 (count={current_count} < {2 * self.max_debate_rounds}) → Msg Clear Bull → Bear Researcher")
        
        # 总是先到Msg Clear Bull，由它决定下一步
        return "Msg Clear Bull"
    
    def should_continue_bear(self, state: WTAgentState) -> str:
        """Determine if Bear Researcher should continue debate or finish.
        Pure function: only reads state, no side effects."""
        # Read current count (Bear node already incremented it)
        current_count = state["investment_debate_state"]["count"]
        
        logger.info(f"🐻 [Bear条件判断] count={current_count}, max_rounds={self.max_debate_rounds}, threshold={2 * self.max_debate_rounds}")
        
        # 统一架构：总是路由到Msg Clear节点
        if current_count >= 2 * self.max_debate_rounds:
            logger.info(f"🐻 [Bear条件判断] 辩论结束 (count={current_count} >= {2 * self.max_debate_rounds}) → Msg Clear Bear")
        else:
            logger.info(f"🐻 [Bear条件判断] 继续辩论 (count={current_count} < {2 * self.max_debate_rounds}) → Msg Clear Bear → Bull Researcher")
        
        # 总是先到Msg Clear Bear，由它决定下一步
        return "Msg Clear Bear"

    def should_continue_debate(self, state: WTAgentState) -> str:
        """[DEPRECATED] Old debate logic - kept for backward compatibility."""
        # This function is no longer used in the new architecture
        # See should_continue_after_bull_clear and should_continue_after_bear_clear
        if (
            state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds
        ):
            if state["investment_debate_state"]["current_response"].startswith("Bull"):
                return "Msg Clear Bull"
            return "Msg Clear Bear"
        if state["investment_debate_state"]["current_response"].startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"

    def should_continue_after_bull_clear(self, state: WTAgentState) -> str:
        """Determine next step after Bull Researcher's clear node."""
        current_count = state["investment_debate_state"]["count"]
        threshold = 2 * self.max_debate_rounds
        
        logger.info(f"🐂➡️ [Bull Clear] count={current_count}, max_rounds={self.max_debate_rounds}, threshold={threshold}")
        
        if current_count >= threshold:
            logger.info(f"🐂➡️ [Bull Clear] 辩论结束 → Research Manager")
            return "Research Manager"
        
        logger.info(f"🐂➡️ [Bull Clear] 继续辩论 → Bear Researcher")
        return "Bear Researcher"
    
    def should_continue_after_bear_clear(self, state: WTAgentState) -> str:
        """Determine next step after Bear Researcher's clear node."""
        current_count = state["investment_debate_state"]["count"]
        threshold = 2 * self.max_debate_rounds
        
        logger.info(f"🐻➡️ [Bear Clear] count={current_count}, max_rounds={self.max_debate_rounds}, threshold={threshold}")
        
        if current_count >= threshold:
            logger.info(f"🐻➡️ [Bear Clear] 辩论结束 → Research Manager")
            return "Research Manager"
        
        logger.info(f"🐻➡️ [Bear Clear] 继续辩论 → Bull Researcher")
        return "Bull Researcher"

    def should_continue_risky(self, state: WTAgentState) -> str:
        """Determine if Risky Analyst should continue debate or finish.
        Pure function: only reads state, no side effects."""
        # Read current count (Risky node already incremented it)
        current_count = state["risk_debate_state"]["count"]
        
        logger.info(f"🔥 [Risky条件判断] count={current_count}, max_rounds={self.max_risk_discuss_rounds}, threshold={3 * self.max_risk_discuss_rounds}")
        
        # 统一架构：总是路由到Msg Clear节点
        if current_count >= 3 * self.max_risk_discuss_rounds:
            logger.info(f"🔥 [Risky条件判断] 分析结束 (count={current_count} >= {3 * self.max_risk_discuss_rounds}) → Msg Clear Risky")
        else:
            logger.info(f"🔥 [Risky条件判断] 继续分析 (count={current_count} < {3 * self.max_risk_discuss_rounds}) → Msg Clear Risky → Safe Analyst")
        
        # 总是先到Msg Clear Risky，由它决定下一步
        return "Msg Clear Risky"
    
    def should_continue_safe(self, state: WTAgentState) -> str:
        """Determine if Safe Analyst should continue debate or finish.
        Pure function: only reads state, no side effects."""
        # Read current count (Safe node already incremented it)
        current_count = state["risk_debate_state"]["count"]
        
        logger.info(f"🛡️ [Safe条件判断] count={current_count}, max_rounds={self.max_risk_discuss_rounds}, threshold={3 * self.max_risk_discuss_rounds}")
        
        # 统一架构：总是路由到Msg Clear节点
        if current_count >= 3 * self.max_risk_discuss_rounds:
            logger.info(f"🛡️ [Safe条件判断] 分析结束 (count={current_count} >= {3 * self.max_risk_discuss_rounds}) → Msg Clear Safe")
        else:
            logger.info(f"🛡️ [Safe条件判断] 继续分析 (count={current_count} < {3 * self.max_risk_discuss_rounds}) → Msg Clear Safe → Neutral Analyst")
        
        # 总是先到Msg Clear Safe，由它决定下一步
        return "Msg Clear Safe"
    
    def should_continue_neutral(self, state: WTAgentState) -> str:
        """Determine if Neutral Analyst should continue debate or finish.
        Pure function: only reads state, no side effects."""
        # Read current count (Neutral node already incremented it)
        current_count = state["risk_debate_state"]["count"]
        
        logger.info(f"⚖️ [Neutral条件判断] count={current_count}, max_rounds={self.max_risk_discuss_rounds}, threshold={3 * self.max_risk_discuss_rounds}")
        
        # 统一架构：总是路由到Msg Clear节点
        if current_count >= 3 * self.max_risk_discuss_rounds:
            logger.info(f"⚖️ [Neutral条件判断] 分析结束 (count={current_count} >= {3 * self.max_risk_discuss_rounds}) → Msg Clear Neutral")
        else:
            logger.info(f"⚖️ [Neutral条件判断] 继续分析 (count={current_count} < {3 * self.max_risk_discuss_rounds}) → Msg Clear Neutral → Risky Analyst")
        
        # 总是先到Msg Clear Neutral，由它决定下一步
        return "Msg Clear Neutral"

    def should_continue_risk_analysis(self, state: WTAgentState) -> str:
        """[DEPRECATED] Old risk analysis logic - kept for backward compatibility."""
        # This function is no longer used in the new architecture
        # See should_continue_risky, should_continue_safe, should_continue_neutral
        if (
            state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):
            if state["risk_debate_state"]["latest_speaker"].startswith("Risky"):
                return "Msg Clear Risky"
            if state["risk_debate_state"]["latest_speaker"].startswith("Safe"):
                return "Msg Clear Safe"
            return "Msg Clear Neutral"
        if state["risk_debate_state"]["latest_speaker"].startswith("Risky"):
            return "Safe Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Safe"):
            return "Neutral Analyst"
        return "Risky Analyst"
    
    def should_continue_after_risky_clear(self, state: WTAgentState) -> str:
        """Determine next step after Risky Analyst's clear node."""
        current_count = state["risk_debate_state"]["count"]
        threshold = 3 * self.max_risk_discuss_rounds
        
        logger.info(f"🔥➡️ [Risky Clear] count={current_count}, max_rounds={self.max_risk_discuss_rounds}, threshold={threshold}")
        
        if current_count >= threshold:
            logger.info(f"🔥➡️ [Risky Clear] 风险分析结束 → Risk Judge")
            return "Risk Judge"
        
        logger.info(f"🔥➡️ [Risky Clear] 继续分析 → Safe Analyst")
        return "Safe Analyst"
    
    def should_continue_after_safe_clear(self, state: WTAgentState) -> str:
        """Determine next step after Safe Analyst's clear node."""
        current_count = state["risk_debate_state"]["count"]
        threshold = 3 * self.max_risk_discuss_rounds
        
        logger.info(f"🛡️➡️ [Safe Clear] count={current_count}, max_rounds={self.max_risk_discuss_rounds}, threshold={threshold}")
        
        if current_count >= threshold:
            logger.info(f"🛡️➡️ [Safe Clear] 风险分析结束 → Risk Judge")
            return "Risk Judge"
        
        logger.info(f"🛡️➡️ [Safe Clear] 继续分析 → Neutral Analyst")
        return "Neutral Analyst"
    
    def should_continue_after_neutral_clear(self, state: WTAgentState) -> str:
        """Determine next step after Neutral Analyst's clear node."""
        current_count = state["risk_debate_state"]["count"]
        threshold = 3 * self.max_risk_discuss_rounds
        
        logger.info(f"⚖️➡️ [Neutral Clear] count={current_count}, max_rounds={self.max_risk_discuss_rounds}, threshold={threshold}")
        
        if current_count >= threshold:
            logger.info(f"⚖️➡️ [Neutral Clear] 风险分析结束 → Risk Judge")
            return "Risk Judge"
        
        logger.info(f"⚖️➡️ [Neutral Clear] 继续分析 → Risky Analyst")
        return "Risky Analyst"

    # New functions for direct Bull/Bear routing (like example project)
    def should_continue_debate_bull(self, state: WTAgentState) -> str:
        """Bull Researcher decides next step: continue debate with Bear or go to Research Manager."""
        current_count = state["investment_debate_state"]["count"]
        
        if current_count >= 2 * self.max_debate_rounds:
            logger.info(f"🐂 [Bull直接路由] 辩论结束 → Research Manager")
            return "Research Manager"
        
        logger.info(f"🐂 [Bull直接路由] 继续辩论 → Bear Researcher")
        return "Bear Researcher"
    
    def should_continue_debate_bear(self, state: WTAgentState) -> str:
        """Bear Researcher decides next step: continue debate with Bull or go to Research Manager."""
        current_count = state["investment_debate_state"]["count"]
        
        if current_count >= 2 * self.max_debate_rounds:
            logger.info(f"🐻 [Bear直接路由] 辩论结束 → Research Manager") 
            return "Research Manager"
        
        logger.info(f"🐻 [Bear直接路由] 继续辩论 → Bull Researcher")
        return "Bull Researcher"
