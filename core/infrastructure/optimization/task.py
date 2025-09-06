"""
异步任务优化器 - 优化后台任务执行效率和资源使用
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
from queue import PriorityQueue, Queue
import weakref

from core.infrastructure.monitoring import performance_metrics, monitor_operation

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class TaskConfig:
    """任务配置"""
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[int] = None  # 任务超时时间（秒）
    retry_count: int = 0  # 重试次数
    retry_delay: float = 1.0  # 重试延迟（秒）
    concurrent_limit: int = 1  # 并发限制
    cpu_bound: bool = False  # 是否为CPU密集型任务
    memory_limit: Optional[int] = None  # 内存限制（MB）


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    memory_used: float = 0.0
    retry_count: int = 0


class TaskQueue:
    """智能任务队列"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.priority_queue = PriorityQueue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: List[TaskResult] = []
        self.task_configs: Dict[str, TaskConfig] = {}
        self.concurrent_counters: Dict[str, int] = {}  # 不同类型任务的并发计数器
        
        # 线程池和进程池
        self.thread_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="TaskOpt")
        self.process_executor = ProcessPoolExecutor(max_workers=2)
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_execution_time": 0.0,
            "queue_size": 0
        }
        
    async def add_task(
        self, 
        task_id: str,
        coro_func: Callable,
        config: TaskConfig = None,
        *args,
        **kwargs
    ):
        """添加任务到队列"""
        if config is None:
            config = TaskConfig()
            
        self.task_configs[task_id] = config
        
        # 创建优先级队列项
        priority_item = (
            config.priority.value,
            time.time(),  # 时间戳用于相同优先级的FIFO
            task_id,
            coro_func,
            args,
            kwargs
        )
        
        self.priority_queue.put(priority_item)
        self.stats["total_tasks"] += 1
        self.stats["queue_size"] = self.priority_queue.qsize()
        
        logger.debug(f"任务已添加到队列: {task_id}, 优先级: {config.priority.name}")
        
    async def execute_task(
        self,
        task_id: str,
        coro_func: Callable,
        config: TaskConfig,
        *args,
        **kwargs
    ) -> TaskResult:
        """执行单个任务"""
        start_time = time.time()
        result = TaskResult(task_id=task_id, success=False)
        
        try:
            # 检查并发限制
            task_type = coro_func.__name__
            current_concurrent = self.concurrent_counters.get(task_type, 0)
            
            if current_concurrent >= config.concurrent_limit:
                logger.warning(f"任务 {task_id} 达到并发限制，等待...")
                while self.concurrent_counters.get(task_type, 0) >= config.concurrent_limit:
                    await asyncio.sleep(0.1)
                    
            # 增加并发计数器
            self.concurrent_counters[task_type] = self.concurrent_counters.get(task_type, 0) + 1
            
            # 执行任务
            async with monitor_operation(task_id, "background_task"):
                if config.cpu_bound:
                    # CPU密集型任务使用进程池
                    loop = asyncio.get_event_loop()
                    if asyncio.iscoroutinefunction(coro_func):
                        # 如果是协程函数，需要特殊处理
                        task_result = await coro_func(*args, **kwargs)
                    else:
                        task_result = await loop.run_in_executor(
                            self.process_executor, 
                            coro_func, 
                            *args
                        )
                else:
                    # 普通任务
                    if asyncio.iscoroutinefunction(coro_func):
                        if config.timeout:
                            task_result = await asyncio.wait_for(
                                coro_func(*args, **kwargs),
                                timeout=config.timeout
                            )
                        else:
                            task_result = await coro_func(*args, **kwargs)
                    else:
                        # 同步函数使用线程池
                        loop = asyncio.get_event_loop()
                        task_result = await loop.run_in_executor(
                            self.thread_executor,
                            coro_func,
                            *args
                        )
                        
            result.success = True
            result.result = task_result
            
        except asyncio.TimeoutError:
            result.error = f"任务超时 ({config.timeout}s)"
            logger.error(f"任务超时: {task_id}")
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"任务执行失败: {task_id}, 错误: {e}")
            
            # 重试逻辑
            if config.retry_count > result.retry_count:
                result.retry_count += 1
                logger.info(f"任务重试: {task_id}, 第{result.retry_count}次")
                
                await asyncio.sleep(config.retry_delay * result.retry_count)  # 指数退避
                return await self.execute_task(task_id, coro_func, config, *args, **kwargs)
                
        finally:
            # 减少并发计数器
            task_type = coro_func.__name__
            self.concurrent_counters[task_type] = max(0, self.concurrent_counters.get(task_type, 1) - 1)
            
            # 计算执行时间
            result.duration = time.time() - start_time
            
            # 更新统计信息
            if result.success:
                self.stats["completed_tasks"] += 1
            else:
                self.stats["failed_tasks"] += 1
                
            # 更新平均执行时间
            total_completed = self.stats["completed_tasks"] + self.stats["failed_tasks"]
            if total_completed > 0:
                current_avg = self.stats["avg_execution_time"]
                self.stats["avg_execution_time"] = (
                    (current_avg * (total_completed - 1) + result.duration) / total_completed
                )
                
        return result
        
    async def process_queue(self):
        """处理任务队列"""
        while True:
            try:
                # 检查运行中的任务数量
                if len(self.running_tasks) >= self.max_concurrent:
                    await asyncio.sleep(0.1)
                    continue
                    
                # 从队列获取任务
                if self.priority_queue.empty():
                    await asyncio.sleep(0.1)
                    continue
                    
                priority, timestamp, task_id, coro_func, args, kwargs = self.priority_queue.get()
                config = self.task_configs.get(task_id, TaskConfig())
                
                # 创建任务
                task = asyncio.create_task(
                    self.execute_task(task_id, coro_func, config, *args, **kwargs)
                )
                
                self.running_tasks[task_id] = task
                self.stats["queue_size"] = self.priority_queue.qsize()
                
                # 添加完成回调
                task.add_done_callback(lambda t, tid=task_id: self._on_task_complete(tid, t))
                
                logger.debug(f"任务开始执行: {task_id}")
                
            except Exception as e:
                logger.error(f"处理任务队列异常: {e}")
                await asyncio.sleep(1)
                
    def _on_task_complete(self, task_id: str, task: asyncio.Task):
        """任务完成回调"""
        try:
            result = task.result()
            self.completed_tasks.append(result)
            
            # 保留最近1000个完成的任务
            if len(self.completed_tasks) > 1000:
                self.completed_tasks.pop(0)
                
            logger.debug(f"任务完成: {task_id}, 成功: {result.success}, 耗时: {result.duration:.3f}s")
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {task_id}, 错误: {e}")
            
        finally:
            # 从运行中任务列表移除
            self.running_tasks.pop(task_id, None)
            
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            **self.stats,
            "running_tasks": len(self.running_tasks),
            "concurrent_counters": dict(self.concurrent_counters),
            "recent_completed": [
                {
                    "task_id": result.task_id,
                    "success": result.success,
                    "duration": result.duration,
                    "error": result.error
                }
                for result in self.completed_tasks[-10:]
            ]
        }
        
    async def shutdown(self):
        """关闭任务队列"""
        logger.info("关闭任务队列...")
        
        # 等待所有运行中的任务完成
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
            
        # 关闭执行器
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        logger.info("任务队列已关闭")


