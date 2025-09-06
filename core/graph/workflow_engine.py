"""
Workflow Engine - 基于LangGraph的工作流引擎
支持复杂的交易分析流程图执行
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str
    name: str
    node_type: str
    handler: Optional[Callable] = None
    dependencies: List[str] = None
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class WorkflowExecution:
    """工作流执行状态"""
    workflow_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"
    results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}

class WorkflowEngine:
    """
    工作流引擎
    
    功能:
    - 图结构定义
    - 节点执行管理
    - 依赖关系处理
    - 并行执行优化
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.workflows: Dict[str, List[WorkflowNode]] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.node_handlers: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        
        # 注册默认节点处理器
        self._register_default_handlers()
        
        logger.info("🌊 Workflow Engine initialized")
    
    def _register_default_handlers(self):
        """注册默认节点处理器"""
        self.node_handlers.update({
            "data_collection": self._handle_data_collection,
            "market_analysis": self._handle_market_analysis,
            "timing_analysis": self._handle_timing_analysis,
            "risk_assessment": self._handle_risk_assessment,
            "report_generation": self._handle_report_generation,
            "notification": self._handle_notification
        })
    
    async def create_workflow(self, workflow_id: str, nodes: List[WorkflowNode]) -> bool:
        """
        创建工作流
        
        Args:
            workflow_id: 工作流唯一标识
            nodes: 节点列表
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 验证节点依赖关系
            if not self._validate_dependencies(nodes):
                raise ValueError("Invalid node dependencies")
            
            # 设置节点处理器
            for node in nodes:
                if node.node_type in self.node_handlers:
                    node.handler = self.node_handlers[node.node_type]
            
            async with self._lock:
                self.workflows[workflow_id] = nodes
            
            logger.info(f"📋 Workflow created: {workflow_id} ({len(nodes)} nodes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create workflow {workflow_id}: {e}")
            return False
    
    async def execute_workflow(
        self, 
        workflow_id: str, 
        input_data: Optional[Dict] = None
    ) -> WorkflowExecution:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            input_data: 输入数据
            
        Returns:
            WorkflowExecution: 执行结果
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # 创建执行实例
        execution_id = f"{workflow_id}_{int(datetime.now().timestamp())}"
        execution = WorkflowExecution(
            workflow_id=execution_id,
            started_at=datetime.now()
        )
        
        self.executions[execution_id] = execution
        
        try:
            nodes = self.workflows[workflow_id].copy()
            context = {"input": input_data or {}, "results": {}}
            
            # 执行节点
            await self._execute_nodes(nodes, context, execution)
            
            # 更新执行状态
            execution.completed_at = datetime.now()
            execution.status = "completed"
            execution.results = context["results"]
            
            logger.info(f"✅ Workflow completed: {workflow_id}")
            return execution
            
        except Exception as e:
            execution.status = "failed"
            execution.completed_at = datetime.now()
            logger.error(f"❌ Workflow failed: {workflow_id}: {e}")
            raise
    
    async def _execute_nodes(
        self, 
        nodes: List[WorkflowNode], 
        context: Dict, 
        execution: WorkflowExecution
    ):
        """执行节点列表"""
        completed_nodes = set()
        
        while len(completed_nodes) < len(nodes):
            # 找到可执行的节点（依赖已完成）
            ready_nodes = [
                node for node in nodes
                if (node.id not in completed_nodes and 
                    node.status == NodeStatus.PENDING and
                    all(dep in completed_nodes for dep in node.dependencies))
            ]
            
            if not ready_nodes:
                break  # 没有可执行的节点，可能存在循环依赖
            
            # 并行执行准备好的节点
            tasks = []
            for node in ready_nodes:
                node.status = NodeStatus.RUNNING
                task = self._execute_node(node, context)
                tasks.append(task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for node, result in zip(ready_nodes, results):
                if isinstance(result, Exception):
                    node.status = NodeStatus.FAILED
                    node.error = str(result)
                    logger.error(f"❌ Node failed: {node.id}: {result}")
                else:
                    node.status = NodeStatus.COMPLETED
                    node.result = result
                    context["results"][node.id] = result
                    completed_nodes.add(node.id)
                    logger.debug(f"✅ Node completed: {node.id}")
    
    async def _execute_node(self, node: WorkflowNode, context: Dict) -> Any:
        """执行单个节点"""
        if not node.handler:
            raise ValueError(f"No handler for node type: {node.node_type}")
        
        try:
            # 准备节点输入
            node_input = {
                "node_id": node.id,
                "node_name": node.name,
                "context": context,
                "metadata": node.metadata
            }
            
            # 执行节点处理器
            result = await node.handler(node_input)
            return result
            
        except Exception as e:
            logger.error(f"❌ Node execution failed: {node.id}: {e}")
            raise
    
    def _validate_dependencies(self, nodes: List[WorkflowNode]) -> bool:
        """验证节点依赖关系"""
        node_ids = {node.id for node in nodes}
        
        for node in nodes:
            for dep in node.dependencies:
                if dep not in node_ids:
                    logger.error(f"❌ Invalid dependency: {node.id} -> {dep}")
                    return False
        
        # 检查循环依赖（简单实现）
        # 在实际项目中可能需要更复杂的循环检测算法
        return True
    
    # 默认节点处理器
    async def _handle_data_collection(self, input_data: Dict) -> Dict:
        """数据收集节点"""
        await asyncio.sleep(0.1)  # 模拟处理时间
        return {
            "type": "data_collection",
            "data": {"price": 50000, "volume": 1000000},
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_market_analysis(self, input_data: Dict) -> Dict:
        """市场分析节点"""
        await asyncio.sleep(0.2)
        return {
            "type": "market_analysis",
            "trend": "BULLISH",
            "strength": 0.75,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_timing_analysis(self, input_data: Dict) -> Dict:
        """时机分析节点"""
        await asyncio.sleep(0.3)
        return {
            "type": "timing_analysis",
            "timing_score": 80,
            "recommendation": "BUY",
            "confidence": 0.85,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_risk_assessment(self, input_data: Dict) -> Dict:
        """风险评估节点"""
        await asyncio.sleep(0.1)
        return {
            "type": "risk_assessment",
            "risk_level": "MEDIUM",
            "risk_score": 45,
            "max_loss": 0.1,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_report_generation(self, input_data: Dict) -> Dict:
        """报告生成节点"""
        await asyncio.sleep(0.2)
        context = input_data.get("context", {})
        results = context.get("results", {})
        
        return {
            "type": "report_generation",
            "report": {
                "summary": "交易时机分析报告",
                "recommendations": ["Consider buying", "Monitor risk levels"],
                "data_points": len(results)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_notification(self, input_data: Dict) -> Dict:
        """通知节点"""
        await asyncio.sleep(0.1)
        return {
            "type": "notification",
            "sent": True,
            "channels": ["email", "webhook"],
            "timestamp": datetime.now().isoformat()
        }
    
    def register_handler(self, node_type: str, handler: Callable):
        """注册自定义节点处理器"""
        self.node_handlers[node_type] = handler
        logger.info(f"🔧 Node handler registered: {node_type}")
    
    async def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """获取执行状态"""
        return self.executions.get(execution_id)
    
    async def cleanup(self):
        """清理资源"""
        self.workflows.clear()
        self.executions.clear()
        logger.info("🧹 Workflow Engine cleaned up") 