"""
Agent映射服务
根据市场类型和分析范围分配合适的Agent
"""

from typing import List, Dict, Any
from enum import Enum

class MarketType(Enum):
    CRYPTO = "crypto"
    POLYMARKET = "polymarket"

class AgentType(Enum):
    # 通用Agent
    TECHNICAL_ANALYST = "technical_analyst"
    FUNDAMENTAL_ANALYST = "fundamental_analyst"
    SENTIMENT_ANALYST = "sentiment_analyst"
    RISK_ANALYST = "risk_analyst"
    
    # 加密市场专属Agent
    ONCHAIN_ANALYST = "onchain_analyst"
    DEFI_ANALYST = "defi_analyst"
    WHALE_TRACKER = "whale_tracker"
    TRADING_STRATEGIST = "trading_strategist"
    PORTFOLIO_MANAGER = "portfolio_manager"
    
    # 预测市场专属Agent
    EVENT_ANALYST = "event_analyst"
    PROBABILITY_ANALYST = "probability_analyst"
    ODDS_ANALYST = "odds_analyst"
    STRATEGY_ANALYST = "strategy_analyst"
    DECISION_ANALYST = "decision_analyst"

class AgentMappingService:
    """Agent映射服务"""
    
    # 市场类型到Agent的映射配置
    MARKET_AGENT_MAP = {
        MarketType.CRYPTO: {
            "technical": [
                {"id": "ca-001", "name": "市场分析师", "type": "market", "status": "idle"}
            ],
            "sentiment": [
                {"id": "ca-004", "name": "社交媒体分析师", "type": "social", "status": "idle"},
                {"id": "ca-005", "name": "新闻分析师", "type": "news", "status": "idle"}
            ]
        },
        MarketType.POLYMARKET: {
            "event": [
                {"id": "pm-001", "name": "事件分析师", "type": AgentType.EVENT_ANALYST.value, "status": "idle"}
            ],
            "probability": [
                {"id": "pm-002", "name": "概率分析师", "type": AgentType.PROBABILITY_ANALYST.value, "status": "idle"}
            ],
            "odds": [
                {"id": "pm-003", "name": "赔率分析师", "type": AgentType.ODDS_ANALYST.value, "status": "idle"}
            ],
            "strategy": [
                {"id": "pm-004", "name": "策略分析师", "type": AgentType.STRATEGY_ANALYST.value, "status": "idle"}
            ],
            "decision": [
                {"id": "pm-005", "name": "决策分析师", "type": AgentType.DECISION_ANALYST.value, "status": "idle"}
            ]
        }
    }
    
    # Agent执行阶段映射 - 与前端截图保持一致
    AGENT_STAGES = {
        MarketType.CRYPTO: {
            "analyst": "分析团队",
            "research": "研究团队", 
            "trading": "交易团队",
            "risk": "风险管理",
            "portfolio": "组合管理"
        },
        MarketType.POLYMARKET: {
            "analyst": "分析团队",
            "research": "研究团队",
            "probability": "概率团队",
            "strategy": "策略团队",
            "decision": "决策团队"
        }
    }
    
    # 团队显示名称映射（用于前端显示）
    TEAM_DISPLAY_NAMES = {
        "analyst": "I 分析团队",
        "research": "II 研究团队",
        "trading": "III 交易团队",
        "risk": "IV 风险管理",
        "portfolio": "V 组合管理",
        "probability": "III 概率团队",
        "strategy": "IV 策略团队", 
        "decision": "V 决策团队"
    }
    
    @classmethod
    def get_agents_for_task(cls, market_type: str, analysis_scopes: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        根据市场类型和分析范围获取Agent配置
        
        Args:
            market_type: 市场类型 (crypto/polymarket)
            analysis_scopes: 分析范围列表
            
        Returns:
            Agent配置字典，按阶段分组
        """
        # 添加调试日志
        print(f"🔍 AgentMappingService.get_agents_for_task called:")
        print(f"  - market_type: {market_type}")
        print(f"  - analysis_scopes: {analysis_scopes}")
        
        try:
            market_enum = MarketType(market_type)
        except ValueError:
            # 默认使用crypto市场
            market_enum = MarketType.CRYPTO
            print(f"  - market_enum (默认): {market_enum}")
        else:
            print(f"  - market_enum: {market_enum}")
            
        # 获取该市场的Agent映射
        market_agents = cls.MARKET_AGENT_MAP.get(market_enum, {})
        print(f"  - 可用的agent映射键: {list(market_agents.keys())}")
        
        # 收集所有相关的Agent，使用字典去重（基于agent的id）
        selected_agents_dict = {}
        for scope in analysis_scopes:
            print(f"  - 检查scope: {scope}")
            if scope in market_agents:
                agents_for_scope = market_agents[scope]
                print(f"    ✅ 找到 {len(agents_for_scope)} 个agents for scope '{scope}'")
                for agent in agents_for_scope:
                    # 使用agent的id作为key来去重
                    selected_agents_dict[agent["id"]] = agent
                    print(f"    📝 添加agent: {agent['id']} - {agent['name']}")
            else:
                print(f"    ❌ scope '{scope}' 未找到对应的agents")
        
        # 转换为列表
        selected_agents = list(selected_agents_dict.values())
        print(f"  - 最终选择的agents: {len(selected_agents)} 个")
        for agent in selected_agents:
            print(f"    • {agent['id']}: {agent['name']} ({agent['type']})")
        
        # 如果没有找到任何Agent，使用默认配置
        if not selected_agents:
            print("  ⚠️ 没有找到匹配的agents，使用默认配置")
            if market_enum == MarketType.CRYPTO:
                selected_agents = [
                    {"id": "ca-001", "name": "技术分析师", "type": AgentType.TECHNICAL_ANALYST.value, "status": "idle"}
                ]
            else:
                selected_agents = [
                    {"id": "pm-001", "name": "事件分析师", "type": AgentType.EVENT_ANALYST.value, "status": "idle"}
                ]
        
        # 按阶段组织Agent
        if market_enum == MarketType.CRYPTO:
            return cls._organize_crypto_agents(selected_agents)
        else:
            return cls._organize_polymarket_agents(selected_agents)
    
    @classmethod
    def _organize_crypto_agents(cls, agents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """组织加密市场的Agent"""
        # 选择的分析范围只决定分析团队的agents
        # 其他团队（研究、交易、风险、组合）有固定的agents - 使用前端定义的角色类型
        
        print(f"🏗️ 组织加密市场agents:")
        print(f"  - analyst团队将包含 {len(agents)} 个agents:")
        for agent in agents:
            print(f"    • {agent['id']}: {agent['name']} ({agent.get('type', 'unknown')})")
        
        result = {
            "analyst": agents,  # 所有根据分析范围选择的agents都归入分析团队
            "research": [
                {"id": "ca-r01", "name": "多头研究员", "type": "bull", "status": "idle"},
                {"id": "ca-r02", "name": "空头研究员", "type": "bear", "status": "idle"},
                {"id": "ca-r03", "name": "研究经理", "type": "manager", "status": "idle"}
            ],
            "trading": [
                {"id": "ca-t01", "name": "交易员", "type": "trader", "status": "idle"}
            ],
            "risk": [
                {"id": "ca-rk01", "name": "激进分析师", "type": "risky", "status": "idle"},
                {"id": "ca-rk02", "name": "中性分析师", "type": "neutral", "status": "idle"},
                {"id": "ca-rk03", "name": "保守分析师", "type": "safe", "status": "idle"}
            ],
            "portfolio": [
                {"id": "ca-p01", "name": "组合经理", "type": "portfolio", "status": "idle"}
            ]
        }
        
        print(f"📋 最终组织结果:")
        for stage, stage_agents in result.items():
            print(f"  - {stage}: {len(stage_agents)} 个agents")
        
        return result
    
    @classmethod
    def _organize_polymarket_agents(cls, agents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """组织预测市场的Agent"""
        # 选择的分析范围只决定分析团队的agents
        # 其他团队有固定的agents
        return {
            "analyst": agents,  # 所有根据分析范围选择的agents都归入分析团队
            "research": [{"id": "pm-r01", "name": "市场研究员", "status": "idle"}],
            "probability": [{"id": "pm-p01", "name": "贝叶斯分析师", "status": "idle"}],
            "strategy": [{"id": "pm-s01", "name": "博弈策略师", "status": "idle"}],
            "decision": [{"id": "pm-d01", "name": "决策优化师", "status": "idle"}]
        }
    
    @classmethod
    def get_stage_names(cls, market_type: str) -> Dict[str, str]:
        """获取阶段名称映射"""
        try:
            market_enum = MarketType(market_type)
            return cls.AGENT_STAGES.get(market_enum, cls.AGENT_STAGES[MarketType.CRYPTO])
        except ValueError:
            return cls.AGENT_STAGES[MarketType.CRYPTO]
    
    @classmethod
    def get_teams_config(cls, market_type: str = "crypto") -> Dict[str, Any]:
        """
        获取完整的团队配置（供前端使用）
        
        Args:
            market_type: 市场类型
            
        Returns:
            包含团队信息和agents的配置
        """
        try:
            market_enum = MarketType(market_type)
        except ValueError:
            market_enum = MarketType.CRYPTO
            
        # 获取基础的团队配置
        if market_enum == MarketType.CRYPTO:
            teams = {
                "analyst": {
                    "displayName": "I 分析团队",
                    "name": "分析团队",
                    "agents": [
                        {"id": "ca-001", "name": "市场分析师", "type": "market", "status": "idle"},
                        {"id": "ca-004", "name": "社交分析师", "type": "social", "status": "idle"},
                        {"id": "ca-005", "name": "新闻分析师", "type": "news", "status": "idle"}
                    ]
                },
                "research": {
                    "displayName": "II 研究团队",
                    "name": "研究团队",
                    "agents": [
                        {"id": "ca-r01", "name": "多头研究员", "type": "bull", "status": "idle"},
                        {"id": "ca-r02", "name": "空头研究员", "type": "bear", "status": "idle"},
                        {"id": "ca-r03", "name": "研究经理", "type": "manager", "status": "idle"}
                    ]
                },
                "trading": {
                    "displayName": "III 交易团队",
                    "name": "交易团队",
                    "agents": [
                        {"id": "ca-t01", "name": "交易员", "type": "trader", "status": "idle"}
                    ]
                },
                "risk": {
                    "displayName": "IV 风险管理",
                    "name": "风险管理",
                    "agents": [
                        {"id": "ca-rk01", "name": "激进分析师", "type": "risky", "status": "idle"},
                        {"id": "ca-rk02", "name": "中性分析师", "type": "neutral", "status": "idle"},
                        {"id": "ca-rk03", "name": "保守分析师", "type": "safe", "status": "idle"}
                    ]
                },
                "portfolio": {
                    "displayName": "V 组合管理",
                    "name": "组合管理",
                    "agents": [
                        {"id": "ca-p01", "name": "组合经理", "type": "portfolio", "status": "idle"}
                    ]
                }
            }
        else:  # POLYMARKET
            teams = {
                "analyst": {
                    "displayName": "I 分析团队",
                    "name": "分析团队",
                    "agents": [
                        {"id": "pm-001", "name": "事件分析师", "type": "event", "status": "idle"},
                        {"id": "pm-003", "name": "赔率分析师", "type": "odds", "status": "idle"},
                        {"id": "pm-004", "name": "策略分析师", "type": "strategy", "status": "idle"}
                    ]
                },
                "research": {
                    "displayName": "II 研究团队",
                    "name": "研究团队",
                    "agents": [
                        {"id": "pm-r01", "name": "YES方研究员", "type": "yes", "status": "idle"},
                        {"id": "pm-r02", "name": "NO方研究员", "type": "no", "status": "idle"},
                        {"id": "pm-r03", "name": "仲裁经理", "type": "arbiter", "status": "idle"}
                    ]
                },
                "probability": {
                    "displayName": "III 概率团队",
                    "name": "概率团队",
                    "agents": [
                        {"id": "pm-p01", "name": "贝叶斯分析师", "type": "bayesian", "status": "idle"},
                        {"id": "pm-p02", "name": "统计模型师", "type": "statistical", "status": "idle"}
                    ]
                },
                "strategy": {
                    "displayName": "IV 策略团队",
                    "name": "策略团队",
                    "agents": [
                        {"id": "pm-s01", "name": "仓位策略师", "type": "position", "status": "idle"},
                        {"id": "pm-s02", "name": "时机分析师", "type": "timing", "status": "idle"},
                        {"id": "pm-s03", "name": "对冲策略师", "type": "hedging", "status": "idle"}
                    ]
                },
                "decision": {
                    "displayName": "V 决策团队",
                    "name": "决策团队",
                    "agents": [
                        {"id": "pm-d01", "name": "决策优化师", "type": "decision", "status": "idle"}
                    ]
                }
            }
            
        return {
            "marketType": market_type,
            "teams": teams
        }