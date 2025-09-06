# WhenTrade/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from core.agents import *
from core.agents.managers.portfolio_manager import create_portfolio_manager
from core.agents.utils.agent_states import WTAgentState
from core.agents.utils.agent_utils import Toolkit

from .conditional_logic import ConditionalLogic

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        portfolio_manager_memory,  # 添加组合经理记忆
        conditional_logic: ConditionalLogic,
        config: Dict[str, Any] = None,
        react_llm = None,
        all_agents = None,  # 添加agents注册列表
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.portfolio_manager_memory = portfolio_manager_memory  # 保存组合经理记忆
        self.conditional_logic = conditional_logic
        self.config = config or {}
        self.react_llm = react_llm
        self.all_agents = all_agents or []  # 保存agents列表引用

    def setup_graph(
        self, selected_analysts=["market", "social", "news"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            # 现在所有LLM都使用标准市场分析师（包括阿里百炼的OpenAI兼容适配器）
            llm_provider = self.config.get("llm_provider", "").lower()

            # 检查是否使用OpenAI兼容的阿里百炼适配器
            using_dashscope_openai = (
                "dashscope" in llm_provider and
                hasattr(self.quick_thinking_llm, '__class__') and
                'OpenAI' in self.quick_thinking_llm.__class__.__name__
            )

            if using_dashscope_openai:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（阿里百炼OpenAI兼容模式）")
            elif "dashscope" in llm_provider or "阿里百炼" in self.config.get("llm_provider", ""):
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（阿里百炼原生模式）")
            elif "deepseek" in llm_provider:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（DeepSeek）")
            else:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师")

            # 所有LLM都使用标准分析师
            market_analyst = create_market_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            analyst_nodes["market"] = market_analyst
            self.all_agents.append(market_analyst)  # 注册agent到列表
            logger.debug(f"🔄 [AgentRegistry] 注册Market Analyst到停止信号列表")
            
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            social_analyst = create_social_media_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            analyst_nodes["social"] = social_analyst
            self.all_agents.append(social_analyst)  # 注册agent到列表
            logger.debug(f"🔄 [AgentRegistry] 注册Social Media Analyst到停止信号列表")
            
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        # News analyst - 独立的新闻分析师
        if "news" in selected_analysts:
            news_analyst = create_news_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            analyst_nodes["news"] = news_analyst
            self.all_agents.append(news_analyst)  # 注册agent到列表
            logger.debug(f"🔄 [AgentRegistry] 注册News Analyst到停止信号列表")
            
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]



        # Create researcher and manager nodes with consistent Msg Clear pattern
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        self.all_agents.append(bull_researcher_node)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Bull Researcher到停止信号列表")
        
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        self.all_agents.append(bear_researcher_node)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Bear Researcher到停止信号列表")
        
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        self.all_agents.append(research_manager_node)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Research Manager到停止信号列表")
        
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)
        self.all_agents.append(trader_node)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Trader到停止信号列表")

        # Create risk analysis nodes
        risky_analyst = create_risky_debator(self.quick_thinking_llm)
        self.all_agents.append(risky_analyst)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Risky Analyst到停止信号列表")
        
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        self.all_agents.append(neutral_analyst)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Neutral Analyst到停止信号列表")
        
        safe_analyst = create_safe_debator(self.quick_thinking_llm)
        self.all_agents.append(safe_analyst)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Safe Analyst到停止信号列表")
        
        risk_manager_node = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )
        self.all_agents.append(risk_manager_node)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Risk Manager到停止信号列表")
        
        # Create portfolio manager node
        portfolio_manager_node = create_portfolio_manager(
            self.deep_thinking_llm, self.portfolio_manager_memory
        )
        self.all_agents.append(portfolio_manager_node)  # 注册agent到列表
        logger.debug(f"🔄 [AgentRegistry] 注册Portfolio Manager到停止信号列表")
        
        logger.info(f"🛑 [AgentRegistry] 总共注册了{len(self.all_agents)}个agents到停止信号系统")
        
        # Create delete nodes for ALL agents (Linus: eliminate special cases)
        other_agent_delete_nodes = {
            "bull": create_msg_delete(),
            "bear": create_msg_delete(), 
            "research": create_msg_delete(),
            "trader": create_msg_delete(),
            "risky": create_msg_delete(),
            "neutral": create_msg_delete(),
            "safe": create_msg_delete(),
            "risk": create_msg_delete(),
            "portfolio": create_msg_delete()
        }

        # Create workflow
        workflow = StateGraph(WTAgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes with consistent Msg Clear pattern (Linus: symmetric data structure)
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Msg Clear Bull", other_agent_delete_nodes["bull"])
        
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Msg Clear Bear", other_agent_delete_nodes["bear"])
        
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Msg Clear Research", other_agent_delete_nodes["research"])
        
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Msg Clear Trader", other_agent_delete_nodes["trader"])
        
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Msg Clear Risky", other_agent_delete_nodes["risky"])
        
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Msg Clear Neutral", other_agent_delete_nodes["neutral"])
        
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Msg Clear Safe", other_agent_delete_nodes["safe"])
        
        workflow.add_node("Risk Judge", risk_manager_node)
        workflow.add_node("Msg Clear Risk", other_agent_delete_nodes["risk"])
        
        workflow.add_node("Portfolio Manager", portfolio_manager_node)
        workflow.add_node("Msg Clear Portfolio", other_agent_delete_nodes["portfolio"])

        # Define edges
        # Start with the first analyst
        first_analyst = selected_analysts[0]
        workflow.add_edge(START, f"{first_analyst.capitalize()} Analyst")

        # Connect analysts in sequence
        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # Add conditional edges for current analyst
            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

            # Connect to next analyst or to Bull Researcher if this is the last analyst
            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i+1].capitalize()} Analyst"
                logger.info(f"➡️ [图构建] 添加边: {current_clear} -> {next_analyst}")
                workflow.add_edge(current_clear, next_analyst)
            else:
                logger.info(f"➡️ [图构建] 添加边: {current_clear} -> Bull Researcher (最后一个分析师)")
                workflow.add_edge(current_clear, "Bull Researcher")

        # 显式确保News到Bull的连接（Linus: 消除特殊情况，确保关键路径）
        if "news" in selected_analysts:
            logger.info("➡️ [图构建] 显式确保: Msg Clear News -> Bull Researcher")
            workflow.add_edge("Msg Clear News", "Bull Researcher")
            # 🔧 添加关键路径确认日志
            logger.info("✅ [图构建] 关键修复：Phase 1 → Phase 2 边已添加，确保流程不会提前结束")
        
        # Bull/Bear debate pattern (修复路由逻辑)
        workflow.add_edge("Bull Researcher", "Msg Clear Bull")
        workflow.add_edge("Bear Researcher", "Msg Clear Bear")
        
        # Msg Clear节点的路由
        workflow.add_conditional_edges(
            "Msg Clear Bull",
            self.conditional_logic.should_continue_after_bull_clear,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        
        workflow.add_conditional_edges(
            "Msg Clear Bear",
            self.conditional_logic.should_continue_after_bear_clear,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Msg Clear Research")
        workflow.add_edge("Msg Clear Research", "Trader")
        workflow.add_edge("Trader", "Msg Clear Trader")
        workflow.add_edge("Msg Clear Trader", "Risky Analyst")
        
        # Risk debate pattern (restore Msg Clear flow for frontend state management)
        # Risky Analyst decides: continue debate or go to Msg Clear Risky
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risky,
            {
                "Safe Analyst": "Safe Analyst",
                "Msg Clear Risky": "Msg Clear Risky",  # Restore Msg Clear flow
            },
        )
        
        # Safe Analyst decides: continue debate or go to Msg Clear Safe
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_safe,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Msg Clear Safe": "Msg Clear Safe",  # Restore Msg Clear flow
            },
        )
        
        # Neutral Analyst decides: continue debate or go to Msg Clear Neutral
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_neutral,
            {
                "Risky Analyst": "Risky Analyst",
                "Msg Clear Neutral": "Msg Clear Neutral",  # Restore Msg Clear flow
            },
        )
        
        # Msg Clear nodes route based on risk analysis state
        workflow.add_conditional_edges(
            "Msg Clear Risky",
            self.conditional_logic.should_continue_after_risky_clear,
            {
                "Safe Analyst": "Safe Analyst",  # Continue analysis
                "Risk Judge": "Risk Judge",  # End analysis
            },
        )
        
        workflow.add_conditional_edges(
            "Msg Clear Safe",
            self.conditional_logic.should_continue_after_safe_clear,
            {
                "Neutral Analyst": "Neutral Analyst",  # Continue analysis
                "Risk Judge": "Risk Judge",  # End analysis
            },
        )
        
        workflow.add_conditional_edges(
            "Msg Clear Neutral",
            self.conditional_logic.should_continue_after_neutral_clear,
            {
                "Risky Analyst": "Risky Analyst",  # Continue analysis
                "Risk Judge": "Risk Judge",  # End analysis
            },
        )

        workflow.add_edge("Risk Judge", "Msg Clear Risk")
        workflow.add_edge("Msg Clear Risk", "Portfolio Manager")
        workflow.add_edge("Portfolio Manager", "Msg Clear Portfolio")
        workflow.add_edge("Msg Clear Portfolio", END)

        # 🔧 关键修复：验证图编译前的关键边
        logger.info("🔍 [图验证] 开始验证关键路径边...")
        
        # 验证Phase 1到Phase 2的关键路径
        if "news" in selected_analysts:
            logger.info("✅ [图验证] Phase 1 → Phase 2 路径: Msg Clear News → Bull Researcher")
        
        # 验证Phase 2内部路径  
        logger.info("✅ [图验证] Phase 2 内部路径: Bull Researcher → Msg Clear Bull")
        logger.info("✅ [图验证] Phase 2 内部路径: Bear Researcher → Msg Clear Bear")
        
        # 验证Phase 2到Phase 3的路径
        logger.info("✅ [图验证] Phase 2 → Phase 3 路径: Research Manager → Trader")
        
        logger.info("🏗️ [图构建] 开始编译图，包含关键修复...")

        # Compile and return
        compiled_graph = workflow.compile()
        
        logger.info("✅ [图构建] 图编译完成，包含Phase 1→2的关键修复")
        return compiled_graph
