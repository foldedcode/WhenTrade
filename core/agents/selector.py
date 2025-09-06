"""
自动Agent选择器
根据市场类型和分析领域自动选择合适的agents
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Type
from abc import ABC

from .base import BaseAnalyst
from core.business.market_config import (
    MarketType, AnalysisDomain, MarketConfig, 
    AnalysisStage, get_market_config
)
from .factory import DynamicAgentFactory, DynamicAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent注册表"""
    
    def __init__(self):
        # 预设agents映射：领域 -> agent类列表
        self._preset_agents: Dict[AnalysisDomain, List[Type[BaseAnalyst]]] = {}
        # 特殊角色agents映射：角色名 -> agent类
        self._role_agents: Dict[str, Type[BaseAnalyst]] = {}
        # 已注册的所有agent类
        self._all_agents: Dict[str, Type[BaseAnalyst]] = {}
        
    def register_preset_agent(
        self, 
        agent_class: Type[BaseAnalyst], 
        domains: List[AnalysisDomain]
    ):
        """注册预设agent到特定领域"""
        agent_name = agent_class.__name__
        self._all_agents[agent_name] = agent_class
        
        for domain in domains:
            if domain not in self._preset_agents:
                self._preset_agents[domain] = []
            self._preset_agents[domain].append(agent_class)
            
    def register_role_agent(self, role: str, agent_class: Type[BaseAnalyst]):
        """注册特定角色的agent"""
        agent_name = agent_class.__name__
        self._all_agents[agent_name] = agent_class
        self._role_agents[role] = agent_class
        
    def get_agents_for_domain(self, domain: AnalysisDomain) -> List[Type[BaseAnalyst]]:
        """获取特定领域的预设agents"""
        return self._preset_agents.get(domain, [])
        
    def get_agent_by_role(self, role: str) -> Optional[Type[BaseAnalyst]]:
        """获取特定角色的agent"""
        return self._role_agents.get(role)
        
    def get_agent_by_name(self, name: str) -> Optional[Type[BaseAnalyst]]:
        """根据名称获取agent类"""
        return self._all_agents.get(name)


