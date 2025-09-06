"""
配置管理 - Linus原则：零硬编码，所有配置从环境变量读取
"""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置 - 消除所有硬编码默认值"""
    
    # 基础配置 - 从环境变量读取
    project_name: str = Field(default="When.Trade", env="PROJECT_NAME")
    version: str = Field(default="1.0.0", env="VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    secret_key: str = Field(..., env="SECRET_KEY")  # 必需，无默认值
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 数据库配置 - 必需环境变量，无默认值
    database_url: str = Field(..., env="DATABASE_URL")
    DATABASE_URL: str = Field(..., env="DATABASE_URL")  # 兼容性别名
    
    # Redis配置 - 必需环境变量，无默认值
    redis_url: str = Field(..., env="REDIS_URL")
    redis_host: str = Field(..., env="REDIS_HOST") 
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # 备份配置
    backup_directory: str = Field(default="./backups", env="BACKUP_DIRECTORY")
    
    # JWT配置 - 必需，无默认值
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    
    # CORS配置 - 从环境变量读取，支持逗号分隔
    cors_origins: str = Field(..., env="CORS_ORIGINS")
    allowed_origins: List[str] = []  # 由cors_origins计算得出
    BACKEND_CORS_ORIGINS: List[str] = []  # 兼容性别名
    
    @validator('allowed_origins', pre=True, always=True)
    def parse_cors_origins(cls, v, values):
        """解析CORS origins"""
        cors_str = values.get('cors_origins', '')
        if cors_str:
            return [origin.strip() for origin in cors_str.split(',') if origin.strip()]
        return []
    
    @validator('BACKEND_CORS_ORIGINS', pre=True, always=True) 
    def set_backend_cors(cls, v, values):
        """设置兼容性CORS配置"""
        return values.get('allowed_origins', [])
    
    # API Keys - 从环境变量读取
    yfinance_api_key: Optional[str] = Field(default=None, env="YFINANCE_API_KEY")
    binance_api_key: Optional[str] = Field(default=None, env="BINANCE_API_KEY")
    binance_api_secret: Optional[str] = Field(default=None, env="BINANCE_API_SECRET")
    
    # 数据库详细配置 - 从环境变量读取
    database_user: str = Field(..., env="DATABASE_USER")
    database_password: str = Field(..., env="DATABASE_PASSWORD")
    database_host: str = Field(..., env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(..., env="DATABASE_NAME")
    
    # 成本控制配置
    cost_tracking_enabled: bool = Field(default=True, env="COST_TRACKING_ENABLED")
    budget_alert_threshold: float = Field(default=0.8, env="BUDGET_ALERT_THRESHOLD")
    usage_retention_days: int = Field(default=90, env="USAGE_RETENTION_DAYS")
    achievement_check_interval: int = Field(default=3600, env="ACHIEVEMENT_CHECK_INTERVAL")
    model_pricing_update_interval: int = Field(default=86400, env="MODEL_PRICING_UPDATE_INTERVAL")
    
    # 多语言配置 - Linus原则：统一语言环境管理
    default_language: str = Field(default="zh-CN", env="DEFAULT_LANGUAGE")
    supported_languages: List[str] = Field(default=["zh-CN", "en-US"], env="SUPPORTED_LANGUAGES")
    
    @validator('supported_languages', pre=True, always=True)
    def parse_supported_languages(cls, v):
        """解析支持的语言列表"""
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(',') if lang.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # 允许大小写不敏感的环境变量匹配
        extra = "ignore"  # 忽略额外的环境变量


# 创建设置实例
settings = Settings()