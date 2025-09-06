"""
分析任务模型
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.sql import func

from core.infrastructure.database import Base


class AnalysisTask(Base):
    """分析任务表 - 记录用户的交易分析任务"""
    
    __tablename__ = "analysis_tasks"
    
    # 主键
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # 用户ID（不再关联表）
    user_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    
    # 任务信息
    task_type = Column(String(50), nullable=False)  # technical, fundamental, sentiment, etc
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    
    # 分析目标
    market_type = Column(String(50), nullable=False)  # crypto, stock, forex, etc
    symbol = Column(String(50), nullable=False)  # BTC/USDT, AAPL, etc
    
    # 任务参数
    parameters = Column(JSON, default=dict)  # 时间范围、指标等参数
    
    # 分析结果
    result_data = Column(JSON)  # 存储分析结果
    error_message = Column(String)  # 错误信息（如果失败）
    
    # AI使用ID（不再关联表）
    ai_usage_id = Column(PostgresUUID(as_uuid=True))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # 索引
    __table_args__ = (
        Index("idx_analysis_tasks_user_id", "user_id"),
        Index("idx_analysis_tasks_status", "status"),
        Index("idx_analysis_tasks_created_at", "created_at"),
        Index("idx_analysis_tasks_user_status", "user_id", "status"),
        Index("idx_analysis_tasks_symbol", "symbol"),
    )
    
    def __repr__(self):
        return f"<AnalysisTask {self.task_type} {self.symbol} {self.status}>"