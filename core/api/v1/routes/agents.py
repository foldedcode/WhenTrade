"""
Agent Engine API端点
管理智能代理和工作流执行
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import logging

from core.agents.engine import agent_engine, TaskStatus, AgentRole
from core.services.agent_mapping import AgentMappingService
# from .auth import get_current_user  # 临时注释，等待认证系统集成
# from ..models.user import User  # 临时注释，等待认证系统集成

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkflowCreateRequest(BaseModel):
    """工作流创建请求"""
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述") 
    tasks: List[Dict[str, Any]] = Field(..., description="任务配置列表")


class AnalysisWorkflowRequest(BaseModel):
    """分析工作流请求"""
    symbol: str = Field(..., description="分析标的")
    analysis_types: List[str] = Field(..., description="分析类型列表")
    

class TaskUpdateRequest(BaseModel):
    """任务更新请求"""
    status: Optional[str] = Field(None, description="任务状态")
    progress: Optional[float] = Field(None, description="任务进度")


@router.get("/status")
async def get_engine_status():  # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
    """获取代理引擎整体状态"""
    try:
        agents_status = agent_engine.get_agents_status()
        
        # 统计工作流信息
        total_workflows = len(agent_engine.workflows)
        active_workflows = len([
            w for w in agent_engine.workflows.values() 
            if w.status == TaskStatus.RUNNING
        ])
        
        # 统计任务信息
        total_tasks = len(agent_engine.tasks)
        running_tasks = len([
            t for t in agent_engine.tasks.values()
            if t.status == TaskStatus.RUNNING
        ])
        
        return {
            "success": True,
            "engine_running": agent_engine.running,
            "agents": agents_status,
            "workflows": {
                "total": total_workflows,
                "active": active_workflows
            },
            "tasks": {
                "total": total_tasks,
                "running": running_tasks,
                "queued": agent_engine.task_queue.qsize()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get engine status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_engine(
    background_tasks: BackgroundTasks,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """启动代理引擎"""
    try:
        if agent_engine.running:
            return {
                "success": True,
                "message": "Agent Engine is already running"
            }
        
        # 在后台启动引擎
        background_tasks.add_task(agent_engine.start)
        
        return {
            "success": True,
            "message": "Agent Engine started successfully"
        }
    except Exception as e:
        logger.error(f"Failed to start engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_engine():  # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
    """停止代理引擎"""
    try:
        await agent_engine.stop()
        
        return {
            "success": True,
            "message": "Agent Engine stopped successfully"
        }
    except Exception as e:
        logger.error(f"Failed to stop engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents():  # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
    """获取所有代理列表"""
    try:
        agents_status = agent_engine.get_agents_status()
        return {
            "success": True,
            "agents": agents_status["agents"]
        }
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """获取代理详细信息"""
    try:
        if agent_id not in agent_engine.agents:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent = agent_engine.agents[agent_id]
        
        # 获取代理的任务历史
        agent_tasks = [
            task.to_dict() for task in agent_engine.tasks.values()
            if task.assigned_agent == agent_id
        ]
        
        return {
            "success": True,
            "agent": agent.to_dict(),
            "task_history": agent_tasks,
            "current_load": len(agent.current_tasks)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows")
async def create_workflow(
    request: WorkflowCreateRequest,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """创建自定义工作流"""
    try:
        workflow_id = await agent_engine.create_workflow(
            name=request.name,
            description=request.description,
            task_configs=request.tasks,
            user_id="temp_user_id"  # 临时用户ID，等待认证系统集成
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": f"Workflow '{request.name}' created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/analysis")
async def create_analysis_workflow(
    request: AnalysisWorkflowRequest,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """创建标准分析工作流"""
    try:
        workflow_id = await agent_engine.create_analysis_workflow(
            symbol=request.symbol,
            analysis_types=request.analysis_types,
            user_id="temp_user_id"  # 临时用户ID，等待认证系统集成
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": f"Analysis workflow for {request.symbol} created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create analysis workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def list_workflows():  # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
    """获取用户的工作流列表"""
    try:
        user_workflows = [
            workflow.to_dict() for workflow in agent_engine.workflows.values()
            if workflow.created_by == "temp_user_id" or workflow.created_by is None  # 临时用户ID，等待认证系统集成
        ]
        
        return {
            "success": True,
            "workflows": user_workflows,
            "total": len(user_workflows)
        }
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """获取工作流状态"""
    try:
        status = await agent_engine.get_workflow_status(workflow_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "success": True,
            **status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """执行工作流"""
    try:
        # 确保引擎正在运行
        if not agent_engine.running:
            background_tasks.add_task(agent_engine.start)
        
        success = await agent_engine.execute_workflow(workflow_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Failed to start workflow execution"
            )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow execution started successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """取消工作流执行"""
    try:
        success = await agent_engine.cancel_workflow(workflow_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """获取任务详细信息"""
    try:
        if task_id not in agent_engine.tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = agent_engine.tasks[task_id]
        
        return {
            "success": True,
            "task": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_engine_analytics():  # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
    """获取引擎分析统计"""
    try:
        # 计算各种统计指标
        total_tasks = len(agent_engine.tasks)
        completed_tasks = len([
            t for t in agent_engine.tasks.values()
            if t.status == TaskStatus.COMPLETED
        ])
        failed_tasks = len([
            t for t in agent_engine.tasks.values()
            if t.status == TaskStatus.FAILED
        ])
        
        # 计算平均执行时间
        completed_with_duration = [
            t for t in agent_engine.tasks.values()
            if t.status == TaskStatus.COMPLETED and t.actual_duration
        ]
        avg_duration = (
            sum(t.actual_duration for t in completed_with_duration) / len(completed_with_duration)
            if completed_with_duration else 0
        )
        
        # 代理利用率
        total_capacity = sum(agent.max_concurrent_tasks for agent in agent_engine.agents.values())
        current_load = sum(len(agent.current_tasks) for agent in agent_engine.agents.values())
        utilization_rate = (current_load / total_capacity * 100) if total_capacity > 0 else 0
        
        # 按代理统计任务
        agent_task_counts = {}
        for task in agent_engine.tasks.values():
            if task.assigned_agent:
                agent_task_counts[task.assigned_agent] = agent_task_counts.get(task.assigned_agent, 0) + 1
        
        return {
            "success": True,
            "analytics": {
                "task_statistics": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "failed": failed_tasks,
                    "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                },
                "performance": {
                    "avg_execution_time": round(avg_duration, 2),
                    "utilization_rate": round(utilization_rate, 2)
                },
                "agent_workload": agent_task_counts,
                "system_health": {
                    "engine_running": agent_engine.running,
                    "queue_size": agent_engine.task_queue.qsize(),
                    "active_workflows": len([
                        w for w in agent_engine.workflows.values()
                        if w.status == TaskStatus.RUNNING
                    ])
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Agent Engine健康检查"""
    try:
        return {
            "success": True,
            "status": "healthy" if agent_engine.running else "stopped",
            "agents_count": len(agent_engine.agents),
            "active_workflows": len([
                w for w in agent_engine.workflows.values()
                if w.status == TaskStatus.RUNNING
            ]),
            "queue_size": agent_engine.task_queue.qsize()
        }
    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/teams")
