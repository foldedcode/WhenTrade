"""动态语言内容加载器 - Linus原则：零特殊情况的内容加载

功能：
1. 运行时动态加载语言资源
2. 支持内容热更新
3. 缓存管理和失效策略
4. 回退机制确保内容可用性
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from threading import Lock, RLock
from datetime import datetime, timedelta
from dataclasses import dataclass
from .locale_manager import locale_manager
from .messages import MESSAGES, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


@dataclass
class ContentCache:
    """内容缓存项"""
    content: Dict[str, Any]
    loaded_at: datetime
    file_path: Optional[Path] = None
    file_mtime: Optional[float] = None


class DynamicContentLoader:
    """动态语言内容加载器
    
    Linus原则：
    - 统一数据结构：所有语言内容使用相同的加载逻辑
    - 零特殊情况：前后端内容加载使用统一接口
    - 简单缓存：基于时间和文件修改时间的简单缓存策略
    """
    
    def __init__(self, cache_ttl_seconds: int = 300):
        """初始化动态内容加载器
        
        Args:
            cache_ttl_seconds: 缓存生存时间（秒）
        """
        self._cache: Dict[str, ContentCache] = {}
        self._cache_lock = RLock()
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._base_paths: List[Path] = []
        self._initialized = False
        
        # 初始化基础路径
        self._setup_base_paths()
        
        # 预加载核心消息
        self._preload_core_messages()
        
        logger.info(f"DynamicContentLoader initialized with TTL: {cache_ttl_seconds}s")
    
    def _setup_base_paths(self):
        """设置基础搜索路径"""
        # 后端i18n目录
        backend_i18n = Path(__file__).parent
        
        # 前端locales目录（如果存在）
        project_root = Path(__file__).parent.parent.parent
        frontend_locales = project_root / "web" / "src" / "locales"
        
        self._base_paths = [backend_i18n]
        if frontend_locales.exists():
            self._base_paths.append(frontend_locales)
            
        logger.debug(f"Base paths: {[str(p) for p in self._base_paths]}")
    
    def _preload_core_messages(self):
        """预加载核心消息到缓存"""
        for language in SUPPORTED_LANGUAGES:
            cache_key = f"core_messages_{language}"
            
            with self._cache_lock:
                self._cache[cache_key] = ContentCache(
                    content=MESSAGES.get(language, {}),
                    loaded_at=datetime.now()
                )
        
        logger.debug("Core messages preloaded")
    
    def _is_cache_valid(self, cache_item: ContentCache) -> bool:
        """检查缓存是否有效"""
        # 检查时间过期
        if datetime.now() - cache_item.loaded_at > self._cache_ttl:
            return False
        
        # 检查文件修改时间（如果有文件路径）
        if cache_item.file_path and cache_item.file_path.exists():
            current_mtime = cache_item.file_path.stat().st_mtime
            if cache_item.file_mtime and current_mtime != cache_item.file_mtime:
                return False
        
        return True
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            logger.debug(f"Loaded JSON file: {file_path}")
            return content
            
        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
            logger.error(f"Failed to load JSON file {file_path}: {e}")
            return {}
    
    def _find_content_file(self, language: str, namespace: str) -> Optional[Path]:
        """查找内容文件
        
        Args:
            language: 语言代码
            namespace: 命名空间（如 'common', 'analysis'）
            
        Returns:
            Path: 文件路径，如果找不到返回None
        """
        # 可能的文件名
        possible_names = [
            f"{namespace}.json",
            f"{language}_{namespace}.json",
            f"{namespace}_{language}.json"
        ]
        
        # 可能的路径
        possible_paths = [
            # 前端格式: locales/zh-CN/common.json
            language,
            # 后端格式: i18n/zh-CN/common.json
            f"locales/{language}",
            f"i18n/{language}"
        ]
        
        for base_path in self._base_paths:
            for sub_path in possible_paths:
                for filename in possible_names:
                    full_path = base_path / sub_path / filename
                    if full_path.exists():
                        return full_path
        
        return None
    
    def load_namespace_content(self, language: str, namespace: str, force_reload: bool = False) -> Dict[str, Any]:
        """加载命名空间内容
        
        Args:
            language: 语言代码
            namespace: 命名空间
            force_reload: 是否强制重新加载
            
        Returns:
            Dict: 内容字典
        """
        cache_key = f"{language}_{namespace}"
        
        with self._cache_lock:
            # 检查缓存
            if not force_reload and cache_key in self._cache:
                cache_item = self._cache[cache_key]
                if self._is_cache_valid(cache_item):
                    logger.debug(f"Cache hit: {cache_key}")
                    return cache_item.content
            
            # 查找并加载文件
            file_path = self._find_content_file(language, namespace)
            
            if file_path:
                content = self._load_json_file(file_path)
                file_mtime = file_path.stat().st_mtime
                
                # 更新缓存
                self._cache[cache_key] = ContentCache(
                    content=content,
                    loaded_at=datetime.now(),
                    file_path=file_path,
                    file_mtime=file_mtime
                )
                
                logger.debug(f"Loaded namespace: {cache_key} from {file_path}")
                return content
            else:
                logger.warning(f"Content file not found: {language}/{namespace}")
                return {}
    
    def get_message(self, key: str, language: Optional[str] = None, namespace: str = "core", **kwargs) -> str:
        """获取本地化消息
        
        Args:
            key: 消息键
            language: 语言代码，如果为None则使用当前语言
            namespace: 命名空间
            **kwargs: 格式化参数
            
        Returns:
            str: 本地化消息
        """
        # 确定语言
        if language is None:
            language = locale_manager.current_language
        
        # 标准化语言代码
        language = locale_manager._normalize_language(language)
        
        # 获取内容
        if namespace == "core":
            # 核心消息直接从预加载缓存获取
            cache_key = f"core_messages_{language}"
            with self._cache_lock:
                if cache_key in self._cache:
                    content = self._cache[cache_key].content
                else:
                    content = MESSAGES.get(language, {})
        else:
            # 其他命名空间动态加载
            content = self.load_namespace_content(language, namespace)
        
        # 获取消息
        message = content.get(key)
        
        if message is None:
            # 尝试回退语言
            fallback_language = locale_manager.get_fallback_language()
            if fallback_language != language:
                logger.debug(f"Message key '{key}' not found in {language}, trying fallback {fallback_language}")
                return self.get_message(key, fallback_language, namespace, **kwargs)
            else:
                # 最后的回退：返回键名
                logger.warning(f"Message key '{key}' not found in any language")
                message = key
        
        # 格式化消息
        if kwargs and isinstance(message, str):
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to format message '{key}': {e}")
                return message
        
        return str(message)
    
    def get_nested_message(self, key_path: str, language: Optional[str] = None, namespace: str = "core", **kwargs) -> str:
        """获取嵌套的本地化消息
        
        Args:
            key_path: 点分隔的键路径，如 'analysis.status.running'
            language: 语言代码
            namespace: 命名空间
            **kwargs: 格式化参数
            
        Returns:
            str: 本地化消息
        """
        # 确定语言
        if language is None:
            language = locale_manager.current_language
        
        # 获取内容
        content = self.load_namespace_content(language, namespace)
        
        # 按路径查找
        keys = key_path.split('.')
        current = content
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                # 尝试回退语言
                fallback_language = locale_manager.get_fallback_language()
                if fallback_language != language:
                    return self.get_nested_message(key_path, fallback_language, namespace, **kwargs)
                else:
                    logger.warning(f"Nested key path '{key_path}' not found")
                    return key_path
        
        # 格式化消息
        message = str(current)
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to format nested message '{key_path}': {e}")
                return message
        
        return message
    
    def reload_namespace(self, language: str, namespace: str) -> bool:
        """重新加载命名空间内容
        
        Args:
            language: 语言代码
            namespace: 命名空间
            
        Returns:
            bool: 是否成功重新加载
        """
        try:
            self.load_namespace_content(language, namespace, force_reload=True)
            logger.info(f"Reloaded namespace: {language}/{namespace}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload namespace {language}/{namespace}: {e}")
            return False
    
    def clear_cache(self, language: Optional[str] = None, namespace: Optional[str] = None):
        """清除缓存
        
        Args:
            language: 特定语言，如果为None则清除所有语言
            namespace: 特定命名空间，如果为None则清除所有命名空间
        """
        with self._cache_lock:
            if language is None and namespace is None:
                # 清除所有缓存
                self._cache.clear()
                logger.info("All cache cleared")
            else:
                # 选择性清除
                keys_to_remove = []
                for key in self._cache.keys():
                    should_remove = True
                    
                    if language and not key.startswith(f"{language}_"):
                        should_remove = False
                    
                    if namespace and not key.endswith(f"_{namespace}"):
                        should_remove = False
                    
                    if should_remove:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._cache[key]
                
                logger.info(f"Cache cleared for language={language}, namespace={namespace}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._cache_lock:
            total_items = len(self._cache)
            valid_items = sum(1 for item in self._cache.values() if self._is_cache_valid(item))
            
            return {
                'total_items': total_items,
                'valid_items': valid_items,
                'invalid_items': total_items - valid_items,
                'cache_keys': list(self._cache.keys()),
                'cache_ttl_seconds': self._cache_ttl.total_seconds()
            }


# 全局动态加载器实例
dynamic_loader = DynamicContentLoader()


# 便利函数
def get_dynamic_message(key: str, language: Optional[str] = None, namespace: str = "core", **kwargs) -> str:
    """获取动态本地化消息"""
    return dynamic_loader.get_message(key, language, namespace, **kwargs)


def get_nested_message(key_path: str, language: Optional[str] = None, namespace: str = "core", **kwargs) -> str:
    """获取嵌套的动态本地化消息"""
    return dynamic_loader.get_nested_message(key_path, language, namespace, **kwargs)


def reload_content(language: str, namespace: str) -> bool:
    """重新加载内容"""
    return dynamic_loader.reload_namespace(language, namespace)


def clear_content_cache(language: Optional[str] = None, namespace: Optional[str] = None):
    """清除内容缓存"""
    dynamic_loader.clear_cache(language, namespace)