"""
成就系统端口接口定义
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AchievementCategory(str, Enum):
    """成就类别枚举"""
    COST_SAVING = "cost_saving"  # 成本节省
    EFFICIENCY = "efficiency"  # 效率提升
    CONSISTENCY = "consistency"  # 持续性
    EXPLORATION = "exploration"  # 探索尝试
    MILESTONE = "milestone"  # 里程碑


class AchievementRarity(str, Enum):
    """成就稀有度枚举"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Achievement:
    """成就定义"""
    id: str
    name: str
    description: str
    category: AchievementCategory
    rarity: AchievementRarity
    icon: str
    points: int
    criteria: Dict[str, Any]  # 达成条件
    is_hidden: bool = False  # 隐藏成就
    created_at: Optional[datetime] = None


@dataclass
class UserAchievement:
    """用户成就记录"""
    user_id: str
    achievement: Achievement
    progress: float  # 0-100的进度百分比
    unlocked_at: Optional[datetime] = None
    is_notified: bool = False
    metadata: Optional[Dict[str, Any]] = None  # 额外数据，如具体节省金额等


@dataclass
class AchievementProgress:
    """成就进度详情"""
    achievement: Achievement
    current_value: float
    target_value: float
    progress_percentage: float
    estimated_completion: Optional[datetime] = None
    recent_contributions: List[Dict[str, Any]]  # 最近的贡献记录


@dataclass
class Leaderboard:
    """排行榜"""
    timeframe: str  # daily, weekly, monthly, all_time
    entries: List['LeaderboardEntry']
    user_rank: Optional[int] = None  # 当前用户的排名
    total_participants: int = 0


@dataclass
class LeaderboardEntry:
    """排行榜条目"""
    rank: int
    user_id: str
    username: str
    score: float  # 可以是效率分数、节省金额等
    achievement_count: int
    total_points: int
    streak_days: Optional[int] = None


class AchievementSystemPort(ABC):
    """成就系统端口接口"""
    
    @abstractmethod
    async def get_all_achievements(
        self,
        category: Optional[AchievementCategory] = None,
        include_hidden: bool = False
    ) -> List[Achievement]:
        """获取所有成就定义"""
        pass
    
    @abstractmethod
    async def get_user_achievements(
        self,
        user_id: str,
        unlocked_only: bool = False
    ) -> List[UserAchievement]:
        """获取用户的成就记录"""
        pass
    
    @abstractmethod
    async def check_achievement_progress(
        self,
        user_id: str,
        achievement_id: str
    ) -> AchievementProgress:
        """检查特定成就的进度"""
        pass
    
    @abstractmethod
    async def unlock_achievement(
        self,
        user_id: str,
        achievement_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserAchievement:
        """解锁成就"""
        pass
    
    @abstractmethod
    async def update_achievement_progress(
        self,
        user_id: str,
        achievement_id: str,
        progress: float,
        contribution: Optional[Dict[str, Any]] = None
    ) -> UserAchievement:
        """更新成就进度"""
        pass
    
    @abstractmethod
    async def check_and_unlock_achievements(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> List[UserAchievement]:
        """检查并解锁符合条件的成就
        
        Args:
            user_id: 用户ID
            context: 上下文信息，如最新的使用数据、节省金额等
            
        Returns:
            新解锁的成就列表
        """
        pass
    
    @abstractmethod
    async def get_achievement_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """获取用户成就统计
        
        Returns:
            包含总成就数、解锁数、总积分、各类别进度等
        """
        pass
    
    @abstractmethod
    async def get_leaderboard(
        self,
        metric: str,  # efficiency_score, total_saved, achievement_points等
        timeframe: str,  # daily, weekly, monthly, all_time
        limit: int = 100
    ) -> Leaderboard:
        """获取排行榜"""
        pass
    
    @abstractmethod
    async def get_user_rank(
        self,
        user_id: str,
        metric: str,
        timeframe: str
    ) -> Optional[LeaderboardEntry]:
        """获取用户在排行榜中的位置"""
        pass
    
    @abstractmethod
    async def create_achievement(
        self,
        achievement: Achievement
    ) -> Achievement:
        """创建新的成就定义（管理功能）"""
        pass
    
    @abstractmethod
    async def get_achievement_recommendations(
        self,
        user_id: str
    ) -> List[AchievementProgress]:
        """获取推荐的成就
        
        基于用户当前进度，推荐接近完成的成就
        """
        pass