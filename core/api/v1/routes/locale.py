"""语言环境API路由 - Linus原则：简单直接的语言切换接口

提供RESTful API来管理全局语言环境：
1. 获取当前语言设置
2. 切换语言环境
3. 获取支持的语言列表
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from core.i18n.locale_manager import (
    locale_manager,
    get_current_language,
    set_current_language,
    get_supported_languages
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locale", tags=["locale"])


class LanguageRequest(BaseModel):
    """语言切换请求模型"""
    language: str


class LanguageResponse(BaseModel):
    """语言响应模型"""
    current_language: str
    supported_languages: List[str]
    success: bool = True
    message: Optional[str] = None


class LanguageInfo(BaseModel):
    """语言信息模型"""
    current: str
    supported: List[str]
    default: str
    fallback: str


@router.get("/current", response_model=LanguageResponse)
async def get_current_locale():
    """获取当前语言设置
    
    Returns:
        LanguageResponse: 当前语言信息
    """
    try:
        current = get_current_language()
        supported = get_supported_languages()
        
        logger.debug(f"Current locale requested: {current}")
        
        return LanguageResponse(
            current_language=current,
            supported_languages=supported,
            message="Current language retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get current locale: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current language")


@router.post("/set", response_model=LanguageResponse)
async def set_locale(request: LanguageRequest):
    """设置当前语言
    
    Args:
        request: 语言切换请求
        
    Returns:
        LanguageResponse: 切换结果
    """
    try:
        success = set_current_language(request.language)
        
        if not success:
            logger.warning(f"Failed to set language to: {request.language}")
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported language: {request.language}"
            )
        
        current = get_current_language()
        supported = get_supported_languages()
        
        logger.info(f"Language set to: {current}")
        
        return LanguageResponse(
            current_language=current,
            supported_languages=supported,
            message=f"Language successfully set to {current}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set locale to {request.language}: {e}")
        raise HTTPException(status_code=500, detail="Failed to set language")


@router.get("/supported", response_model=List[str])
async def get_supported_locales():
    """获取支持的语言列表
    
    Returns:
        List[str]: 支持的语言代码列表
    """
    try:
        supported = get_supported_languages()
        logger.debug(f"Supported locales requested: {supported}")
        return supported
    except Exception as e:
        logger.error(f"Failed to get supported locales: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported languages")


@router.get("/info", response_model=LanguageInfo)
async def get_locale_info():
    """获取完整的语言环境信息
    
    Returns:
        LanguageInfo: 完整的语言环境信息
    """
    try:
        info = locale_manager.get_language_info()
        logger.debug(f"Locale info requested: {info}")
        
        return LanguageInfo(
            current=info['current'],
            supported=info['supported'],
            default=info['default'],
            fallback=info['fallback']
        )
    except Exception as e:
        logger.error(f"Failed to get locale info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get language info")


@router.get("/health")
async def locale_health_check():
    """语言环境健康检查
    
    Returns:
        dict: 健康状态信息
    """
    try:
        info = locale_manager.get_language_info()
        
        # 检查当前语言是否在支持列表中
        is_healthy = info['current'] in info['supported']
        
        return {
            "status": "healthy" if is_healthy else "warning",
            "current_language": info['current'],
            "is_supported": is_healthy,
            "supported_count": len(info['supported']),
            "message": "Locale system is healthy" if is_healthy else "Current language not in supported list"
        }
    except Exception as e:
        logger.error(f"Locale health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }