"""
智能分析代理实现
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import json
import asyncio
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ThoughtType(str, Enum):
    """Thought type enumeration"""
    OBSERVATION = "observation"
    ANALYSIS = "analysis"
    CONCLUSION = "conclusion"
    QUESTION = "question"


class AgentThought:
    """Agent thought record"""
    
    def __init__(
        self,
        agent_id: str,
        domain: str,
        thought_type: ThoughtType,
        content: str,
        confidence: float = 0.5,
        evidence: List[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.domain = domain
        self.timestamp = datetime.utcnow().timestamp()
        self.thought_type = thought_type
        self.content = content
        self.confidence = confidence
        self.evidence = evidence or []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "agentId": self.agent_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "thoughtType": self.thought_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "evidence": self.evidence
        }


class BaseAnalyst(ABC):
    """Base analyst class"""
    
    def __init__(self, llm: Any, name: str = None, domain: str = None):
        self.llm = llm
        self.name = name or self.__class__.__name__
        self.domain = domain or self._get_default_domain()
        self.analysis_cache = {}
        self.confidence_factors = {}
        self.thought_stream: List[AgentThought] = []
        self.stop_event = None  # Add stop event support
        
        # Inject tool adapter
        try:
            from core.agents.tools import analyst_tools
            self.tools = analyst_tools
        except ImportError as e:
            import logging
            logging.warning(f"⚠️ Failed to import tool adapter: {e}")
            self.tools = None
        
    @abstractmethod
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """Execute analysis"""
        pass
        
    @abstractmethod
    def get_expertise_areas(self) -> List[str]:
        """Get expertise areas"""
        pass
        
    @abstractmethod
    def _get_default_domain(self) -> str:
        """Get default analysis domain"""
        pass
        
    def record_thought(
        self,
        thought_type: ThoughtType,
        content: str,
        confidence: float = 0.5,
        evidence: List[Dict[str, Any]] = None
    ) -> AgentThought:
        """Record thinking process"""
        thought = AgentThought(
            agent_id=self.name,
            domain=self.domain,
            thought_type=thought_type,
            content=content,
            confidence=confidence,
            evidence=evidence
        )
        self.thought_stream.append(thought)
        logger.debug(f"{self.name} {thought_type.value}: {content}")
        return thought
        
    def get_thought_stream(self) -> List[Dict[str, Any]]:
        """Get thought stream"""
        return [thought.to_dict() for thought in self.thought_stream]
        
    def clear_thoughts(self):
        """Clear thought records"""
        self.thought_stream = []
        
    def check_stop_signal(self) -> bool:
        """Check stop signal
        
        Returns:
            bool: Returns True if stop signal received
        """
        if self.stop_event and self.stop_event.is_set():
            logger.info(f"Agent {self.name} received stop signal, interrupting execution")
            return True
        return False
        
    def set_stop_event(self, stop_event):
        """Set stop event - propagate to APIExecutor"""
        self.stop_event = stop_event
        
        # Propagate to tool set's APIExecutor
        if hasattr(self, 'toolkit') and self.toolkit:
            # Get global APIExecutor instance
            from core.services.tools.api_executor import get_api_executor
            api_executor = get_api_executor()
            api_executor.set_stop_event(stop_event)
            logger.debug(f"🛑 [{self.name}] Stop event propagated to APIExecutor")
        
    async def debate(self, topic: str, other_opinions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Debate with other analysts"""
        prompt = f"""
        As {self.name}, I need to express my opinion on the following topic and respond to other analysts:
        
        Topic: {topic}
        
        Other analysts' opinions:
        {json.dumps(other_opinions, ensure_ascii=False, indent=2)}
        
        Based on my professional domain and analytical methods, please provide:
        1. My core viewpoint
        2. Evaluation of other viewpoints
        3. Evidence supporting my viewpoint
        4. Potential risks or uncertainties
        
        Return in JSON format.
        """
        
        response = await self.llm.generate(prompt)
        return {
            "analyst": self.name,
            "debate_response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def calculate_confidence(self, factors: Dict[str, float]) -> float:
        """Calculate confidence score"""
        # Calculate weighted confidence based on multiple factors
        weights = {
            "data_quality": 0.3,
            "data_recency": 0.2,
            "analysis_depth": 0.2,
            "market_conditions": 0.3
        }
        
        confidence = 0.0
        for factor, value in factors.items():
            weight = weights.get(factor, 0.1)
            confidence += weight * value
            
        return min(max(confidence, 0.0), 1.0)


class BaseCryptoAnalyst(BaseAnalyst):
    """Base crypto analyst class - eliminate code duplication, configuration-driven"""
    
    def __init__(self, llm: Any, config: Dict[str, Any]):
        """
        Initialize crypto analyst
        
        Args:
            llm: Language model instance
            config: Analyst configuration (loaded from YAML)
        """
        super().__init__(
            llm, 
            config.get("name", self.__class__.__name__),
            config.get("domain", "Cryptocurrency Analysis")
        )
        self.config = config
        
        # Load professional settings from configuration
        self.expertise_areas = config.get("expertise_areas", [])
        self.analysis_depth = config.get("analysis_depth", 3)
        self.tool_config = config.get("tools", {})
        
        logger.debug(f"Initializing crypto analyst: {self.name}")
    
    def get_expertise_areas(self) -> List[str]:
        """Get expertise areas"""
        return self.expertise_areas
    
    def _get_default_domain(self) -> str:
        """Get default analysis domain"""
        return "Cryptocurrency Analysis"
    
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = None) -> Dict[str, Any]:
        """
        Execute cryptocurrency analysis - unified process, configuration-driven
        
        Args:
            target: Analysis target (cryptocurrency symbol)
            data: Input data
            depth: Analysis depth
        
        Returns:
            Analysis result
        """
        # Check stop signal
        if self.check_stop_signal():
            return {"cancelled": True, "analyst_type": "crypto", "message": "Analysis cancelled by user"}
            
        analysis_depth = depth or self.analysis_depth
        self.clear_thoughts()
        
        # Record analysis start
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"Starting {self.name} analysis for {target}, depth level: {analysis_depth}",
            confidence=0.9
        )
        
        # Tool execution phase
        tool_results = {}
        if self.tools and self.tool_config.get("enabled", True):
            # Check stop signal（工具执行前）
            if self.check_stop_signal():
                return {"cancelled": True, "analyst_type": "crypto", "message": "Analysis cancelled before tool execution"}
            tool_results = await self._execute_tools(target, data)
        
        # Check stop signal（分析阶段前）
        if self.check_stop_signal():
            return {"cancelled": True, "analyst_type": "crypto", "message": "Analysis cancelled before LLM analysis"}
        
        # 分析阶段 - 使用配置的提示词模板
        analysis_result = await self._perform_analysis(target, data, tool_results, analysis_depth)
        
        # 计算置信度
        confidence = self._calculate_analysis_confidence(tool_results, analysis_depth)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            f"{self.name} analysis completed, confidence: {confidence:.2f}",
            confidence=confidence
        )
        
        return {
            "analyst_type": self.config.get("type", "crypto"),
            "analysis": analysis_result,
            "confidence_score": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream(),
            "tool_results": tool_results
        }
    
    async def _execute_tools(self, target: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tools to get data - subclasses can override to customize tool execution"""
        tool_results = {}
        
        # 基础价格数据
        if hasattr(self.tools, 'get_crypto_price_data'):
            try:
                price_data = self.tools.get_crypto_price_data(target, days_back=30)
                if 'error' not in price_data:
                    tool_results['price_data'] = price_data
                    self.record_thought(
                        ThoughtType.OBSERVATION,
                        f"Successfully retrieved price data for {target}",
                        confidence=0.8
                    )
            except Exception as e:
                logger.warning(f"Failed to retrieve price data: {e}")
        
        return tool_results
    
    async def _perform_analysis(self, target: str, data: Dict[str, Any], tool_results: Dict[str, Any], depth: int) -> str:
        """
        Execute specific analysis - using configured prompts
        Subclasses can override to implement specific analysis logic
        """
        # 使用提示词加载器获取配置
        from core.agents.prompt_loader import get_prompt_loader
        
        # 获取语言参数（从data中提取，如果没有则使用默认中文）
        language = data.get("language", "zh-CN")
        
        prompt_loader = get_prompt_loader()
        analyst_type = self.config.get("prompt_type", "market")
        prompt_config = prompt_loader.load_prompt(analyst_type, language=language)
        
        # 构建分析提示词
        analysis_prompt = self._build_analysis_prompt(
            target, data, tool_results, depth, prompt_config
        )
        
        # 执行LLM分析
        response = await self.llm.generate(analysis_prompt)
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            f"Completed {analyst_type} analysis",
            confidence=0.7
        )
        
        return response
    
    def _build_analysis_prompt(self, target: str, data: Dict[str, Any], 
                              tool_results: Dict[str, Any], depth: int,
                              prompt_config: Dict[str, Any]) -> str:
        """Build analysis prompt - unified template"""
        
        system_message = prompt_config.get("system_message", f"You are a professional {self.name}")
        
        # 格式化基础信息
        base_prompt = f"""
{system_message}

Analysis Target: {target}
Analysis Depth: {depth}/5
Current Date: {datetime.utcnow().strftime('%Y-%m-%d')}

"""
        
        # 添加工具数据
        if tool_results:
            base_prompt += "Retrieved Data:\n"
            for tool_name, result in tool_results.items():
                base_prompt += f"{tool_name}: {json.dumps(result, ensure_ascii=False, indent=2)}\n\n"
        
        # 添加分析要求
        focus_areas = self.config.get("analysis_focus", [])
        if focus_areas:
            base_prompt += f"Key Analysis Areas: {', '.join(focus_areas)}\n\n"
        
        base_prompt += """
Please conduct professional analysis based on the above data, including:
1. Key indicator interpretation
2. Trend analysis
3. Risk assessment
4. Investment recommendations

Return analysis results in structured format.
"""
        
        return base_prompt
    
    def _calculate_analysis_confidence(self, tool_results: Dict[str, Any], depth: int) -> float:
        """Calculate analysis confidence"""
        factors = {
            "data_quality": 0.8 if tool_results else 0.5,
            "data_recency": 0.8,  # Assume data is recent
            "analysis_depth": depth / 5,
            "market_conditions": 0.7
        }
        
        return self.calculate_confidence(factors)


class TechnicalAnalyst(BaseAnalyst):
    """Technical Analyst"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "Technical Analyst")
        
    def get_expertise_areas(self) -> List[str]:
        return ["price_patterns", "technical_indicators", "trend_analysis", "support_resistance"]
        
    def _get_default_domain(self) -> str:
        return "Technical Analysis"
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """Execute technical analysis"""
        # Check stop signal
        if self.check_stop_signal():
            return {"cancelled": True, "analyst_type": "technical", "message": "Analysis cancelled by user"}
            
        # 清空之前的思考记录
        self.clear_thoughts()
        
        # 使用工具获取实时价格数据
        real_time_data = {}
        technical_indicators = {}
        
        if self.tools:
            self.record_thought(
                ThoughtType.OBSERVATION,
                f"Retrieving real-time price data and technical indicators for {target}...",
                confidence=0.9
            )
            
            # 获取实时价格数据
            price_result = self.tools.get_crypto_price_data(target, days_back=30)
            
            # Check stop signal
            if self.check_stop_signal():
                return {"cancelled": True, "analyst_type": "technical", "message": "Analysis cancelled during price data retrieval"}
            
            if 'error' not in price_result:
                real_time_data = price_result
                latest_price = price_result.get('latest_price')
                price_change_pct = price_result.get('price_change_pct')
                
                self.record_thought(
                    ThoughtType.OBSERVATION,
                    f"Retrieved real-time data for {target}: Current price ${latest_price:.2f}, " +
                    f"Change {price_change_pct:.2f}% ({price_result.get('total_records')} records)",
                    confidence=0.95
                )
            
            # Check stop signal
            if self.check_stop_signal():
                return {"cancelled": True, "analyst_type": "technical", "message": "Analysis cancelled before retrieving technical indicators"}
            
            # 获取技术指标
            indicators_result = self.tools.get_technical_indicators(
                target, 
                indicators=['sma', 'rsi', 'macd', 'bb'],
                period_days=30
            )
            if 'error' not in indicators_result:
                technical_indicators = indicators_result.get('indicators', {})
                
                # 分析RSI信号
                rsi = technical_indicators.get('rsi')
                if rsi:
                    if rsi > 70:
                        self.record_thought(
                            ThoughtType.ANALYSIS,
                            f"RSI indicator at {rsi:.1f}, showing overbought condition, may face pullback pressure",
                            confidence=0.8
                        )
                    elif rsi < 30:
                        self.record_thought(
                            ThoughtType.ANALYSIS,
                            f"RSI indicator at {rsi:.1f}, showing oversold condition, may see bounce opportunity",
                            confidence=0.8
                        )
        
        # 使用传入的数据作为后备
        price_data = real_time_data if real_time_data else data.get("price_data", {})
        
        # 记录观察
        latest_price = price_data.get('latest_price') or price_data.get('current_price', 0)
        price_change = price_data.get('price_change_pct') or price_data.get('change_24h', 0)
        
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"Starting technical analysis of {target}. Current price: ${latest_price}, " +
            f"Change: {price_change}%",
            confidence=0.9
        )
        
        # 记录初步分析
        if price_data.get('change_24h', 0) > 5:
            self.record_thought(
                ThoughtType.ANALYSIS,
                "Strong uptrend detected, 24-hour gain exceeds 5%, need to analyze if this is sustainable growth",
                confidence=0.7
            )
        elif price_data.get('change_24h', 0) < -5:
            self.record_thought(
                ThoughtType.ANALYSIS,
                "Significant downtrend detected, 24-hour decline exceeds 5%, need to assess support level strength",
                confidence=0.7
            )
        
        # 构建包含实时数据的分析提示
        indicators_text = ""
        if technical_indicators:
            indicators_text = "\nTechnical Indicators:"
            for indicator, value in technical_indicators.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        indicators_text += f"\n- {sub_key}: {sub_value}"
                else:
                    indicators_text += f"\n- {indicator}: {value}"
        
        analysis_prompt = f"""
        Conduct in-depth technical analysis for {target} (Depth Level: {depth}/5):
        
        Real-time Price Data:
        - Current Price: ${price_data.get('latest_price') or price_data.get('current_price', 0)}
        - Price Change: {price_data.get('price_change_pct') or price_data.get('change_24h', 0)}%
        - Price Change Amount: ${price_data.get('price_change', 0)}
        - Data Records: {price_data.get('total_records', 'N/A')}
        - Analysis Period: {price_data.get('start_date', 'N/A')} to {price_data.get('end_date', 'N/A')}
        {indicators_text}
        
        Please analyze based on the above real-time data:
        1. Price trends (short-term, medium-term, long-term)
        2. Key support and resistance levels
        3. Technical indicator signal interpretation
        4. Risk assessment
        5. Trading recommendations
        
        Special Notes:
        - RSI > 70 indicates overbought, < 30 indicates oversold
        - MACD signal line crossovers indicate trend changes
        - Bollinger Bands position indicates price pressure/support
        
        Return in JSON format, including:
        - analysis: Detailed analysis content
        - summary: Brief summary
        - rating: Rating (bullish/neutral/bearish)
        - confidence_score: Confidence level (0-1)
        - key_findings: List of key findings
        - recommendations: List of specific recommendations
        """
        
        # 记录分析过程
        self.record_thought(
            ThoughtType.ANALYSIS,
            "Conducting comprehensive analysis of price trends, technical indicators, and volume data...",
            confidence=0.8
        )
        
        # Check stop signal（LLM调用前）
        if self.check_stop_signal():
            return {"cancelled": True, "analyst_type": "technical", "message": "Analysis cancelled before LLM call"}
        
        response = await self.llm.generate(analysis_prompt)
        
        # 计算置信度
        confidence_factors = {
            "data_quality": 0.8 if price_data else 0.2,
            "data_recency": 0.9,  # Assume data is latest
            "analysis_depth": depth / 5,
            "market_conditions": 0.7
        }
        
        final_confidence = self.calculate_confidence(confidence_factors)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            f"Technical analysis completed, overall confidence: {final_confidence:.2f}",
            confidence=final_confidence
        )
        
        result = {
            "analyst_type": "technical",
            "analysis": response,
            "confidence_score": final_confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }
        
        return result


