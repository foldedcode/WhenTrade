"""
统一的抽象基类定义
整合来自各个模块的基类
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass, field

from .types import Status, Result
from .exceptions import NotImplementedError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseService(ABC):
    """所有服务的基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化服务"""
        if self._initialized:
            return
            
        self.logger.info(f"Initializing {self.name}...")
        await self._initialize()
        self._initialized = True
        self.logger.info(f"{self.name} initialized successfully")
        
    async def shutdown(self) -> None:
        """关闭服务"""
        if not self._initialized:
            return
            
        self.logger.info(f"Shutting down {self.name}...")
        await self._shutdown()
        self._initialized = False
        self.logger.info(f"{self.name} shut down successfully")
        
    @abstractmethod
    async def _initialize(self) -> None:
        """子类实现的初始化逻辑"""
        pass
        
    @abstractmethod
    async def _shutdown(self) -> None:
        """子类实现的关闭逻辑"""
        pass


class BaseAdapter(ABC):
    """数据适配器基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"adapter.{self.name}")
        
    async def validate_request(self, request: Any) -> bool:
        """验证请求"""
        try:
            return await self._validate_request(request)
        except Exception as e:
            self.logger.error(f"Request validation failed: {e}")
            return False
            
    @abstractmethod
    async def _validate_request(self, request: Any) -> bool:
        """子类实现的验证逻辑"""
        pass
        
    @abstractmethod
    async def fetch(self, request: Any) -> Any:
        """获取数据"""
        pass
        
    async def batch_fetch(self, requests: List[Any]) -> List[Any]:
        """批量获取数据"""
        results = []
        for request in requests:
            try:
                result = await self.fetch(request)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Batch fetch error for {request}: {e}")
                results.append(None)
        return results


class BaseAnalyst(ABC):
    """分析师基类"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"analyst.{agent_id}")
        self.thoughts: List[Dict[str, Any]] = []
        
    def add_thought(self, thought_type: str, content: str, confidence: float = 0.5):
        """添加思考记录"""
        thought = {
            "type": thought_type,
            "content": content,
            "confidence": confidence,
            "timestamp": datetime.utcnow()
        }
        self.thoughts.append(thought)
        self.logger.debug(f"Thought added: {thought}")
        
    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> Result:
        """执行分析"""
        pass
        
    def calculate_confidence(self, factors: Dict[str, float]) -> float:
        """计算置信度"""
        if not factors:
            return 0.5
            
        # 加权平均
        total_weight = sum(factors.values())
        if total_weight == 0:
            return 0.5
            
        confidence = sum(k * v for k, v in factors.items()) / total_weight
        return max(0.0, min(1.0, confidence))


class BaseToolInterface(ABC):
    """通用工具接口基类
    
    注意：对于 legacy 工具，请使用 core.tools.legacy.base.BaseTool
    """
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"tool.{self.name}")
        self.enabled = True
        
    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass
        
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """获取参数定义"""
        pass
        
    @abstractmethod
    async def execute(self, **kwargs) -> Result:
        """执行工具"""
        pass
        
    async def validate_parameters(self, **kwargs) -> bool:
        """验证参数"""
        required_params = self.get_parameters()
        for param, config in required_params.items():
            if config.get("required", False) and param not in kwargs:
                self.logger.error(f"Missing required parameter: {param}")
                return False
        return True


class BaseProvider(ABC):
    """数据提供者基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"provider.{self.name}")
        self._connected = False
        
    async def connect(self) -> None:
        """连接到数据源"""
        if self._connected:
            return
            
        self.logger.info(f"Connecting to {self.name}...")
        await self._connect()
        self._connected = True
        self.logger.info(f"Connected to {self.name}")
        
    async def disconnect(self) -> None:
        """断开连接"""
        if not self._connected:
            return
            
        self.logger.info(f"Disconnecting from {self.name}...")
        await self._disconnect()
        self._connected = False
        self.logger.info(f"Disconnected from {self.name}")
        
    @abstractmethod
    async def _connect(self) -> None:
        """子类实现的连接逻辑"""
        pass
        
    @abstractmethod
    async def _disconnect(self) -> None:
        """子类实现的断开逻辑"""
        pass
        
    @abstractmethod
    async def fetch_data(self, request: Any) -> Any:
        """获取数据"""
        pass