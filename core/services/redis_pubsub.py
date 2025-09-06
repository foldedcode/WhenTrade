"""
Redis Pub/Sub服务
用于Celery任务和WebSocket之间的实时消息传递
"""
import json
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import redis.asyncio as aioredis
import redis
from core.config import settings

logger = logging.getLogger(__name__)


class RedisPublisher:
    """Redis消息发布者（用于Celery任务）"""
    
    def __init__(self):
        # 使用同步Redis客户端（Celery任务是同步的）
        self.client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
    
    def publish_progress(self, task_id: str, progress: int, message: str, **kwargs):
        """发布任务进度"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "task.progress",
                "data": {
                    "taskId": task_id,
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                    **kwargs
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.debug(f"Published progress to {channel}: {progress}% - {message}")
        except Exception as e:
            logger.error(f"Failed to publish progress: {str(e)}")
    
    def publish_agent_thought(self, task_id: str, agent_id: str, thought: str, confidence: float = 0.7):
        """发布Agent思考"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "agent.thought",
                "data": {
                    "agentId": agent_id,
                    "thought": thought,
                    "confidence": confidence,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.debug(f"Published agent thought from {agent_id}")
        except Exception as e:
            logger.error(f"Failed to publish agent thought: {str(e)}")
    
    def publish_stage_update(self, task_id: str, stage: str, agents: list):
        """发布阶段更新"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "stage.update",
                "data": {
                    "stage": stage,
                    "agents": agents,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.debug(f"Published stage update: {stage}")
        except Exception as e:
            logger.error(f"Failed to publish stage update: {str(e)}")
    
    def publish_complete(self, task_id: str, result: Dict[str, Any]):
        """发布分析完成"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "analysis.complete",
                "data": {
                    "analysisId": task_id,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.info(f"Published analysis complete for {task_id}")
        except Exception as e:
            logger.error(f"Failed to publish complete: {str(e)}")
    
    def publish_error(self, task_id: str, error: str):
        """发布错误"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "error",
                "data": {
                    "taskId": task_id,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.error(f"Published error for {task_id}: {error}")
        except Exception as e:
            logger.error(f"Failed to publish error: {str(e)}")
    
    def publish_tool_execution_start(self, task_id: str, agent_id: str, tools: list):
        """发布工具执行开始"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "tool.execution.start",
                "data": {
                    "agentId": agent_id,
                    "tools": tools,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.info(f"Published tool execution start for {agent_id}: {tools}")
        except Exception as e:
            logger.error(f"Failed to publish tool execution start: {str(e)}")
    
    def publish_tool_execution_progress(self, task_id: str, agent_id: str, tool_name: str, message: str):
        """发布工具执行进度"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "tool.execution.progress",
                "data": {
                    "agentId": agent_id,
                    "toolName": tool_name,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.debug(f"Published tool progress for {agent_id}/{tool_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish tool execution progress: {str(e)}")
    
    def publish_tool_execution_complete(self, task_id: str, agent_id: str, tool_name: str, success: bool, result_summary: str = None):
        """发布工具执行完成"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "tool.execution.complete",
                "data": {
                    "agentId": agent_id,
                    "toolName": tool_name,
                    "success": success,
                    "resultSummary": result_summary,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.info(f"Published tool execution complete for {agent_id}/{tool_name}: {'success' if success else 'failed'}")
        except Exception as e:
            logger.error(f"Failed to publish tool execution complete: {str(e)}")
    
    def publish_tool_execution_error(self, task_id: str, agent_id: str, tool_name: str, error: str):
        """发布工具执行错误"""
        try:
            channel = f"analysis:{task_id}"
            data = {
                "type": "tool.execution.error",
                "data": {
                    "agentId": agent_id,
                    "toolName": tool_name,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            self.client.publish(channel, json.dumps(data))
            logger.error(f"Published tool execution error for {agent_id}/{tool_name}: {error}")
        except Exception as e:
            logger.error(f"Failed to publish tool execution error: {str(e)}")


class RedisSubscriber:
    """Redis消息订阅者（用于WebSocket）"""
    
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.subscriptions: Dict[str, asyncio.Task] = {}
    
    async def connect(self):
        """连接到Redis"""
        if not self.client:
            self.client = await aioredis.from_url(
                settings.redis_url,
                decode_responses=True
            )
            self.pubsub = self.client.pubsub()
            logger.info("Connected to Redis for subscriptions")
    
    async def disconnect(self):
        """断开Redis连接"""
        try:
            # 取消所有订阅任务
            for task in self.subscriptions.values():
                task.cancel()
            
            # 等待任务完成
            if self.subscriptions:
                await asyncio.gather(*self.subscriptions.values(), return_exceptions=True)
            
            # 关闭pubsub和客户端
            if self.pubsub:
                await self.pubsub.close()
            if self.client:
                await self.client.close()
            
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {str(e)}")
    
    async def subscribe_task(self, task_id: str, callback: Callable[[Dict[str, Any]], None]):
        """订阅任务消息"""
        await self.connect()
        
        channel = f"analysis:{task_id}"
        
        # 如果已经订阅，先取消
        if channel in self.subscriptions:
            self.subscriptions[channel].cancel()
        
        # 创建订阅任务
        async def listen():
            try:
                await self.pubsub.subscribe(channel)
                logger.info(f"Subscribed to {channel}")
                
                async for message in self.pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            await callback(data)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in message: {message['data']}")
                        except Exception as e:
                            logger.error(f"Error processing message: {str(e)}")
            except asyncio.CancelledError:
                logger.info(f"Subscription to {channel} cancelled")
            except Exception as e:
                logger.error(f"Error in subscription {channel}: {str(e)}")
            finally:
                try:
                    # 只有在连接仍然有效时才尝试取消订阅
                    if self.pubsub and hasattr(self.pubsub, 'connection') and self.pubsub.connection:
                        await self.pubsub.unsubscribe(channel)
                        logger.debug(f"Successfully unsubscribed from {channel}")
                except (ConnectionError, redis.exceptions.ConnectionError) as e:
                    # 连接已经关闭，忽略错误
                    logger.debug(f"Connection already closed during unsubscribe from {channel}: {e}")
                except Exception as e:
                    # 其他错误也记录但不影响清理流程
                    logger.warning(f"Error during unsubscribe from {channel}: {e}")
        
        # 启动监听任务
        self.subscriptions[channel] = asyncio.create_task(listen())
        
    async def unsubscribe_task(self, task_id: str):
        """取消订阅任务消息"""
        channel = f"analysis:{task_id}"
        if channel in self.subscriptions:
            self.subscriptions[channel].cancel()
            del self.subscriptions[channel]
            logger.info(f"Unsubscribed from {channel}")


# 全局实例
redis_publisher = RedisPublisher()
redis_subscriber = RedisSubscriber()