class TaskOptimizer:
    """任务优化器主类"""
    
    def __init__(self):
        self.task_queue = TaskQueue()
        self.optimization_rules: List[Callable] = []
        self.task_templates: Dict[str, TaskConfig] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # 注册内置优化规则
        self._register_builtin_rules()
        
    def _register_builtin_rules(self):
        """注册内置优化规则"""
        
        def cpu_intensive_rule(task_name: str, config: TaskConfig) -> TaskConfig:
            """CPU密集型任务优化规则"""
            if any(keyword in task_name.lower() for keyword in ['analysis', 'compute', 'calculate']):
                config.cpu_bound = True
                config.concurrent_limit = min(config.concurrent_limit, 2)  # 限制并发
                config.timeout = config.timeout or 300  # 5分钟超时
            return config
            
        def io_bound_rule(task_name: str, config: TaskConfig) -> TaskConfig:
            """IO密集型任务优化规则"""
            if any(keyword in task_name.lower() for keyword in ['fetch', 'download', 'upload', 'backup']):
                config.concurrent_limit = max(config.concurrent_limit, 5)  # 允许更多并发
                config.timeout = config.timeout or 600  # 10分钟超时
                config.retry_count = max(config.retry_count, 2)  # 允许重试
            return config
            
        def critical_task_rule(task_name: str, config: TaskConfig) -> TaskConfig:
            """关键任务优化规则"""
            if any(keyword in task_name.lower() for keyword in ['backup', 'restore', 'migrate']):
                config.priority = TaskPriority.HIGH
                config.retry_count = max(config.retry_count, 3)
                config.timeout = config.timeout or 1800  # 30分钟超时
            return config
            
        self.optimization_rules = [cpu_intensive_rule, io_bound_rule, critical_task_rule]
        
    def register_task_template(self, task_type: str, config: TaskConfig):
        """注册任务模板"""
        self.task_templates[task_type] = config
        logger.info(f"注册任务模板: {task_type}")
        
    def optimize_task_config(self, task_name: str, config: TaskConfig) -> TaskConfig:
        """应用优化规则"""
        optimized_config = config
        
        for rule in self.optimization_rules:
            try:
                optimized_config = rule(task_name, optimized_config)
            except Exception as e:
                logger.error(f"应用优化规则失败: {rule.__name__}, 错误: {e}")
                
        return optimized_config
        
    async def submit_task(
        self,
        task_id: str,
        coro_func: Callable,
        config: Optional[TaskConfig] = None,
        *args,
        **kwargs
    ):
        """提交优化后的任务"""
        if config is None:
            # 尝试从模板获取配置
            task_type = coro_func.__name__
            config = self.task_templates.get(task_type, TaskConfig())
        else:
            config = TaskConfig(**config.__dict__)  # 复制配置
            
        # 应用优化规则
        optimized_config = self.optimize_task_config(task_id, config)
        
        # 提交到任务队列
        await self.task_queue.add_task(task_id, coro_func, optimized_config, *args, **kwargs)
        
        logger.info(f"任务已优化并提交: {task_id}")
        
    async def start(self):
        """启动任务优化器"""
        # 启动任务队列处理
        asyncio.create_task(self.task_queue.process_queue())
        
        # 启动监控任务
        self._monitoring_task = asyncio.create_task(self._monitor_performance())
        
        logger.info("任务优化器已启动")
        
    async def _monitor_performance(self):
        """监控任务执行性能"""
        while True:
            try:
                stats = self.task_queue.get_stats()
                
                # 记录性能指标
                performance_metrics.record_request(
                    "task_queue_stats",
                    "INTERNAL",
                    stats["avg_execution_time"],
                    200
                )
                
                # 检查性能问题
                if stats["queue_size"] > 100:
                    logger.warning(f"任务队列积压: {stats['queue_size']} 个任务")
                    
                if stats["avg_execution_time"] > 30:
                    logger.warning(f"平均任务执行时间过长: {stats['avg_execution_time']:.2f}s")
                    
                # 每5分钟输出一次统计信息
                if datetime.now().minute % 5 == 0 and datetime.now().second < 10:
                    logger.info(f"任务队列统计: {stats}")
                    
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"任务性能监控异常: {e}")
                await asyncio.sleep(60)
                
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.task_queue.get_stats()
        
    async def shutdown(self):
        """关闭任务优化器"""
        logger.info("关闭任务优化器...")
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            
        await self.task_queue.shutdown()
        logger.info("任务优化器已关闭")


