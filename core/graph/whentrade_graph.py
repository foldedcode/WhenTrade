# WhenTrade/graph/whentrade_graph.py

import os
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from core.llm_adapters import OpenAICompatibleBase, ChatDeepSeek

from langgraph.prebuilt import ToolNode

from core.agents import *
from core.default_config import WHENTRADE_CONFIG
from core.agents.utils.memory import FinancialSituationMemory

# 导入日志模块
from core.utils.logging_manager import get_logger
logger = get_logger('agents')
from core.agents.utils.agent_states import (
    WTAgentState,
    InvestDebateState,
    RiskDebateState,
)
from core.dataflows.interface import set_config

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class WhenTradeGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news"],
        config: Dict[str, Any] = None,
        analysis_depth: int = 1,
        selected_tools: List[str] = None,
        selected_data_sources: List[str] = None,
        websocket=None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            config: Configuration dictionary. If None, uses default config
            analysis_depth: Depth of analysis (1-5), controls debate rounds
            selected_tools: List of user-selected tools to use in analysis
            selected_data_sources: List of user-selected data sources
            websocket: WebSocket connection for real-time tool status notifications
        """
        self.config = config or WHENTRADE_CONFIG
        self.analysis_depth = analysis_depth
        self.selected_tools = selected_tools or []
        self.selected_data_sources = selected_data_sources or []
        self.websocket = websocket  # 添加WebSocket支持
        self.stop_event = None  # 添加停止事件支持
        self.all_agents = []  # 存储所有创建的agents
        
        # Log工具配置以便调试 (Linus: use i18n for system-level messages)
        from core.i18n.messages import get_message
        init_msg = get_message('tool_config_init', 'zh-CN')  # Default to Chinese for system logs
        logger.info(f"🔧 [WhenTradeGraph] {init_msg}: tools={len(self.selected_tools)}个, sources={len(self.selected_data_sources)}个")
        if self.selected_tools:
            tools_label = get_message('selected_tools_label', 'zh-CN')
            logger.info(f"   {tools_label}: {self.selected_tools}")
        if self.selected_data_sources:
            sources_label = get_message('selected_data_sources_label', 'zh-CN')
            logger.info(f"   {sources_label}: {self.selected_data_sources}")

        # Update the interface's config
        set_config(self.config)
        
        # 检测LLM是否支持工具调用
        self.supports_tool_calling = self._check_tool_calling_support()
        if not self.supports_tool_calling:
            logger.warning(f"⚠️ [WhenTradeGraph] {self.config['llm_provider']}不支持工具调用，将使用直接执行模式")

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs
        if self.config["llm_provider"].lower() == "openai":
            # 根据backend_url判断实际的提供商并获取相应的API密钥
            backend_url = self.config.get("backend_url", "")
            api_key = None
            
            if "moonshot" in backend_url or "kimi" in backend_url.lower():
                # Kimi/Moonshot API - 不支持工具调用
                api_key = os.getenv('KIMI_API_KEY')
                if not api_key:
                    raise ValueError("使用Kimi需要设置KIMI_API_KEY环境变量")
                logger.info(f"🌙 使用Kimi API密钥: {api_key[:20]}...")
                logger.warning(f"⚠️ Kimi/Moonshot不支持工具调用，将使用直接执行模式")
            elif "deepseek" in backend_url:
                # DeepSeek API
                api_key = os.getenv('DEEPSEEK_API_KEY')
                if not api_key:
                    raise ValueError("使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量")
                logger.info(f"🔍 使用DeepSeek API密钥: {api_key[:20]}...")
            else:
                # 标准OpenAI API
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("使用OpenAI需要设置OPENAI_API_KEY环境变量")
                logger.info(f"🤖 使用OpenAI API密钥: {api_key[:20]}...")
            
            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"], 
                base_url=self.config["backend_url"],
                api_key=api_key
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"], 
                base_url=self.config["backend_url"],
                api_key=api_key
            )
        elif self.config["llm_provider"] == "openrouter":
            # OpenRouter支持：优先使用OPENROUTER_API_KEY，否则使用OPENAI_API_KEY
            openrouter_api_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
            if not openrouter_api_key:
                raise ValueError("使用OpenRouter需要设置OPENROUTER_API_KEY或OPENAI_API_KEY环境变量")

            logger.info(f"🌐 [OpenRouter] 使用API密钥: {openrouter_api_key[:20]}...")

            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                base_url=self.config["backend_url"],
                api_key=openrouter_api_key
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                base_url=self.config["backend_url"],
                api_key=openrouter_api_key
            )
        elif self.config["llm_provider"] == "deepseek":
            # DeepSeek专用处理
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                raise ValueError("使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量")
            
            logger.info(f"🔍 使用DeepSeek API密钥: {api_key[:20]}...")
            
            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                base_url=self.config["backend_url"],
                api_key=api_key
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                base_url=self.config["backend_url"],
                api_key=api_key
            )
        elif self.config["llm_provider"] == "ollama":
            # Ollama不需要API密钥，但ChatOpenAI需要一个假的密钥来通过验证
            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"], 
                base_url=self.config["backend_url"],
                api_key="ollama"  # Ollama不需要真实的API密钥
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"], 
                base_url=self.config["backend_url"],
                api_key="ollama"  # Ollama不需要真实的API密钥
            )
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            google_api_key = os.getenv('GOOGLE_API_KEY')
            self.deep_thinking_llm = ChatGoogleGenerativeAI(
                model=self.config["deep_think_llm"],
                google_api_key=google_api_key,
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatGoogleGenerativeAI(
                model=self.config["quick_think_llm"],
                google_api_key=google_api_key,
                temperature=0.1,
                max_tokens=2000
            )
        elif (self.config["llm_provider"].lower() == "dashscope" or
              self.config["llm_provider"].lower() == "alibaba" or
              "dashscope" in self.config["llm_provider"].lower() or
              "阿里百炼" in self.config["llm_provider"]):
            # 使用 OpenAI 兼容适配器，支持原生 Function Calling
            logger.info(f"🔧 使用阿里百炼 OpenAI 兼容适配器 (支持原生工具调用)")
            # DashScope已删除，使用默认LLM
            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                temperature=0.1,
                max_tokens=2000
            )
        elif (self.config["llm_provider"].lower() == "deepseek" or
              "deepseek" in self.config["llm_provider"].lower()):
            # DeepSeek V3配置 - 使用支持token统计的适配器
            from core.llm_adapters.deepseek_adapter import ChatDeepSeek


            deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
            if not deepseek_api_key:
                raise ValueError("使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量")

            deepseek_base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

            # 使用支持token统计的DeepSeek适配器
            self.deep_thinking_llm = ChatDeepSeek(
                model=self.config["deep_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatDeepSeek(
                model=self.config["quick_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=0.1,
                max_tokens=2000
                )

            logger.info(f"✅ [DeepSeek] 已启用token统计功能")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
        # Phase 2: 创建Toolkit，传递selected_tools和selected_data_sources参数
        self.toolkit = Toolkit(
            selected_tools=self.selected_tools,
            selected_data_sources=self.selected_data_sources,
            stop_event=self.stop_event,
            websocket=self.websocket
        )
        # 将工具调用支持标记添加到toolkit
        self.toolkit.supports_tool_calling = self.supports_tool_calling
        logger.info(f"🔧 [Toolkit] 创建时包含 {len(self.selected_tools)} 个工具，{len(self.selected_data_sources)} 个数据源")

        # Initialize memories (如果启用)
        memory_enabled = self.config.get("memory_enabled", True)
        if memory_enabled:
            # 使用单例ChromaDB管理器，避免并发创建冲突
            self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
            self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
            self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
            self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
            self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)
            self.portfolio_manager_memory = FinancialSituationMemory("portfolio_manager_memory", self.config)
        else:
            # 创建空的内存对象
            self.bull_memory = None
            self.bear_memory = None
            self.trader_memory = None
            self.invest_judge_memory = None
            self.risk_manager_memory = None
            self.portfolio_manager_memory = None

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components with analysis depth
        # 使用analysis_depth同时控制第二阶段和第四阶段的辩论轮数（与示例项目一致）
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.analysis_depth,  # 第二阶段：投资辩论轮数
            max_risk_discuss_rounds=self.analysis_depth  # 第四阶段：风险评估轮数
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.portfolio_manager_memory,
            self.conditional_logic,
            self.config,
            getattr(self, 'react_llm', None),
            self.all_agents  # 传递agents列表引用，关键修复！
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)
    
    def _check_tool_calling_support(self) -> bool:
        """检测LLM是否支持工具调用
        
        Returns:
            bool: True如果支持工具调用，False否则
        """
        provider = self.config.get("llm_provider", "").lower()
        backend_url = self.config.get("backend_url", "").lower()
        
        # 已知不支持工具调用的提供商
        no_tool_calling_providers = {
            "kimi": False,
            "moonshot": False,
            # DeepSeek支持工具调用（默认支持）
            # OpenAI系支持工具调用（默认支持）
        }
        
        # 检查backend_url
        if "moonshot" in backend_url or "kimi" in backend_url:
            return False
        
        # 检查provider名称
        for provider_name, supports in no_tool_calling_providers.items():
            if provider_name in provider:
                return supports
        
        # 默认假设支持（OpenAI、DeepSeek等）
        return True

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources.
        
        Phase 2: 根据用户选择的工具动态创建工具节点
        """
        # 如果用户选择了工具，使用动态工具节点
        if self.selected_tools:
            logger.info(f"🔧 [ToolNodes] 根据用户选择创建动态工具节点")
            return self._create_dynamic_tool_nodes()
        
        def _ensure_docstring(func, default_desc: str = ""):
            """确保函数有docstring"""
            if not hasattr(func, '__doc__') or not func.__doc__:
                func.__doc__ = default_desc or "工具函数"
            return func
        
        # 否则使用默认工具节点
        logger.info(f"🔧 [ToolNodes] 使用默认工具节点")
        return {
            "market": ToolNode(
                [
                    # 统一工具
                    _ensure_docstring(self.toolkit.get_stock_market_data_unified, "统一股票市场数据获取"),
                    # online tools
                    _ensure_docstring(self.toolkit.get_YFin_data_online, "Yahoo Finance在线数据"),
                    _ensure_docstring(self.toolkit.get_stockstats_indicators_report_online, "在线技术指标报告"),
                    # offline tools
                    _ensure_docstring(self.toolkit.get_YFin_data, "Yahoo Finance数据"),
                    _ensure_docstring(self.toolkit.get_stockstats_indicators_report, "技术指标报告"),
                ]
            ),
            "social": ToolNode(
                [
                    # online tools
                    _ensure_docstring(self.toolkit.get_stock_news_openai, "OpenAI股票新闻分析"),
                    # offline tools
                    _ensure_docstring(self.toolkit.get_reddit_stock_info, "Reddit股票信息"),
                ]
            ),
            "news": ToolNode(
                [
                    # 新闻分析工具
                    _ensure_docstring(self.toolkit.get_stock_news_openai, "股票新闻OpenAI分析"),
                ]
            ),
        }
    
    def _create_dynamic_tool_nodes(self) -> Dict[str, ToolNode]:
        """Phase 2: 根据用户选择的工具动态创建工具节点"""
        from core.services.tools.tool_registry import ToolRegistry
        
        # 工具分类映射
        tool_categories = {
            'market': [],
            'social': [],
            'news': []
        }
        
        def _ensure_docstring(func, tool_id: str, default_name: str = ""):
            """确保函数有docstring，如果没有则添加默认docstring"""
            if not hasattr(func, '__doc__') or not func.__doc__:
                func.__doc__ = f"{default_name or tool_id} - 工具函数"
            return func
        
        # 根据选择的工具ID获取对应的函数
        for tool_id in self.selected_tools:
            # 查找工具属于哪个分类
            for category, tools in ToolRegistry.TOOL_REGISTRY.items():
                if tool_id in tools:
                    tool_info = tools[tool_id]
                    tool_func = getattr(self.toolkit, f"tool_{tool_id}", None)
                    
                    if not tool_func:
                        # 如果动态方法不存在，尝试使用原始函数
                        tool_func = tool_info['function']
                    
                    # 确保函数有docstring
                    tool_func = _ensure_docstring(tool_func, tool_id, tool_info.get('name', ''))
                    
                    # 根据工具类别分配到相应的节点
                    if category == 'technical':
                        tool_categories['market'].append(tool_func)
                    elif category == 'sentiment':
                        # sentiment工具可以分配给social和news
                        if 'news' in tool_id.lower() or 'finnhub' in tool_id.lower():
                            tool_categories['news'].append(tool_func)
                        else:
                            tool_categories['social'].append(tool_func)
                    
                    logger.info(f"📌 [ToolNodes] 工具 {tool_id} 分配到 {category} 节点")
                    break
        
        # 创建工具节点
        nodes = {}
        for node_name, tools in tool_categories.items():
            if tools:
                nodes[node_name] = ToolNode(tools)
                logger.info(f"✅ [ToolNodes] 创建 {node_name} 节点，包含 {len(tools)} 个工具")
        
        # 如果某个节点没有工具，使用默认的最小工具集
        if not nodes.get('market'):
            default_tool = _ensure_docstring(self.toolkit.get_stock_market_data_unified, 'market_data', '股票市场数据')
            nodes['market'] = ToolNode([default_tool])
        if not nodes.get('social'):
            default_tool = _ensure_docstring(self.toolkit.__class__.get_reddit_stock_info, 'reddit_info', 'Reddit股票信息')
            nodes['social'] = ToolNode([default_tool])
        if not nodes.get('news'):
            default_tool = _ensure_docstring(self.toolkit.get_stock_news_openai, 'stock_news', '股票新闻')
            nodes['news'] = ToolNode([default_tool])
        
        return nodes

    def propagate(self, company_name, trade_date, language="zh-CN"):
        """Run the trading agents graph for a company on a specific date.
        
        Args:
            company_name: Company symbol to analyze
            trade_date: Date for analysis
            language: Language preference for all generated messages (default: zh-CN)
        """

        # 添加详细的接收日志
        logger.debug(f"🔍 [GRAPH DEBUG] ===== WhenTradeGraph.propagate 接收参数 =====")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的company_name: '{company_name}' (类型: {type(company_name)})")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的trade_date: '{trade_date}' (类型: {type(trade_date)})")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的language: '{language}' (类型: {type(language)})")

        # Linus: Create/update MessageGenerator with correct language (eliminate special cases)
        from core.i18n.message_generator import create_message_generator
        self.message_generator = create_message_generator(language)
        logger.debug(f"🌐 [GRAPH DEBUG] MessageGenerator initialized with language: {language}")
        
        self.ticker = company_name
        logger.debug(f"🔍 [GRAPH DEBUG] 设置self.ticker: '{self.ticker}'")

        # Initialize state with language support (Linus: language becomes part of core state)
        logger.debug(f"🔍 [GRAPH DEBUG] 创建初始状态，传递参数: company_name='{company_name}', trade_date='{trade_date}', language='{language}', tools={len(self.selected_tools)}个")
        init_agent_state = self.propagator.create_initial_state(
            company_name, 
            trade_date,
            language=language,  # Linus: eliminate special cases through data structure
            selected_tools=self.selected_tools,
            selected_data_sources=self.selected_data_sources
        )
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的company_of_interest: '{init_agent_state.get('company_of_interest', 'NOT_FOUND')}'")
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的trade_date: '{init_agent_state.get('trade_date', 'NOT_FOUND')}'")
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的language: '{init_agent_state.get('language', 'NOT_FOUND')}'")
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的selected_tools: {init_agent_state.get('selected_tools', [])}")
        args = self.propagator.get_graph_args()

        # Production mode without tracing
        final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal
        return final_state, self.process_signal(final_state["final_trade_decision"], company_name)

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/WhenTradeStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/WhenTradeStrategy_logs/full_states_log.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal, stock_symbol=None):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal, stock_symbol)
        
    def set_stop_event(self, stop_event):
        """设置停止事件并传递给所有agents和toolkit
        
        Args:
            stop_event: threading.Event对象，用于发送停止信号
        """
        self.stop_event = stop_event
        logger.info(f"🛑 [WhenTradeGraph] 设置停止事件，将传递给{len(self.all_agents)}个agents")
        
        # 传递给所有已创建的agents
        for agent in self.all_agents:
            if hasattr(agent, 'set_stop_event'):
                agent.set_stop_event(stop_event)
                logger.debug(f"   已设置停止事件: {type(agent).__name__}")
        
        # Linus: 传递给toolkit，确保API调用也能被中断
        if hasattr(self, 'toolkit') and self.toolkit:
            self.toolkit.stop_event = stop_event
            logger.debug("   已设置toolkit停止事件")
                
    def check_stop_signal(self) -> bool:
        """检查是否收到停止信号
        
        Returns:
            bool: 如果收到停止信号返回True
        """
        if self.stop_event and self.stop_event.is_set():
            logger.info("🛑 [WhenTradeGraph] 收到停止信号，中断执行")
            return True
        return False
