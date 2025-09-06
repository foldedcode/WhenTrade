"""
LLM工厂类 - 支持多种LLM提供商
"""

from typing import Any, Optional, Dict
import os
from abc import ABC, abstractmethod
import asyncio
import json
import logging

# LLM客户端导入
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """LLM基类"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        pass
        
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """计算token数量"""
        pass


class OpenAILLM(BaseLLM):
    """OpenAI LLM实现"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        if not openai:
            raise ImportError("openai package not installed")
            
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens")
        
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            content = response.choices[0].message.content
            
            # 尝试解析JSON响应
            try:
                result = json.loads(content)
            except:
                result = {"response": content}
                
            return {
                **result,
                "token_usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            raise
            
    def count_tokens(self, text: str) -> int:
        """估算token数量"""
        # 简单估算：平均每个字符约0.25个token
        return int(len(text) * 0.25)


class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM实现"""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229", **kwargs):
        if not anthropic:
            raise ImportError("anthropic package not installed")
            
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens", 1024)
        
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            content = response.content[0].text
            
            # 尝试解析JSON响应
            try:
                result = json.loads(content)
            except:
                result = {"response": content}
                
            return {
                **result,
                "token_usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {str(e)}")
            raise
            
    def count_tokens(self, text: str) -> int:
        """估算token数量"""
        return int(len(text) * 0.25)


class GoogleLLM(BaseLLM):
    """Google Gemini LLM实现"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro", **kwargs):
        if not genai:
            raise ImportError("google-generativeai package not installed")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens")
        
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        try:
            # Gemini是同步的，需要在线程池中运行
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.model.generate_content,
                prompt
            )
            
            content = response.text
            
            # 尝试解析JSON响应
            try:
                result = json.loads(content)
            except:
                result = {"response": content}
                
            # Gemini不直接提供token计数
            return {
                **result,
                "token_usage": {
                    "input_tokens": self.count_tokens(prompt),
                    "output_tokens": self.count_tokens(content)
                }
            }
            
        except Exception as e:
            logger.error(f"Google generation failed: {str(e)}")
            raise
            
    def count_tokens(self, text: str) -> int:
        """估算token数量"""
        return int(len(text) * 0.25)


class LocalLLM(BaseLLM):
    """本地LLM实现（模拟）"""
    
    def __init__(self, **kwargs):
        self.temperature = kwargs.get("temperature", 0.7)
        
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成模拟响应"""
        # 这里可以接入本地部署的模型
        # 现在只是返回模拟数据
        await asyncio.sleep(0.5)  # 模拟延迟
        
        return {
            "analysis": {
                "overview": "This is a simulated analysis from local LLM",
                "details": "Local analysis details here"
            },
            "summary": "Local LLM analysis summary",
            "rating": "neutral",
            "confidence_score": 0.7,
            "key_findings": [
                {"finding": "Simulated finding 1", "importance": "high"},
                {"finding": "Simulated finding 2", "importance": "medium"}
            ],
            "recommendations": [
                {"action": "Hold", "reason": "Simulated recommendation"}
            ],
            "token_usage": {
                "input_tokens": self.count_tokens(prompt),
                "output_tokens": 100
            }
        }
        
    def count_tokens(self, text: str) -> int:
        """估算token数量"""
        return int(len(text) * 0.25)


class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM实现"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat", **kwargs):
        if not openai:
            raise ImportError("openai package not installed")
            
        # DeepSeek使用OpenAI兼容的API
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        self.model = model
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens")
        
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            content = response.choices[0].message.content
            
            # 尝试解析JSON响应
            try:
                result = json.loads(content)
            except:
                result = {"response": content}
                
            return {
                **result,
                "token_usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {str(e)}")
            raise
            
    def count_tokens(self, text: str) -> int:
        """估算token数量"""
        return int(len(text) * 0.25)


class KimiLLM(BaseLLM):
    """Kimi (Moonshot) LLM实现"""
    
    def __init__(self, api_key: str, model: str = "moonshot-v1-128k", **kwargs):
        if not openai:
            raise ImportError("openai package not installed")
            
        # Kimi使用OpenAI兼容的API
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1"
        )
        self.model = model
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens")
        
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成响应"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            content = response.choices[0].message.content
            
            # 尝试解析JSON响应
            try:
                result = json.loads(content)
            except:
                result = {"response": content}
                
            return {
                **result,
                "token_usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Kimi generation failed: {str(e)}")
            raise
            
    def count_tokens(self, text: str) -> int:
        """估算token数量"""
        return int(len(text) * 0.25)


class LLMFactory:
    """LLM工厂类"""
    
    def __init__(self):
        self.providers = {
            "openai": OpenAILLM,
            "anthropic": AnthropicLLM,
            "google": GoogleLLM,
            "deepseek": DeepSeekLLM,
            "kimi": KimiLLM,
            "local": LocalLLM
        }
        
    def create_llm(
        self, 
        provider: str, 
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLM:
        """创建LLM实例"""
        provider = provider.lower()
        
        if provider not in self.providers:
            raise ValueError(f"Unknown LLM provider: {provider}")
            
        llm_class = self.providers[provider]
        
        # 获取API密钥
        api_key = None
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            model = model or "gpt-4o"
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model = model or "claude-3-opus-20240229"
        elif provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            model = model or "gemini-1.5-pro"
        elif provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            model = model or "deepseek-chat"
        elif provider == "kimi":
            api_key = os.getenv("KIMI_API_KEY")
            model = model or "moonshot-v1-128k"
            
        if provider != "local" and not api_key:
            raise ValueError(f"API key not found for {provider}")
            
        # 创建实例
        if provider == "local":
            return llm_class(**kwargs)
        else:
            return llm_class(api_key=api_key, model=model, **kwargs)