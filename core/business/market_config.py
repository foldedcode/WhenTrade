"""
市场配置管理系统
定义不同市场的分析领域、流程和配置
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class MarketType(str, Enum):
    """市场类型枚举"""
    CRYPTO = "crypto"      # 加密货币
    POLYMARKET = "polymarket"  # 预测市场
    FOREX = "forex"        # 外汇（预留）
    COMMODITY = "commodity"  # 大宗商品（预留）


class AnalysisDomain(str, Enum):
    """分析领域枚举"""
    # 通用领域
    TECHNICAL = "技术分析"
    FUNDAMENTAL = "基本面分析"
    SENTIMENT = "情绪分析"
    RISK = "风险管理"
    MARKET = "市场分析"
    
    # 加密货币特有
    ONCHAIN = "链上分析"
    DEFI = "DeFi分析"
    TOKENOMICS = "代币经济"
    
    # 预测市场特有
    EVENT = "事件分析"
    PROBABILITY = "概率分析"
    ODDS = "赔率分析"
    INFORMATION = "信息分析"


@dataclass
class StageLogic:
    """阶段特定逻辑配置"""
    type: str  # 逻辑类型：debate、consensus、vote等
    participants: List[str] = field(default_factory=list)  # 参与的agent角色
    rounds: int = 3  # 轮次（如辩论轮次）
    config: Dict[str, Any] = field(default_factory=dict)  # 额外配置


@dataclass
class AnalysisStage:
    """分析阶段定义"""
    id: str
    name: str
    description: str
    required_domains: List[AnalysisDomain]
    optional_domains: List[AnalysisDomain] = field(default_factory=list)
    specific_logic: Optional[StageLogic] = None
    min_agents: int = 1
    max_agents: int = 5


@dataclass
class MarketConfig:
    """市场配置"""
    market_type: MarketType
    name: str
    description: str
    available_domains: List[AnalysisDomain]
    analysis_stages: List[AnalysisStage]
    default_depth: int = 3
    special_features: List[str] = field(default_factory=list)
    
    def get_required_domains(self) -> List[AnalysisDomain]:
        """获取所有必需的分析领域"""
        domains = set()
        for stage in self.analysis_stages:
            domains.update(stage.required_domains)
        return list(domains)




# 加密货币市场配置
CRYPTO_CONFIG = MarketConfig(
    market_type=MarketType.CRYPTO,
    name="加密货币市场",
    description="加密货币和DeFi深度分析",
    available_domains=[
        AnalysisDomain.TECHNICAL,
        AnalysisDomain.SENTIMENT,
        AnalysisDomain.ONCHAIN,
        AnalysisDomain.DEFI,
        AnalysisDomain.TOKENOMICS,
        AnalysisDomain.RISK,
        AnalysisDomain.MARKET
    ],
    analysis_stages=[
        AnalysisStage(
            id="technical_onchain",
            name="技术与链上分析",
            description="价格技术分析结合链上数据",
            required_domains=[AnalysisDomain.TECHNICAL, AnalysisDomain.ONCHAIN],
            optional_domains=[AnalysisDomain.SENTIMENT],
            min_agents=2,
            max_agents=4
        ),
        AnalysisStage(
            id="defi_analysis",
            name="DeFi生态分析",
            description="协议健康度和收益机会分析",
            required_domains=[AnalysisDomain.DEFI],
            optional_domains=[AnalysisDomain.TOKENOMICS],
            min_agents=1,
            max_agents=2
        ),
        AnalysisStage(
            id="long_short_debate",
            name="多空辩论阶段",
            description="24小时市场的多空观点交锋",
            required_domains=[],
            specific_logic=StageLogic(
                type="debate",
                participants=["LongTrader", "ShortTrader"],
                rounds=3,
                config={"debate_topics": ["趋势持续性", "链上指标", "市场情绪"]}
            ),
            min_agents=2,
            max_agents=4
        ),
        AnalysisStage(
            id="risk_management",
            name="风险管理阶段",
            description="评估波动性和下行风险",
            required_domains=[AnalysisDomain.RISK],
            min_agents=1,
            max_agents=2
        )
    ],
    default_depth=3,
    special_features=["24小时市场监控", "链上实时数据", "DeFi收益优化", "巨鲸追踪"]
)


# Polymarket预测市场配置
POLYMARKET_CONFIG = MarketConfig(
    market_type=MarketType.POLYMARKET,
    name="预测市场",
    description="事件预测和概率分析",
    available_domains=[
        AnalysisDomain.EVENT,
        AnalysisDomain.PROBABILITY,
        AnalysisDomain.ODDS,
        AnalysisDomain.SENTIMENT,
        AnalysisDomain.INFORMATION,
        AnalysisDomain.RISK
    ],
    analysis_stages=[
        AnalysisStage(
            id="event_analysis",
            name="事件背景分析",
            description="深入分析事件背景和影响因素",
            required_domains=[AnalysisDomain.EVENT, AnalysisDomain.INFORMATION],
            min_agents=2,
            max_agents=3
        ),
        AnalysisStage(
            id="probability_modeling",
            name="概率建模阶段",
            description="使用多种方法估算事件概率",
            required_domains=[AnalysisDomain.PROBABILITY],
            optional_domains=[AnalysisDomain.ODDS],
            specific_logic=None,  # 将使用领域预设agents
            min_agents=2,
            max_agents=3
        ),
        AnalysisStage(
            id="sentiment_check",
            name="市场情绪校验",
            description="分析市场押注分布和情绪偏差",
            required_domains=[AnalysisDomain.SENTIMENT, AnalysisDomain.ODDS],
            min_agents=1,
            max_agents=2
        ),
        AnalysisStage(
            id="convergence_analysis",
            name="概率收敛分析",
            description="评估当前赔率是否合理",
            required_domains=[],
            specific_logic=None,  # 将使用领域预设agents
            min_agents=1,
            max_agents=1
        )
    ],
    default_depth=2,
    special_features=["事件时间线追踪", "信息可靠性评估", "概率实时更新", "套利机会发现"]
)


# 市场配置注册表
MARKET_CONFIGS: Dict[MarketType, MarketConfig] = {
    MarketType.CRYPTO: CRYPTO_CONFIG,
    MarketType.POLYMARKET: POLYMARKET_CONFIG
}


def get_market_config(market_type: MarketType) -> MarketConfig:
    """获取市场配置"""
    config = MARKET_CONFIGS.get(market_type)
    if not config:
        raise ValueError(f"未找到市场类型 {market_type} 的配置")
    return config


def get_available_markets() -> List[MarketConfig]:
    """获取所有可用市场配置"""
    return list(MARKET_CONFIGS.values())


def get_domains_for_market(market_type: MarketType) -> List[AnalysisDomain]:
    """获取特定市场的可用分析领域"""
    config = get_market_config(market_type)
    return config.available_domains