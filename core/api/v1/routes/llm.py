"""
LLM配置API端点
提供LLM提供商和模型信息
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any

from core.services.llm_config_service import llm_config_service

router = APIRouter()

@router.get("/providers")
async def get_llm_providers() -> Dict[str, Any]:
    """
    获取所有LLM提供商列表
    
    Returns:
        包含所有提供商信息的响应
    """
    try:
        providers = llm_config_service.get_all_providers()
        
        # 将列表转换为字典格式，便于前端使用
        providers_dict = {
            provider["id"]: provider["available"]
            for provider in providers
        }
        
        return {
            "success": True,
            "providers": providers,
            "available": providers_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers/available")
async def get_available_providers() -> Dict[str, Any]:
    """
    获取可用的LLM提供商（配置了API密钥的）
    
    Returns:
        包含可用提供商信息的响应
    """
    try:
        providers = llm_config_service.get_available_providers()
        
        return {
            "success": True,
            "providers": providers,
            "count": len(providers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers/{provider_id}/models")
async def get_provider_models(provider_id: str) -> List[Dict[str, Any]]:
    """
    获取指定提供商的模型列表
    
    Args:
        provider_id: 提供商ID (openai/google/deepseek)
        
    Returns:
        模型列表
    """
    try:
        models = llm_config_service.get_provider_models(provider_id)
        
        if not models:
            raise HTTPException(
                status_code=404, 
                detail=f"Provider '{provider_id}' not found or has no models"
            )
        
        return models
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers/{provider_id}/models/{model_id}")
async def get_model_info(provider_id: str, model_id: str) -> Dict[str, Any]:
    """
    获取指定模型的详细信息
    
    Args:
        provider_id: 提供商ID
        model_id: 模型ID
        
    Returns:
        模型详细信息
    """
    try:
        model = llm_config_service.get_model(provider_id, model_id)
        
        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_id}' not found for provider '{provider_id}'"
            )
        
        return {
            "success": True,
            "model": model
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommended")
async def get_recommended_config() -> Dict[str, Any]:
    """
    获取推荐的LLM配置
    基于可用性和优先级返回推荐的提供商和模型
    
    Returns:
        推荐的配置信息
    """
    try:
        config = llm_config_service.get_recommended_config()
        
        if not config:
            return {
                "success": False,
                "message": "No LLM providers available. Please configure API keys.",
                "config": None
            }
        
        return {
            "success": True,
            "config": config,
            "message": f"Recommended: {config['provider_name']} - {config['model_name']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    LLM服务健康检查
    
    Returns:
        服务状态信息
    """
    try:
        all_providers = llm_config_service.get_all_providers()
        available_providers = llm_config_service.get_available_providers()
        
        return {
            "success": True,
            "status": "healthy",
            "total_providers": len(all_providers),
            "available_providers": len(available_providers),
            "providers_status": {
                provider["id"]: provider["available"]
                for provider in all_providers
            }
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }