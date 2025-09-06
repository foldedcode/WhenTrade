"""
加密货币市场特定Agents
包括链上分析、DeFi分析、巨鲸追踪等专业agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

from ..base import BaseAnalyst, ThoughtType
from core.business.market_config import AnalysisDomain

logger = logging.getLogger(__name__)


class OnChainAnalyst(BaseAnalyst):
    """链上数据分析师 - 分析区块链上的交易和地址行为"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "链上分析师")
        
    def get_expertise_areas(self) -> List[str]:
        return ["onchain_metrics", "whale_tracking", "network_activity", "tvl_analysis"]
        
    def _get_default_domain(self) -> str:
        return AnalysisDomain.ONCHAIN.value
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行链上数据分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行链上数据分析，关注交易活动、大户动向和网络健康度",
            confidence=0.9
        )
        
        # 获取链上数据
        onchain_data = data.get("onchain_data", {})
        
        # 分析交易量
        if onchain_data.get("transaction_count_24h", 0) > 100000:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"24小时交易数量达{onchain_data.get('transaction_count_24h', 0)}笔，网络活跃度高",
                confidence=0.8,
                evidence=[{"type": "transaction_count", "value": onchain_data.get('transaction_count_24h', 0)}]
            )
        
        # 分析大户动向
        whale_movements = onchain_data.get("whale_movements", [])
        if whale_movements:
            large_inflows = sum(1 for m in whale_movements if m.get("type") == "exchange_inflow" and m.get("amount_usd", 0) > 1000000)
            large_outflows = sum(1 for m in whale_movements if m.get("type") == "exchange_outflow" and m.get("amount_usd", 0) > 1000000)
            
            if large_outflows > large_inflows:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"巨鲸从交易所提币趋势明显（{large_outflows}笔流出 vs {large_inflows}笔流入），看涨信号",
                    confidence=0.85,
                    evidence=[{"outflows": large_outflows, "inflows": large_inflows}]
                )
            elif large_inflows > large_outflows:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"巨鲸向交易所充值增加（{large_inflows}笔流入 vs {large_outflows}笔流出），需警惕抛压",
                    confidence=0.85,
                    evidence=[{"outflows": large_outflows, "inflows": large_inflows}]
                )
        
        # 分析网络价值
        nvt_ratio = onchain_data.get("nvt_ratio", 0)
        if nvt_ratio > 0:
            if nvt_ratio > 100:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"NVT比率高达{nvt_ratio}，可能存在估值泡沫",
                    confidence=0.7
                )
            elif nvt_ratio < 50:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"NVT比率为{nvt_ratio}，网络价值被低估",
                    confidence=0.7
                )
        
        # 构建分析提示
        analysis_prompt = f"""
        作为链上数据分析师，对{target}进行深度链上分析（深度：{depth}/5）：
        
        链上数据概览：
        - 24小时交易数：{onchain_data.get('transaction_count_24h', 'N/A')}
        - 活跃地址数：{onchain_data.get('active_addresses_24h', 'N/A')}
        - 平均Gas费：{onchain_data.get('avg_gas_price', 'N/A')}
        - NVT比率：{onchain_data.get('nvt_ratio', 'N/A')}
        - 交易所净流量：{onchain_data.get('exchange_netflow_24h', 'N/A')}
        
        巨鲸动向（最近10笔）：
        {json.dumps(whale_movements[:10], ensure_ascii=False, indent=2) if whale_movements else "无数据"}
        
        请分析：
        1. 网络活跃度和使用趋势
        2. 大户地址行为模式（积累/分发）
        3. 交易所流入流出情况
        4. 长期持有者vs短期交易者比例
        5. 链上指标的买卖信号
        6. 网络安全性和去中心化程度
        
        特别关注：
        - 异常的大额转账
        - 交易所储备变化
        - 智能合约交互趋势
        - Layer2活动（如适用）
        
        以JSON格式返回，包含：
        - network_health: 网络健康度评估
        - whale_sentiment: 巨鲸情绪（积累/分发/中性）
        - onchain_signals: 链上信号列表
        - risk_indicators: 风险指标
        - bullish_factors: 看涨因素
        - bearish_factors: 看跌因素
        - recommendation: 基于链上数据的建议
        - confidence_score: 分析置信度
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在深入分析链上交易模式、地址行为和网络指标...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "链上分析完成，已识别关键的链上信号和巨鲸动向",
            confidence=0.85
        )
        
        return {
            "analyst_type": "onchain",
            "analyst_role": "specialist",
            "analysis": response,
            "confidence_score": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class DefiAnalyst(BaseAnalyst):
    """DeFi分析师 - 分析去中心化金融协议和收益机会"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "DeFi分析师")
        
    def get_expertise_areas(self) -> List[str]:
        return ["liquidity_analysis", "yield_optimization", "protocol_health", "impermanent_loss"]
        
    def _get_default_domain(self) -> str:
        return AnalysisDomain.DEFI.value
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行DeFi协议分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行DeFi生态分析，评估协议健康度和收益机会",
            confidence=0.9
        )
        
        # 获取DeFi数据
        defi_data = data.get("defi_data", {})
        
        # 分析TVL（总锁仓价值）
        tvl = defi_data.get("tvl", 0)
        tvl_change_7d = defi_data.get("tvl_change_7d", 0)
        
        if tvl > 0:
            self.record_thought(
                ThoughtType.OBSERVATION,
                f"当前TVL为${tvl:,.0f}，7天变化{tvl_change_7d:+.1f}%",
                confidence=0.9
            )
            
            if tvl_change_7d > 10:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    "TVL快速增长，显示用户信心增强和资金流入",
                    confidence=0.8,
                    evidence=[{"tvl_growth": tvl_change_7d}]
                )
            elif tvl_change_7d < -10:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    "TVL明显下降，可能存在资金外流或信心不足",
                    confidence=0.8,
                    evidence=[{"tvl_decline": tvl_change_7d}]
                )
        
        # 分析收益率
        yields = defi_data.get("yields", {})
        if yields:
            highest_apy = max(yields.values()) if yields else 0
            if highest_apy > 20:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"发现高收益机会，最高APY达{highest_apy}%，但需评估风险",
                    confidence=0.7
                )
        
        # 构建分析提示
        analysis_prompt = f"""
        作为DeFi分析师，对{target}的DeFi生态进行深度分析（深度：{depth}/5）：
        
        DeFi数据概览：
        - 总锁仓价值(TVL)：${defi_data.get('tvl', 0):,.0f}
        - TVL 7天变化：{defi_data.get('tvl_change_7d', 0):+.1f}%
        - 协议数量：{defi_data.get('protocol_count', 'N/A')}
        - 平均收益率：{defi_data.get('avg_yield', 'N/A')}%
        
        主要协议数据：
        {json.dumps(defi_data.get('top_protocols', []), ensure_ascii=False, indent=2)}
        
        收益率数据：
        {json.dumps(yields, ensure_ascii=False, indent=2)}
        
        请分析：
        1. DeFi协议健康度和安全性
        2. 流动性分布和深度
        3. 收益率可持续性分析
        4. 无常损失风险评估
        5. 协议创新和竞争优势
        6. 跨链桥接和互操作性
        
        风险考量：
        - 智能合约风险
        - 流动性风险
        - 治理风险
        - 预言机依赖性
        - 监管风险
        
        以JSON格式返回，包含：
        - protocol_health: 协议健康度评分（1-10）
        - yield_opportunities: 收益机会列表
        - risk_assessment: 风险评估详情
        - liquidity_analysis: 流动性分析
        - innovation_score: 创新评分（1-10）
        - recommendations: 具体建议
        - best_strategies: 最佳策略推荐
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在评估协议安全性、收益可持续性和流动性状况...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 提出关键问题
        self.record_thought(
            ThoughtType.QUESTION,
            "当前的高收益是否可持续？协议是否经过审计？",
            confidence=0.6
        )
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "DeFi分析完成，已评估协议健康度和最佳收益策略",
            confidence=0.85
        )
        
        return {
            "analyst_type": "defi",
            "analyst_role": "specialist",
            "analysis": response,
            "confidence_score": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class WhaleTracker(BaseAnalyst):
    """巨鲸追踪专家 - 追踪和分析大户地址的行为模式"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "巨鲸追踪专家")
        
    def get_expertise_areas(self) -> List[str]:
        return ["whale_behavior", "accumulation_patterns", "market_manipulation", "smart_money"]
        
    def _get_default_domain(self) -> str:
        return AnalysisDomain.ONCHAIN.value
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行巨鲸行为分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始追踪{target}的巨鲸动向，识别聪明钱的行为模式",
            confidence=0.9
        )
        
        # 获取巨鲸数据
        whale_data = data.get("whale_data", {})
        whale_addresses = whale_data.get("top_holders", [])
        recent_transactions = whale_data.get("recent_large_txs", [])
        
        # 分析持仓集中度
        if whale_addresses:
            top_10_percentage = sum(addr.get("balance_percentage", 0) for addr in whale_addresses[:10])
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"前10大地址持有{top_10_percentage:.1f}%的流通量，" + 
                ("集中度较高" if top_10_percentage > 30 else "分布相对分散"),
                confidence=0.9,
                evidence=[{"concentration": top_10_percentage}]
            )
        
        # 分析近期大额交易
        if recent_transactions:
            accumulating = sum(1 for tx in recent_transactions if tx.get("type") == "buy" and tx.get("amount_usd", 0) > 100000)
            distributing = sum(1 for tx in recent_transactions if tx.get("type") == "sell" and tx.get("amount_usd", 0) > 100000)
            
            if accumulating > distributing * 1.5:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"巨鲸积累明显，大额买入{accumulating}笔 vs 卖出{distributing}笔",
                    confidence=0.85,
                    evidence=[{"buys": accumulating, "sells": distributing}]
                )
            elif distributing > accumulating * 1.5:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"巨鲸分发迹象，大额卖出{distributing}笔 vs 买入{accumulating}笔",
                    confidence=0.85,
                    evidence=[{"buys": accumulating, "sells": distributing}]
                )
        
        # 识别聪明钱地址
        smart_money = whale_data.get("smart_money_addresses", [])
        if smart_money:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"识别到{len(smart_money)}个聪明钱地址，需要密切关注其动向",
                confidence=0.8
            )
        
        # 构建分析提示
        analysis_prompt = f"""
        作为巨鲸追踪专家，对{target}的大户行为进行深度分析（深度：{depth}/5）：
        
        巨鲸数据概览：
        - 前100大地址数量：{whale_data.get('whale_count', 'N/A')}
        - 总持仓占比：{whale_data.get('total_whale_percentage', 'N/A')}%
        - 30天净变化：{whale_data.get('net_change_30d', 'N/A')}
        - 新增巨鲸地址：{whale_data.get('new_whales_7d', 'N/A')}
        
        前10大持有者：
        {json.dumps(whale_addresses[:10], ensure_ascii=False, indent=2) if whale_addresses else "无数据"}
        
        近期大额交易（>$100k）：
        {json.dumps(recent_transactions[:20], ensure_ascii=False, indent=2) if recent_transactions else "无数据"}
        
        聪明钱地址：
        {json.dumps(smart_money[:5], ensure_ascii=False, indent=2) if smart_money else "无数据"}
        
        请分析：
        1. 巨鲸积累/分发模式
        2. 持仓集中度变化趋势
        3. 聪明钱vs散户行为对比
        4. 可能的市场操纵迹象
        5. 巨鲸地址间的关联性
        6. OTC交易和黑池活动推测
        
        行为模式识别：
        - 吸筹模式（缓慢积累）
        - 洗盘模式（震荡吸筹）
        - 派发模式（高位出货）
        - 锁仓模式（长期持有）
        
        以JSON格式返回，包含：
        - whale_sentiment: 巨鲸情绪（积累/中性/分发）
        - accumulation_score: 积累评分（-10到+10）
        - manipulation_risk: 操纵风险等级（低/中/高）
        - smart_money_signal: 聪明钱信号
        - key_addresses: 需要关注的关键地址
        - behavior_pattern: 识别的行为模式
        - trading_recommendation: 基于巨鲸行为的交易建议
        - confidence_level: 分析置信度
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在分析地址间关联、交易模式和潜在的市场操纵行为...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 提出警示
        self.record_thought(
            ThoughtType.QUESTION,
            "是否存在协同操作？大额转账是否与价格异动相关？",
            confidence=0.7
        )
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            "巨鲸追踪分析完成，已识别主要行为模式和潜在风险",
            confidence=0.9
        )
        
        return {
            "analyst_type": "whale_tracker",
            "analyst_role": "specialist",
            "analysis": response,
            "confidence_score": 0.9,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }