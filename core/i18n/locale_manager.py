"""全局语言环境管理器 - Linus原则：统一的语言配置管理

这个模块负责：
1. 统一前后端语言环境配置
2. 提供全局语言状态管理
3. 支持动态语言切换
4. 确保语言配置的一致性
"""

import os
import logging
from typing import Optional, List
from threading import Lock
from core.config import settings

logger = logging.getLogger(__name__)

class LocaleManager:
    """全局语言环境管理器
    
    Linus原则：
    - 单一数据源：所有语言配置从这里获取
    - 零特殊情况：统一的语言处理逻辑
    - 线程安全：支持并发访问
    """
    
    _instance: Optional['LocaleManager'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'LocaleManager':
        """单例模式 - 确保全局唯一的语言管理器"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化语言管理器"""
        if hasattr(self, '_initialized'):
            return
            
        self._current_language = settings.default_language
        self._supported_languages = self._parse_supported_languages()
        self._language_lock = Lock()
        self._initialized = True
        
        logger.info(f"LocaleManager initialized: current={self._current_language}, supported={self._supported_languages}")
    
    def _parse_supported_languages(self) -> List[str]:
        """解析支持的语言列表"""
        if isinstance(settings.supported_languages, list):
            return settings.supported_languages
        elif isinstance(settings.supported_languages, str):
            return [lang.strip() for lang in settings.supported_languages.split(',') if lang.strip()]
        else:
            return ['zh-CN', 'en-US']  # 默认支持的语言
    
    @property
    def current_language(self) -> str:
        """获取当前语言"""
        with self._language_lock:
            return self._current_language
    
    @property
    def supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return self._supported_languages.copy()
    
    def set_language(self, language: str) -> bool:
        """设置当前语言
        
        Args:
            language: 语言代码 (如 'zh-CN', 'en-US')
            
        Returns:
            bool: 设置是否成功
        """
        normalized_lang = self._normalize_language(language)
        
        if not self._is_supported_language(normalized_lang):
            logger.warning(f"Unsupported language: {language} (normalized: {normalized_lang})")
            return False
        
        with self._language_lock:
            old_language = self._current_language
            self._current_language = normalized_lang
            
        logger.info(f"Language changed: {old_language} -> {normalized_lang}")
        return True
    
    def _normalize_language(self, language: str) -> str:
        """标准化语言代码
        
        Linus原则：消除特殊情况，统一处理逻辑
        """
        if not language:
            return settings.default_language
            
        lang_lower = language.lower().strip()
        
        # 标准化映射
        lang_mapping = {
            'zh': 'zh-CN',
            'zh-cn': 'zh-CN', 
            'zh_cn': 'zh-CN',
            'chinese': 'zh-CN',
            'en': 'en-US',
            'en-us': 'en-US',
            'en_us': 'en-US', 
            'english': 'en-US'
        }
        
        return lang_mapping.get(lang_lower, language)
    
    def _is_supported_language(self, language: str) -> bool:
        """检查语言是否被支持"""
        return language in self._supported_languages
    
    def get_fallback_language(self) -> str:
        """获取回退语言"""
        # 优先使用配置的默认语言
        if self._is_supported_language(settings.default_language):
            return settings.default_language
        
        # 如果默认语言不在支持列表中，使用第一个支持的语言
        if self._supported_languages:
            return self._supported_languages[0]
            
        # 最后的回退
        return 'zh-CN'
    
    def get_language_for_request(self, request_language: Optional[str] = None) -> str:
        """为请求获取合适的语言
        
        Args:
            request_language: 请求指定的语言
            
        Returns:
            str: 最终使用的语言代码
        """
        # 1. 优先使用请求指定的语言
        if request_language:
            normalized = self._normalize_language(request_language)
            if self._is_supported_language(normalized):
                return normalized
        
        # 2. 使用当前全局语言
        if self._is_supported_language(self.current_language):
            return self.current_language
        
        # 3. 使用回退语言
        return self.get_fallback_language()
    
    def is_chinese(self, language: Optional[str] = None) -> bool:
        """判断是否为中文"""
        lang = language or self.current_language
        return lang.startswith('zh')
    
    def is_english(self, language: Optional[str] = None) -> bool:
        """判断是否为英文"""
        lang = language or self.current_language
        return lang.startswith('en')
    
    def get_language_info(self) -> dict:
        """获取语言环境信息"""
        return {
            'current': self.current_language,
            'supported': self.supported_languages,
            'default': settings.default_language,
            'fallback': self.get_fallback_language()
        }


# 全局语言管理器实例
locale_manager = LocaleManager()


# 便利函数
def get_current_language() -> str:
    """获取当前语言"""
    return locale_manager.current_language


def set_current_language(language: str) -> bool:
    """设置当前语言"""
    return locale_manager.set_language(language)


def get_supported_languages() -> List[str]:
    """获取支持的语言列表"""
    return locale_manager.supported_languages


def get_language_for_request(request_language: Optional[str] = None) -> str:
    """为请求获取合适的语言"""
    return locale_manager.get_language_for_request(request_language)


def is_chinese_language(language: Optional[str] = None) -> bool:
    """判断是否为中文"""
    return locale_manager.is_chinese(language)


def is_english_language(language: Optional[str] = None) -> bool:
    """判断是否为英文"""
    return locale_manager.is_english(language)