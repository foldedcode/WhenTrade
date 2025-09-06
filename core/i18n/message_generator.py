"""
MessageGenerator - 统一消息生成器
用于生成多语言的系统消息和用户界面消息，消除硬编码文本
"""

from typing import List, Dict, Any, Optional
from .messages import get_message, get_agent_name, get_tool_name
from .locale_manager import locale_manager, get_language_for_request
import logging

logger = logging.getLogger(__name__)


class MessageGenerator:
    """统一消息生成器 - 符合Linus原则：通过数据结构消除特殊情况"""
    
    def __init__(self, language: Optional[str] = None):
        """
        初始化消息生成器
        
        Args:
            language: 语言代码，如果为None则使用全局语言管理器的当前语言
        """
        self.language = get_language_for_request(language)
        logger.info(f"MessageGenerator initialized with language: {self.language}")
    
    def system_message(self, message_key: str) -> str:
        """
        生成系统消息
        
        Args:
            message_key: 消息键，如 'system', 'analysis_task_start'
            
        Returns:
            本地化的系统消息
        """
        system_label = get_message('system', self.language)
        message = get_message(message_key, self.language)
        return f"[{system_label}] {message}"
    
    def phase_message(self, phase_num: int) -> str:
        """
        生成阶段消息
        
        Args:
            phase_num: 阶段编号 (1, 2, 3)
            
        Returns:
            本地化的阶段消息，如 "[System] Entering Phase 1: Data Collection & Analysis"
        """
        system_label = get_message('system', self.language)
        phase_message = get_message(f'phase{phase_num}_message', self.language)
        return f"[{system_label}] {phase_message}"
    
    def agent_message(self, agent_type: str, message_key: str, **kwargs) -> str:
        """
        生成Agent消息
        
        Args:
            agent_type: Agent类型，如 'market', 'news', 'social'
            message_key: 消息键
            **kwargs: 消息格式化参数
            
        Returns:
            本地化的Agent消息
        """
        agent_name = get_agent_name(agent_type, self.language)
        message = get_message(message_key, self.language)
        if kwargs:
            message = message.format(**kwargs)
        return f"[{agent_name}] {message}"
    
    def tool_execution_start_message(self, agent_type: str, tools: List[str]) -> str:
        """
        生成工具执行开始消息
        
        Args:
            agent_type: Agent类型
            tools: 工具列表
            
        Returns:
            本地化的工具执行开始消息
        """
        agent_name = get_agent_name(agent_type, self.language)
        
        # 动态获取工具名称列表
        tools_localized = [get_tool_name(tool_id, self.language) for tool_id in tools]
        tools_str = ", ".join(tools_localized)
        
        # 构建动态消息
        start_msg = get_message('tool_execution_start', self.language)
        total_count_label = get_message('total_count', self.language)
        tools_count_label = get_message('tools_count', self.language)
        colon = get_message('colon', self.language)
        
        message = f"{start_msg}{colon} {tools_str} ({total_count_label} {len(tools)} {tools_count_label})"
        return f"[{agent_name}] {message}"
    
    def tool_execution_complete_message(self, agent_type: str, total_tools: int, 
                                      successful_tools: int, failed_tools: int, 
                                      duration: float) -> str:
        """
        生成工具执行完成消息
        
        Args:
            agent_type: Agent类型
            total_tools: 工具总数
            successful_tools: 成功工具数
            failed_tools: 失败工具数
            duration: 执行时长（秒）
            
        Returns:
            本地化的工具执行完成消息
        """
        agent_name = get_agent_name(agent_type, self.language)
        
        complete_msg = get_message('tool_execution_complete', self.language)
        tools_label = get_message('tools_count', self.language)
        success_label = get_message('success_count', self.language)
        failed_label = get_message('failed_count', self.language)
        time_label = get_message('time_spent', self.language)
        
        comma = get_message('comma', self.language)
        total_count_label = get_message('total_count', self.language)
        
        message = f"{complete_msg}{comma} {total_count_label} {total_tools} {tools_label}{comma} {successful_tools} {success_label}{comma} {failed_tools} {failed_label}{comma} {time_label} {duration:.1f}s"
        return f"[{agent_name}] {message}"
    
    def analysis_progress_message(self, phase_name: str, agent_type: str = None) -> str:
        """
        生成分析进度消息
        
        Args:
            phase_name: 阶段名称键，如 'data_collection_analysis'
            agent_type: 可选的Agent类型
            
        Returns:
            本地化的进度消息
        """
        if agent_type:
            agent_name = get_agent_name(agent_type, self.language)
            message = get_message(phase_name, self.language)
            return f"[{agent_name}] {message}"
        else:
            return get_message(phase_name, self.language)
    
    def error_message(self, error_key: str, **kwargs) -> str:
        """
        生成错误消息
        
        Args:
            error_key: 错误消息键
            **kwargs: 格式化参数
            
        Returns:
            本地化的错误消息
        """
        error_label = get_message('error', self.language)
        message = get_message(error_key, self.language)
        if kwargs:
            message = message.format(**kwargs)
        return f"[{error_label}] {message}"
    
    def update_language(self, language: str):
        """
        更新语言设置
        
        Args:
            language: 新的语言代码
        """
        self.language = get_language_for_request(language)
        logger.info(f"MessageGenerator language updated to: {self.language}")


# 便利函数：创建消息生成器实例
def create_message_generator(language: Optional[str] = None) -> MessageGenerator:
    """
    创建消息生成器实例的便利函数
    
    Args:
        language: 语言代码，如果为None则使用全局语言管理器的当前语言
        
    Returns:
        MessageGenerator: 消息生成器实例
    """
    return MessageGenerator(language)