"""
LLM配置服务
提供LLM提供商和模型的配置信息
"""

from typing import List, Dict, Any, Optional
import os
from enum import Enum

class LLMProvider(Enum):
    """支持的LLM提供商"""
    OPENAI = "openai"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    KIMI = "kimi"

class LLMModel:
    """LLM模型信息"""
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        context_window: int,
        pricing: Optional[Dict[str, float]] = None,
        capabilities: List[str] = None,
        recommended: bool = False
    ):
        self.id = id
        self.name = name
        self.description = description
        self.context_window = context_window
        self.pricing = pricing or {}
        self.capabilities = capabilities or []
        self.recommended = recommended
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "context_window": self.context_window,
            "pricing": self.pricing,
            "capabilities": self.capabilities,
            "recommended": self.recommended
        }

class LLMProviderConfig:
    """LLM提供商配置"""
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        api_key_env: str,
        models: List[LLMModel]
    ):
        self.id = id
        self.name = name
        self.description = description
        self.api_key_env = api_key_env
        self.models = models
        
    def is_available(self) -> bool:
        """检查提供商是否可用（是否配置了API密钥）"""
        return bool(os.getenv(self.api_key_env))
    
    def to_dict(self, include_models: bool = False) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "available": self.is_available()
        }
        if include_models:
            result["models"] = [model.to_dict() for model in self.models]
        return result

