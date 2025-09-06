"""
初始化数据库表结构
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings
from core.infrastructure.database import Base
from core.database.models import *  # 导入所有模型以注册到Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """初始化数据库表结构"""
    # 创建异步引擎
    engine = create_async_engine(
        settings.database_url,
        echo=True,  # 打印SQL语句
    )
    
    try:
        # 创建所有表
        async with engine.begin() as conn:
            logger.info("开始创建数据库表...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("数据库表创建完成！")
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())