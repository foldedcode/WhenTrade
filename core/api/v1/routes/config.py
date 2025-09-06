"""
配置API端点 - 提供动态配置给前端
消除前端硬编码，实现配置集中管理
"""

from fastapi import APIRouter, Depends
from typing import Dict, List, Any
from pydantic import BaseModel

from core.config.constants import (
    MarketType,
    AnalysisScope,
    AgentType,
    LLMProvider,
    MARKET_CONFIG,
    ANALYSIS_DEPTH_CONFIG,
    API_ENDPOINTS,
    WS_EVENT_TYPES,
    DEFAULT_CONFIG,
    get_market_scopes,
    get_market_agents,
    get_market_data_sources
)

router = APIRouter(prefix="/config", tags=["configuration"])


class MarketConfigResponse(BaseModel):
    """市场配置响应"""
    market_type: str
    name: str
    supported_scopes: List[str]
    default_agents: List[str]
    data_sources: List[str]


class AnalysisScopeConfig(BaseModel):
    """分析范围配置"""
    id: str
    name: str
    description: str
    available_tools: List[Dict[str, str]]
    available_mcp: List[Dict[str, str]]
    available_data_sources: List[Dict[str, str]]


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    markets: List[MarketConfigResponse]
    analysis_depths: Dict[int, Dict[str, str]]
    llm_providers: List[str]
    api_endpoints: Dict[str, Any]
    ws_events: Dict[str, str]
    defaults: Dict[str, Any]


@router.get("/system", response_model=SystemConfigResponse)
async def get_system_config():
    """
    获取系统配置
    前端可以通过此接口获取所有配置，避免硬编码
    """
    # 构建市场配置
    markets = []
    for market_type in MarketType:
        config = MARKET_CONFIG.get(market_type, {})
        markets.append(MarketConfigResponse(
            market_type=market_type.value,
            name=config.get("name", market_type.value),
            supported_scopes=[s.value for s in config.get("supported_scopes", [])],
            default_agents=[a.value for a in config.get("default_agents", [])],
            data_sources=config.get("data_sources", [])
        ))
    
    # LLM提供商列表
    llm_providers = [provider.value for provider in LLMProvider]
    
    return SystemConfigResponse(
        markets=markets,
        analysis_depths=ANALYSIS_DEPTH_CONFIG,
        llm_providers=llm_providers,
        api_endpoints=API_ENDPOINTS,
        ws_events=WS_EVENT_TYPES,
        defaults=DEFAULT_CONFIG
    )


@router.get("/markets/{market_type}", response_model=MarketConfigResponse)
async def get_market_config(market_type: str):
    """
    获取特定市场的配置
    
    Args:
        market_type: 市场类型（crypto, polymarket, us, china等）
    """
    try:
        market_enum = MarketType(market_type)
    except ValueError:
        # 如果市场类型无效，返回默认的crypto配置
        market_enum = MarketType.CRYPTO
    
    config = MARKET_CONFIG.get(market_enum, {})
    
    return MarketConfigResponse(
        market_type=market_enum.value,
        name=config.get("name", market_enum.value),
        supported_scopes=[s.value for s in config.get("supported_scopes", [])],
        default_agents=[a.value for a in config.get("default_agents", [])],
        data_sources=config.get("data_sources", [])
    )


@router.get("/analysis-tools/{scope}")
async def get_scope_tools(scope: str):
    """
    获取分析范围的可用工具
    
    Args:
        scope: 分析范围 (technical, sentiment, etc.)
    """
    from core.services.tools.tool_registry import ToolRegistry
    
    tools = ToolRegistry.get_scope_tools(scope)
    
    # 返回包含 display_name 和 data_sources 的工具列表
    tool_list = []
    for tool_id, info in tools.items():
        tool_list.append({
            "id": tool_id,
            "name": info["name"],
            "display_name": info.get("display_name", info["name"]),
            "description": info["description"],
            "data_sources": info.get("data_sources", [])
        })
    
    # 获取此scope的所有可用数据源
    all_data_sources = ToolRegistry.get_scope_data_sources(scope)
    data_source_list = [
        {
            "id": source_id,
            "name": source_id.replace("_", " ").replace(".", " ").title()
        }
        for source_id in all_data_sources
    ]
    
    return {
        "scope": scope,
        "tools": tool_list,
        "data_sources": data_source_list
    }


