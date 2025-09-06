"""
工具管理相关的 Pydantic 模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
from enum import Enum


class ToolTypeEnum(str, Enum):
    """工具类型枚举"""
    BUILTIN = "builtin"
    MCP = "mcp"
    CUSTOM = "custom"
    MARKETPLACE = "marketplace"


class ConnectionStatusEnum(str, Enum):
    """连接状态枚举"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


class UserToolResponse(BaseModel):
    """用户工具响应模型"""
    id: int
    tool_id: str
    tool_name: str
    tool_type: ToolTypeEnum
    connection_status: ConnectionStatusEnum
    configuration: Dict[str, Any] = {}
    permissions: List[str] = []
    last_used: Optional[datetime] = None
    created_at: datetime
    is_active: bool = True
    version: Optional[str] = None
    marketplace_url: Optional[str] = None


class ToolConfigurationRequest(BaseModel):
    """工具配置请求模型"""
    tool_id: str = Field(..., min_length=1)
    settings: Dict[str, Any] = {}
    permissions: List[str] = []


class ToolConnectRequest(BaseModel):
    """连接工具请求模型"""
    tool_id: str = Field(..., min_length=1)
    tool_name: str = Field(..., min_length=1)
    tool_type: ToolTypeEnum = ToolTypeEnum.CUSTOM
    configuration: ToolConfigurationRequest


class ToolPermissionsUpdateRequest(BaseModel):
    """工具权限更新请求模型"""
    permissions: List[str] = Field(..., min_items=0)
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v):
        # 验证权限格式
        for perm in v:
            if not perm or ':' not in perm:
                raise ValueError(f"无效的权限格式: {perm}")
        return v


class MCPConnectionResponse(BaseModel):
    """MCP连接响应模型"""
    id: int
    server_name: str
    server_url: str
    connection_status: ConnectionStatusEnum
    available_tools: List[str] = []
    last_sync: Optional[datetime] = None
    created_at: datetime
    is_active: bool = True
    error_message: Optional[str] = None


class MCPConnectRequest(BaseModel):
    """连接MCP服务器请求模型"""
    server_name: str = Field(..., min_length=1)
    server_url: HttpUrl


class ToolStatsResponse(BaseModel):
    """工具使用统计响应模型"""
    tool_id: str
    usage_count: int = 0
    last_used: Optional[datetime] = None
    total_cost: float = 0.0
    average_response_time: float = 0.0


class MarketplaceToolResponse(BaseModel):
    """市场工具响应模型"""
    tool_id: str
    name: str
    description: str
    category: str
    rating: float = Field(..., ge=0, le=5)
    installs: int = 0
    price: float = 0.0
    marketplace_url: str


class ToolListResponse(BaseModel):
    """工具列表响应模型"""
    tools: List[UserToolResponse]
    total: int
    page: int = 1
    page_size: int = 20


class MCPConnectionListResponse(BaseModel):
    """MCP连接列表响应模型"""
    connections: List[MCPConnectionResponse]
    total: int


class MarketplaceRecommendationsResponse(BaseModel):
    """市场推荐响应模型"""
    recommendations: List[MarketplaceToolResponse]
    based_on: str = "usage_pattern"  # usage_pattern, popular, new, similar