class FundamentalAnalyst(BaseAnalyst):
    """Fundamental Analyst"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "Fundamental Analyst")
        
    def get_expertise_areas(self) -> List[str]:
        return ["financial_metrics", "business_model", "competitive_position", "growth_potential"]
        
    def _get_default_domain(self) -> str:
        return "Fundamental Analysis"
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """Execute fundamental analysis"""
        fundamentals = data.get("fundamentals", {})
        market_type = data.get("market_type", "stock")
        
        # 清空之前的思考记录
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"Starting fundamental analysis for {target}, market type: {market_type}",
            confidence=0.9
        )
        
        if market_type == "stock":
            # 分析财务数据
            if fundamentals:
                pe_ratio = fundamentals.get("pe_ratio", 0)
                revenue_growth = fundamentals.get("revenue_growth", 0)
                
                if pe_ratio > 0 and pe_ratio < 20:
                    self.record_thought(
                        ThoughtType.ANALYSIS,
                        f"P/E ratio of {pe_ratio} is in reasonable valuation range",
                        confidence=0.8,
                        evidence=[{"type": "valuation", "value": pe_ratio}]
                    )
                elif pe_ratio >= 20:
                    self.record_thought(
                        ThoughtType.ANALYSIS,
                        f"High P/E ratio of {pe_ratio}, need to check if supported by high growth",
                        confidence=0.7,
                        evidence=[{"type": "valuation", "value": pe_ratio}]
                    )
                
                if revenue_growth > 15:
                    self.record_thought(
                        ThoughtType.ANALYSIS,
                        f"Revenue growth rate of {revenue_growth}% shows good growth potential",
                        confidence=0.8,
                        evidence=[{"type": "growth", "value": revenue_growth}]
                    )
            
            analysis_prompt = f"""
            Conduct fundamental analysis for {target} (Depth Level: {depth}/5):
            
            Fundamental Data:
            {json.dumps(fundamentals, ensure_ascii=False, indent=2)}
            
            Please analyze:
            1. Financial health status
            2. Profitability and growth trends
            3. Valuation levels
            4. Industry position and competitive advantages
            5. Management quality
            
            Return analysis results in JSON format.
            """
        else:
            # 加密货币的基本面分析
            self.record_thought(
                ThoughtType.ANALYSIS,
                "Cryptocurrency fundamental analysis will focus on technical innovation, team strength, and ecosystem development",
                confidence=0.8
            )
            
            analysis_prompt = f"""
            Conduct fundamental analysis for {target} (Depth Level: {depth}/5):
            
            Please analyze:
            1. Project technology and innovation
            2. Team background and execution capability
            3. Token economic model
            4. Market adoption and ecosystem development
            5. Competitive landscape
            
            Return analysis results in JSON format.
            """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "Conducting comprehensive analysis of financial data, business model, and competitive advantages...",
            confidence=0.85
        )
            
        response = await self.llm.generate(analysis_prompt)
        
        # 计算置信度
        confidence_factors = {
            "data_quality": 0.9 if fundamentals else 0.3,
            "data_recency": 0.8,
            "analysis_depth": depth / 5,
            "market_conditions": 0.6
        }
        
        final_confidence = self.calculate_confidence(confidence_factors)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            f"Fundamental analysis completed, overall confidence: {final_confidence:.2f}",
            confidence=final_confidence
        )
        
        return {
            "analyst_type": "fundamental",
            "analysis": response,
            "confidence_score": final_confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class SentimentAnalyst(BaseAnalyst):
    """Sentiment Analyst"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "Sentiment Analyst")
        
    def get_expertise_areas(self) -> List[str]:
        return ["social_sentiment", "news_analysis", "market_psychology", "trend_momentum"]
        
    def _get_default_domain(self) -> str:
        return "Sentiment Analysis"
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行情绪分析"""
        # 清空之前的思考记录
        self.clear_thoughts()
        
        # 使用工具获取实时新闻和情绪数据
        real_time_news = []
        sentiment_data = {}
        
        if self.tools:
            self.record_thought(
                ThoughtType.OBSERVATION,
                f"正在获取{target}的实时新闻和市场情绪数据...",
                confidence=0.9
            )
            
            # 获取实时新闻
            news_result = self.tools.get_crypto_news(target, days_back=7, max_results=15)
            if 'error' not in news_result:
                real_time_news = news_result.get('articles', [])
                news_count = news_result.get('news_count', 0)
                
                self.record_thought(
                    ThoughtType.OBSERVATION,
                    f"获取到{news_count}条{target}相关新闻（过去7天）",
                    confidence=0.95
                )
                
                # 分析新闻标题情感倾向（简单启发式）
                positive_keywords = ['rise', 'surge', 'bull', 'gain', 'up', 'positive', 'growth', '涨', '上涨', '看涨']
                negative_keywords = ['fall', 'drop', 'bear', 'loss', 'down', 'negative', 'crash', '跌', '下跌', '看跌']
                
                positive_count = 0
                negative_count = 0
                
                for article in real_time_news[:10]:
                    headline = article.get('headline', '').lower()
                    if any(keyword in headline for keyword in positive_keywords):
                        positive_count += 1
                    elif any(keyword in headline for keyword in negative_keywords):
                        negative_count += 1
                
                if positive_count > negative_count:
                    self.record_thought(
                        ThoughtType.ANALYSIS,
                        f"新闻情绪偏向积极：{positive_count}正面 vs {negative_count}负面，市场预期乐观",
                        confidence=0.75
                    )
                elif negative_count > positive_count:
                    self.record_thought(
                        ThoughtType.ANALYSIS,
                        f"新闻情绪偏向消极：{negative_count}负面 vs {positive_count}正面，市场情绪谨慎",
                        confidence=0.75
                    )
                else:
                    self.record_thought(
                        ThoughtType.ANALYSIS,
                        f"新闻情绪中性：{positive_count}正面 vs {negative_count}负面，观望情绪浓厚",
                        confidence=0.7
                    )
            
            # 获取综合情绪分析
            sentiment_result = self.tools.get_sentiment_analysis(target, days_back=7)
            if 'error' not in sentiment_result:
                sentiment_data = sentiment_result
                
                total_articles = sentiment_result.get('summary', {}).get('total_news_articles', 0)
                self.record_thought(
                    ThoughtType.OBSERVATION,
                    f"综合情绪分析涵盖{total_articles}篇文章，数据来源：FinnHub、Reddit等",
                    confidence=0.8
                )
        
        # 使用实时数据，传入数据作为后备
        news = real_time_news if real_time_news else data.get("news", [])
        sentiment = sentiment_data if sentiment_data else data.get("sentiment", {})
        
        # 记录最终数据统计
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"情绪分析数据：{len(news)}条新闻，情绪数据{'已获取' if sentiment else '缺失'}",
            confidence=0.9
        )
        
        # 分析新闻情绪
        if news:
            positive_count = sum(1 for n in news[:10] if n.get("sentiment", 0) > 0.5)
            negative_count = sum(1 for n in news[:10] if n.get("sentiment", 0) < -0.5)
            
            if positive_count > negative_count:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"近期新闻偏向积极（{positive_count}正面 vs {negative_count}负面），市场情绪乐观",
                    confidence=0.7,
                    evidence=[{"positive_news": positive_count, "negative_news": negative_count}]
                )
            elif negative_count > positive_count:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"近期新闻偏向消极（{negative_count}负面 vs {positive_count}正面），市场情绪谨慎",
                    confidence=0.7,
                    evidence=[{"positive_news": positive_count, "negative_news": negative_count}]
                )
        
        # 分析社交媒体情绪
        if sentiment.get("twitter_mentions", 0) > 1000:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"社交媒体讨论热度高（{sentiment.get('twitter_mentions', 0)}次提及），关注度上升",
                confidence=0.8
            )
        
        # 格式化实时新闻数据
        news_summary = ""
        if news:
            news_summary = f"实时新闻标题（最近{len(news)}条）：\n"
            for i, article in enumerate(news[:5], 1):  # 只显示前5条避免太长
                news_summary += f"{i}. {article.get('headline', 'No headline')}\n"
                news_summary += f"   来源: {article.get('source', 'Unknown')} | 时间: {article.get('datetime', 'N/A')}\n"
        
        analysis_prompt = f"""
        对{target}进行市场情绪分析（深度级别：{depth}/5）：
        
        {news_summary}
        
        情绪数据统计：
        - 新闻文章数量: {len(news)}条
        - 数据来源: FinnHub、Reddit等多平台
        - 分析时间范围: 过去7天
        
        综合情绪分析结果：
        {json.dumps(sentiment, ensure_ascii=False, indent=2) if sentiment else "暂无综合情绪数据"}
        
        请基于以上实时数据进行深度情绪分析：
        1. 整体市场情绪趋势（积极/中性/消极）
        2. 新闻媒体报道倾向分析
        3. 市场关注度和讨论热度
        4. 潜在的情绪转折信号
        5. 主要情绪驱动因素识别
        6. 对价格走势的情绪影响预测
        
        以JSON格式返回分析结果，包含：
        - analysis: 详细分析内容
        - summary: 简短总结
        - sentiment_score: 情绪评分(-1到1，-1最消极，1最积极)
        - confidence_score: 置信度（0-1）
        - key_findings: 关键发现列表
        - recommendations: 基于情绪的操作建议
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在综合分析新闻情感、社交媒体热度和市场心理...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 计算置信度
        confidence_factors = {
            "data_quality": min(1.0, len(news) / 20),
            "data_recency": 0.9,
            "analysis_depth": depth / 5,
            "market_conditions": 0.7
        }
        
        final_confidence = self.calculate_confidence(confidence_factors)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            f"情绪分析完成，综合置信度：{final_confidence:.2f}",
            confidence=final_confidence
        )
        
        return {
            "analyst_type": "sentiment",
            "analysis": response,
            "confidence_score": final_confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class RiskAnalyst(BaseAnalyst):
    """风险分析师"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "风险分析师")
        
    def get_expertise_areas(self) -> List[str]:
        return ["risk_assessment", "volatility_analysis", "downside_protection", "portfolio_impact"]
        
    def _get_default_domain(self) -> str:
        return "风险管理"
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行风险分析"""
        price_data = data.get("price_data", {})
        
        # 清空之前的思考记录
        self.clear_thoughts()
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行风险评估，重点关注波动性和下行风险",
            confidence=0.9
        )
        
        # 分析波动性
        volatility = price_data.get('volatility_daily', 0)
        if volatility > 5:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"日波动率高达{volatility}%，属于高风险资产",
                confidence=0.9,
                evidence=[{"type": "volatility", "value": volatility}]
            )
        elif volatility > 2:
            self.record_thought(
                ThoughtType.ANALYSIS,
                f"日波动率为{volatility}%，风险适中",
                confidence=0.8,
                evidence=[{"type": "volatility", "value": volatility}]
            )
        
        # 分析价格位置
        current_price = price_data.get('current_price', 0)
        high_52w = price_data.get('high_52w', 0)
        low_52w = price_data.get('low_52w', 0)
        
        if high_52w > 0 and current_price > 0:
            price_position = (current_price - low_52w) / (high_52w - low_52w) * 100
            if price_position > 80:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"当前价格接近52周高点（{price_position:.1f}%位置），需警惕回调风险",
                    confidence=0.8
                )
            elif price_position < 20:
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    f"当前价格接近52周低点（{price_position:.1f}%位置），可能存在反弹机会",
                    confidence=0.7
                )
        
        analysis_prompt = f"""
        对{target}进行风险分析（深度级别：{depth}/5）：
        
        价格波动数据：
        - 当前价格：${price_data.get('current_price', 0)}
        - 52周最高：${price_data.get('high_52w', 0)}
        - 52周最低：${price_data.get('low_52w', 0)}
        - 日波动率：{price_data.get('volatility_daily', 0)}%
        
        请分析：
        1. 主要风险因素
        2. 波动性评估
        3. 下行风险
        4. 风险缓解策略
        5. 风险收益比
        
        以JSON格式返回分析结果。
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在综合评估市场风险、个股风险和系统性风险...",
            confidence=0.85
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 计算置信度
        confidence_factors = {
            "data_quality": 0.8 if price_data else 0.2,
            "data_recency": 0.9,
            "analysis_depth": depth / 5,
            "market_conditions": 0.5  # 风险分析在不确定市场中更重要
        }
        
        final_confidence = self.calculate_confidence(confidence_factors)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            f"风险分析完成，综合置信度：{final_confidence:.2f}",
            confidence=final_confidence
        )
        
        return {
            "analyst_type": "risk",
            "analysis": response,
            "confidence_score": final_confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class MarketAnalyst(BaseAnalyst):
    """市场分析师"""
    
    def __init__(self, llm: Any):
        super().__init__(llm, "市场分析师")
        
    def get_expertise_areas(self) -> List[str]:
        return ["macro_trends", "sector_analysis", "market_cycles", "cross_asset_correlation"]
        
    def _get_default_domain(self) -> str:
        return "市场分析"
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行市场分析"""
        # 清空之前的思考记录
        self.clear_thoughts()
        
        # 使用工具获取市场数据和新闻
        market_context = {}
        if self.tools:
            self.record_thought(
                ThoughtType.OBSERVATION,
                f"正在获取{target}的市场数据和相关新闻...",
                confidence=0.9
            )
            
            # 获取价格数据作为市场背景
            price_result = self.tools.get_crypto_price_data(target, days_back=30)
            if 'error' not in price_result:
                market_context['price_data'] = price_result
                
                self.record_thought(
                    ThoughtType.OBSERVATION,
                    f"获取{target}市场数据：当前价格${price_result.get('latest_price', 0):.2f}，" +
                    f"30天变化{price_result.get('price_change_pct', 0):.2f}%",
                    confidence=0.9
                )
        
        # 记录初始观察
        self.record_thought(
            ThoughtType.OBSERVATION,
            f"开始对{target}进行宏观市场分析，评估整体市场环境和行业趋势",
            confidence=0.9
        )
        
        # 分析市场数据
        market_data = data.get("market_data", {})
        if market_data:
            market_trend = market_data.get("trend", "unknown")
            if market_trend == "bullish":
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    "整体市场趋势向好，有利于风险资产表现",
                    confidence=0.8
                )
            elif market_trend == "bearish":
                self.record_thought(
                    ThoughtType.ANALYSIS,
                    "市场处于下行趋势，需要谨慎评估风险",
                    confidence=0.8
                )
        
        # 检查是否有行业数据
        sector_data = data.get("sector_data", {})
        if sector_data:
            self.record_thought(
                ThoughtType.ANALYSIS,
                "正在分析行业表现和板块轮动情况...",
                confidence=0.7
            )
        
        # 提出关键问题
        self.record_thought(
            ThoughtType.QUESTION,
            "当前市场周期处于什么阶段？政策面是否有重大变化？",
            confidence=0.6
        )
        
        analysis_prompt = f"""
        对{target}进行宏观市场分析（深度级别：{depth}/5）：
        
        市场数据：
        {json.dumps(market_data, ensure_ascii=False, indent=2) if market_data else "无"}
        
        行业数据：
        {json.dumps(sector_data, ensure_ascii=False, indent=2) if sector_data else "无"}
        
        请分析：
        1. 宏观经济环境
        2. 行业/板块趋势
        3. 市场周期位置
        4. 相关资产表现
        5. 政策和监管影响
        
        以JSON格式返回分析结果。
        """
        
        self.record_thought(
            ThoughtType.ANALYSIS,
            "正在综合分析宏观环境、行业趋势和政策影响...",
            confidence=0.8
        )
        
        response = await self.llm.generate(analysis_prompt)
        
        # 计算置信度
        confidence_factors = {
            "data_quality": 0.7,
            "data_recency": 0.8,
            "analysis_depth": depth / 5,
            "market_conditions": 0.6
        }
        
        final_confidence = self.calculate_confidence(confidence_factors)
        
        # 记录结论
        self.record_thought(
            ThoughtType.CONCLUSION,
            f"市场分析完成，综合置信度：{final_confidence:.2f}",
            confidence=final_confidence
        )
        
        return {
            "analyst_type": "market",
            "analysis": response,
            "confidence_score": final_confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }


