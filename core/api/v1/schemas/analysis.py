"""
分析相关的Pydantic模型
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum
from core.database.enums import AnalysisStatus, MarketType


class LLMProvider(str, Enum):
    """LLM提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: LLMProvider
    model: str
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)


class AnalysisRequest(BaseModel):
    """创建分析任务请求"""
    symbol: str = Field(..., min_length=1, max_length=20)
    market_type: MarketType
    analysis_depth: int = Field(default=3, ge=1, le=5)
    analysts: List[str] = Field(default=["technical", "fundamental", "sentiment", "risk"])
    llm_config: Optional[LLMConfig] = None
    
    @field_validator('analysts')
    @classmethod
    def validate_analysts(cls, v):
        valid_analysts = {"technical", "fundamental", "sentiment", "risk", "market"}
        for analyst in v:
            if analyst not in valid_analysts:
                raise ValueError(f"Invalid analyst type: {analyst}")
        return v


class AnalysisTaskResponse(BaseModel):
    """分析任务响应"""
    id: UUID
    user_id: int
    symbol: str
    market_type: MarketType
    analysis_depth: int
    analysts: List[str]
    llm_config: Dict[str, Any]
    status: AnalysisStatus
    progress: int
    error_message: Optional[str]
    token_usage: Dict[str, int]
    cost_usd: float
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AnalysisReportResponse(BaseModel):
    """分析报告响应"""
    id: UUID
    task_id: UUID
    analyst_type: str
    content: Dict[str, Any]
    summary: str
    rating: Optional[str]
    confidence_score: Optional[float]
    key_findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnalysisLogResponse(BaseModel):
    """分析日志响应"""
    id: UUID
    task_id: UUID
    timestamp: datetime
    level: str
    agent_name: Optional[str]
    message: str
    details: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class AnalysisProgress(BaseModel):
    """分析进度更新"""
    task_id: UUID
    status: AnalysisStatus
    progress: int
    current_step: Optional[str]
    message: Optional[str]


class AnalysisStatistics(BaseModel):
    """用户分析统计"""
    task_statistics: Dict[str, int]
    total_reports: int
    total_cost: float
    average_duration_minutes: float
    most_analyzed_symbols: List[Dict[str, Any]]
    user_since: datetime