@router.get("/analysis-scopes/{market_type}")
async def get_analysis_scopes(market_type: str):
    """
    获取市场支持的分析范围详细配置
    
    Args:
        market_type: 市场类型
    """
    try:
        market_enum = MarketType(market_type)
    except ValueError:
        market_enum = MarketType.CRYPTO
    
    scopes = get_market_scopes(market_enum)
    
    # 构建详细的分析范围配置
    # 这里应该从数据库或配置文件加载，现在先返回示例数据
    scope_configs = []
    for scope in scopes:
        scope_config = {
            "id": scope.value,
            "name": _get_scope_name(scope),
            "description": _get_scope_description(scope),
            "available_tools": _get_scope_tools(scope, market_enum),
            "available_mcp": _get_scope_mcp(scope, market_enum),
            "available_data_sources": _get_scope_data_sources(scope, market_enum)
        }
        scope_configs.append(scope_config)
    
    return scope_configs


def _get_scope_name(scope: AnalysisScope) -> str:
    """获取分析范围的显示名称"""
    name_map = {
        AnalysisScope.TECHNICAL: "技术分析",
        AnalysisScope.SENTIMENT: "市场情绪",
        AnalysisScope.EVENT: "事件分析",
        AnalysisScope.PROBABILITY: "概率分析",
        AnalysisScope.ODDS: "赔率分析"
    }
    return name_map.get(scope, scope.value)


def _get_scope_description(scope: AnalysisScope) -> str:
    """获取分析范围的描述"""
    desc_map = {
        AnalysisScope.TECHNICAL: "价格走势、技术指标、图表形态分析",
        AnalysisScope.SENTIMENT: "社交媒体情绪、新闻事件、市场心理分析",
        AnalysisScope.EVENT: "重大事件影响、时间线分析",
        AnalysisScope.PROBABILITY: "概率模型、贝叶斯分析",
        AnalysisScope.ODDS: "赔率变化、套利机会分析"
    }
    return desc_map.get(scope, "")


def _get_scope_tools(scope: AnalysisScope, market: MarketType) -> List[Dict[str, str]]:
    """获取分析范围可用的工具"""
    from core.services.tools.tool_registry import ToolRegistry
    
    # 将 AnalysisScope 枚举映射到 ToolRegistry 的 scope 字符串
    scope_mapping = {
        AnalysisScope.TECHNICAL: 'technical',
        AnalysisScope.SENTIMENT: 'sentiment',
        # 其他范围暂时没有注册工具
    }
    
    registry_scope = scope_mapping.get(scope)
    if not registry_scope:
        return []
    
    # 从 ToolRegistry 获取真实的工具信息
    scope_tools = ToolRegistry.get_scope_tools(registry_scope)
    
    # 转换为 API 响应格式
    tools = []
    for tool_id, tool_info in scope_tools.items():
        tools.append({
            "id": tool_id,
            "name": tool_info.get('name', tool_id)
        })
    
    return tools


def _get_scope_mcp(scope: AnalysisScope, market: MarketType) -> List[Dict[str, str]]:
    """获取分析范围可用的MCP服务"""
    # TODO: 实现真实的MCP服务注册和发现机制
    # 目前后端没有注册任何MCP服务，返回空列表
    # 不再返回不存在的ctx7-*服务
    return []


def _get_scope_data_sources(scope: AnalysisScope, market: MarketType) -> List[Dict[str, str]]:
    """获取分析范围的数据源（从ToolRegistry动态获取）"""
    from core.services.tools.tool_registry import ToolRegistry
    
    # 将 AnalysisScope 枚举映射到 ToolRegistry 的 scope 字符串
    scope_mapping = {
        AnalysisScope.TECHNICAL: 'technical',
        AnalysisScope.SENTIMENT: 'sentiment',
    }
    
    registry_scope = scope_mapping.get(scope)
    if not registry_scope:
        # 对于未映射的范围，返回默认数据源
        sources = get_market_data_sources(market)
        return [{"id": s, "name": s.replace("_", " ").title()} for s in sources]
    
    # 从 ToolRegistry 获取真实的数据源
    sources = ToolRegistry.get_scope_data_sources(registry_scope)
    
    return [{"id": s, "name": s.replace("_", " ").title()} for s in sources]


@router.get("/agents")
async def get_agent_config():
    """获取所有智能体配置"""
    agents = []
    for agent_type in AgentType:
        agents.append({
            "id": agent_type.value,
            "name": agent_type.value.replace("_", " ").title(),
            "type": agent_type.value
        })
    return agents


@router.get("/llm-providers")
async def get_llm_providers():
    """获取支持的LLM提供商"""
    providers = []
    for provider in LLMProvider:
        providers.append({
            "id": provider.value,
            "name": provider.value.upper(),
            "enabled": True  # 可以根据实际配置动态返回
        })
    return providers