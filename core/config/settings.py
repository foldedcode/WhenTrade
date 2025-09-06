"""
应用配置设置 - 备用配置文件（已被 core/config.py 替换）
注意：这个文件存在硬编码问题，已经被 core/config.py 的统一配置替换
如果仍有代码引用此文件，应该迁移到 core/config.py
"""

import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # 兼容旧版本 pydantic
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """应用设置 - 已废弃，请使用 core.config.settings"""
    
    # 基础配置
    app_name: str = os.getenv("APP_NAME", "When.Trade")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    
    # 数据库配置
    database_url: Optional[str] = os.getenv("DATABASE_URL")  # 移除默认值
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")  # 兼容性别名
    
    # JWT配置
    jwt_secret_key: Optional[str] = os.getenv("JWT_SECRET_KEY")  # 移除默认值
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")  # 兼容性别名
    jwt_algorithm: str = "HS256"
    JWT_ALGORITHM: str = "HS256"  # 兼容性别名
    jwt_expiration_minutes: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "10080"))  # 7天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 兼容性别名
    
    # CORS配置 - 移除硬编码列表  
    cors_origins: str = os.getenv("CORS_ORIGINS", "")
    
    @property
    def allowed_origins(self):
        """获取允许的CORS源"""
        if self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return []
    
    # LLM API密钥
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Redis配置
    redis_url: Optional[str] = os.getenv("REDIS_URL")  # 移除默认值
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")  # 兼容性别名
    
    # 文件上传
    max_upload_size: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # 备份配置
    backup_directory: str = os.getenv("BACKUP_DIRECTORY", "./backups")
    
    # AWS S3配置（可选）
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_backup_bucket: Optional[str] = os.getenv("S3_BACKUP_BUCKET")
    aws_region: Optional[str] = os.getenv("AWS_REGION", "us-east-1")
    
    # 前端URL
    FRONTEND_URL: Optional[str] = os.getenv("FRONTEND_URL")  # 移除默认值
    
    # 交易所API密钥
    YFINANCE_API_KEY: Optional[str] = os.getenv("YFINANCE_API_KEY")
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    
    # 多语言配置 - Linus原则：统一语言环境管理
    default_language: str = os.getenv("DEFAULT_LANGUAGE", "zh-CN")
    supported_languages: str = os.getenv("SUPPORTED_LANGUAGES", "zh-CN,en-US")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量


# 创建全局设置实例
settings = Settings()