"""
统一的分析范围映射配置
作为整个系统的单一真相源，消除硬编码的命名映射问题
"""

from typing import Dict, List, TypedDict

class AnalysisScopeConfig(TypedDict):
    """分析范围配置类型定义"""
    analysts: List[str]      # 对应的分析师类型
    agent_names: List[str]   # 实际的Agent名称
    display_name: str        # 显示名称
    nodes: List[str]         # 包含的所有节点（Agent + 工具 + 消息清理）

# 分析范围到分析师的完整映射配置
ANALYSIS_SCOPE_MAPPING: Dict[str, AnalysisScopeConfig] = {
    "technical": {
        "analysts": ["market"],
        "agent_names": ["Market Analyst"],
        "display_name": "技术分析",
        "nodes": ["Market Analyst", "tools_market", "Msg Clear Market"]
    },
    "sentiment": {
        "analysts": ["social", "news"],
        "agent_names": ["Social Analyst", "News Analyst"],
        "display_name": "市场情绪",
        "nodes": [
            "Social Analyst", "tools_social", "Msg Clear Social",
            "News Analyst", "tools_news", "Msg Clear News"
        ]
    },
    "fundamental": {
        "analysts": ["fundamentals"],
        "agent_names": ["Fundamentals Analyst"],
        "display_name": "基本面分析",
        "nodes": ["Fundamentals Analyst", "tools_fundamentals", "Msg Clear Fundamentals"]
    }
    # 注意：暂时只包含已验证存在的Agent，避免配置错误
}

def get_analysis_scope_config(scope: str) -> AnalysisScopeConfig:
    """获取指定分析范围的配置"""
    if scope not in ANALYSIS_SCOPE_MAPPING:
        raise ValueError(f"未知的分析范围: {scope}")
    return ANALYSIS_SCOPE_MAPPING[scope]

def build_nodes_for_scopes(analysis_scopes: List[str]) -> List[str]:
    """根据分析范围列表构建所有需要的节点"""
    all_nodes = []
    for scope in analysis_scopes:
        if scope in ANALYSIS_SCOPE_MAPPING:
            all_nodes.extend(ANALYSIS_SCOPE_MAPPING[scope]["nodes"])
    return all_nodes

def build_agent_names_for_scopes(analysis_scopes: List[str]) -> List[str]:
    """根据分析范围列表构建所有Agent名称（用于analyst_order）"""
    all_agents = []
    for scope in analysis_scopes:
        if scope in ANALYSIS_SCOPE_MAPPING:
            all_agents.extend(ANALYSIS_SCOPE_MAPPING[scope]["agent_names"])
    return all_agents

def get_supported_scopes() -> List[str]:
    """获取支持的所有分析范围"""
    return list(ANALYSIS_SCOPE_MAPPING.keys())