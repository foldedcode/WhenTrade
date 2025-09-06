"""
Agent Prompt Definitions - Deprecated
所有提示词已迁移到 core/agents/prompts/ 目录下的YAML文件中
This file is kept for compatibility but returns empty prompts to force YAML loading
"""

from enum import Enum
from typing import Dict, Any

class Language(Enum):
    ZH_CN = "zh-CN"
    EN_US = "en-US"

# Empty prompt definitions - all agents now use YAML files
BASE_ANALYST_PROMPTS = {}
MARKET_ANALYST_PROMPTS = {}
SOCIAL_MEDIA_ANALYST_PROMPTS = {}
NEWS_ANALYST_PROMPTS = {}
BULL_RESEARCHER_PROMPTS = {}
BEAR_RESEARCHER_PROMPTS = {}
TRADER_PROMPTS = {}
RESEARCH_MANAGER_PROMPTS = {}
RISK_MANAGER_PROMPTS = {}
AGGRESSIVE_DEBATOR_PROMPTS = {}
CONSERVATIVE_DEBATOR_PROMPTS = {}
NEUTRAL_DEBATOR_PROMPTS = {}

# Agent mapping - returns empty to force YAML loading
AGENT_PROMPTS = {
    "base_analyst": BASE_ANALYST_PROMPTS,
    "market_analyst": MARKET_ANALYST_PROMPTS,
    "social_media_analyst": SOCIAL_MEDIA_ANALYST_PROMPTS,
    "news_analyst": NEWS_ANALYST_PROMPTS,
    "bull_researcher": BULL_RESEARCHER_PROMPTS,
    "bear_researcher": BEAR_RESEARCHER_PROMPTS,
    "trader": TRADER_PROMPTS,
    "research_manager": RESEARCH_MANAGER_PROMPTS,
    "risk_manager": RISK_MANAGER_PROMPTS,
    "aggressive_debator": AGGRESSIVE_DEBATOR_PROMPTS,
    "conservative_debator": CONSERVATIVE_DEBATOR_PROMPTS,
    "neutral_debator": NEUTRAL_DEBATOR_PROMPTS,
}

def get_agent_prompt(agent_type: str, language: Language) -> Dict[str, Any]:
    """
    获取Agent提示词 - 现在返回空字典强制使用YAML文件
    
    Args:
        agent_type: Agent类型
        language: 语言枚举
        
    Returns:
        空字典，强制prompt_loader使用YAML文件
    """
    # Return empty dict to force YAML loading
    return {}

def is_language_supported(language: str) -> bool:
    """
    检查是否支持指定语言
    
    Args:
        language: 语言代码
        
    Returns:
        是否支持（现在总是返回True，由YAML文件处理）
    """
    # Return True to let YAML files handle language support
    return language in ["zh-CN", "en-US"]