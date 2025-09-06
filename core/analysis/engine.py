"""
高级分析引擎
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database.models.analysis import AnalysisTask, AnalysisReport, AnalysisLog, AnalysisStatus
from core.api.v1.schemas.analysis import AnalysisRequest, LLMProvider
from core.agents.base import (
    TechnicalAnalyst,
    FundamentalAnalyst,
    SentimentAnalyst,
    RiskAnalyst,
    MarketAnalyst,
    AgentCoordinator
)
from core.dependencies import get_data_gateway
from core.business.llm_factory import LLMFactory
# WebSocket导入将在运行时进行，避免循环导入

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """分析引擎主类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_gateway = get_data_gateway()
        self.llm_factory = LLMFactory()
        self.agents = {
            'technical': TechnicalAnalyst,
            'fundamental': FundamentalAnalyst,
            'sentiment': SentimentAnalyst,
            'risk': RiskAnalyst,
            'market': MarketAnalyst
        }
        
    async def run_analysis(self, task_id: UUID, request: AnalysisRequest):
        """运行分析任务"""
        try:
            # 更新任务状态为运行中
            await self._update_task_status(task_id, AnalysisStatus.RUNNING)
            await self._log(task_id, "info", None, "分析任务开始")
            
            # 获取市场数据
            await self._update_progress(task_id, 10, "正在获取市场数据...")
            market_data = await self._fetch_market_data(task_id, request.symbol, request.market_type)
            
            # 初始化LLM
            llm_config = request.llm_config or self._get_default_llm_config()
            llm = self.llm_factory.create_llm(
                provider=llm_config.provider,
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens
            )
            
            # 创建分析师实例
            agents = []
            for analyst_type in request.analysts:
                analyst_class = self.agents.get(analyst_type)
                if analyst_class:
                    agents.append(analyst_class(llm=llm))
            
            if not agents:
                raise ValueError("没有有效的分析师")
            
            # 使用协作分析模式
            await self._update_progress(task_id, 25, "正在进行协作分析...")
            
            # 创建思考流广播器 - 使用优化的处理
            async def thought_broadcaster(agent_name: str, thought_data: Dict[str, Any]):
                """广播agent思考流 - 通过优化器批处理"""
                # 动态导入避免循环导入
                from core.websocket.manager import manager as websocket_manager
                await websocket_manager.process_agent_thought(
                    analysis_id=str(task_id),
                    agent_id=agent_name,
                    thought=thought_data
                )
            
            # 为每个agent注册思考流回调
            for agent in agents:
                # 包装原有的record_thought方法
                original_record_thought = agent.record_thought
                
                def create_wrapped_record_thought(agent_instance):
                    def wrapped_record_thought(thought_type, content, confidence=0.5, evidence=None):
                        # 调用原方法
                        thought = original_record_thought(thought_type, content, confidence, evidence)
                        # 异步广播思考
                        asyncio.create_task(thought_broadcaster(agent_instance.name, thought.to_dict()))
                        return thought
                    return wrapped_record_thought
                
                agent.record_thought = create_wrapped_record_thought(agent)
            
            coordinator = AgentCoordinator(agents)
            collaboration_result = await coordinator.collaborative_analysis(
                symbol=request.symbol,
                data=market_data,
                depth=request.analysis_depth
            )
            
            # 保存各个分析师的独立分析
            reports = []
            for analysis in collaboration_result.get("individual_analyses", []):
                report = AnalysisReport(
                    task_id=task_id,
                    analyst_type=analysis.get("analyst_type", "unknown"),
                    content=analysis.get("analysis", {}),
                    summary=analysis.get("summary", ""),
                    rating=analysis.get("rating"),
                    confidence_score=analysis.get("confidence_score"),
                    key_findings=analysis.get("key_findings", []),
                    recommendations=analysis.get("recommendations", [])
                )
                self.db.add(report)
                reports.append(analysis)
            
            # 保存辩论结果
            await self._save_debate_logs(task_id, collaboration_result.get("debate_results", []))
            
            await self.db.commit()
            await self._update_progress(task_id, 70, "协作分析完成，正在生成综合报告...")
            
            # 生成综合报告（使用协作结果）
            await self._update_progress(task_id, 85, "正在生成综合报告...")
            final_report = await self._generate_collaborative_report(
                task_id, 
                collaboration_result, 
                llm
            )
            
            # 计算成本
            total_cost = await self._calculate_total_cost(task_id)
            
            # 更新任务状态为完成
            await self._update_task_status(task_id, AnalysisStatus.COMPLETED, cost=total_cost)
            await self._log(task_id, "info", None, f"分析任务完成，总成本: ${total_cost:.4f}")
            
        except Exception as e:
            logger.error(f"Analysis failed for task {task_id}: {str(e)}")
            await self._update_task_status(
                task_id, 
                AnalysisStatus.FAILED, 
                error_message=str(e)
            )
            await self._log(task_id, "error", None, f"分析任务失败: {str(e)}")
            raise
            
    async def _fetch_market_data(self, task_id: UUID, symbol: str, market_type: str) -> Dict[str, Any]:
        """获取市场数据"""
        try:
            # 获取各类数据
            price_response = await self.data_gateway.fetch(
                symbol=symbol,
                data_type="price",
                provider="mock",  # 使用mock提供者
                market_type=market_type
            )
            price_data = price_response.data
            
            if market_type == "stock":
                fundamentals_response = await self.data_gateway.fetch(
                    symbol=symbol,
                    data_type="fundamentals",
                    provider="mock"
                )
                fundamentals = fundamentals_response.data
                
                news_response = await self.data_gateway.fetch(
                    symbol=symbol,
                    data_type="news",
                    provider="mock",
                    limit=20
                )
                news = news_response.data
            else:
                fundamentals = {}
                news_response = await self.data_gateway.fetch(
                    symbol=symbol,
                    data_type="crypto_news",
                    provider="mock",
                    limit=20
                )
                news = news_response.data
            
            sentiment_response = await self.data_gateway.fetch(
                symbol=symbol,
                data_type="social_sentiment",
                provider="mock"
            )
            sentiment = sentiment_response.data
            
            await self._log(task_id, "info", None, f"成功获取{symbol}的市场数据")
            
            return {
                "symbol": symbol,
                "market_type": market_type,
                "price_data": price_data,
                "fundamentals": fundamentals,
                "news": news,
                "sentiment": sentiment,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await self._log(task_id, "error", None, f"获取市场数据失败: {str(e)}")
            raise
            
    async def _run_analyst(
        self, 
        task_id: UUID,
        analyst_type: str,
        symbol: str,
        market_data: Dict[str, Any],
        llm: Any,
        analysis_depth: int
    ) -> Optional[Dict[str, Any]]:
        """运行单个分析师"""
        try:
            # 创建分析师实例
            analyst_class = self.agents.get(analyst_type)
            if not analyst_class:
                await self._log(task_id, "warning", analyst_type, f"未知的分析师类型: {analyst_type}")
                return None
                
            analyst = analyst_class(llm=llm)
            
            # 运行分析
            await self._log(task_id, "info", analyst_type, f"开始{analyst_type}分析")
            
            analysis_result = await analyst.analyze(
                symbol=symbol,
                data=market_data,
                depth=analysis_depth
            )
            
            # 保存报告
            report = AnalysisReport(
                task_id=task_id,
                analyst_type=analyst_type,
                content=analysis_result.get("analysis", {}),
                summary=analysis_result.get("summary", ""),
                rating=analysis_result.get("rating"),
                confidence_score=analysis_result.get("confidence_score"),
                key_findings=analysis_result.get("key_findings", []),
                recommendations=analysis_result.get("recommendations", [])
            )
            
            self.db.add(report)
            await self.db.commit()
            
            await self._log(task_id, "info", analyst_type, f"{analyst_type}分析完成")
            
            # 更新token使用量
            token_usage = analysis_result.get("token_usage", {})
            if token_usage:
                await self._update_token_usage(task_id, token_usage)
            
            return analysis_result
            
        except Exception as e:
            await self._log(task_id, "error", analyst_type, f"分析失败: {str(e)}")
            return None
            
    async def _generate_final_report(
        self, 
        task_id: UUID,
        reports: List[Dict[str, Any]],
        llm: Any
    ) -> Dict[str, Any]:
        """生成综合报告"""
        try:
            # 汇总各个分析师的观点
            summaries = []
            ratings = []
            all_findings = []
            all_recommendations = []
            
            for report in reports:
                if report:
                    summaries.append({
                        "analyst": report.get("analyst_type", "unknown"),
                        "summary": report.get("summary", "")
                    })
                    
                    if report.get("rating"):
                        ratings.append(report["rating"])
                        
                    all_findings.extend(report.get("key_findings", []))
                    all_recommendations.extend(report.get("recommendations", []))
            
            # 使用LLM生成综合报告
            synthesis_prompt = f"""
            基于以下各个分析师的报告，生成一份综合投资分析报告：
            
            分析师报告摘要：
            {json.dumps(summaries, ensure_ascii=False, indent=2)}
            
            请生成：
            1. 综合评级（看涨/中性/看跌）
            2. 关键发现（最重要的3-5个）
            3. 投资建议（具体可执行的）
            4. 风险提示
            
            以JSON格式返回。
            """
            
            synthesis_result = await llm.generate(synthesis_prompt)
            
            # 保存综合报告
            final_report = AnalysisReport(
                task_id=task_id,
                analyst_type="synthesis",
                content=synthesis_result,
                summary="综合分析报告",
                rating=self._calculate_consensus_rating(ratings),
                confidence_score=self._calculate_average_confidence(reports),
                key_findings=all_findings[:5],  # 取前5个最重要的发现
                recommendations=all_recommendations[:3]  # 取前3个最重要的建议
            )
            
            self.db.add(final_report)
            await self.db.commit()
            
            await self._log(task_id, "info", None, "综合报告生成完成")
            
            return synthesis_result
            
        except Exception as e:
            await self._log(task_id, "error", None, f"生成综合报告失败: {str(e)}")
            raise
            
    async def _calculate_total_cost(self, task_id: UUID) -> float:
        """计算总成本"""
        # 查询任务的token使用量
        result = await self.db.execute(
            select(AnalysisTask).where(AnalysisTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return 0.0
            
        token_usage = task.token_usage or {}
        input_tokens = token_usage.get("input_tokens", 0)
        output_tokens = token_usage.get("output_tokens", 0)
        
        # 根据模型计算成本（示例价格）
        # TODO: 从配置中读取实际价格
        input_cost = input_tokens * 0.00001  # $0.01 per 1K tokens
        output_cost = output_tokens * 0.00003  # $0.03 per 1K tokens
        
        return input_cost + output_cost
        
    async def _update_task_status(
        self, 
        task_id: UUID, 
        status: AnalysisStatus,
        error_message: Optional[str] = None,
        cost: Optional[float] = None
    ):
        """更新任务状态"""
        result = await self.db.execute(
            select(AnalysisTask).where(AnalysisTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if task:
            task.status = status
            task.updated_at = datetime.utcnow()
            
            if status == AnalysisStatus.RUNNING:
                task.started_at = datetime.utcnow()
            elif status in [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]:
                task.completed_at = datetime.utcnow()
                
            if error_message:
                task.error_message = error_message
                
            if cost is not None:
                task.cost_usd = cost
                
            await self.db.commit()
            
    async def _update_progress(self, task_id: UUID, progress: int, message: str):
        """更新任务进度"""
        result = await self.db.execute(
            select(AnalysisTask).where(AnalysisTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if task:
            task.progress = progress
            await self.db.commit()
            
        await self._log(task_id, "info", None, f"进度: {progress}% - {message}")
        
    async def _update_token_usage(self, task_id: UUID, usage: Dict[str, int]):
        """更新token使用量"""
        result = await self.db.execute(
            select(AnalysisTask).where(AnalysisTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if task:
            current_usage = task.token_usage or {"input_tokens": 0, "output_tokens": 0}
            current_usage["input_tokens"] += usage.get("input_tokens", 0)
            current_usage["output_tokens"] += usage.get("output_tokens", 0)
            task.token_usage = current_usage
            await self.db.commit()
            
    async def _log(self, task_id: UUID, level: str, agent_name: Optional[str], message: str):
        """记录日志"""
        log = AnalysisLog(
            task_id=task_id,
            level=level,
            agent_name=agent_name,
            message=message
        )
        self.db.add(log)
        await self.db.commit()
        
    def _get_default_llm_config(self) -> Dict[str, Any]:
        """获取默认LLM配置"""
        return {
            "provider": LLMProvider.OPENAI,
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": None
        }
        
    def _calculate_consensus_rating(self, ratings: List[str]) -> str:
        """计算共识评级"""
        if not ratings:
            return "neutral"
            
        rating_scores = {
            "bullish": 1,
            "neutral": 0,
            "bearish": -1
        }
        
        total_score = sum(rating_scores.get(r, 0) for r in ratings)
        avg_score = total_score / len(ratings)
        
        if avg_score > 0.3:
            return "bullish"
        elif avg_score < -0.3:
            return "bearish"
        else:
            return "neutral"
            
    def _calculate_average_confidence(self, reports: List[Dict[str, Any]]) -> float:
        """计算平均置信度"""
        confidences = [
            r.get("confidence_score", 0.5) 
            for r in reports 
            if r and "confidence_score" in r
        ]
        
        if not confidences:
            return 0.5
            
        return sum(confidences) / len(confidences)
        
    async def _save_debate_logs(self, task_id: UUID, debate_results: List[Dict[str, Any]]):
        """保存辩论日志"""
        for debate in debate_results:
            topic = debate.get("topic", "未知话题")
            
            # 记录辩论开始
            await self._log(task_id, "info", None, f"开始辩论话题: {topic}")
            
            # 记录每个分析师的观点
            for opinion in debate.get("round", []):
                analyst = opinion.get("analyst", "未知分析师")
                response = opinion.get("debate_response", {})
                
                # 提取核心观点
                core_opinion = str(response)[:500] if response else "无观点"
                
                await self._log(
                    task_id, 
                    "info", 
                    analyst, 
                    f"就'{topic}'发表观点: {core_opinion}"
                )
                
    async def _generate_collaborative_report(
        self, 
        task_id: UUID,
        collaboration_result: Dict[str, Any],
        llm: Any
    ) -> Dict[str, Any]:
        """基于协作结果生成综合报告"""
        try:
            individual_analyses = collaboration_result.get("individual_analyses", [])
            debate_results = collaboration_result.get("debate_results", [])
            consensus = collaboration_result.get("consensus", {})
            
            # 构建综合分析提示
            synthesis_prompt = f"""
            基于多位分析师的协作分析结果，生成综合投资分析报告：
            
            ## 参与分析师观点摘要
            {self._format_individual_analyses(individual_analyses)}
            
            ## 辩论话题和观点交锋
            {self._format_debate_results(debate_results)}
            
            ## 初步共识
            - 共识评级：{consensus.get('consensus_rating', '中性')}
            - 平均置信度：{consensus.get('average_confidence', 0.5):.2f}
            - 参与分析师数量：{consensus.get('participating_analysts', 0)}
            
            请生成最终的综合分析报告，包含：
            1. 执行摘要（整体观点和建议）
            2. 关键发现（结合各方观点后的核心发现）
            3. 风险评估（综合风险因素）
            4. 投资建议（具体可操作的建议）
            5. 置信度分析（对结论的置信程度）
            
            以结构化JSON格式返回。
            """
            
            synthesis_result = await llm.generate(synthesis_prompt)
            
            # 保存综合报告
            final_report = AnalysisReport(
                task_id=task_id,
                analyst_type="collaborative_synthesis",
                content={
                    "synthesis": synthesis_result,
                    "collaboration_metadata": {
                        "analysts_count": len(individual_analyses),
                        "debate_topics": [d.get("topic") for d in debate_results],
                        "consensus_rating": consensus.get("consensus_rating"),
                        "average_confidence": consensus.get("average_confidence")
                    }
                },
                summary="多智能体协作综合分析报告",
                rating=consensus.get("consensus_rating", "neutral"),
                confidence_score=consensus.get("average_confidence", 0.5),
                key_findings=consensus.get("key_findings", []),
                recommendations=consensus.get("recommendations", [])
            )
            
            self.db.add(final_report)
            await self.db.commit()
            
            await self._log(task_id, "info", None, "协作综合报告生成完成")
            
            return {
                "synthesis_result": synthesis_result,
                "collaboration_summary": consensus,
                "metadata": {
                    "analysts_participated": len(individual_analyses),
                    "debate_rounds": len(debate_results)
                }
            }
            
        except Exception as e:
            await self._log(task_id, "error", None, f"生成协作综合报告失败: {str(e)}")
            raise
            
    def _format_individual_analyses(self, analyses: List[Dict[str, Any]]) -> str:
        """格式化独立分析结果"""
        formatted = []
        for analysis in analyses:
            analyst_type = analysis.get("analyst_type", "未知")
            summary = str(analysis.get("analysis", {}))[:300]  # 截取前300字符
            confidence = analysis.get("confidence_score", 0.5)
            
            formatted.append(f"- {analyst_type}（置信度: {confidence:.2f}）: {summary}")
            
        return "\n".join(formatted)
        
    def _format_debate_results(self, debates: List[Dict[str, Any]]) -> str:
        """格式化辩论结果"""
        if not debates:
            return "无辩论记录"
            
        formatted = []
        for debate in debates:
            topic = debate.get("topic", "未知话题")
            round_data = debate.get("round", [])
            
            formatted.append(f"话题: {topic}")
            for opinion in round_data:
                analyst = opinion.get("analyst", "未知")
                response = str(opinion.get("debate_response", ""))[:200]
                formatted.append(f"  - {analyst}: {response}")
                
        return "\n".join(formatted)