class LLMConfigService:
    """LLM配置服务"""
    
    def __init__(self):
        self.providers = self._init_providers()
    
    def _init_providers(self) -> Dict[str, LLMProviderConfig]:
        """初始化提供商配置"""
        return {
            LLMProvider.OPENAI.value: LLMProviderConfig(
                id="openai",
                name="OpenAI",
                description="领先的AI研究公司，提供GPT系列模型",
                api_key_env="OPENAI_API_KEY",
                models=[
                    LLMModel(
                        id="gpt-4o",
                        name="GPT-4o",
                        description="最新的GPT-4 Omni模型，支持多模态",
                        context_window=128000,
                        pricing={"input": 0.005, "output": 0.015},
                        capabilities=["文本生成", "代码生成", "分析推理", "多模态"],
                        recommended=True
                    ),
                    LLMModel(
                        id="gpt-4o-mini",
                        name="GPT-4o Mini",
                        description="轻量级GPT-4o，更快更便宜",
                        context_window=128000,
                        pricing={"input": 0.00015, "output": 0.0006},
                        capabilities=["文本生成", "代码生成", "快速分析"]
                    ),
                    LLMModel(
                        id="gpt-4-turbo",
                        name="GPT-4 Turbo",
                        description="GPT-4 Turbo模型，128K上下文",
                        context_window=128000,
                        pricing={"input": 0.01, "output": 0.03},
                        capabilities=["文本生成", "代码生成", "分析推理"]
                    )
                ]
            ),
            LLMProvider.GOOGLE.value: LLMProviderConfig(
                id="google",
                name="Google",
                description="谷歌AI服务，提供Gemini系列模型",
                api_key_env="GOOGLE_API_KEY",
                models=[
                    LLMModel(
                        id="gemini-1.5-pro",
                        name="Gemini 1.5 Pro",
                        description="谷歌最强大的AI模型，支持超长上下文",
                        context_window=1048576,  # 1M tokens
                        pricing={"input": 0.00125, "output": 0.005},
                        capabilities=["文本生成", "多模态", "分析推理", "超长文本"],
                        recommended=True
                    ),
                    LLMModel(
                        id="gemini-1.5-flash",
                        name="Gemini 1.5 Flash",
                        description="快速轻量的Gemini模型",
                        context_window=1048576,  # 1M tokens
                        pricing={"input": 0.00025, "output": 0.001},
                        capabilities=["文本生成", "快速分析", "多模态"]
                    )
                ]
            ),
            LLMProvider.DEEPSEEK.value: LLMProviderConfig(
                id="deepseek",
                name="DeepSeek",
                description="深度求索AI，提供高性价比的推理模型",
                api_key_env="DEEPSEEK_API_KEY",
                models=[
                    LLMModel(
                        id="deepseek-chat",
                        name="DeepSeek Chat",
                        description="通用对话模型，性价比极高",
                        context_window=32768,
                        pricing={"input": 0.0014, "output": 0.0028},
                        capabilities=["文本生成", "代码生成", "分析推理"],
                        recommended=True
                    ),
                    LLMModel(
                        id="deepseek-coder",
                        name="DeepSeek Coder",
                        description="专业代码生成和分析模型",
                        context_window=16384,
                        pricing={"input": 0.0014, "output": 0.0028},
                        capabilities=["代码生成", "代码分析", "技术文档"]
                    )
                ]
            ),
            LLMProvider.KIMI.value: LLMProviderConfig(
                id="kimi",
                name="Moonshot Kimi",
                description="月之暗面AI，超长上下文对话模型",
                api_key_env="KIMI_API_KEY",
                models=[
                    LLMModel(
                        id="moonshot-v1-8k",
                        name="Moonshot v1 8K",
                        description="标准上下文模型，适合日常对话",
                        context_window=8192,
                        pricing={"input": 0.012, "output": 0.012},
                        capabilities=["文本生成", "对话", "分析"]
                    ),
                    LLMModel(
                        id="moonshot-v1-32k",
                        name="Moonshot v1 32K",
                        description="中等上下文模型，适合文档分析",
                        context_window=32768,
                        pricing={"input": 0.024, "output": 0.024},
                        capabilities=["文本生成", "长文本", "分析"]
                    ),
                    LLMModel(
                        id="moonshot-v1-128k",
                        name="Moonshot v1 128K",
                        description="超长上下文模型，适合复杂任务",
                        context_window=131072,
                        pricing={"input": 0.06, "output": 0.06},
                        capabilities=["文本生成", "超长文本", "深度分析"],
                        recommended=True
                    )
                ]
            )
        }
    
    def get_all_providers(self) -> List[Dict[str, Any]]:
        """获取所有提供商信息"""
        return [
            provider.to_dict()
            for provider in self.providers.values()
        ]
    
    def get_available_providers(self) -> List[Dict[str, Any]]:
        """获取可用的提供商（配置了API密钥的）"""
        return [
            provider.to_dict()
            for provider in self.providers.values()
            if provider.is_available()
        ]
    
    def get_provider(self, provider_id: str) -> Optional[LLMProviderConfig]:
        """获取指定提供商"""
        return self.providers.get(provider_id)
    
    def is_provider_available(self, provider_id: str) -> bool:
        """检查指定提供商是否可用（是否配置了API密钥）"""
        provider = self.get_provider(provider_id)
        if not provider:
            return False
        return provider.is_available()
    
    def get_provider_models(self, provider_id: str) -> List[Dict[str, Any]]:
        """获取指定提供商的模型列表"""
        provider = self.get_provider(provider_id)
        if not provider:
            return []
        return [model.to_dict() for model in provider.models]
    
    def get_model(self, provider_id: str, model_id: str) -> Optional[Dict[str, Any]]:
        """获取指定模型信息"""
        provider = self.get_provider(provider_id)
        if not provider:
            return None
        
        for model in provider.models:
            if model.id == model_id:
                return model.to_dict()
        return None
    
    def get_recommended_config(self) -> Optional[Dict[str, str]]:
        """获取推荐的配置（优先级：Kimi > DeepSeek > OpenAI > Google）"""
        priority_order = [
            LLMProvider.KIMI.value,
            LLMProvider.DEEPSEEK.value,
            LLMProvider.OPENAI.value,
            LLMProvider.GOOGLE.value
        ]
        
        for provider_id in priority_order:
            provider = self.get_provider(provider_id)
            if provider and provider.is_available():
                # 找到推荐的模型
                for model in provider.models:
                    if model.recommended:
                        return {
                            "provider": provider_id,
                            "model": model.id,
                            "provider_name": provider.name,
                            "model_name": model.name
                        }
                # 如果没有推荐模型，使用第一个
                if provider.models:
                    return {
                        "provider": provider_id,
                        "model": provider.models[0].id,
                        "provider_name": provider.name,
                        "model_name": provider.models[0].name
                    }
        
        return None
    
    def set_llm_config(self, provider_id: str, model_id: str) -> Dict[str, Any]:
        """设置当前使用的LLM配置
        
        Args:
            provider_id: 提供商ID
            model_id: 模型ID
            
        Returns:
            配置信息字典
            
        Raises:
            ValueError: 如果提供商或模型不存在
        """
        # 验证提供商
        provider = self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_id}")
        
        if not provider.is_available():
            raise ValueError(f"Provider {provider_id} is not available (API key not configured)")
        
        # 验证模型
        model = None
        for m in provider.models:
            if m.id == model_id:
                model = m
                break
        
        if not model:
            raise ValueError(f"Unknown model {model_id} for provider {provider_id}")
        
        # 保存当前配置（这里可以扩展为持久化存储）
        self.current_provider = provider_id
        self.current_model = model_id
        
        return {
            "provider": provider_id,
            "model": model_id,
            "provider_name": provider.name,
            "model_name": model.name,
            "api_key_env": provider.api_key_env,
            "context_window": model.context_window,
            "capabilities": model.capabilities
        }

# 单例实例
llm_config_service = LLMConfigService()