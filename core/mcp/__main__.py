"""
MCP服务入口
"""
import asyncio
import logging
import uvicorn
from fastapi import FastAPI

# 延迟导入以避免循环导入
RealMCPClient = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建FastAPI应用来提供MCP服务的HTTP接口
app = FastAPI(title="MCP Service", version="1.0.0")

# 延迟创建MCP客户端实例
mcp_client = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "mcp"}

@app.on_event("startup")
async def startup_event():
    """启动时初始化MCP客户端"""
    global mcp_client, RealMCPClient
    
    # 现在导入以避免循环导入
    from .server import RealMCPClient as _RealMCPClient
    RealMCPClient = _RealMCPClient
    
    logging.info("Starting MCP service...")
    mcp_client = RealMCPClient()
    # MCP客户端会在第一次使用时自动连接到配置的服务器

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时断开所有MCP连接"""
    logging.info("Shutting down MCP service...")
    if mcp_client:
        await mcp_client.disconnect_all()

async def main():
    """主函数"""
    import os
    # 从环境变量获取端口，默认为 8001
    port = int(os.environ.get('MCP_SERVER_PORT', '8001'))
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())