"""
调度器入口
"""
import asyncio
from .main import run_scheduler

if __name__ == "__main__":
    asyncio.run(run_scheduler())