class AutoAgentSelector:
    """自动Agent选择器"""
    
    def __init__(self, agent_registry: AgentRegistry, llm_factory: Any):
        self.registry = agent_registry
        self.llm_factory = llm_factory
        self._selection_cache = {}
        self.dynamic_factory = DynamicAgentFactory(llm_factory)
        
    async def auto_select_agents(
        self,
        market_type: MarketType,
        selected_domains: List[AnalysisDomain],
        analysis_depth: int = 3,
        custom_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[BaseAnalyst]]:
        """
        根据市场类型和选择的分析领域自动配置agents
        
        返回格式：
        {
            "stage_id": [agent1, agent2, ...],
            ...
        }
        """
        # 获取市场配置
        market_config = get_market_config(market_type)
        
        # 构建缓存键
        cache_key = f"{market_type.value}:{':'.join(d.value for d in selected_domains)}:{analysis_depth}"
        if cache_key in self._selection_cache:
            logger.debug(f"使用缓存的agent选择方案: {cache_key}")
            return self._selection_cache[cache_key]
        
        # 为每个分析阶段选择agents
        stage_agents = {}
        
        for stage in market_config.analysis_stages:
            agents = await self._select_agents_for_stage(
                stage=stage,
                market_type=market_type,
                selected_domains=selected_domains,
                analysis_depth=analysis_depth,
                custom_requirements=custom_requirements
            )
            
            if agents:
                stage_agents[stage.id] = agents
                logger.info(f"阶段 {stage.name} 分配了 {len(agents)} 个agents")
        
        # 缓存选择结果
        self._selection_cache[cache_key] = stage_agents
        
        return stage_agents
        
    async def _select_agents_for_stage(
        self,
        stage: AnalysisStage,
        market_type: MarketType,
        selected_domains: List[AnalysisDomain],
        analysis_depth: int,
        custom_requirements: Optional[Dict[str, Any]] = None
    ) -> List[BaseAnalyst]:
        """为特定阶段选择agents"""
        agents = []
        
        # 1. 处理特定逻辑要求的agents
        if stage.specific_logic:
            for role in stage.specific_logic.participants:
                agent_class = self.registry.get_agent_by_role(role)
                if agent_class:
                    llm = self.llm_factory.create_llm()
                    agent = agent_class(llm)
                    agents.append(agent)
                    logger.debug(f"为角色 {role} 创建agent: {agent.name}")
                else:
                    logger.warning(f"未找到角色 {role} 的agent实现")
        
        # 2. 根据必需领域选择agents
        for domain in stage.required_domains:
            if domain in selected_domains:
                domain_agents = self.registry.get_agents_for_domain(domain)
                for agent_class in domain_agents[:1]:  # 每个领域选择一个
                    llm = self.llm_factory.create_llm()
                    agent = agent_class(llm)
                    agents.append(agent)
                    logger.debug(f"为领域 {domain.value} 创建agent: {agent.name}")
        
        # 3. 根据可选领域和深度选择额外agents
        if analysis_depth >= 3 and len(agents) < stage.max_agents:
            for domain in stage.optional_domains:
                if domain in selected_domains and len(agents) < stage.max_agents:
                    domain_agents = self.registry.get_agents_for_domain(domain)
                    for agent_class in domain_agents[:1]:
                        llm = self.llm_factory.create_llm()
                        agent = agent_class(llm)
                        agents.append(agent)
                        logger.debug(f"为可选领域 {domain.value} 创建agent: {agent.name}")
        
        # 4. 确保满足最小agent数量要求
        if len(agents) < stage.min_agents:
            # 从已选择的领域中补充agents
            for domain in selected_domains:
                if len(agents) >= stage.min_agents:
                    break
                domain_agents = self.registry.get_agents_for_domain(domain)
                for agent_class in domain_agents:
                    if not any(isinstance(a, agent_class) for a in agents):
                        llm = self.llm_factory.create_llm()
                        agent = agent_class(llm)
                        agents.append(agent)
                        logger.debug(f"补充agent以满足最小数量: {agent.name}")
                        if len(agents) >= stage.min_agents:
                            break
        
        # 5. 去重（避免同一个agent类被多次实例化）
        unique_agents = []
        seen_types = set()
        for agent in agents:
            agent_type = type(agent).__name__
            if agent_type not in seen_types:
                seen_types.add(agent_type)
                unique_agents.append(agent)
        
        return unique_agents
        
    def get_recommended_domains(
        self, 
        market_type: MarketType,
        user_goal: Optional[str] = None
    ) -> List[AnalysisDomain]:
        """根据市场类型推荐分析领域"""
        market_config = get_market_config(market_type)
        
        # 获取所有必需的领域
        required_domains = market_config.get_required_domains()
        
        # 根据市场类型添加推荐领域
        recommended = list(required_domains)
        
        if market_type == MarketType.STOCK_US:
            # 美股推荐添加估值和行业分析
            recommended.extend([
                AnalysisDomain.VALUATION,
                AnalysisDomain.SECTOR
            ])
        elif market_type == MarketType.CRYPTO:
            # 加密货币推荐添加链上和DeFi分析
            recommended.extend([
                AnalysisDomain.ONCHAIN,
                AnalysisDomain.DEFI
            ])
        elif market_type == MarketType.POLYMARKET:
            # 预测市场推荐添加概率和赔率分析
            recommended.extend([
                AnalysisDomain.PROBABILITY,
                AnalysisDomain.ODDS
            ])
        
        # 去重并返回
        return list(set(recommended))
        
    def estimate_agent_count(
        self,
        market_type: MarketType,
        selected_domains: List[AnalysisDomain],
        analysis_depth: int = 3
    ) -> int:
        """估算将创建的agent数量"""
        market_config = get_market_config(market_type)
        total_agents = 0
        
        for stage in market_config.analysis_stages:
            # 特定逻辑的agents
            if stage.specific_logic:
                total_agents += len(stage.specific_logic.participants)
            
            # 必需领域的agents
            for domain in stage.required_domains:
                if domain in selected_domains:
                    total_agents += 1
            
            # 根据深度添加可选agents
            if analysis_depth >= 3:
                optional_count = min(
                    len([d for d in stage.optional_domains if d in selected_domains]),
                    stage.max_agents - total_agents
                )
                total_agents += max(0, optional_count)
            
            # 确保满足最小要求
            total_agents = max(total_agents, stage.min_agents)
        
        return total_agents
        
    async def create_dynamic_agents_for_scenario(
        self,
        scenario: str,
        market_type: MarketType,
        analysis_goals: List[str],
        existing_agents: Optional[List[BaseAnalyst]] = None
    ) -> List[BaseAnalyst]:
        """
        根据场景动态创建补充agents
        
        Args:
            scenario: 分析场景描述
            market_type: 市场类型
            analysis_goals: 分析目标
            existing_agents: 已有的agents列表
            
        Returns:
            动态创建的agents列表
        """
        # 获取推荐的动态agents
        recommendations = self.dynamic_factory.recommend_agents_for_scenario(
            scenario=scenario,
            market_type=market_type.value,
            analysis_goals=analysis_goals
        )
        
        # 过滤掉与现有agents重复的类型
        existing_types = set()
        if existing_agents:
            for agent in existing_agents:
                if hasattr(agent, 'template'):
                    existing_types.add(agent.template.template_id)
                else:
                    existing_types.add(type(agent).__name__.lower())
        
        # 创建推荐的agents
        dynamic_agents = []
        for rec in recommendations:
            template_id = rec.get("template_id")
            
            # 检查是否已存在类似agent
            if template_id in existing_types:
                logger.debug(f"跳过已存在的agent类型: {template_id}")
                continue
                
            # 创建动态agent
            agent = self.dynamic_factory.create_agent_from_template(
                template_id=template_id,
                custom_config=rec.get("custom_config"),
                agent_id=f"dynamic_{template_id}_{len(dynamic_agents)}"
            )
            
            if agent:
                dynamic_agents.append(agent)
                logger.info(f"创建动态agent: {agent.name} (原因: {rec.get('reason', '未知')})")
                
        return dynamic_agents
        
    async def enhance_selection_with_dynamic_agents(
        self,
        stage_agents: Dict[str, List[BaseAnalyst]],
        scenario: Optional[str] = None,
        market_type: Optional[MarketType] = None,
        enable_dynamic: bool = True
    ) -> Dict[str, List[BaseAnalyst]]:
        """
        使用动态agents增强现有选择
        
        Args:
            stage_agents: 现有的阶段agents配置
            scenario: 场景描述
            market_type: 市场类型
            enable_dynamic: 是否启用动态创建
            
        Returns:
            增强后的agents配置
        """
        if not enable_dynamic or not scenario:
            return stage_agents
            
        # 统计所有现有agents
        all_existing_agents = []
        for agents in stage_agents.values():
            all_existing_agents.extend(agents)
            
        # 根据场景创建动态agents
        dynamic_agents = await self.create_dynamic_agents_for_scenario(
            scenario=scenario,
            market_type=market_type or MarketType.STOCK_US,
            analysis_goals=["深度分析", "专业评估"],
            existing_agents=all_existing_agents
        )
        
        if dynamic_agents:
            # 将动态agents添加到合适的阶段
            # 这里简单地添加到第一个有agents的阶段
            for stage_id, agents in stage_agents.items():
                if agents:
                    stage_agents[stage_id].extend(dynamic_agents)
                    logger.info(f"向阶段{stage_id}添加了{len(dynamic_agents)}个动态agents")
                    break
                    
        return stage_agents


