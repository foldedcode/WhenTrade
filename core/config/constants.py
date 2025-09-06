"""
配置常量定义 - 消除硬编码，统一管理
遵循Linus原则：通过数据结构消除特殊情况
"""

from enum import Enum
from typing import Dict, List


class MarketType(Enum):
    """市场类型枚举"""
    CRYPTO = "crypto"
    POLYMARKET = "polymarket"
    US_STOCK = "us"
    CHINA_STOCK = "china"
    HK_STOCK = "hk"


class AnalysisScope(Enum):
    """分析范围枚举"""
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    EVENT = "event"
    PROBABILITY = "probability"
    ODDS = "odds"


class AgentType(Enum):
    """智能体类型枚举"""
    MARKET_ANALYST = "market_analyst"
    SOCIAL_MEDIA_ANALYST = "social_media_analyst"
    CHINA_MARKET_ANALYST = "china_market_analyst"
    BULL_RESEARCHER = "bull_researcher"
    BEAR_RESEARCHER = "bear_researcher"
    RESEARCH_MANAGER = "research_manager"
    RISK_MANAGER = "risk_manager"
    PORTFOLIO_MANAGER = "portfolio_manager"
    TRADER = "trader"


class LLMProvider(Enum):
    """LLM提供商枚举"""
    DEEPSEEK = "deepseek"
    KIMI = "kimi"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DASHSCOPE = "dashscope"


# 市场配置映射
MARKET_CONFIG: Dict[MarketType, Dict] = {
    MarketType.CRYPTO: {
        "name": "加密货币",
        "supported_scopes": [
            AnalysisScope.TECHNICAL,
            AnalysisScope.SENTIMENT
        ],
        "default_agents": [
            AgentType.MARKET_ANALYST,
            AgentType.SOCIAL_MEDIA_ANALYST
        ],
        "data_sources": [
            "binance",
            "coingecko",
            "etherscan"
        ]
    },
    MarketType.POLYMARKET: {
        "name": "预测市场",
        "supported_scopes": [
            AnalysisScope.EVENT,
            AnalysisScope.PROBABILITY,
            AnalysisScope.ODDS
        ],
        "default_agents": [
            AgentType.SOCIAL_MEDIA_ANALYST
        ],
        "data_sources": [
            "polymarket_api",
            "google_news",
            "reuters"
        ]
    },
    MarketType.US_STOCK: {
        "name": "美股",
        "supported_scopes": [
            AnalysisScope.TECHNICAL,
            AnalysisScope.SENTIMENT
        ],
        "default_agents": [
            AgentType.MARKET_ANALYST
        ],
        "data_sources": [
            "yahoo_finance",
            "alpha_vantage",
            "finnhub"
        ]
    },
    MarketType.CHINA_STOCK: {
        "name": "A股",
        "supported_scopes": [
            AnalysisScope.TECHNICAL,
            AnalysisScope.SENTIMENT
        ],
        "default_agents": [
            AgentType.CHINA_MARKET_ANALYST
        ],
        "data_sources": [
            "tushare",
            "akshare",
            "eastmoney"
        ]
    }
}


# 分析深度配置
ANALYSIS_DEPTH_CONFIG = {
    1: {"name": "快速", "description": "基础分析，1-2分钟"},
    2: {"name": "标准", "description": "标准分析，3-5分钟"},
    3: {"name": "深度", "description": "深度分析，5-10分钟"},
    4: {"name": "专业", "description": "专业分析，10-15分钟"},
    5: {"name": "极致", "description": "全面分析，15分钟以上"}
}


# API端点配置
API_ENDPOINTS = {
    "auth": "/api/v1/auth",
    "analysis": "/api/v1/analysis",
    "agents": "/api/v1/agents",
    "data": "/api/v1/data",
    "tools": "/api/v1/tools",
    "cost": "/api/v1/cost",
    "settings": "/api/v1/settings"
}


# WebSocket事件类型
WS_EVENT_TYPES = {
    "connection": "connection",
    "auth": "auth",
    "analysis_start": "analysis.start",
    "analysis_progress": "analysis.progress",
    "analysis_complete": "analysis.complete",
    "analysis_error": "analysis.error",
    "agent_thought": "agent.thought",
    "agent_status": "agent.status",
    "tool_execution": "tool.execution",
    "error": "error"
}


# 默认配置值
DEFAULT_CONFIG = {
    "max_tokens": 4096,
    "temperature": 0.7,
    "timeout": 60,
    "retry_count": 3,
    "cache_ttl": 3600,
    "max_message_length": 10000,
    "max_history_size": 100
}


def get_market_scopes(market_type: MarketType) -> List[AnalysisScope]:
    """获取市场支持的分析范围"""
    config = MARKET_CONFIG.get(market_type, {})
    return config.get("supported_scopes", [])


def get_market_agents(market_type: MarketType) -> List[AgentType]:
    """获取市场默认的智能体"""
    config = MARKET_CONFIG.get(market_type, {})
    return config.get("default_agents", [])


def get_market_data_sources(market_type: MarketType) -> List[str]:
    """获取市场的数据源"""
    config = MARKET_CONFIG.get(market_type, {})
    return config.get("data_sources", [])