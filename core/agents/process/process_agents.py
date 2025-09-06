"""
通用流程Agents
包括牛熊辩论、风险管理等流程型agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

from .agents import BaseAnalyst, ThoughtType
from .market_config import AnalysisDomain

logger = logging.getLogger(__name__)


class BullishResearcher(BaseAnalyst):
    """看涨研究员 - 专注于寻找上涨理由和机会"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "看涨研究员")
        
    def get_expertise_areas(self) -> List[str]:
        return ["bullish_analysis", "growth_opportunities", "positive_catalysts"]
        
    def _get_default_domain(self) -> str:
        return "看涨分析"
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行看涨分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行看涨分析，寻找上涨机会和正面因素",
            confidence=0.9
        )
        
        # 分析各种看涨因素
        price_data = data.get("price_data", {})
        fundamentals = data.get("fundamentals", {})
        news = data.get("news", [])
        
        # 技术面看涨信号
        if price_data.get("change_7d", 0) > 0:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"7天价格趋势为正（+{price_data.get('change_7d', 0)}%），显示短期动能良好",
                confidence=0.7,
                evidence=[{"type": "price_trend", "value": price_data.get('change_7d', 0)}]
            )
        
        # 基本面看涨因素
        if fundamentals.get("revenue_growth", 0) > 10:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"收入增长强劲（{fundamentals.get('revenue_growth', 0)}%），基本面支撑上涨",
                confidence=0.8,
                evidence=[{"type": "revenue_growth", "value": fundamentals.get('revenue_growth', 0)}]
            )
        
        # 构建看涨分析提示
        analysis_prompt = f"""
        作为看涨研究员，对{target}进行深入的上涨潜力分析（深度：{depth}/5）：
        
        数据概览：
        - 当前价格：${price_data.get('current_price', 0)}
        - 7天变化：{price_data.get('change_7d', 0)}%
        - 30天变化：{price_data.get('change_30d', 0)}%
        - 成交量趋势：{price_data.get('volume_trend', 'unknown')}
        
        请从以下角度分析上涨潜力：
        1. 技术面的看涨信号（突破、形态、指标）
        2. 基本面的增长动力（业绩、行业地位、护城河）
        3. 市场情绪和资金流向
        4. 潜在的正面催化剂（新产品、并购、政策利好）
        5. 风险收益比分析
        
        特别关注：
        - 被市场忽视的积极因素
        - 中长期增长逻辑
        - 相对估值优势
        
        以JSON格式返回，包含：
        - bullish_case: 看涨理由详述
        - key_catalysts: 关键催化剂列表
        - price_targets: 目标价位（短期、中期、长期）
        - conviction_level: 信心等级（1-10）
        - risk_factors: 需要关注的风险
        - recommendation: 具体建议
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在深入分析技术面、基本面和市场情绪，寻找看涨理由...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "看涨分析完成，已识别关键上涨驱动因素和目标价位",
            confidence=0.85
        )
        
        return {
            "analyst_type": "bullish",
            "analyst_role": "researcher",
            "analysis": response,
            "confidence_score": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class BearishResearcher(BaseAnalyst):
    """看跌研究员 - 专注于识别下跌风险和负面因素"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "看跌研究员")
        
    def get_expertise_areas(self) -> List[str]:
        return ["bearish_analysis", "risk_identification", "negative_catalysts"]
        
    def _get_default_domain(self) -> str:
        return "看跌分析"
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行看跌分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行看跌分析，识别下跌风险和负面因素",
            confidence=0.9
        )
        
        # 分析各种看跌因素
        price_data = data.get("price_data", {})
        fundamentals = data.get("fundamentals", {})
        
        # 技术面看跌信号
        if price_data.get("change_30d", 0) < -10:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"30天跌幅达{abs(price_data.get('change_30d', 0))}%，趋势明显走弱",
                confidence=0.8,
                evidence=[{"type": "price_decline", "value": price_data.get('change_30d', 0)}]
            )
        
        # 估值风险
        if fundamentals.get("pe_ratio", 0) > 30:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"市盈率高达{fundamentals.get('pe_ratio', 0)}，存在估值泡沫风险",
                confidence=0.7,
                evidence=[{"type": "valuation", "value": fundamentals.get('pe_ratio', 0)}]
            )
        
        # 构建看跌分析提示
        analysis_prompt = f"""
        作为看跌研究员，对{target}进行深入的下跌风险分析（深度：{depth}/5）：
        
        数据概览：
        - 当前价格：${price_data.get('current_price', 0)}
        - 30天变化：{price_data.get('change_30d', 0)}%
        - 市盈率：{fundamentals.get('pe_ratio', 'N/A')}
        - 负债率：{fundamentals.get('debt_ratio', 'N/A')}
        
        请从以下角度分析下跌风险：
        1. 技术面的看跌信号（破位、顶部形态、指标背离）
        2. 基本面的恶化迹象（业绩下滑、市场份额流失）
        3. 估值泡沫和均值回归风险
        4. 潜在的负面催化剂（监管、竞争、技术颠覆）
        5. 宏观和行业逆风
        
        特别关注：
        - 被市场忽视的风险因素
        - 财务造假或治理问题迹象
        - 流动性和融资风险
        
        以JSON格式返回，包含：
        - bearish_case: 看跌理由详述
        - key_risks: 主要风险列表
        - downside_targets: 下跌目标位（短期、中期、长期）
        - risk_level: 风险等级（1-10）
        - protective_measures: 风险对冲建议
        - recommendation: 具体建议
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在深入挖掘潜在风险，分析技术破位和基本面恶化信号...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "看跌分析完成，已识别主要下跌风险和目标位",
            confidence=0.85
        )
        
        return {
            "analyst_type": "bearish",
            "analyst_role": "researcher",
            "analysis": response,
            "confidence_score": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


