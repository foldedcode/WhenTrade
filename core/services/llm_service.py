"""
LLM服务
处理与AI模型的交互
"""

import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional, AsyncGenerator, List
from dataclasses import dataclass
from datetime import datetime

import logging
from core.i18n.system_prompts import get_system_prompt
# from core.infrastructure.logger import logger
# from core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """LLM响应结果"""
    content: str
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None

@dataclass
class LLMStreamChunk:
    """LLM流式响应块"""
    content: str
    tokens_used: Optional[int] = None
    is_final: bool = False

class LLMService:
    """LLM服务类"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        self.max_tokens = 4000
        self.temperature = 0.7
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY 未设置，聊天功能将不可用")
    
    async def chat_completion(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        发送聊天完成请求
        
        Args:
            message: 用户消息
            context: 上下文信息
            system_prompt: 系统提示词
            
        Returns:
            LLMResponse: 响应结果
        """
        
        if not self.api_key:
            raise Exception("DEEPSEEK_API_KEY 未配置")
        
        try:
            # 构建消息列表
            messages = self._build_messages(message, context, system_prompt)
            
            # 准备请求数据
            request_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API请求失败 {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    # 解析响应
                    choice = result["choices"][0]
                    content = choice["message"]["content"]
                    usage = result.get("usage", {})
                    
                    return LLMResponse(
                        content=content,
                        tokens_used=usage.get("total_tokens"),
                        model=result.get("model"),
                        finish_reason=choice.get("finish_reason")
                    )
                    
        except Exception as e:
            logger.error(f"LLM聊天完成请求失败: {str(e)}")
            raise Exception(f"AI响应失败: {str(e)}")
    
    def chat_completion_stream(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        发送流式聊天完成请求
        
        Args:
            message: 用户消息
            context: 上下文信息
            system_prompt: 系统提示词
            
        Yields:
            LLMStreamChunk: 流式响应块
        """
        
        return self._stream_chat_completion(message, context, system_prompt)
    
    async def _stream_chat_completion(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """内部流式请求实现"""
        
        if not self.api_key:
            raise Exception("DEEPSEEK_API_KEY 未配置")
        
        try:
            # 构建消息列表
            messages = self._build_messages(message, context, system_prompt)
            
            # 准备请求数据
            request_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"流式API请求失败 {response.status}: {error_text}")
                    
                    # 处理流式响应
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        
                        if not line_text or not line_text.startswith('data: '):
                            continue
                        
                        # 移除 "data: " 前缀
                        json_str = line_text[6:]
                        
                        # 检查是否是结束标记
                        if json_str == '[DONE]':
                            yield LLMStreamChunk(content="", is_final=True)
                            break
                        
                        try:
                            import json
                            chunk_data = json.loads(json_str)
                            
                            choices = chunk_data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    yield LLMStreamChunk(content=content)
                                
                                # 检查是否完成
                                finish_reason = choices[0].get("finish_reason")
                                if finish_reason:
                                    yield LLMStreamChunk(
                                        content="",
                                        is_final=True,
                                        tokens_used=chunk_data.get("usage", {}).get("total_tokens")
                                    )
                                    break
                        
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析流式响应: {json_str}")
                            continue
                            
        except Exception as e:
            logger.error(f"LLM流式聊天请求失败: {str(e)}")
            raise Exception(f"AI流式响应失败: {str(e)}")
    
    def _build_messages(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            system_message = system_prompt
        else:
            system_message = self._get_default_system_prompt(context)
        
        messages.append({
            "role": "system",
            "content": system_message
        })
        
        # 添加上下文信息（如果有的话）
        if context and context.get("chat_history"):
            for hist_msg in context["chat_history"]:
                messages.append({
                    "role": hist_msg["role"],
                    "content": hist_msg["content"]
                })
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
    
    def _get_default_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """获取默认系统提示词"""
        
        # 从上下文中获取语言设置，默认使用中文
        language = "zh-CN"
        if context and context.get("language"):
            language = context["language"]
        
        # 使用多语言系统提示词
        return get_system_prompt(language, context)
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        if not self.api_key:
            return {
                "status": "error",
                "message": "API密钥未配置"
            }
        
        try:
            # 发送简单的测试请求
            test_response = await self.chat_completion(
                message="Hello",
                system_prompt="Reply with just 'OK'"
            )
            
            return {
                "status": "healthy",
                "model": self.model,
                "response_length": len(test_response.content),
                "tokens_used": test_response.tokens_used
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        
        return {
            "model": self.model,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "api_key_configured": bool(self.api_key)
        }