class AgentCoordinator:
    """代理协调器 - 管理多个分析师的协作"""
    
    def __init__(self, agents: List[BaseAnalyst]):
        self.agents = agents
        self.debate_rounds = 3
        
    async def collaborative_analysis(
        self, 
        target: str, 
        data: Dict[str, Any], 
        depth: int = 3
    ) -> Dict[str, Any]:
        """执行协作分析"""
        logger.info(f"开始对{target}的协作分析，参与分析师：{len(self.agents)}个")
        
        # 第一阶段：独立分析
        individual_analyses = await self._conduct_individual_analyses(target, data, depth)
        
        # 第二阶段：观点交流和辩论
        debate_results = await self._conduct_debate(target, individual_analyses)
        
        # 第三阶段：形成共识
        consensus = await self._form_consensus(individual_analyses, debate_results)
        
        return {
            "individual_analyses": individual_analyses,
            "debate_results": debate_results,
            "consensus": consensus,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def _conduct_individual_analyses(
        self, 
        target: str, 
        data: Dict[str, Any], 
        depth: int
    ) -> List[Dict[str, Any]]:
        """进行独立分析"""
        tasks = []
        for agent in self.agents:
            task = agent.analyze(target, data, depth)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉失败的分析
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Agent {self.agents[i].name} analysis failed: {result}")
            else:
                valid_results.append(result)
                
        return valid_results
        
    async def _conduct_debate(
        self, 
        target: str, 
        analyses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """进行观点辩论"""
        debate_results = []
        
        # 提取主要观点分歧
        divergent_topics = self._identify_divergent_topics(analyses)
        
        for topic in divergent_topics[:3]:  # 限制辩论话题数量
            logger.info(f"开始辩论话题：{topic}")
            
            # 每个分析师对该话题发表观点
            debate_round = []
            for agent in self.agents:
                other_opinions = [
                    {
                        "analyst": a.get("analyst_type"),
                        "opinion": a.get("analysis", {}).get(topic, "无观点")
                    }
                    for a in analyses
                    if a.get("analyst_type") != agent.name.lower()
                ]
                
                opinion = await agent.debate(topic, other_opinions)
                debate_round.append(opinion)
                
            debate_results.append({
                "topic": topic,
                "round": debate_round,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        return debate_results
        
    async def _form_consensus(
        self, 
        analyses: List[Dict[str, Any]], 
        debates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """形成共识意见"""
        # 收集所有评级
        ratings = []
        confidences = []
        
        for analysis in analyses:
            if "rating" in analysis.get("analysis", {}):
                ratings.append(analysis["analysis"]["rating"])
            if "confidence_score" in analysis:
                confidences.append(analysis["confidence_score"])
                
        # 计算共识评级
        consensus_rating = self._calculate_weighted_consensus(ratings, confidences)
        
        # 整合关键发现
        all_findings = []
        for analysis in analyses:
            findings = analysis.get("analysis", {}).get("key_findings", [])
            all_findings.extend(findings)
            
        # 整合建议
        all_recommendations = []
        for analysis in analyses:
            recommendations = analysis.get("analysis", {}).get("recommendations", [])
            all_recommendations.extend(recommendations)
            
        return {
            "consensus_rating": consensus_rating,
            "average_confidence": sum(confidences) / len(confidences) if confidences else 0.5,
            "key_findings": self._prioritize_findings(all_findings),
            "recommendations": self._prioritize_recommendations(all_recommendations),
            "participating_analysts": len(analyses),
            "debate_topics": [d["topic"] for d in debates]
        }
        
    def _identify_divergent_topics(self, analyses: List[Dict[str, Any]]) -> List[str]:
        """识别分歧话题"""
        # 简化实现：返回预定义的关键话题
        return [
            "价格走势预测",
            "主要风险因素",
            "投资时机判断"
        ]
        
    def _calculate_weighted_consensus(
        self, 
        ratings: List[str], 
        confidences: List[float]
    ) -> str:
        """计算加权共识"""
        if not ratings:
            return "neutral"
            
        rating_scores = {
            "bullish": 1,
            "neutral": 0,
            "bearish": -1
        }
        
        # 如果没有置信度，使用简单平均
        if not confidences or len(confidences) != len(ratings):
            total_score = sum(rating_scores.get(r, 0) for r in ratings)
            avg_score = total_score / len(ratings)
        else:
            # 使用置信度加权
            weighted_sum = sum(
                rating_scores.get(r, 0) * c 
                for r, c in zip(ratings, confidences)
            )
            total_confidence = sum(confidences)
            avg_score = weighted_sum / total_confidence if total_confidence > 0 else 0
            
        if avg_score > 0.3:
            return "bullish"
        elif avg_score < -0.3:
            return "bearish"
        else:
            return "neutral"
            
    def _prioritize_findings(self, findings: List[Any]) -> List[Any]:
        """优先级排序关键发现"""
        # 简化实现：去重并返回前5个
        unique_findings = []
        seen = set()
        
        for finding in findings:
            finding_str = str(finding)
            if finding_str not in seen:
                seen.add(finding_str)
                unique_findings.append(finding)
                
        return unique_findings[:5]
        
    def _prioritize_recommendations(self, recommendations: List[Any]) -> List[Any]:
        """优先级排序建议"""
        # 简化实现：去重并返回前3个
        unique_recommendations = []
        seen = set()
        
        for rec in recommendations:
            rec_str = str(rec)
            if rec_str not in seen:
                seen.add(rec_str)
                unique_recommendations.append(rec)
                
        return unique_recommendations[:3]