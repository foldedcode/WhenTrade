"""
分析相关端点（简化版）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from core.database.session import get_db
from core.database.models.analysis_task import AnalysisTask
from pydantic import BaseModel
from core.tasks import process_analysis_task

router = APIRouter(prefix="/analysis", tags=["analysis"])



class AnalysisRequest(BaseModel):
    """分析请求"""
    symbol: str
    analysis_type: str = "technical"
    timeframe: str = "1d"
    parameters: Optional[dict] = None
    # 兼容前端直接发送的字段
    market_type: Optional[str] = None
    depth: Optional[int] = None
    analysis_scopes: Optional[list] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class AnalysisTaskResponse(BaseModel):
    """分析任务响应"""
    id: UUID
    user_id: UUID
    task_type: str
    status: str
    market_type: str
    symbol: str
    created_at: datetime
    # updated_at字段已移除，因为数据库模型中不存在

    class Config:
        from_attributes = True


@router.post("/tasks", response_model=AnalysisTaskResponse)
async def create_analysis_task(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """创建新的分析任务"""
    
    import os
    
    # 开发模式：使用内存模式，不使用数据库（因为已移除认证）
    if os.getenv('DEVELOPMENT', 'true').lower() == 'true':
        from datetime import datetime
        task_id = uuid4()
        
        # 创建内存中的任务对象
        task = type('Task', (), {
            'id': task_id,
            'user_id': uuid4(),
            'task_type': request.analysis_type,
            'status': 'pending',
            'market_type': request.market_type or 'crypto',
            'symbol': request.symbol,
            'created_at': datetime.utcnow(),
            'parameters': request.parameters or {}
        })()
        
        # 启动分析（使用真实的分析流程）
        import logging
        logging.info(f"Dev mode: Starting analysis task {task_id}")
        
        # 这里可以直接调用分析逻辑，或者通过WebSocket处理
        # 暂时返回任务信息，让WebSocket处理实际分析
        
        return AnalysisTaskResponse(
            id=task.id,
            user_id=task.user_id,
            task_type=task.task_type,
            status=task.status,
            market_type=task.market_type,
            symbol=task.symbol,
            created_at=task.created_at
        )
    
    try:
        # 提取市场类型
        if request.market_type:
            market_type = request.market_type
        elif request.parameters and "market_type" in request.parameters:
            market_type = request.parameters["market_type"]
        else:
            market_type = "crypto"
        
        # 合并所有参数
        all_parameters = request.parameters or {}
        if request.depth is not None:
            all_parameters["depth"] = request.depth
        if request.analysis_scopes is not None:
            all_parameters["analysis_scopes"] = request.analysis_scopes
        if request.llm_provider:
            all_parameters["llm_provider"] = request.llm_provider
        if request.llm_model:
            all_parameters["llm_model"] = request.llm_model
        
        # 创建任务 - 使用固定的默认user_id以避免外键约束问题
        # 这个UUID是一个固定值，需要确保在users表中存在这条记录
        default_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        task = AnalysisTask(
            id=uuid4(),
            user_id=default_user_id,  # 使用默认用户ID
            task_type=request.analysis_type,
            status="pending",
            market_type=market_type,
            symbol=request.symbol,
            parameters=all_parameters
            # 移除created_at，让数据库使用server_default自动设置
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # 启动Celery后台任务执行分析
        import logging
        logging.info(f"Starting Celery task for analysis {task.id}")
        
        # 准备任务参数 - 扁平化结构避免双重嵌套
        task_params = {
            "symbol": request.symbol,
            "analysis_type": request.analysis_type,
            "timeframe": request.timeframe,
            "market_type": task.market_type,
            "analysis_scopes": all_parameters.get("analysis_scopes", ["technical"]),
            "llm_provider": all_parameters.get("llm_provider", "deepseek"),
            "llm_model": all_parameters.get("llm_model", "deepseek-chat"),
            "depth": all_parameters.get("depth", 3),
            "user_id": str(uuid4())
        }
        
        # 异步启动Celery任务
        process_analysis_task.delay(str(task.id), task_params)
        logging.info(f"Celery task started for analysis {task.id}")
        
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Failed to create analysis task: {str(e)}")
        logging.error(f"Exception type: {type(e).__name__}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        logging.error(f"Request data: symbol={request.symbol}, type={request.analysis_type}, params={request.parameters}")
        raise HTTPException(status_code=422, detail=f"Failed to create task: {str(e)}")
    
    return AnalysisTaskResponse.model_validate(task)


@router.get("/tasks", response_model=List[AnalysisTaskResponse])
async def get_analysis_tasks(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取分析任务列表"""
    
    query = select(AnalysisTask)
    
    if status:
        query = query.where(AnalysisTask.status == status)
    
    query = query.order_by(AnalysisTask.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [AnalysisTaskResponse.model_validate(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=AnalysisTaskResponse)
async def get_analysis_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取特定的分析任务"""
    
    result = await db.execute(
        select(AnalysisTask).where(
            AnalysisTask.id == task_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return AnalysisTaskResponse.model_validate(task)


@router.delete("/tasks/{task_id}")
async def cancel_analysis_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """取消分析任务（增强版）"""
    import logging
    
    # 转换UUID为字符串以便与WebSocket系统兼容
    task_id_str = str(task_id)
    
    logger = logging.getLogger(__name__)
    logger.info(f"🛑 HTTP DELETE取消请求: {task_id_str}")
    
    # 1. 首先尝试停止WebSocket中的活动任务
    try:
        # 导入WebSocket的活动任务追踪
        from .analysis_ws import active_analysis_threads, active_analysis_tasks
        
        cancelled_websocket = False
        
        # 停止正在运行的线程
        if task_id_str in active_analysis_threads:
            thread, stop_event = active_analysis_threads[task_id_str]
            stop_event.set()  # 发送停止信号给线程
            logger.info(f"🧵 WebSocket线程停止信号已发送: {task_id_str}")
            del active_analysis_threads[task_id_str]
            cancelled_websocket = True
        
        # 取消asyncio任务
        if task_id_str in active_analysis_tasks:
            task = active_analysis_tasks[task_id_str]
            if not task.done():
                task.cancel()
                logger.info(f"⚡ Asyncio任务已取消: {task_id_str}")
            del active_analysis_tasks[task_id_str]
            cancelled_websocket = True
            
        if cancelled_websocket:
            logger.info(f"✅ WebSocket任务取消成功: {task_id_str}")
        else:
            logger.info(f"ℹ️ 未找到活动的WebSocket任务: {task_id_str}")
            
    except Exception as e:
        logger.warning(f"⚠️ WebSocket任务取消失败: {e}")
        # 继续执行数据库更新，即使WebSocket取消失败
    
    # 2. 更新数据库状态（如果使用数据库模式）
    if not True:  # 当前使用内存模式，跳过数据库操作
        result = await db.execute(
            select(AnalysisTask).where(
                AnalysisTask.id == task_id
            )
        )
        task = result.scalar_one_or_none()
        
        if not task:
            # 如果WebSocket取消成功，仍然返回成功
            if cancelled_websocket:
                return {"message": f"WebSocket任务已取消: {task_id_str}", "status": "cancelled"}
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status not in ["pending", "processing"]:
            # 如果WebSocket取消成功，允许更新
            if not cancelled_websocket:
                raise HTTPException(status_code=400, detail="任务无法取消")
        
        task.status = "cancelled"
        await db.commit()
    
    return {
        "message": f"任务已取消: {task_id_str}", 
        "status": "cancelled",
        "websocket_cancelled": cancelled_websocket if 'cancelled_websocket' in locals() else False
    }