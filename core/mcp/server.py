"""
真实MCP客户端实现
支持连接外部AI服务和工具提供商
"""

import asyncio
import json
import websockets
import httpx
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class MCPTransportType(Enum):
    """MCP传输类型"""
    WEBSOCKET = "websocket"
    HTTP = "http"
    STDIO = "stdio"


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    url: str
    transport: MCPTransportType
    auth_token: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    capabilities: Optional[List[str]] = None
    timeout: int = 30
    retry_attempts: int = 3
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.capabilities is None:
            self.capabilities = []


@dataclass 
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


@dataclass
class MCPResource:
    """MCP资源定义"""
    uri: str
    name: str
    description: str
    mime_type: str
    server_name: str


@dataclass
class MCPPrompt:
    """MCP提示词定义"""
    name: str
    description: str
    arguments: List[Dict[str, Any]]
    server_name: str


class RealMCPClient:
    """
    真实MCP协议客户端
    支持多种传输协议和外部服务连接
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.connections: Dict[str, Any] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self._lock = asyncio.Lock()
        
        # 预配置一些知名的MCP服务器
        self._setup_default_servers()
        
        logger.info("🔗 Real MCP Client initialized")
    
    def _setup_default_servers(self):
        """设置默认的MCP服务器配置"""
        
        # 从配置文件加载服务器配置
        config_path = Path(__file__).parent.parent / "config" / "mcp_servers.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                servers = config_data.get('servers', [])
                for server_config in servers:
                    if not server_config.get('enabled', True):
                        continue
                        
                    # 替换环境变量
                    auth_token = server_config.get('auth_token')
                    if auth_token and auth_token.startswith('${') and auth_token.endswith('}'):
                        env_var = auth_token[2:-1]
                        auth_token = os.getenv(env_var)
                    
                    # 创建服务器配置
                    self.add_server(MCPServerConfig(
                        name=server_config['name'],
                        url=server_config['url'],
                        transport=MCPTransportType(server_config['transport']),
                        auth_token=auth_token,
                        capabilities=server_config.get('capabilities', []),
                        timeout=server_config.get('timeout', 30)
                    ))
                    
                logger.info(f"📋 Loaded {len(servers)} server configurations from config file")
                
            except Exception as e:
                logger.error(f"❌ Failed to load MCP server config: {e}")
                # 回退到硬编码的默认配置
                self._setup_fallback_servers()
        else:
            logger.warning("⚠️ MCP server config file not found, using fallback servers")
            self._setup_fallback_servers()
    
    def _setup_fallback_servers(self):
        """设置备用的MCP服务器配置"""
        # 本地文件系统MCP服务器
        self.add_server(MCPServerConfig(
            name="filesystem",
            url="stdio://mcp-server-filesystem",
            transport=MCPTransportType.STDIO,
            capabilities=["resources", "tools"]
        ))
        
        # 时间天气MCP服务器
        self.add_server(MCPServerConfig(
            name="time_weather",
            url="stdio://mcp-server-time",
            transport=MCPTransportType.STDIO,
            capabilities=["tools"]
        ))
    
    def add_server(self, config: MCPServerConfig):
        """添加MCP服务器"""
        self.servers[config.name] = config
        logger.info(f"📡 Added MCP server: {config.name} ({config.transport.value})")
    
    async def connect_server(self, server_name: str) -> bool:
        """连接到MCP服务器"""
        if server_name not in self.servers:
            logger.error(f"❌ Server not found: {server_name}")
            return False
            
        config = self.servers[server_name]
        
        try:
            if config.transport == MCPTransportType.WEBSOCKET:
                connection = await self._connect_websocket(config)
            elif config.transport == MCPTransportType.HTTP:
                connection = await self._connect_http(config)
            elif config.transport == MCPTransportType.STDIO:
                connection = await self._connect_stdio(config)
            else:
                raise ValueError(f"Unsupported transport: {config.transport}")
            
            async with self._lock:
                self.connections[server_name] = connection
                
            # 发现服务器功能
            await self._discover_server_capabilities(server_name)
            
            logger.info(f"✅ Connected to MCP server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to {server_name}: {e}")
            return False
    
    async def _connect_websocket(self, config: MCPServerConfig):
        """连接WebSocket MCP服务器"""
        headers = config.headers.copy() if config.headers else {}
        if config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
            
        try:
            websocket = await websockets.connect(
                config.url,
                extra_headers=headers,
                timeout=config.timeout
            )
            
            # 发送初始化消息
            init_message = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    },
                    "clientInfo": {
                        "name": "WhenTrade",
                        "version": "1.0.0"
                    }
                }
            }
            
            await websocket.send(json.dumps(init_message))
            response = await websocket.recv()
            
            logger.debug(f"📤 WebSocket init response: {response}")
            return websocket
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            raise
    
    async def _connect_http(self, config: MCPServerConfig):
        """连接HTTP MCP服务器"""
        headers = config.headers.copy() if config.headers else {}
        if config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
            
        client = httpx.AsyncClient(
            base_url=config.url,
            headers=headers,
            timeout=config.timeout
        )
        
        # 测试连接
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                return client
            else:
                raise Exception(f"Health check failed: {response.status_code}")
        except Exception as e:
            await client.aclose()
            raise e
    
    async def _connect_stdio(self, config: MCPServerConfig):
        """连接STDIO MCP服务器"""
        # 解析stdio URL获取命令
        command = config.url.replace("stdio://", "")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command.split(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            return process
        except Exception as e:
            logger.error(f"❌ STDIO connection failed: {e}")
            raise
    
    async def _discover_server_capabilities(self, server_name: str):
        """发现服务器能力"""
        try:
            # 获取可用工具
            tools = await self._list_tools(server_name)
            for tool_data in tools:
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=server_name
                )
                self.tools[f"{server_name}.{tool.name}"] = tool
            
            # 获取可用资源
            resources = await self._list_resources(server_name)
            for resource_data in resources:
                resource = MCPResource(
                    uri=resource_data["uri"],
                    name=resource_data.get("name", ""),
                    description=resource_data.get("description", ""),
                    mime_type=resource_data.get("mimeType", ""),
                    server_name=server_name
                )
                self.resources[resource.uri] = resource
            
            # 获取可用提示词
            prompts = await self._list_prompts(server_name)
            for prompt_data in prompts:
                prompt = MCPPrompt(
                    name=prompt_data["name"],
                    description=prompt_data.get("description", ""),
                    arguments=prompt_data.get("arguments", []),
                    server_name=server_name
                )
                self.prompts[f"{server_name}.{prompt.name}"] = prompt
                
            logger.info(f"🔍 Discovered capabilities for {server_name}: "
                       f"{len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts")
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to discover capabilities for {server_name}: {e}")
    
    async def _list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """列出服务器可用工具"""
        try:
            response = await self._send_request(server_name, "tools/list", {})
            return response.get("tools", [])
        except Exception:
            return []
    
    async def _list_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """列出服务器可用资源"""
        try:
            response = await self._send_request(server_name, "resources/list", {})
            return response.get("resources", [])
        except Exception:
            return []
    
    async def _list_prompts(self, server_name: str) -> List[Dict[str, Any]]:
        """列出服务器可用提示词"""
        try:
            response = await self._send_request(server_name, "prompts/list", {})
            return response.get("prompts", [])
        except Exception:
            return []
    
    async def _send_request(self, server_name: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送MCP请求"""
        if server_name not in self.connections:
            raise ValueError(f"Not connected to server: {server_name}")
        
        connection = self.connections[server_name]
        config = self.servers[server_name]
        
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params
        }
        
        try:
            if config.transport == MCPTransportType.WEBSOCKET:
                return await self._send_websocket_request(connection, request)
            elif config.transport == MCPTransportType.HTTP:
                return await self._send_http_request(connection, request)
            elif config.transport == MCPTransportType.STDIO:
                return await self._send_stdio_request(connection, request)
        except Exception as e:
            logger.error(f"❌ Request failed to {server_name}: {e}")
            raise
    
    async def _send_websocket_request(self, websocket, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送WebSocket请求"""
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        return json.loads(response)
    
    async def _send_http_request(self, client: httpx.AsyncClient, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP请求"""
        response = await client.post("/", json=request)
        response.raise_for_status()
        return response.json()
    
    async def _send_stdio_request(self, process: asyncio.subprocess.Process, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送STDIO请求"""
        request_json = json.dumps(request) + "\n"
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        response_line = await process.stdout.readline()
        return json.loads(response_line.decode())
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool = self.tools[tool_name]
        server_name = tool.server_name
        
        try:
            response = await self._send_request(server_name, "tools/call", {
                "name": tool.name,
                "arguments": arguments
            })
            
            logger.info(f"🔧 Called tool {tool_name} on {server_name}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Tool call failed: {tool_name}: {e}")
            raise
    
    async def get_resource(self, resource_uri: str) -> Dict[str, Any]:
        """获取MCP资源"""
        if resource_uri not in self.resources:
            raise ValueError(f"Resource not found: {resource_uri}")
        
        resource = self.resources[resource_uri]
        server_name = resource.server_name
        
        try:
            response = await self._send_request(server_name, "resources/read", {
                "uri": resource_uri
            })
            
            logger.info(f"📄 Retrieved resource {resource_uri} from {server_name}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Resource retrieval failed: {resource_uri}: {e}")
            raise
    
    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取MCP提示词"""
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt not found: {prompt_name}")
        
        prompt = self.prompts[prompt_name]
        server_name = prompt.server_name
        
        try:
            response = await self._send_request(server_name, "prompts/get", {
                "name": prompt.name,
                "arguments": arguments or {}
            })
            
            logger.info(f"💬 Retrieved prompt {prompt_name} from {server_name}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Prompt retrieval failed: {prompt_name}: {e}")
            raise
    
    async def stream_completion(self, server_name: str, prompt: str, 
                              **kwargs) -> AsyncGenerator[str, None]:
        """流式完成请求"""
        if server_name not in self.connections:
            raise ValueError(f"Not connected to server: {server_name}")
        
        try:
            response = await self._send_request(server_name, "completion/stream", {
                "prompt": prompt,
                **kwargs
            })
            
            # 这里应该处理流式响应，简化为单次响应
            if "content" in response:
                yield response["content"]
            
        except Exception as e:
            logger.error(f"❌ Stream completion failed: {e}")
            raise
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        tools_info = []
        for tool_name, tool in self.tools.items():
            tools_info.append({
                "name": tool_name,
                "description": tool.description,
                "server": tool.server_name,
                "input_schema": tool.input_schema
            })
        return tools_info
    
    async def get_available_resources(self) -> List[Dict[str, Any]]:
        """获取所有可用资源"""
        resources_info = []
        for resource_uri, resource in self.resources.items():
            resources_info.append({
                "uri": resource_uri,
                "name": resource.name,
                "description": resource.description,
                "mime_type": resource.mime_type,
                "server": resource.server_name
            })
        return resources_info
    
    async def get_server_status(self) -> Dict[str, Any]:
        """获取服务器连接状态"""
        status = {}
        for server_name, config in self.servers.items():
            is_connected = server_name in self.connections
            status[server_name] = {
                "connected": is_connected,
                "transport": config.transport.value,
                "url": config.url,
                "capabilities": config.capabilities,
                "tools_count": len([t for t in self.tools.values() if t.server_name == server_name]),
                "resources_count": len([r for r in self.resources.values() if r.server_name == server_name])
            }
        return status
    
    async def disconnect_server(self, server_name: str) -> bool:
        """断开服务器连接"""
        if server_name not in self.connections:
            return False
        
        connection = self.connections[server_name]
        config = self.servers[server_name]
        
        try:
            if config.transport == MCPTransportType.WEBSOCKET:
                await connection.close()
            elif config.transport == MCPTransportType.HTTP:
                await connection.aclose()
            elif config.transport == MCPTransportType.STDIO:
                connection.terminate()
                await connection.wait()
            
            async with self._lock:
                del self.connections[server_name]
            
            logger.info(f"🔌 Disconnected from MCP server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to disconnect from {server_name}: {e}")
            return False
    
    async def cleanup(self):
        """清理所有连接"""
        for server_name in list(self.connections.keys()):
            await self.disconnect_server(server_name)
        
        self.tools.clear()
        self.resources.clear()
        self.prompts.clear()
        
        logger.info("🧹 Real MCP Client cleaned up")