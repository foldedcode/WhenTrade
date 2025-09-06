"""
提示词加载器 - 统一管理所有Agent的提示词配置
遵循Linus哲学：通过数据结构消除特殊情况
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("prompt_loader")

# 导入多语言提示词资源
from core.i18n.agent_prompts import get_agent_prompt, is_language_supported, Language


class PromptLoader:
    """提示词加载器 - 统一管理所有Agent的提示词"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化提示词加载器
        
        Args:
            base_dir: 提示词配置文件的基础目录，默认为当前文件所在目录的prompts子目录
        """
        if base_dir is None:
            base_dir = Path(__file__).parent / "prompts"
        self.base_dir = Path(base_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._base_template: Optional[Dict[str, Any]] = None
        
        logger.debug(f"初始化提示词加载器，基础目录: {self.base_dir}")
    
    def load_base_template(self) -> Dict[str, Any]:
        """加载基础模板"""
        if self._base_template is None:
            base_path = self.base_dir / "base" / "analyst_base.yaml"
            if base_path.exists():
                with open(base_path, 'r', encoding='utf-8') as f:
                    self._base_template = yaml.safe_load(f)
                logger.debug("加载基础分析师模板")
            else:
                logger.warning(f"基础模板不存在: {base_path}")
                self._base_template = {}
        return self._base_template
    
    def load_prompt(self, agent_type: str, variant: Optional[str] = None, language: str = "zh-CN") -> Dict[str, Any]:
        """
        加载指定Agent的提示词配置
        
        Args:
            agent_type: Agent类型（如 market, onchain, defi, social_media_analyst 等）
            variant: 变体版本（如 react, simple 等）
            language: 语言代码（如 zh-CN, en-US）
        
        Returns:
            提示词配置字典
        """
        # 首先尝试从多语言资源加载
        multilingual_prompt = self._load_multilingual_prompt(agent_type, language)
        if multilingual_prompt:
            return multilingual_prompt
            
        # 降级到YAML文件加载，支持多语言文件选择
        cache_key = f"{agent_type}_{variant}_{language}" if variant else f"{agent_type}_{language}"
        
        # 检查缓存
        if cache_key in self._cache:
            logger.debug(f"从缓存返回提示词: {cache_key}")
            return self._cache[cache_key]
        
        # 获取基础文件路径
        base_prompt_file = self._get_base_prompt_file_path(agent_type, variant)
        
        # 根据语言选择文件
        prompt_file = self._select_language_file(base_prompt_file, language)
        
        # 加载基础模板
        base_config = self.load_base_template().copy()
        
        # 加载特定配置并合并
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                specific_config = yaml.safe_load(f)
                
            # 深度合并配置
            merged_config = self._deep_merge(base_config, specific_config)
            
            logger.info(f"加载提示词配置: {prompt_file} (语言: {language})")
            self._cache[cache_key] = merged_config
            return merged_config
        else:
            logger.warning(f"提示词配置文件不存在: {prompt_file}，使用默认配置")
            # 返回默认配置
            default_config = self._get_default_config(agent_type)
            self._cache[cache_key] = default_config
            return default_config
    
    def _load_multilingual_prompt(self, agent_type: str, language: str) -> Optional[Dict[str, Any]]:
        """
        从多语言资源加载提示词
        
        Args:
            agent_type: Agent类型
            language: 语言代码
            
        Returns:
            提示词配置字典或None（如果不支持）
        """
        try:
            # 转换语言代码到Language枚举
            lang_enum = Language.ZH_CN if language.startswith('zh') else Language.EN_US
            
            # 从多语言资源获取提示词
            prompt_data = get_agent_prompt(agent_type, lang_enum)
            if prompt_data:
                logger.info(f"从多语言资源加载提示词: {agent_type} ({language})")
                return {
                    "version": "2.0.0",  # 多语言版本
                    "type": agent_type,
                    "language": language,
                    "system_role": prompt_data.get("system_role", f"专业的{agent_type}分析师"),
                    "system_message": prompt_data.get("system_message", ""),
                    "source": "multilingual_resource"
                }
        except Exception as e:
            logger.debug(f"多语言资源加载失败: {agent_type} ({language}) - {e}")
            
        return None

    def _get_base_prompt_file_path(self, agent_type: str, variant: Optional[str] = None) -> Path:
        """
        获取基础提示词文件路径（不包含语言后缀）
        
        Args:
            agent_type: Agent类型
            variant: 变体版本
            
        Returns:
            基础文件路径
        """
        # 处理特殊的命名（如 social_media_analyst -> social/social_media_analyst.yaml）
        if agent_type == "social_media_analyst":
            return self.base_dir / "social" / "social_media_analyst"
        elif agent_type == "fundamentals_analyst":
            return self.base_dir / "market" / "fundamentals_analyst"
        elif agent_type == "china_market_analyst":
            return self.base_dir / "market" / "china_market_analyst"
        elif agent_type == "risk_manager":
            return self.base_dir / "managers" / "risk_manager"
        elif agent_type == "research_manager":
            return self.base_dir / "managers" / "research_manager"
        elif agent_type == "portfolio_manager":
            return self.base_dir / "managers" / "portfolio_manager"
        elif agent_type == "aggressive_debator":
            return self.base_dir / "risk_debators" / "aggressive_debator"
        elif agent_type == "conservative_debator":
            return self.base_dir / "risk_debators" / "conservative_debator"
        elif agent_type == "neutral_debator":
            return self.base_dir / "risk_debators" / "neutral_debator"
        elif agent_type == "trader":
            return self.base_dir / "trader" / "trader"
        elif agent_type == "bear_researcher":
            return self.base_dir / "researchers" / "bear_researcher"
        elif agent_type == "bull_researcher":
            return self.base_dir / "researchers" / "bull_researcher"
        elif agent_type == "market_analyst":
            return self.base_dir / "market" / "market_analyst"
        elif agent_type == "news_analyst":
            return self.base_dir / "news" / "news_analyst"
        elif variant:
            # 构建文件路径
            return self.base_dir / agent_type / f"{agent_type}_analyst_{variant}"
        else:
            return self.base_dir / agent_type / f"{agent_type}_analyst"
    
    def _select_language_file(self, base_path: Path, language: str) -> Path:
        """
        根据语言选择对应的YAML文件
        
        Args:
            base_path: 基础文件路径（不含扩展名）
            language: 语言代码
            
        Returns:
            最终的文件路径
        """
        # 如果是中文，优先尝试_zh.yaml文件
        if language.startswith('zh'):
            zh_file = base_path.with_suffix('').with_name(f"{base_path.name}_zh.yaml")
            if zh_file.exists():
                logger.debug(f"使用中文提示词文件: {zh_file}")
                return zh_file
        
        # 如果是英文，优先尝试_en.yaml文件
        elif language.startswith('en'):
            en_file = base_path.with_suffix('').with_name(f"{base_path.name}_en.yaml")
            if en_file.exists():
                logger.debug(f"使用英文提示词文件: {en_file}")
                return en_file
        
        # 降级到原始文件
        original_file = base_path.with_suffix('.yaml')
        logger.debug(f"降级到原始提示词文件: {original_file}")
        return original_file

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典，override的值优先"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _get_default_config(self, agent_type: str) -> Dict[str, Any]:
        """获取默认配置（向后兼容）"""
        defaults = {
            "market": {
                "version": "1.0.0",
                "system_role": "专业的股票技术分析师",
                "system_message": "你是一位专业的股票技术分析师，负责分析技术指标和价格趋势。",
                "analysis_focus": ["技术指标", "价格趋势", "成交量分析"],
                "output_format": "structured_report"
            },
            "onchain": {
                "version": "1.0.0",
                "system_role": "链上数据分析师",
                "system_message": "你是一位专业的链上数据分析师，专注于区块链数据分析。",
                "analysis_focus": ["交易量", "钱包活动", "网络指标"],
                "output_format": "structured_report"
            },
            "defi": {
                "version": "1.0.0",
                "system_role": "DeFi协议分析师",
                "system_message": "你是一位专业的DeFi协议分析师，专注于去中心化金融分析。",
                "analysis_focus": ["TVL", "APY", "流动性"],
                "output_format": "structured_report"
            }
        }
        
        return defaults.get(agent_type, {
            "version": "1.0.0",
            "system_role": f"{agent_type}分析师",
            "system_message": f"你是一位专业的{agent_type}分析师。",
            "analysis_focus": [],
            "output_format": "text"
        })
    
    def create_chat_template(self, agent_type: str, variant: Optional[str] = None) -> ChatPromptTemplate:
        """
        创建LangChain的ChatPromptTemplate
        
        Args:
            agent_type: Agent类型
            variant: 变体版本
        
        Returns:
            ChatPromptTemplate实例
        """
        config = self.load_prompt(agent_type, variant)
        
        # 构建系统消息
        system_message = config.get("system_message", "")
        if config.get("tool_usage"):
            system_message += f"\n\n您可以使用以下工具：{{tool_names}}。"
        system_message += "\n当前日期是{current_date}。分析股票：{ticker}。"
        
        # 创建消息模板
        messages = [
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages")
        ]
        
        # 如果有人类消息模板，添加它
        if config.get("human_message"):
            messages.insert(1, ("human", config["human_message"]))
        
        return ChatPromptTemplate.from_messages(messages)
    
    def reload_cache(self):
        """清空缓存，强制重新加载所有提示词"""
        self._cache.clear()
        self._base_template = None
        logger.info("提示词缓存已清空")
    
    def get_prompt_version(self, agent_type: str, variant: Optional[str] = None, language: str = "zh-CN") -> str:
        """获取提示词版本号"""
        config = self.load_prompt(agent_type, variant, language)
        return config.get("version", "unknown")
    
    def validate_prompt(self, agent_type: str, variant: Optional[str] = None, language: str = "zh-CN") -> bool:
        """
        验证提示词配置的完整性
        
        Returns:
            True if valid, False otherwise
        """
        try:
            config = self.load_prompt(agent_type, variant, language)
            
            # 检查必需字段
            required_fields = ["version", "system_role", "system_message"]
            for field in required_fields:
                if field not in config:
                    logger.error(f"提示词配置缺少必需字段: {field}")
                    return False
            
            # 检查占位符
            system_msg = config.get("system_message", "")
            placeholders = ["{ticker}", "{current_date}"]
            
            # 验证占位符格式
            for placeholder in placeholders:
                if placeholder in system_msg and not placeholder.replace("{", "{{").replace("}", "}}") in system_msg:
                    logger.warning(f"占位符格式可能有问题: {placeholder}")
            
            return True
            
        except Exception as e:
            logger.error(f"验证提示词失败: {e}")
            return False


# 全局实例
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """获取全局提示词加载器实例"""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


def reload_prompts():
    """重新加载所有提示词（用于开发模式热重载）"""
    loader = get_prompt_loader()
    loader.reload_cache()
    logger.info("所有提示词已重新加载")