# 创建全局agent注册表实例
global_agent_registry = AgentRegistry()


def register_existing_agents():
    """注册现有的agents到注册表"""
    from .agents import (
        TechnicalAnalyst, FundamentalAnalyst, 
        SentimentAnalyst, RiskAnalyst, MarketAnalyst
    )
    from .process_agents import (
        BullishResearcher, BearishResearcher, 
        RiskManager, PortfolioManager
    )
    from .crypto_agents import (
        OnChainAnalyst, DefiAnalyst, WhaleTracker
    )
    from .prediction_agents import (
        EventAnalyst, BayesianAnalyst, OddsAnalyst
    )
    
    # 注册现有的分析师
    global_agent_registry.register_preset_agent(
        TechnicalAnalyst, 
        [AnalysisDomain.TECHNICAL]
    )
    global_agent_registry.register_preset_agent(
        FundamentalAnalyst,
        [AnalysisDomain.FUNDAMENTAL, AnalysisDomain.VALUATION]
    )
    global_agent_registry.register_preset_agent(
        SentimentAnalyst,
        [AnalysisDomain.SENTIMENT]
    )
    global_agent_registry.register_preset_agent(
        RiskAnalyst,
        [AnalysisDomain.RISK]
    )
    global_agent_registry.register_preset_agent(
        MarketAnalyst,
        [AnalysisDomain.MARKET, AnalysisDomain.SECTOR]
    )
    
    # 注册加密货币特定agents
    global_agent_registry.register_preset_agent(
        OnChainAnalyst,
        [AnalysisDomain.ONCHAIN]
    )
    global_agent_registry.register_preset_agent(
        DefiAnalyst,
        [AnalysisDomain.DEFI]
    )
    global_agent_registry.register_preset_agent(
        WhaleTracker,
        [AnalysisDomain.ONCHAIN]  # 巨鲸追踪也属于链上分析
    )
    
    # 注册预测市场特定agents
    global_agent_registry.register_preset_agent(
        EventAnalyst,
        [AnalysisDomain.EVENT]
    )
    global_agent_registry.register_preset_agent(
        BayesianAnalyst,
        [AnalysisDomain.PROBABILITY]
    )
    global_agent_registry.register_preset_agent(
        OddsAnalyst,
        [AnalysisDomain.ODDS]
    )
    
    # 注册通用流程agents作为角色
    global_agent_registry.register_role_agent("BullishResearcher", BullishResearcher)
    global_agent_registry.register_role_agent("BearishResearcher", BearishResearcher)
    global_agent_registry.register_role_agent("RiskManager", RiskManager)
    global_agent_registry.register_role_agent("PortfolioManager", PortfolioManager)
    
    # 用于加密货币市场的多空角色
    global_agent_registry.register_role_agent("LongTrader", BullishResearcher)  # 复用看涨研究员
    global_agent_registry.register_role_agent("ShortTrader", BearishResearcher)  # 复用看跌研究员
    
    # 用于预测市场的专门角色
    global_agent_registry.register_role_agent("YesBacker", BullishResearcher)  # YES支持者
    global_agent_registry.register_role_agent("NoBacker", BearishResearcher)   # NO支持者