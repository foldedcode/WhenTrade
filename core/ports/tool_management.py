"""
工具管理接口定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ToolType(str, Enum):
    """工具类型枚举"""
    BUILTIN = "builtin"
    MCP = "mcp"
    CUSTOM = "custom"
    MARKETPLACE = "marketplace"


class ConnectionStatus(str, Enum):
    """连接状态枚举"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


@dataclass
class UserTool:
    """用户工具数据模型"""
    id: int
    user_id: int
    tool_id: str
    tool_name: str
    tool_type: ToolType
    connection_status: ConnectionStatus
    configuration: Dict[str, Any]
    permissions: List[str]
    last_used: Optional[datetime]
    created_at: datetime
    is_active: bool
    version: Optional[str]
    marketplace_url: Optional[str]


@dataclass
class MCPConnection:
    """MCP连接数据模型"""
    id: int
    user_id: int
    server_name: str
    server_url: str
    connection_status: ConnectionStatus
    available_tools: List[str]
    last_sync: Optional[datetime]
    created_at: datetime
    is_active: bool
    error_message: Optional[str]


@dataclass
class ToolConfiguration:
    """工具配置"""
    tool_id: str
    settings: Dict[str, Any]
    permissions: List[str]


@dataclass
class ToolStats:
    """工具使用统计"""
    tool_id: str
    usage_count: int
    last_used: Optional[datetime]
    total_cost: float
    average_response_time: float


@dataclass
class MarketplaceTool:
    """市场工具信息"""
    tool_id: str
    name: str
    description: str
    category: str
    rating: float
    installs: int
    price: float
    marketplace_url: str


class ToolManagementPort(ABC):
    """工具管理接口"""
    
    @abstractmethod
    async def get_user_tools(
        self,
        user_id: int,
        tool_type: Optional[ToolType] = None
    ) -> List[UserTool]:
        """获取用户工具列表"""
        pass
    
    @abstractmethod
    async def connect_tool(
        self,
        user_id: int,
        tool_id: str,
        configuration: ToolConfiguration
    ) -> UserTool:
        """连接工具"""
        pass
    
    @abstractmethod
    async def disconnect_tool(
        self,
        user_id: int,
        tool_id: str
    ) -> bool:
        """断开工具连接"""
        pass
    
    @abstractmethod
    async def update_tool_config(
        self,
        user_id: int,
        tool_id: str,
        configuration: ToolConfiguration
    ) -> UserTool:
        """更新工具配置"""
        pass
    
    @abstractmethod
    async def get_tool_permissions(
        self,
        user_id: int,
        tool_id: str
    ) -> List[str]:
        """获取工具权限"""
        pass
    
    @abstractmethod
    async def update_tool_permissions(
        self,
        user_id: int,
        tool_id: str,
        permissions: List[str]
    ) -> bool:
        """更新工具权限"""
        pass
    
    @abstractmethod
    async def get_mcp_connections(
        self,
        user_id: int
    ) -> List[MCPConnection]:
        """获取MCP连接列表"""
        pass
    
    @abstractmethod
    async def connect_mcp_server(
        self,
        user_id: int,
        server_name: str,
        server_url: str
    ) -> MCPConnection:
        """连接MCP服务器"""
        pass
    
    @abstractmethod
    async def disconnect_mcp_server(
        self,
        user_id: int,
        connection_id: int
    ) -> bool:
        """断开MCP连接"""
        pass
    
    @abstractmethod
    async def sync_mcp_tools(
        self,
        user_id: int,
        connection_id: int
    ) -> List[str]:
        """同步MCP工具，返回可用工具列表"""
        pass
    
    @abstractmethod
    async def get_tool_stats(
        self,
        user_id: int,
        tool_id: str
    ) -> ToolStats:
        """获取工具使用统计"""
        pass
    
    @abstractmethod
    async def get_marketplace_recommendations(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[MarketplaceTool]:
        """获取市场推荐工具"""
        pass
    
    @abstractmethod
    async def get_tool_marketplace_url(
        self,
        tool_id: str
    ) -> Optional[str]:
        """获取工具市场链接"""
        pass