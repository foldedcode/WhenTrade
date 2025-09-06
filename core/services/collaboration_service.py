"""
协作服务
管理智能体协作过程的实时状态和事件
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from core.cache.manager import cache_manager
from core.websocket.manager import manager as websocket_manager

logger = logging.getLogger(__name__)


class CollaborationService:
    """协作服务"""
    
    def __init__(self):
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}
        
    async def start_collaboration(self, analysis_id: str, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """开始协作分析"""
        collaboration_id = f"collab_{analysis_id}"
        
        # 初始化协作状态
        collaboration_state = {
            "id": collaboration_id,
            "analysis_id": analysis_id,
            "agents": {agent["id"]: agent for agent in agents},
            "current_phase": 0,
            "phases": [
                {"name": "数据收集", "status": "pending"},
                {"name": "独立分析", "status": "pending"},
                {"name": "观点交流", "status": "pending"},
                {"name": "深度辩论", "status": "pending"},
                {"name": "共识形成", "status": "pending"}
            ],
            "events": [],
            "interactions": [],
            "start_time": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        self.active_collaborations[collaboration_id] = collaboration_state
        
        # 缓存状态
        await cache_manager.set(
            f"collaboration:{collaboration_id}",
            collaboration_state,
            ttl=3600,  # 1小时
            serialize_method="json"
        )
        
        # 通知WebSocket客户端
        await self._broadcast_event(analysis_id, {
            "type": "collaboration_started",
            "data": collaboration_state
        })
        
        logger.info(f"协作开始: {collaboration_id}")
        return collaboration_state
        
    async def update_agent_status(
        self, 
        analysis_id: str, 
        agent_id: str, 
        status_update: Dict[str, Any]
    ):
        """更新智能体状态"""
        collaboration_id = f"collab_{analysis_id}"
        collaboration = self.active_collaborations.get(collaboration_id)
        
        if not collaboration:
            # 从缓存加载
            collaboration = await cache_manager.get(f"collaboration:{collaboration_id}")
            if collaboration:
                self.active_collaborations[collaboration_id] = collaboration
            else:
                logger.error(f"未找到协作: {collaboration_id}")
                return
                
        # 更新智能体状态
        if agent_id in collaboration["agents"]:
            agent = collaboration["agents"][agent_id]
            agent.update(status_update)
            agent["last_update"] = datetime.utcnow().isoformat()
            
            # 更新缓存
            await cache_manager.set(
                f"collaboration:{collaboration_id}",
                collaboration,
                ttl=3600,
                serialize_method="json"
            )
            
            # 广播更新
            await self._broadcast_event(analysis_id, {
                "type": "agent_update",
                "agent": agent
            })
            
            # 检查是否需要切换阶段
            await self._check_phase_transition(collaboration_id)
            
    async def add_agent_thought(
        self, 
        analysis_id: str, 
        agent_id: str, 
        thought: str,
        confidence: float = 0.5
    ):
        """添加智能体思考"""
        collaboration_id = f"collab_{analysis_id}"
        collaboration = self.active_collaborations.get(collaboration_id)
        
        if not collaboration or agent_id not in collaboration["agents"]:
            return
            
        agent = collaboration["agents"][agent_id]
        
        # 添加思考记录
        if "thoughts" not in agent:
            agent["thoughts"] = []
            
        thought_data = {
            "text": thought,
            "confidence": confidence,
            "timestamp": datetime.utcnow().timestamp()
        }
        
        agent["thoughts"].append(thought_data)
        
        # 保持最近10条思考
        if len(agent["thoughts"]) > 10:
            agent["thoughts"] = agent["thoughts"][-10:]
            
        # 更新置信度
        agent["confidence"] = confidence
        
        # 广播思考流
        await self._broadcast_event(analysis_id, {
            "type": "agent_thought",
            "agent_id": agent_id,
            "thought": thought_data
        })
        
    async def add_interaction(
        self,
        analysis_id: str,
        source_id: str,
        target_id: str,
        interaction_type: str,
        content: Optional[str] = None
    ):
        """添加智能体交互"""
        collaboration_id = f"collab_{analysis_id}"
        collaboration = self.active_collaborations.get(collaboration_id)
        
        if not collaboration:
            return
            
        interaction = {
            "id": datetime.utcnow().timestamp(),
            "source_id": source_id,
            "target_id": target_id,
            "type": interaction_type,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        collaboration["interactions"].append(interaction)
        
        # 更新智能体交互记录
        if source_id in collaboration["agents"]:
            agent = collaboration["agents"][source_id]
            if "interactions" not in agent:
                agent["interactions"] = []
            agent["interactions"].append({
                "targetId": target_id,
                "type": interaction_type,
                "timestamp": datetime.utcnow().timestamp()
            })
            
        # 广播交互事件
        await self._broadcast_event(analysis_id, {
            "type": "interaction",
            "sourceId": source_id,
            "targetId": target_id,
            "interactionType": interaction_type,
            "content": content
        })
        
    async def update_phase(self, analysis_id: str, phase: int):
        """更新协作阶段"""
        collaboration_id = f"collab_{analysis_id}"
        collaboration = self.active_collaborations.get(collaboration_id)
        
        if not collaboration:
            return
            
        # 更新阶段状态
        if 0 <= phase < len(collaboration["phases"]):
            collaboration["current_phase"] = phase
            collaboration["phases"][phase]["status"] = "active"
            
            # 标记之前的阶段为完成
            for i in range(phase):
                collaboration["phases"][i]["status"] = "completed"
                
            # 添加事件
            event = {
                "type": "phase_change",
                "title": "阶段切换",
                "description": f"进入{collaboration['phases'][phase]['name']}阶段",
                "timestamp": datetime.utcnow().timestamp()
            }
            collaboration["events"].append(event)
            
            # 广播阶段更新
            await self._broadcast_event(analysis_id, {
                "type": "phase_update",
                "phase": phase
            })
            
            await self._broadcast_event(analysis_id, {
                "type": "collaboration_event",
                "event": event
            })
            
    async def start_debate(
        self, 
        analysis_id: str, 
        topic: str, 
        participants: List[str]
    ):
        """开始辩论"""
        collaboration_id = f"collab_{analysis_id}"
        collaboration = self.active_collaborations.get(collaboration_id)
        
        if not collaboration:
            return
            
        # 更新智能体状态为辩论中
        for agent_id in participants:
            if agent_id in collaboration["agents"]:
                collaboration["agents"][agent_id]["status"] = "debating"
                
        # 添加辩论事件
        event = {
            "type": "debate_start",
            "title": "开始辩论",
            "description": f"主题: {topic}",
            "participants": participants,
            "timestamp": datetime.utcnow().timestamp()
        }
        collaboration["events"].append(event)
        
        # 广播辩论开始
        await self._broadcast_event(analysis_id, {
            "type": "debate_start",
            "topic": topic,
            "participants": participants
        })
        
        await self._broadcast_event(analysis_id, {
            "type": "collaboration_event",
            "event": event
        })
        
    async def add_debate_opinion(
        self,
        analysis_id: str,
        agent_id: str,
        opinion: str,
        confidence: float
    ):
        """添加辩论观点"""
        await self._broadcast_event(analysis_id, {
            "type": "debate_opinion",
            "agent": agent_id,
            "opinion": opinion,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def reach_consensus(
        self,
        analysis_id: str,
        consensus: Dict[str, Any]
    ):
        """达成共识"""
        collaboration_id = f"collab_{analysis_id}"
        collaboration = self.active_collaborations.get(collaboration_id)
        
        if not collaboration:
            return
            
        # 更新所有智能体状态为完成
        for agent in collaboration["agents"].values():
            agent["status"] = "completed"
            agent["progress"] = 100
            
        # 添加共识事件
        event = {
            "type": "consensus_reached",
            "title": "达成共识",
            "description": "所有分析师完成分析并形成统一结论",
            "timestamp": datetime.utcnow().timestamp(),
            "participants": list(collaboration["agents"].keys())
        }
        collaboration["events"].append(event)
        
        # 广播共识
        await self._broadcast_event(analysis_id, {
            "type": "consensus_reached",
            "consensus": consensus
        })
        
        await self._broadcast_event(analysis_id, {
            "type": "collaboration_event",
            "event": event
        })
        
        # 标记协作完成
        collaboration["status"] = "completed"
        collaboration["end_time"] = datetime.utcnow().isoformat()
        
    async def get_collaboration_state(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """获取协作状态"""
        collaboration_id = f"collab_{analysis_id}"
        
        # 先从内存获取
        if collaboration_id in self.active_collaborations:
            return self.active_collaborations[collaboration_id]
            
        # 再从缓存获取
        collaboration = await cache_manager.get(f"collaboration:{collaboration_id}")
        if collaboration:
            self.active_collaborations[collaboration_id] = collaboration
            return collaboration
            
        return None
        
    async def get_collaboration_history(
        self, 
        analysis_id: str, 
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """获取协作历史"""
        collaboration = await self.get_collaboration_state(analysis_id)
        if not collaboration:
            return []
            
        events = collaboration.get("events", [])
        
        # 过滤事件类型
        if event_types:
            events = [e for e in events if e["type"] in event_types]
            
        return events
        
    async def _check_phase_transition(self, collaboration_id: str):
        """检查是否需要切换阶段"""
        collaboration = self.active_collaborations.get(collaboration_id)
        if not collaboration:
            return
            
        current_phase = collaboration["current_phase"]
        agents = collaboration["agents"].values()
        
        # 根据智能体状态判断阶段
        if current_phase == 0:  # 数据收集
            if all(agent.get("progress", 0) >= 30 for agent in agents):
                await self.update_phase(
                    collaboration["analysis_id"], 
                    current_phase + 1
                )
                
        elif current_phase == 1:  # 独立分析
            if all(agent.get("progress", 0) >= 60 for agent in agents):
                await self.update_phase(
                    collaboration["analysis_id"], 
                    current_phase + 1
                )
                
        elif current_phase == 2:  # 观点交流
            if len(collaboration.get("interactions", [])) >= 3:
                await self.update_phase(
                    collaboration["analysis_id"], 
                    current_phase + 1
                )
                
    async def _broadcast_event(self, analysis_id: str, event: Dict[str, Any]):
        """广播事件到WebSocket客户端"""
        topic = f"analysis:{analysis_id}:collaboration"
        await websocket_manager.broadcast_to_topic(topic, event)
        
    async def simulate_collaboration(self, analysis_id: str):
        """模拟协作过程（用于测试）"""
        # 初始化智能体
        agents = [
            {
                "id": "technical_analyst",
                "name": "技术分析师",
                "type": "technical",
                "role": "专注于价格走势和技术指标",
                "status": "idle",
                "progress": 0,
                "confidence": 0.5
            },
            {
                "id": "fundamental_analyst", 
                "name": "基本面分析师",
                "type": "fundamental",
                "role": "研究公司财务和业务",
                "status": "idle",
                "progress": 0,
                "confidence": 0.5
            },
            {
                "id": "sentiment_analyst",
                "name": "情绪分析师", 
                "type": "sentiment",
                "role": "分析市场情绪和新闻",
                "status": "idle",
                "progress": 0,
                "confidence": 0.5
            },
            {
                "id": "risk_analyst",
                "name": "风险分析师",
                "type": "risk", 
                "role": "评估投资风险",
                "status": "idle",
                "progress": 0,
                "confidence": 0.5
            }
        ]
        
        # 开始协作
        await self.start_collaboration(analysis_id, agents)
        
        # 模拟协作流程
        await asyncio.sleep(1)
        
        # 阶段1：数据收集
        for agent in agents:
            await self.update_agent_status(analysis_id, agent["id"], {
                "status": "thinking",
                "currentTask": "收集市场数据...",
                "progress": 20
            })
            
        await asyncio.sleep(2)
        
        # 添加一些思考
        await self.add_agent_thought(
            analysis_id, 
            "technical_analyst",
            "发现RSI超买信号，需要进一步分析",
            0.7
        )
        
        await asyncio.sleep(1)
        
        # 阶段2：独立分析
        for agent in agents:
            await self.update_agent_status(analysis_id, agent["id"], {
                "status": "analyzing",
                "currentTask": "执行专业分析...",
                "progress": 60
            })
            
        await asyncio.sleep(2)
        
        # 添加交互
        await self.add_interaction(
            analysis_id,
            "technical_analyst",
            "fundamental_analyst",
            "sharing",
            "技术指标显示超买，但需要确认基本面"
        )
        
        await asyncio.sleep(1)
        
        # 阶段3：辩论
        await self.start_debate(
            analysis_id,
            "市场趋势判断",
            ["technical_analyst", "fundamental_analyst", "sentiment_analyst"]
        )
        
        await asyncio.sleep(2)
        
        # 达成共识
        await self.reach_consensus(analysis_id, {
            "rating": "买入",
            "confidence": 0.75,
            "key_findings": [
                "技术指标短期超买，但趋势向好",
                "基本面稳健，估值合理",
                "市场情绪积极"
            ],
            "recommendations": [
                "建议分批建仓",
                "设置止损位在支撑位下方",
                "关注即将发布的财报"
            ]
        })


# 全局协作服务实例
collaboration_service = CollaborationService()