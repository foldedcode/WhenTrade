# WhenTrade/graph/propagation.py

from typing import Dict, Any

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")
from core.agents.utils.agent_states import (
    WTAgentState,
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, 
        company_name: str, 
        trade_date: str, 
        timeframe: str = "1d",
        language: str = "zh-CN",  # Linus: add language to data structure
        selected_tools: list = None,
        selected_data_sources: list = None,
        analysis_id: str = None
    ) -> Dict[str, Any]:
        """Create the initial state for the agent graph (Linus: single source of truth)."""
        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "timeframe": timeframe,
            "language": language,  # Linus: language becomes part of core state
            "analysis_id": analysis_id,
            # Phase 2: 用户选择的工具和数据源
            "selected_tools": selected_tools or [],
            "selected_data_sources": selected_data_sources or [],
            # 序列执行控制
            "current_sequence": None,
            "sequence_lock": False,
            "investment_debate_state": InvestDebateState(
                {
                    # New structure - single source of truth
                    "debate_turns": [],
                    "judge_decision": "",
                    "count": 0,
                    # Deprecated fields - initialized for compatibility
                    "history": "",
                    "bull_history": "",
                    "bear_history": "",
                    "current_response": "",
                }
            ),
            "risk_debate_state": RiskDebateState(
                {
                    # New structure - single source of truth
                    "debate_turns": [],
                    "latest_speaker": "",
                    "judge_decision": "",
                    "count": 0,
                    # Deprecated fields - initialized for compatibility
                    "history": "",
                    "risky_history": "",
                    "safe_history": "",
                    "neutral_history": "",
                    "current_risky_response": "",
                    "current_safe_response": "",
                    "current_neutral_response": "",
                }
            ),
            "market_report": "",
            "sentiment_report": "",
            "news_report": "",
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Get arguments for the graph invocation."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