# 批量任务处理器
class BatchProcessor:
    """批量任务处理器"""
    
    def __init__(self, batch_size: int = 10, max_wait_time: float = 5.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_tasks: List = []
        self.batch_handlers: Dict[str, Callable] = {}
        self._last_batch_time = time.time()
        
    def register_batch_handler(self, task_type: str, handler: Callable):
        """注册批量处理器"""
        self.batch_handlers[task_type] = handler
        
    async def add_to_batch(self, task_type: str, task_data: Any):
        """添加任务到批次"""
        self.pending_tasks.append((task_type, task_data, time.time()))
        
        # 检查是否需要处理批次
        if (len(self.pending_tasks) >= self.batch_size or 
            time.time() - self._last_batch_time > self.max_wait_time):
            await self._process_batch()
            
    async def _process_batch(self):
        """处理当前批次"""
        if not self.pending_tasks:
            return
            
        # 按任务类型分组
        batches = {}
        for task_type, task_data, timestamp in self.pending_tasks:
            if task_type not in batches:
                batches[task_type] = []
            batches[task_type].append(task_data)
            
        # 处理每个类型的批次
        for task_type, batch_data in batches.items():
            if task_type in self.batch_handlers:
                try:
                    await self.batch_handlers[task_type](batch_data)
                    logger.debug(f"批次处理完成: {task_type}, 数量: {len(batch_data)}")
                except Exception as e:
                    logger.error(f"批次处理失败: {task_type}, 错误: {e}")
                    
        # 清空待处理任务
        self.pending_tasks.clear()
        self._last_batch_time = time.time()


# 全局任务优化器实例
task_optimizer = TaskOptimizer()
batch_processor = BatchProcessor()