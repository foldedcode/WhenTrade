"""
用户工具配置 Schema
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class UserToolConfigBase(BaseModel):
    """用户工具配置基础模型"""
    tool_id: str = Field(..., description="工具唯一标识")
    tool_type: str = Field(..., description="工具类型：builtin 或 mcp")
    is_enabled: bool = Field(False, description="是否启用（内置工具）")
    is_connected: bool = Field(False, description="是否连接（MCP工具）")
    connection_config: Dict[str, Any] = Field(default_factory=dict, description="MCP连接配置")
    user_settings: Dict[str, Any] = Field(default_factory=dict, description="用户自定义设置")


class UserToolConfigCreate(UserToolConfigBase):
    """创建用户工具配置"""
    pass


class UserToolConfigUpdate(BaseModel):
    """更新用户工具配置"""
    is_enabled: Optional[bool] = None
    is_connected: Optional[bool] = None
    connection_config: Optional[Dict[str, Any]] = None
    user_settings: Optional[Dict[str, Any]] = None


class UserToolConfigInDB(UserToolConfigBase):
    """数据库中的用户工具配置"""
    id: int
    user_id: int
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserToolConfigResponse(UserToolConfigInDB):
    """用户工具配置响应"""
    pass


class UserToolStats(BaseModel):
    """用户工具使用统计"""
    tool_id: str
    tool_type: str
    usage_count: int
    last_used_at: Optional[datetime]
    is_enabled: bool
    is_connected: bool