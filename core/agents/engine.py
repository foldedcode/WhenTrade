"""
智能代理引擎 (Agent Engine)
协调多个工具和服务来完成复杂的分析任务
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running" 
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(Enum):
    """代理角色枚举"""
    COORDINATOR = "coordinator"  # 协调者
    ANALYST = "analyst"         # 分析师
    RESEARCHER = "researcher"   # 研究员
    VALIDATOR = "validator"     # 验证者
    EXECUTOR = "executor"       # 执行者
    REPORTER = "reporter"       # 报告生成器


@dataclass
class Task:
    """任务数据结构"""
    id: str
    name: str
    description: str
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    estimated_duration: Optional[int] = None  # 秒
    actual_duration: Optional[int] = None
    assigned_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data


@dataclass
class Agent:
    """智能代理数据结构"""
    id: str
    name: str
    role: AgentRole
    description: str
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 3
    current_tasks: List[str] = field(default_factory=list)
    status: str = "idle"  # idle, busy, offline
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['role'] = self.role.value
        data['created_at'] = self.created_at.isoformat()
        data['last_active'] = self.last_active.isoformat()
        return data


@dataclass
class Workflow:
    """工作流数据结构"""
    id: str
    name: str
    description: str
    tasks: List[Task] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        data['tasks'] = [task.to_dict() for task in self.tasks]
        return data


class AgentEngine:
    """
    智能代理引擎核心类
    
    功能：
    - 代理管理和任务分配
    - 工作流编排和执行
    - 工具和MCP服务协调
    - 实时状态监控
    """
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self._executor_task: Optional[asyncio.Task] = None
        
        # 创建默认代理
        self._create_default_agents()
        
        logger.info("🤖 Agent Engine initialized")
    
    def _create_default_agents(self):
        """创建默认的智能代理"""
        
        # 协调者代理
        coordinator = Agent(
            id="coordinator-001",
            name="主协调者",
            role=AgentRole.COORDINATOR,
            description="负责任务分解、调度和协调其他代理",
            capabilities=[
                "task_decomposition",
                "agent_coordination", 
                "workflow_management",
                "resource_allocation"
            ],
            tools=["task_planner", "resource_manager"],
            max_concurrent_tasks=10
        )
        
        # 市场分析师代理
        analyst = Agent(
            id="analyst-001", 
            name="加密市场分析师",
            role=AgentRole.ANALYST,
            description="专门进行加密货币市场技术分析和基本面分析",
            capabilities=[
                "technical_analysis",
                "market_data_analysis",
                "pattern_recognition",
                "risk_assessment"
            ],
            tools=[
                "crypto.indicators.RSIIndicator",
                "crypto.indicators.MACDIndicator", 
                "crypto.indicators.BollingerBandsIndicator",
                "crypto.patterns.TrendPatternDetector"
            ],
            mcp_servers=["market_data", "technical_analysis"]
        )
        
        # DeFi研究员代理  
        defi_researcher = Agent(
            id="defi-researcher-001",
            name="DeFi研究员",
            role=AgentRole.RESEARCHER,
            description="专注于DeFi协议分析和链上数据研究",
            capabilities=[
                "defi_analysis",
                "onchain_analysis", 
                "yield_optimization",
                "liquidity_analysis"
            ],
            tools=[
                "crypto.defi.LiquidityAnalyzer",
                "crypto.defi.YieldOptimizer",
                "crypto.onchain.WhaleTracker",
                "crypto.onchain.TVLMonitor"
            ],
            mcp_servers=["defi_data", "onchain_analytics"]
        )
        
        # 情绪分析师代理
        sentiment_analyst = Agent(
            id="sentiment-analyst-001",
            name="市场情绪分析师", 
            role=AgentRole.ANALYST,
            description="分析社交媒体情绪和市场心理",
            capabilities=[
                "sentiment_analysis",
                "social_monitoring",
                "news_analysis",
                "fear_greed_analysis"
            ],
            tools=[
                "crypto.sentiment.SocialSentimentAnalyzer",
                "crypto.sentiment.FearGreedIndex",
                "crypto.sentiment.NewsImpactAnalyzer"
            ],
            mcp_servers=["social_media", "news_feeds"]
        )
        
        # 验证者代理
        validator = Agent(
            id="validator-001",
            name="分析验证者",
            role=AgentRole.VALIDATOR,
            description="验证分析结果的一致性和可靠性",
            capabilities=[
                "result_validation",
                "cross_verification",
                "confidence_scoring",
                "outlier_detection"
            ],
            tools=["statistical_validator", "consensus_checker"]
        )
        
        # 报告生成器代理
        reporter = Agent(
            id="reporter-001",
            name="智能报告生成器",
            role=AgentRole.REPORTER, 
            description="整合分析结果并生成专业报告",
            capabilities=[
                "report_generation",
                "data_visualization",
                "insight_summarization", 
                "recommendation_synthesis"
            ],
            tools=["report_builder", "chart_generator"],
            mcp_servers=["document_generator"]
        )
        
        # 注册所有代理
        for agent in [coordinator, analyst, defi_researcher, sentiment_analyst, validator, reporter]:
            self.agents[agent.id] = agent
            
        logger.info(f"🤖 Created {len(self.agents)} default agents")
    
    async def start(self):
        """启动代理引擎"""
        if self.running:
            logger.warning("Agent Engine is already running")
            return
            
        self.running = True
        self._executor_task = asyncio.create_task(self._task_executor())
        logger.info("🚀 Agent Engine started")
    
    async def stop(self):
        """停止代理引擎"""
        if not self.running:
            return
            
        self.running = False
        
        # 取消所有正在运行的任务
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.CANCELLED
                task.updated_at = datetime.utcnow()
        
        # 停止执行器
        if self._executor_task:
            self._executor_task.cancel()
            try:
                await self._executor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Agent Engine stopped")
    
    async def _task_executor(self):
        """任务执行器主循环"""
        while self.running:
            try:
                # 从队列获取任务（带超时）
                task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                if task_id in self.tasks:
                    await self._execute_task(task_id)
                    
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                logger.error(f"Task executor error: {e}", exc_info=True)
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        task_configs: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> str:
        """
        创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述  
            task_configs: 任务配置列表
            user_id: 用户ID
            
        Returns:
            workflow_id: 工作流ID
        """
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        # 创建任务
        tasks = []
        for config in task_configs:
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            task = Task(
                id=task_id,
                name=config.get("name", "未命名任务"),
                description=config.get("description", ""),
                priority=config.get("priority", 1),
                dependencies=config.get("dependencies", []),
                parameters=config.get("parameters", {}),
                estimated_duration=config.get("estimated_duration")
            )
            tasks.append(task)
            self.tasks[task_id] = task
        
        # 创建工作流
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            tasks=tasks,
            created_by=user_id
        )
        
        self.workflows[workflow_id] = workflow
        
        logger.info(f"📋 Created workflow: {name} ({workflow_id}) with {len(tasks)} tasks")
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功启动
        """
        if workflow_id not in self.workflows:
            logger.error(f"Workflow not found: {workflow_id}")
            return False
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != TaskStatus.PENDING:
            logger.warning(f"Workflow {workflow_id} is not in pending status")
            return False
        
        # 更新工作流状态
        workflow.status = TaskStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        
        # 将所有就绪的任务加入队列
        ready_tasks = self._find_ready_tasks(workflow.tasks)
        for task in ready_tasks:
            await self.task_queue.put(task.id)
            task.status = TaskStatus.PENDING
        
        logger.info(f"🚀 Started workflow: {workflow.name} ({workflow_id})")
        return True
    
    def _find_ready_tasks(self, tasks: List[Task]) -> List[Task]:
        """找出所有就绪的任务（依赖已完成）"""
        ready_tasks = []
        
        for task in tasks:
            if task.status != TaskStatus.PENDING:
                continue
                
            # 检查所有依赖是否已完成
            dependencies_completed = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )
            
            if dependencies_completed:
                ready_tasks.append(task)
                
        return ready_tasks
    
    async def _execute_task(self, task_id: str):
        """执行单个任务"""
        if task_id not in self.tasks:
            logger.error(f"Task not found: {task_id}")
            return
        
        task = self.tasks[task_id]
        
        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.utcnow()
            start_time = datetime.utcnow()
            
            logger.info(f"🏃 Executing task: {task.name} ({task_id})")
            
            # 选择合适的代理
            agent = await self._assign_agent(task)
            if not agent:
                raise Exception("No suitable agent found for task")
            
            task.assigned_agent = agent.id
            
            # 执行任务
            result = await self._run_task_with_agent(task, agent)
            
            # 更新任务结果
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            task.actual_duration = int((datetime.utcnow() - start_time).total_seconds())
            task.updated_at = datetime.utcnow()
            
            # 释放代理
            if task_id in agent.current_tasks:
                agent.current_tasks.remove(task_id)
            agent.status = "idle"
            agent.last_active = datetime.utcnow()
            
            logger.info(f"✅ Task completed: {task.name} ({task_id})")
            
            # 检查是否有新的就绪任务
            await self._check_dependent_tasks(task_id)
            
        except Exception as e:
            # 任务失败
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.utcnow()
            
            # 释放代理
            if task.assigned_agent and task.assigned_agent in self.agents:
                agent = self.agents[task.assigned_agent]
                if task_id in agent.current_tasks:
                    agent.current_tasks.remove(task_id)
                agent.status = "idle"
            
            logger.error(f"❌ Task failed: {task.name} ({task_id}): {e}")
    
    async def _assign_agent(self, task: Task) -> Optional[Agent]:
        """为任务分配合适的代理"""
        
        # 根据任务类型和参数选择代理
        task_type = task.parameters.get("type", "general")
        
        # 代理选择逻辑
        preferred_agents = []
        
        if task_type in ["technical_analysis", "market_analysis"]:
            preferred_agents = ["analyst-001"]
        elif task_type in ["defi_analysis", "onchain_analysis"]:
            preferred_agents = ["defi-researcher-001"]
        elif task_type in ["sentiment_analysis", "social_analysis"]:
            preferred_agents = ["sentiment-analyst-001"]
        elif task_type == "validation":
            preferred_agents = ["validator-001"]
        elif task_type == "report_generation":
            preferred_agents = ["reporter-001"]
        else:
            # 通用任务，使用协调者
            preferred_agents = ["coordinator-001"]
        
        # 找到可用的代理
        for agent_id in preferred_agents:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                if len(agent.current_tasks) < agent.max_concurrent_tasks:
                    agent.current_tasks.append(task.id)
                    agent.status = "busy"
                    return agent
        
        # 如果首选代理都忙，找任何可用的代理
        for agent in self.agents.values():
            if len(agent.current_tasks) < agent.max_concurrent_tasks:
                agent.current_tasks.append(task.id)
                agent.status = "busy"
                return agent
        
        return None
    
    async def _run_task_with_agent(self, task: Task, agent: Agent) -> Dict[str, Any]:
        """使用代理执行任务"""
        
        task_type = task.parameters.get("type", "general")
        
        # 根据任务类型调用相应的处理方法
        if task_type == "technical_analysis":
            return await self._run_technical_analysis(task, agent)
        elif task_type == "defi_analysis":
            return await self._run_defi_analysis(task, agent)
        elif task_type == "sentiment_analysis":
            return await self._run_sentiment_analysis(task, agent)
        elif task_type == "validation":
            return await self._run_validation(task, agent)
        elif task_type == "report_generation":
            return await self._run_report_generation(task, agent)
        else:
            return await self._run_general_task(task, agent)
    
    async def _run_technical_analysis(self, task: Task, agent: Agent) -> Dict[str, Any]:
        """执行技术分析任务"""
        symbol = task.parameters.get("symbol", "BTCUSDT")
        timeframe = task.parameters.get("timeframe", "1h")
        
        # 模拟技术分析执行
        await asyncio.sleep(2)  # 模拟分析时间
        
        # 更新进度
        task.progress = 50.0
        
        await asyncio.sleep(2)  # 继续分析
        
        return {
            "type": "technical_analysis",
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": {
                "rsi": 65.5,
                "macd": {"value": 0.25, "signal": 0.20},
                "bb": {"upper": 52000, "middle": 50000, "lower": 48000}
            },
            "signals": ["RSI显示超买信号", "MACD金叉形成"],
            "recommendation": "SHORT_TERM_BULLISH",
            "confidence": 0.75,
            "agent_id": agent.id,
            "execution_time": datetime.utcnow().isoformat()
        }
    
    async def _run_defi_analysis(self, task: Task, agent: Agent) -> Dict[str, Any]:
        """执行DeFi分析任务"""
        protocol = task.parameters.get("protocol", "uniswap")
        
        await asyncio.sleep(3)  # 模拟DeFi数据获取
        
        return {
            "type": "defi_analysis", 
            "protocol": protocol,
            "tvl": 1500000000,
            "volume_24h": 850000000,
            "liquidity_health": "GOOD",
            "yield_opportunities": [
                {"pool": "ETH/USDC", "apy": 12.5, "risk": "MEDIUM"},
                {"pool": "WBTC/ETH", "apy": 8.7, "risk": "LOW"}
            ],
            "agent_id": agent.id,
            "execution_time": datetime.utcnow().isoformat()
        }
    
    async def _run_sentiment_analysis(self, task: Task, agent: Agent) -> Dict[str, Any]:
        """执行情绪分析任务"""
        symbol = task.parameters.get("symbol", "bitcoin")
        
        await asyncio.sleep(2.5)  # 模拟情绪数据收集
        
        return {
            "type": "sentiment_analysis",
            "symbol": symbol,
            "sentiment_score": 72.3,
            "fear_greed_index": 68,
            "social_mentions": 15420,
            "news_sentiment": "POSITIVE",
            "key_topics": ["价格突破", "机构采用", "监管明确"],
            "agent_id": agent.id,
            "execution_time": datetime.utcnow().isoformat()
        }
    
    async def _run_validation(self, task: Task, agent: Agent) -> Dict[str, Any]:
        """执行验证任务"""
        results_to_validate = task.parameters.get("results", [])
        
        await asyncio.sleep(1.5)  # 模拟验证过程
        
        return {
            "type": "validation",
            "validation_score": 0.85,
            "consistency_check": "PASSED",
            "outliers_detected": 0,
            "confidence_level": "HIGH", 
            "validated_count": len(results_to_validate),
            "agent_id": agent.id,
            "execution_time": datetime.utcnow().isoformat()
        }
    
    async def _run_report_generation(self, task: Task, agent: Agent) -> Dict[str, Any]:
        """执行报告生成任务"""
        report_type = task.parameters.get("report_type", "summary")
        data_sources = task.parameters.get("data_sources", [])
        
        await asyncio.sleep(3.5)  # 模拟报告生成
        
        return {
            "type": "report_generation",
            "report_type": report_type,
            "sections": [
                {"title": "执行摘要", "status": "COMPLETED"},
                {"title": "市场分析", "status": "COMPLETED"},
                {"title": "风险评估", "status": "COMPLETED"}, 
                {"title": "投资建议", "status": "COMPLETED"}
            ],
            "word_count": 2500,
            "charts_generated": 8,
            "agent_id": agent.id,
            "execution_time": datetime.utcnow().isoformat()
        }
    
    async def _run_general_task(self, task: Task, agent: Agent) -> Dict[str, Any]:
        """执行通用任务"""
        await asyncio.sleep(1)  # 模拟处理时间
        
        return {
            "type": "general",
            "task_name": task.name,
            "status": "completed",
            "agent_id": agent.id,
            "execution_time": datetime.utcnow().isoformat()
        }
    
    async def _check_dependent_tasks(self, completed_task_id: str):
        """检查依赖任务是否可以执行"""
        
        # 找到所有依赖这个任务的任务
        for workflow in self.workflows.values():
            if workflow.status != TaskStatus.RUNNING:
                continue
                
            ready_tasks = self._find_ready_tasks(workflow.tasks)
            for task in ready_tasks:
                if completed_task_id in task.dependencies:
                    await self.task_queue.put(task.id)
                    task.status = TaskStatus.PENDING
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        if workflow_id not in self.workflows:
            return None
        
        workflow = self.workflows[workflow_id]
        
        # 计算总体进度
        if not workflow.tasks:
            progress = 0.0
        else:
            total_progress = sum(task.progress for task in workflow.tasks)
            progress = total_progress / len(workflow.tasks)
        
        # 统计任务状态
        status_counts = {}
        for task in workflow.tasks:
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "workflow": workflow.to_dict(),
            "progress": round(progress, 1),
            "task_counts": status_counts,
            "active_agents": list(set(
                task.assigned_agent for task in workflow.tasks 
                if task.assigned_agent and task.status == TaskStatus.RUNNING
            ))
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流执行"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        workflow.status = TaskStatus.CANCELLED
        
        # 取消所有未完成的任务
        for task in workflow.tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.CANCELLED
                task.updated_at = datetime.utcnow()
                
                # 释放代理
                if task.assigned_agent and task.assigned_agent in self.agents:
                    agent = self.agents[task.assigned_agent]
                    if task.id in agent.current_tasks:
                        agent.current_tasks.remove(task.id)
                    if not agent.current_tasks:
                        agent.status = "idle"
        
        logger.info(f"🚫 Cancelled workflow: {workflow.name} ({workflow_id})")
        return True
    
    def get_agents_status(self) -> Dict[str, Any]:
        """获取所有代理状态"""
        return {
            "agents": [agent.to_dict() for agent in self.agents.values()],
            "total_agents": len(self.agents),
            "busy_agents": len([a for a in self.agents.values() if a.status == "busy"]),
            "idle_agents": len([a for a in self.agents.values() if a.status == "idle"])
        }
    
    async def create_analysis_workflow(
        self,
        symbol: str,
        analysis_types: List[str],
        user_id: Optional[int] = None
    ) -> str:
        """创建标准分析工作流"""
        
        task_configs = []
        
        # 技术分析任务
        if "technical" in analysis_types:
            task_configs.append({
                "name": f"{symbol} 技术分析",
                "description": f"对{symbol}进行技术指标分析",
                "type": "technical_analysis",
                "priority": 1,
                "parameters": {
                    "type": "technical_analysis",
                    "symbol": symbol,
                    "timeframe": "1h"
                },
                "estimated_duration": 30
            })
        
        # DeFi分析任务
        if "defi" in analysis_types:
            task_configs.append({
                "name": f"{symbol} DeFi分析", 
                "description": f"分析{symbol}的DeFi生态",
                "type": "defi_analysis",
                "priority": 1,
                "parameters": {
                    "type": "defi_analysis",
                    "symbol": symbol
                },
                "estimated_duration": 45
            })
        
        # 情绪分析任务
        if "sentiment" in analysis_types:
            task_configs.append({
                "name": f"{symbol} 情绪分析",
                "description": f"分析{symbol}的市场情绪",
                "type": "sentiment_analysis", 
                "priority": 1,
                "parameters": {
                    "type": "sentiment_analysis",
                    "symbol": symbol
                },
                "estimated_duration": 25
            })
        
        # 验证任务（依赖前面的分析任务）
        validation_dependencies = []
        for i in range(len(task_configs)):
            validation_dependencies.append(f"task_{i}")  # 这将在实际创建时被替换为真实ID
        
        task_configs.append({
            "name": f"{symbol} 结果验证",
            "description": "验证分析结果的一致性",
            "type": "validation",
            "priority": 2,
            "dependencies": validation_dependencies,
            "parameters": {
                "type": "validation",
                "symbol": symbol
            },
            "estimated_duration": 15
        })
        
        # 报告生成任务（依赖验证任务）
        task_configs.append({
            "name": f"{symbol} 综合报告",
            "description": "生成综合分析报告",
            "type": "report_generation", 
            "priority": 3,
            "dependencies": ["validation_task"],  # 将被替换为真实ID
            "parameters": {
                "type": "report_generation",
                "symbol": symbol,
                "report_type": "comprehensive"
            },
            "estimated_duration": 40
        })
        
        # 创建工作流
        workflow_id = await self.create_workflow(
            name=f"{symbol} 综合分析",
            description=f"对{symbol}进行全面的技术、DeFi和情绪分析",
            task_configs=task_configs,
            user_id=user_id
        )
        
        return workflow_id


# 创建全局代理引擎实例
agent_engine = AgentEngine()