async def get_agent_teams(
    market_type: str = "crypto",
    analysis_scopes: str = None  # 逗号分隔的分析范围列表
    # current_user: User = Depends(get_current_user)  # 临时注释，等待认证系统集成
):
    """
    获取智能体团队配置
    
    Args:
        market_type: 市场类型 (crypto/polymarket)
        analysis_scopes: 分析范围列表（逗号分隔）
        
    Returns:
        团队配置信息
    """
    try:
        # 获取基础团队配置
        teams_config = AgentMappingService.get_teams_config(market_type)
        
        # 如果提供了分析范围，获取动态agents
        if analysis_scopes:
            scopes_list = [s.strip() for s in analysis_scopes.split(',') if s.strip()]
            if scopes_list:
                # 获取基于分析范围的动态agents
                dynamic_agents = AgentMappingService.get_agents_for_task(market_type, scopes_list)
                
                # 更新团队配置中的agents
                if "teams" in teams_config:
                    for team_key, agents_list in dynamic_agents.items():
                        if team_key in teams_config["teams"]:
                            teams_config["teams"][team_key]["agents"] = agents_list
        
        return {
            "success": True,
            "data": teams_config
        }
    except Exception as e:
        logger.error(f"Failed to get agent teams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 启动事件：自动启动代理引擎
@router.on_event("startup")
async def startup_event():
    """API启动时自动启动代理引擎"""
    try:
        logger.info("🚀 Starting Agent Engine...")
        await agent_engine.start()
    except Exception as e:
        logger.error(f"Failed to auto-start Agent Engine: {e}")


# 关闭事件：停止代理引擎
@router.on_event("shutdown")
async def shutdown_event():
    """API关闭时停止代理引擎"""
    try:
        logger.info("🛑 Stopping Agent Engine...")
        await agent_engine.stop()
    except Exception as e:
        logger.error(f"Failed to stop Agent Engine: {e}")