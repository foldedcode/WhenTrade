"""
When.Trade API Main Application (简化版)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# 导入配置
from core.config import settings

# 导入核心路由
from core.api.v1.routes.health import router as health_router
from core.api.v1.routes.analysis import router as analysis_router
from core.api.v1.routes.analysis_ws import router as analysis_ws_router
from core.api.v1.routes.llm import router as llm_router
from core.api.v1.routes.cost import router as cost_router
from core.api.v1.routes.config import router as config_router
from core.api.v1.routes.agents import router as agents_router
from core.api.v1.routes.locale import router as locale_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting When.Trade API...")
    yield
    logger.info("Shutting down When.Trade API...")


# 创建FastAPI应用
app = FastAPI(
    title="When.Trade API",
    description="智能交易时机分析平台API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(analysis_ws_router, tags=["websocket"])
app.include_router(llm_router, prefix="/api/v1/llm", tags=["llm"])
app.include_router(config_router, prefix="/api/v1", tags=["config"])
app.include_router(cost_router, tags=["cost"])  # provides /api/v1/cost/* endpoints
app.include_router(agents_router, prefix="/api/v1", tags=["agents"])  # provides /api/v1/agents/* endpoints
app.include_router(locale_router, prefix="/api/v1", tags=["locale"])  # provides /api/v1/locale/* endpoints


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to When.Trade API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    import os
    uvicorn.run(
        "core.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true"
    )
