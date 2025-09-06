"""
预测市场特定Agents
包括事件分析、贝叶斯推理、赔率分析等专业agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

from ..base import BaseAnalyst, ThoughtType
from core.business.market_config import AnalysisDomain

logger = logging.getLogger(__name__)


class EventAnalyst(BaseAnalyst):
    """事件分析师 - 分析预测市场事件的真实概率"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "事件分析师")
        
    def get_expertise_areas(self) -> List[str]:
        return ["event_analysis", "outcome_probability", "news_correlation", "historical_patterns"]
        
    def _get_default_domain(self) -> str:
        return AnalysisDomain.EVENT.value
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行事件概率分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行事件分析，评估各种结果的真实概率",
            confidence=0.9
        )
        
        # 获取事件数据
        event_data = data.get("event_data", {})
        market_data = data.get("polymarket_data", {})
        
        # 分析市场价格vs真实概率
        if market_data.get("yes_price", 0) > 0:
            yes_price = market_data.get("yes_price", 0)
            self.record_thought(
                ThoughtType.OBSERVATION,
                f"当前YES价格为${yes_price}，隐含概率{yes_price*100}%",
                confidence=0.9,
                evidence=[{"type": "market_price", "value": yes_price}]
            )
            
            # 检查是否存在定价偏差
            if yes_price > 0.8 or yes_price < 0.2:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"价格接近极端值，可能存在市场偏见或信息不对称",
                    confidence=0.7
                )
        
        # 分析交易量和流动性
        volume_24h = market_data.get("volume_24h", 0)
        if volume_24h > 100000:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"24小时交易量达${volume_24h:,.0f}，市场活跃度高，价格发现机制有效",
                confidence=0.8,
                evidence=[{"type": "volume", "value": volume_24h}]
            )
        elif volume_24h < 10000:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"交易量较低（${volume_24h:,.0f}），价格可能不够有效",
                confidence=0.6
            )
        
        # 分析相关新闻和事件
        related_news = event_data.get("related_news", [])
        if related_news:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"发现{len(related_news)}条相关新闻，需要评估对事件结果的影响",
                confidence=0.7
            )
        
        # 构建分析提示
        analysis_prompt = f"""
        作为事件分析师，对预测市场{target}进行深度分析（深度：{depth}/5）：
        
        事件描述：
        {event_data.get('description', '无描述')}
        
        市场数据：
        - YES价格：${market_data.get('yes_price', 0)}
        - NO价格：${market_data.get('no_price', 0)}
        - 24小时交易量：${market_data.get('volume_24h', 0):,.0f}
        - 总流动性：${market_data.get('liquidity', 0):,.0f}
        - 持仓人数：{market_data.get('holders', 0)}
        
        事件时间线：
        - 创建时间：{event_data.get('created_date', 'N/A')}
        - 解决截止日期：{event_data.get('resolution_date', 'N/A')}
        - 当前状态：{event_data.get('status', 'active')}
        
        相关新闻（最近5条）：
        {json.dumps(related_news[:5], ensure_ascii=False, indent=2) if related_news else "无"}
        
        历史类似事件：
        {json.dumps(event_data.get('similar_events', [])[:3], ensure_ascii=False, indent=2)}
        
        请分析：
        1. 事件结果的真实概率评估
        2. 市场定价vs真实概率的偏差
        3. 影响事件结果的关键因素
        4. 信息来源的可靠性评估
        5. 时间因素对概率的影响
        6. 潜在的黑天鹅风险
        
        注意事项：
        - 识别市场情绪偏见
        - 考虑信息不对称
        - 评估操纵风险
        - 分析解决标准的清晰度
        
        以JSON格式返回，包含：
        - true_probability: 真实概率评估（0-1）
        - market_efficiency: 市场效率评分（1-10）
        - key_factors: 影响因素列表
        - bias_analysis: 偏见分析
        - information_quality: 信息质量评分
        - resolution_risks: 解决风险
        - trading_opportunity: 交易机会评估
        - confidence_interval: 概率置信区间
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在综合分析历史模式、新闻事件和市场行为...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 提出关键问题
        self.record_thought(
            ThoughtType.QUESTION,
            "是否存在未被市场充分认识的信息？解决标准是否可能产生争议？",
            confidence=0.7
        )
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "事件分析完成，已评估真实概率和市场定价偏差",
            confidence=0.85
        )
        
        return {
            "analyst_type": "event",
            "analyst_role": "specialist",
            "analysis": response,
            "confidence_score": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class BayesianAnalyst(BaseAnalyst):
    """贝叶斯分析师 - 使用贝叶斯推理更新概率估计"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "贝叶斯分析师")
        
    def get_expertise_areas(self) -> List[str]:
        return ["bayesian_inference", "probability_update", "evidence_weight", "statistical_modeling"]
        
    def _get_default_domain(self) -> str:
        return AnalysisDomain.PROBABILITY.value
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行贝叶斯概率分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行贝叶斯分析，基于新证据更新概率估计",
            confidence=0.9
        )
        
        # 获取先验概率（市场价格）
        market_data = data.get("polymarket_data", {})
        prior_prob = market_data.get("yes_price", 0.5)
        
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"先验概率（基于市场价格）：{prior_prob:.2%}",
            confidence=0.9
        )
        
        # 分析新证据
        new_evidence = data.get("new_evidence", [])
        if new_evidence:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"发现{len(new_evidence)}项新证据，需要评估其似然比和证据强度",
                confidence=0.8
            )
            
            # 评估证据强度
            strong_evidence = [e for e in new_evidence if e.get("strength", 0) > 0.7]
            if strong_evidence:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"识别到{len(strong_evidence)}项强证据，将显著影响概率更新",
                    confidence=0.85,
                    evidence=strong_evidence[:3]
                )
        
        # 检查历史预测准确率
        historical_accuracy = data.get("historical_accuracy", {})
        if historical_accuracy:
            accuracy_rate = historical_accuracy.get("accuracy_rate", 0)
            if accuracy_rate > 0:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"历史预测准确率为{accuracy_rate:.1%}，用于校准概率估计",
                    confidence=0.7
                )
        
        # 构建分析提示
        analysis_prompt = f"""
        作为贝叶斯分析师，对{target}进行概率推理分析（深度：{depth}/5）：
        
        先验信息：
        - 市场隐含概率：{prior_prob:.2%}
        - 交易量权重：{market_data.get('volume_24h', 0)/1000000:.2f}M
        - 市场参与者：{market_data.get('holders', 0)}
        
        新证据列表：
        {json.dumps(new_evidence, ensure_ascii=False, indent=2) if new_evidence else "无新证据"}
        
        历史数据：
        - 类似事件基础概率：{historical_accuracy.get('base_rate', 'N/A')}
        - 预测准确率：{historical_accuracy.get('accuracy_rate', 'N/A')}
        - 样本数量：{historical_accuracy.get('sample_size', 'N/A')}
        
        条件概率：
        {json.dumps(data.get('conditional_probabilities', {}), ensure_ascii=False, indent=2)}
        
        请进行：
        1. 证据似然比计算（P(E|H) / P(E|¬H)）
        2. 贝叶斯更新计算
        3. 证据独立性检验
        4. 敏感性分析
        5. 置信区间估计
        6. 模型不确定性量化
        
        贝叶斯推理要点：
        - 评估每项证据的诊断价值
        - 考虑证据之间的相关性
        - 避免重复计算相关证据
        - 使用合适的先验分布
        - 考虑模型误设风险
        
        以JSON格式返回，包含：
        - prior_probability: 先验概率
        - likelihood_ratios: 各证据的似然比
        - posterior_probability: 后验概率
        - confidence_interval: 95%置信区间
        - evidence_strength: 证据强度评估
        - key_updates: 关键概率更新
        - model_uncertainty: 模型不确定性
        - sensitivity_analysis: 敏感性分析结果
        - recommendation: 基于贝叶斯分析的建议
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在计算似然比、更新后验概率并评估模型不确定性...",
            confidence=0.85
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "贝叶斯分析完成，已基于新证据更新概率估计",
            confidence=0.9
        )
        
        return {
            "analyst_type": "bayesian",
            "analyst_role": "specialist",
            "analysis": response,
            "confidence_score": 0.9,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class OddsAnalyst(BaseAnalyst):
    """赔率分析师 - 分析预测市场的赔率和套利机会"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "赔率分析师")
        
    def get_expertise_areas(self) -> List[str]:
        return ["odds_analysis", "arbitrage_detection", "market_making", "risk_pricing"]
        
    def _get_default_domain(self) -> str:
        return AnalysisDomain.ODDS.value
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行赔率和套利分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行赔率分析，寻找定价效率和套利机会",
            confidence=0.9
        )
        
        # 获取市场数据
        market_data = data.get("polymarket_data", {})
        yes_price = market_data.get("yes_price", 0)
        no_price = market_data.get("no_price", 0)
        
        # 检查价格一致性
        price_sum = yes_price + no_price
        if abs(price_sum - 1.0) > 0.02:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"YES+NO价格和为{price_sum:.3f}，偏离1.0达{abs(price_sum-1.0)*100:.1f}%，" +
                ("存在套利机会" if price_sum < 0.98 else "存在做市商利润"),
                confidence=0.9,
                evidence=[{"type": "price_sum", "value": price_sum}]
            )
        
        # 分析买卖价差
        spread_data = market_data.get("spread", {})
        if spread_data:
            yes_spread = spread_data.get("yes_spread", 0)
            if yes_spread > 0.02:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"YES买卖价差达{yes_spread*100:.1f}%，流动性较差或波动性高",
                    confidence=0.8
                )
        
        # 分析历史赔率变化
        odds_history = data.get("odds_history", [])
        if odds_history:
            # 计算赔率波动性
            recent_odds = [h.get("yes_price", 0) for h in odds_history[-20:]]
            if recent_odds:
                max_odds = max(recent_odds)
                min_odds = min(recent_odds)
                volatility = max_odds - min_odds
                
                if volatility > 0.2:
                    self.record_thought(
                        ThoughtType.ANALYSIS,
                        f"近期赔率波动范围达{volatility*100:.0f}%，市场存在分歧或新信息冲击",
                        confidence=0.75,
                        evidence=[{"type": "volatility", "value": volatility}]
                    )
        
        # 与其他市场比较
        other_markets = data.get("related_markets", [])
        if other_markets:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"发现{len(other_markets)}个相关市场，需要检查跨市场套利机会",
                confidence=0.8
            )
        
        # 构建分析提示
        analysis_prompt = f"""
        作为赔率分析师，对{target}进行深度赔率分析（深度：{depth}/5）：
        
        当前赔率：
        - YES价格：${yes_price} (隐含概率：{yes_price*100:.1f}%)
        - NO价格：${no_price} (隐含概率：{no_price*100:.1f}%)
        - 价格和：{price_sum:.3f}
        - 偏离度：{abs(price_sum-1.0)*100:.1f}%
        
        市场深度：
        - YES买卖价差：{spread_data.get('yes_spread', 0)*100:.1f}%
        - NO买卖价差：{spread_data.get('no_spread', 0)*100:.1f}%
        - 订单簿深度：${market_data.get('order_book_depth', 0):,.0f}
        
        历史赔率（最近20个数据点）：
        {json.dumps(odds_history[-20:], ensure_ascii=False, indent=2) if odds_history else "无"}
        
        相关市场：
        {json.dumps(other_markets, ensure_ascii=False, indent=2) if other_markets else "无"}
        
        大额交易：
        {json.dumps(data.get('large_trades', [])[:10], ensure_ascii=False, indent=2)}
        
        请分析：
        1. 赔率定价效率评估
        2. 套利机会识别（单市场/跨市场）
        3. 流动性和市场深度分析
        4. 大户行为和市场操纵迹象
        5. 最优交易策略（做市/套利/方向性）
        6. 风险收益比计算
        
        特别关注：
        - 价格发现机制效率
        - 滑点和交易成本
        - 尾部风险评估
        - 市场微观结构
        
        以JSON格式返回，包含：
        - pricing_efficiency: 定价效率评分（1-10）
        - arbitrage_opportunities: 套利机会列表
        - optimal_strategy: 最优交易策略
        - expected_return: 预期收益率
        - risk_metrics: 风险指标
        - market_depth_analysis: 市场深度分析
        - manipulation_risk: 操纵风险等级
        - trading_recommendations: 具体交易建议
        - kelly_criterion: 凯利公式建议仓位
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在分析价格效率、套利空间和最优交易策略...",
            confidence=0.85
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 提出风险警示
        self.record_thought(
            ThoughtType.QUESTION,
            "是否考虑了解决风险和平台风险？流动性是否足够执行策略？",
            confidence=0.7
        )
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "赔率分析完成，已识别定价效率和潜在交易机会",
            confidence=0.88
        )
        
        return {
            "analyst_type": "odds",
            "analyst_role": "specialist",
            "analysis": response,
            "confidence_score": 0.88,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }