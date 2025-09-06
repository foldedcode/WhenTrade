#!/usr/bin/env python3
"""
Token管理器 - 智能消息截断和压缩
基于Linus理念：好的数据结构消除复杂性
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")


@dataclass
class TokenUsage:
    """Token使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_tokens: int = 0  # 本地估算


class TokenManager:
    """
    Token管理器 - Linus式简洁设计
    
    核心理念：
    1. 好品味：通过数据结构消除特殊情况
    2. 实用主义：解决真实的token限制问题
    3. 零破坏：不影响现有功能
    """
    
    def __init__(self, max_tokens: int = 32768):
        """
        初始化Token管理器
        
        Args:
            max_tokens: 最大token限制
        """
        self.max_tokens = max_tokens
        self.safety_buffer = 2048  # 安全缓冲区
        self.effective_limit = max_tokens - self.safety_buffer
        
        # 🔧 Linus式数据结构：消除特殊情况的压缩规则
        self.compression_rules = {
            'system': {
                'priority': 10,  # 最高优先级，不删除
                'max_length': -1,  # 不限制长度
                'compress_func': None
            },
            'tool': {
                'priority': 8,   # 高优先级
                'max_length': 800,  # 工具结果限制800字符
                'compress_func': self._compress_tool_result
            },
            'assistant': {
                'priority': 6,   # 中优先级
                'max_length': 1200,  # 助手消息限制1200字符
                'compress_func': self._compress_assistant_message
            },
            'user': {
                'priority': 9,   # 用户消息高优先级
                'max_length': 2000,  # 用户消息限制2000字符
                'compress_func': self._compress_user_message
            },
            'function': {
                'priority': 7,   # 函数调用中等优先级
                'max_length': 600,  # 函数调用限制600字符
                'compress_func': self._compress_function_call
            }
        }
        
        logger.debug(f"🎯 [TokenManager] 初始化完成 - 限制: {max_tokens}, 有效: {self.effective_limit}")
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本token数量
        粗略估算：1 token ≈ 4字符（英文）或 1.5个中文字符
        """
        if not text:
            return 0
        
        # 简单估算：英文4:1，中文1.5:1
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(text) - chinese_chars
        
        estimated = int(english_chars / 4 + chinese_chars / 1.5)
        return max(estimated, len(text.split()) // 2)  # 至少是单词数的一半
    
    def estimate_messages_tokens(self, messages: List[Any]) -> int:
        """估算消息列表的总token数量"""
        total = 0
        for message in messages:
            # 估算消息结构开销
            total += 10  # 每个消息的结构开销
            
            # 🛠 Linus式修复：统一处理字典和LangChain消息对象
            if hasattr(message, 'content'):
                # LangChain消息对象（HumanMessage, AIMessage等）
                content = message.content
            elif isinstance(message, dict) and 'content' in message:
                # 字典格式消息
                content = message['content']
            else:
                # 其他格式，转为字符串
                content = str(message)
            
            # 估算内容token数
            if isinstance(content, str):
                total += self.estimate_tokens(content)
            elif isinstance(content, list):
                # 处理多模态消息
                for content_item in content:
                    if isinstance(content_item, dict) and 'text' in content_item:
                        total += self.estimate_tokens(content_item['text'])
            
            # 工具调用开销（兼容字典和对象格式）
            tool_calls = None
            if hasattr(message, 'tool_calls'):
                tool_calls = message.tool_calls
            elif isinstance(message, dict) and 'tool_calls' in message:
                tool_calls = message['tool_calls']
                
            if tool_calls:
                total += len(tool_calls) * 50  # 每个工具调用50token开销
        
        return total
    
    def _compress_tool_result(self, content: str) -> str:
        """压缩工具结果 - 保留关键信息"""
        if len(content) <= 800:
            return content
        
        try:
            # 尝试解析JSON结果
            if content.startswith('{') or content.startswith('['):
                data = json.loads(content)
                return self._compress_json_data(data, max_items=5)
        except:
            pass
        
        # 文本压缩：保留开头和重要信息
        lines = content.split('\n')
        if len(lines) > 10:
            important_lines = []
            for line in lines[:5]:  # 前5行
                important_lines.append(line)
            important_lines.append('...[数据已压缩]...')
            for line in lines[-3:]:  # 后3行
                important_lines.append(line)
            content = '\n'.join(important_lines)
        
        return content[:800] + '...' if len(content) > 800 else content
    
    def _compress_json_data(self, data: Any, max_items: int = 5) -> str:
        """压缩JSON数据"""
        if isinstance(data, dict):
            # 保留最重要的键
            important_keys = ['error', 'status', 'symbol', 'name', 'price', 'change', 'data']
            compressed = {}
            
            for key in important_keys:
                if key in data:
                    compressed[key] = data[key]
            
            # 如果还有空间，添加其他键（限制数量）
            other_keys = [k for k in data.keys() if k not in important_keys][:max_items-len(compressed)]
            for key in other_keys:
                compressed[key] = data[key]
                
            return json.dumps(compressed, ensure_ascii=False)
            
        elif isinstance(data, list):
            # 列表只保留前几项
            return json.dumps(data[:max_items], ensure_ascii=False)
        
        return json.dumps(data, ensure_ascii=False)
    
    def _compress_assistant_message(self, content: str) -> str:
        """压缩助手消息 - 保留核心分析"""
        if len(content) <= 1200:
            return content
        
        # 保留分析结论和重要段落
        lines = content.split('\n')
        important_lines = []
        
        for line in lines:
            # 保留标题、结论、重要关键词
            if any(keyword in line for keyword in ['##', '###', '结论', '建议', '风险', '机会', '总结']):
                important_lines.append(line)
            elif len(important_lines) < 15:  # 前15行内容
                important_lines.append(line)
        
        compressed = '\n'.join(important_lines)
        return compressed[:1200] + '...[分析已压缩]' if len(compressed) > 1200 else compressed
    
    def _compress_user_message(self, content: str) -> str:
        """压缩用户消息 - 保留完整意图"""
        if len(content) <= 2000:
            return content
        
        # 用户消息优先级高，尽量保留完整
        return content[:2000] + '...[消息已截断]'
    
    def _compress_function_call(self, content: str) -> str:
        """压缩函数调用 - 保留函数名和关键参数"""
        if len(content) <= 600:
            return content
        
        try:
            # 解析函数调用
            data = json.loads(content)
            if 'name' in data:
                compressed = {'name': data['name']}
                if 'arguments' in data:
                    args = json.loads(data['arguments']) if isinstance(data['arguments'], str) else data['arguments']
                    # 只保留最重要的参数
                    important_params = ['symbol', 'query', 'timeframe', 'limit', 'type']
                    filtered_args = {k: v for k, v in args.items() if k in important_params}
                    compressed['arguments'] = filtered_args
                return json.dumps(compressed, ensure_ascii=False)
        except:
            pass
        
        return content[:600] + '...'
    
    def compress_messages(self, messages: List[Any]) -> Tuple[List[Any], TokenUsage]:
        """
        智能压缩消息列表
        
        Returns:
            Tuple[压缩后的消息列表, Token使用统计]
        """
        if not messages:
            return messages, TokenUsage()
        
        # 估算当前token使用量
        current_tokens = self.estimate_messages_tokens(messages)
        logger.debug(f"🔍 [TokenManager] 当前估算tokens: {current_tokens}/{self.effective_limit}")
        
        if current_tokens <= self.effective_limit:
            return messages, TokenUsage(estimated_tokens=current_tokens)
        
        # 需要压缩
        logger.info(f"📦 [TokenManager] 开始消息压缩 - 超出限制: {current_tokens - self.effective_limit} tokens")
        
        compressed_messages = []
        token_budget = self.effective_limit
        
        # 🛠 Linus式解决方案：统一消息格式处理
        def _get_message_role(msg):
            """获取消息角色，兼容字典和LangChain对象"""
            if hasattr(msg, '__class__'):
                # LangChain消息对象
                class_name = msg.__class__.__name__
                if 'HumanMessage' in class_name:
                    return 'user'
                elif 'AIMessage' in class_name:
                    return 'assistant'
                elif 'SystemMessage' in class_name:
                    return 'system'
                elif 'FunctionMessage' in class_name or 'ToolMessage' in class_name:
                    return 'function'
                else:
                    return 'user'  # 默认
            elif isinstance(msg, dict) and 'role' in msg:
                return msg['role']
            else:
                return 'user'  # 默认

        def _get_message_content(msg):
            """获取消息内容，兼容字典和LangChain对象"""
            if hasattr(msg, 'content'):
                return msg.content
            elif isinstance(msg, dict) and 'content' in msg:
                return msg['content']
            else:
                return str(msg)
        
        # 1. 按角色分类消息
        system_messages = [msg for msg in messages if _get_message_role(msg) == 'system']
        other_messages = [msg for msg in messages if _get_message_role(msg) != 'system']
        
        # 2. 保留系统消息（最高优先级）
        for msg in system_messages:
            compressed_messages.append(msg)
            content = _get_message_content(msg)
            token_budget -= self.estimate_tokens(str(content))
        
        # 3. 倒序处理其他消息（保留最新的）
        for msg in reversed(other_messages):
            if token_budget <= 0:
                break
                
            role = _get_message_role(msg)
            content = _get_message_content(msg)
            
            # 应用压缩规则
            rule = self.compression_rules.get(role, self.compression_rules['user'])
            
            if rule['compress_func'] and isinstance(content, str):
                compressed_content = rule['compress_func'](content)
            else:
                compressed_content = content
            
            # 检查是否还有token预算
            msg_tokens = self.estimate_tokens(str(compressed_content))
            if msg_tokens <= token_budget:
                # 🛠 保持原始消息格式（LangChain对象或字典）
                if hasattr(msg, 'content'):
                    # LangChain消息对象 - 创建新对象以避免修改原对象
                    if 'HumanMessage' in msg.__class__.__name__:
                        from langchain_core.messages import HumanMessage
                        compressed_msg = HumanMessage(content=compressed_content)
                    elif 'AIMessage' in msg.__class__.__name__:
                        from langchain_core.messages import AIMessage  
                        compressed_msg = AIMessage(content=compressed_content)
                    elif 'SystemMessage' in msg.__class__.__name__:
                        from langchain_core.messages import SystemMessage
                        compressed_msg = SystemMessage(content=compressed_content)
                    else:
                        # 其他类型，尝试复制
                        compressed_msg = msg.__class__(content=compressed_content)
                elif isinstance(msg, dict):
                    # 字典格式 - 复制并更新内容
                    compressed_msg = msg.copy()
                    compressed_msg['content'] = compressed_content
                else:
                    # 其他格式，保持原样
                    compressed_msg = msg
                
                compressed_messages.insert(-len(system_messages) if system_messages else 0, compressed_msg)
                token_budget -= msg_tokens
            else:
                logger.debug(f"⏭️ [TokenManager] 跳过消息 - 超出预算: {msg_tokens} > {token_budget}")
        
        final_tokens = self.estimate_messages_tokens(compressed_messages)
        logger.info(f"✅ [TokenManager] 压缩完成 - 消息数: {len(messages)} -> {len(compressed_messages)}, tokens: {current_tokens} -> {final_tokens}")
        
        return compressed_messages, TokenUsage(
            estimated_tokens=final_tokens,
            total_tokens=final_tokens
        )
    
    def should_compress(self, messages: List[Any]) -> bool:
        """判断是否需要压缩"""
        estimated = self.estimate_messages_tokens(messages)
        return estimated > self.effective_limit


# 全局实例
_token_manager = None

def get_token_manager(max_tokens: int = 32768) -> TokenManager:
    """获取Token管理器单例"""
    global _token_manager
    if _token_manager is None or _token_manager.max_tokens != max_tokens:
        _token_manager = TokenManager(max_tokens)
    return _token_manager


def compress_messages_smart(messages: List[Any], max_tokens: int = 32768) -> Tuple[List[Any], TokenUsage]:
    """
    智能消息压缩的便捷函数
    
    Args:
        messages: 消息列表
        max_tokens: 最大token限制
        
    Returns:
        Tuple[压缩后的消息列表, Token使用统计]
    """
    manager = get_token_manager(max_tokens)
    return manager.compress_messages(messages)