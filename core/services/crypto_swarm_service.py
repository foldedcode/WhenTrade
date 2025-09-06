"""
加密货币Swarm风格新闻服务
使用DuckDuckGo作为唯一数据源的多代理新闻聚合系统
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from duckduckgo_search import DDGS
import logging
import time
import random

# 导入日志模块
from core.utils.logging_manager import get_logger
logger = get_logger('crypto_swarm')


class NewsSearchAgent:
    """新闻搜索代理 - 负责从DuckDuckGo获取加密货币新闻"""
    
    def __init__(self):
        self.ddgs = DDGS()
        self.crypto_keywords = {
            'BTC': ['Bitcoin', 'BTC', '比特币'],
            'ETH': ['Ethereum', 'ETH', '以太坊'],
            'SOL': ['Solana', 'SOL'],
            'BNB': ['Binance', 'BNB', '币安币'],
            'XRP': ['Ripple', 'XRP', '瑞波币'],
            'ADA': ['Cardano', 'ADA'],
            'DOGE': ['Dogecoin', 'DOGE', '狗狗币'],
            'DOT': ['Polkadot', 'DOT']
        }
    
    def search(self, symbol: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        搜索指定加密货币的新闻
        
        Args:
            symbol: 加密货币符号 (如 BTC, ETH)
            max_results: 最大结果数
            
        Returns:
            新闻列表
        """
        try:
            # 获取搜索关键词
            keywords = self.crypto_keywords.get(symbol.upper(), [symbol])
            primary_keyword = keywords[0] if keywords else symbol
            
            # 构建搜索查询
            queries = [
                f"{primary_keyword} cryptocurrency news",
                f"{primary_keyword} price analysis",
                f"{primary_keyword} market update"
            ]
            
            all_news = []
            seen_urls = set()
            
            for query in queries:
                try:
                    # 使用DuckDuckGo搜索新闻
                    results = self.ddgs.news(
                        keywords=query,
                        region='wt-wt',  # 全球
                        safesearch='off',
                        max_results=max_results
                    )
                    
                    for result in results:
                        # 去重
                        if result.get('url') in seen_urls:
                            continue
                        seen_urls.add(result.get('url'))
                        
                        # 格式化结果
                        news_item = {
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                            'body': result.get('body', ''),
                            'date': result.get('date', ''),
                            'source': result.get('source', ''),
                            'image': result.get('image', ''),
                            'symbol': symbol,
                            'query': query
                        }
                        all_news.append(news_item)
                        
                        if len(all_news) >= max_results:
                            break
                    
                    if len(all_news) >= max_results:
                        break
                        
                    # 避免请求过快
                    time.sleep(random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    logger.warning(f"搜索失败 for query '{query}': {e}")
                    continue
            
            logger.info(f"搜索到 {len(all_news)} 条关于 {symbol} 的新闻")
            return all_news[:max_results]
            
        except Exception as e:
            logger.error(f"新闻搜索失败: {e}")
            return []


class NewsAnalyzerAgent:
    """新闻分析代理 - 分析新闻内容并提取关键信息"""
    
    def __init__(self):
        self.sentiment_keywords = {
            'positive': [
                'bullish', 'surge', 'rally', 'gain', 'rise', 'soar', 'jump',
                'breakthrough', 'record', 'high', 'boom', 'growth', 'adoption',
                'upgrade', 'partnership', 'integration', 'institutional'
            ],
            'negative': [
                'bearish', 'crash', 'fall', 'drop', 'plunge', 'decline', 'slump',
                'concern', 'warning', 'risk', 'hack', 'exploit', 'regulation',
                'ban', 'restriction', 'lawsuit', 'investigation', 'sell-off'
            ],
            'neutral': [
                'stable', 'steady', 'consolidate', 'range', 'sideways', 'unchanged',
                'update', 'announce', 'report', 'discuss', 'consider', 'review'
            ]
        }
    
    def analyze(self, news_items: List[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
        """
        分析新闻列表并提取关键信息
        
        Args:
            news_items: 新闻列表
            symbol: 加密货币符号
            
        Returns:
            分析结果
        """
        try:
            if not news_items:
                return {
                    'symbol': symbol,
                    'total_news': 0,
                    'sentiment': 'neutral',
                    'key_topics': [],
                    'price_mentions': [],
                    'major_events': [],
                    'analyzed_news': []
                }
            
            analyzed_news = []
            sentiments = []
            key_topics = set()
            price_mentions = []
            major_events = []
            
            for news in news_items:
                # 分析单条新闻
                analysis = self._analyze_single_news(news)
                analyzed_news.append(analysis)
                
                # 收集情感
                sentiments.append(analysis['sentiment'])
                
                # 收集主题
                key_topics.update(analysis['topics'])
                
                # 收集价格提及
                if analysis['price_mention']:
                    price_mentions.append(analysis['price_mention'])
                
                # 收集重大事件
                if analysis['is_major_event']:
                    major_events.append({
                        'title': news['title'],
                        'date': news['date'],
                        'type': analysis['event_type']
                    })
            
            # 计算整体情感
            overall_sentiment = self._calculate_overall_sentiment(sentiments)
            
            return {
                'symbol': symbol,
                'total_news': len(news_items),
                'sentiment': overall_sentiment,
                'sentiment_distribution': self._get_sentiment_distribution(sentiments),
                'key_topics': list(key_topics)[:10],  # 前10个主题
                'price_mentions': price_mentions[:5],  # 前5个价格提及
                'major_events': major_events[:3],  # 前3个重大事件
                'analyzed_news': analyzed_news[:5],  # 前5条分析结果
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"新闻分析失败: {e}")
            return {
                'symbol': symbol,
                'total_news': len(news_items) if news_items else 0,
                'sentiment': 'neutral',
                'error': str(e)
            }
    
    def _analyze_single_news(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """分析单条新闻"""
        text = f"{news.get('title', '')} {news.get('body', '')}".lower()
        
        # 情感分析
        sentiment_scores = {
            'positive': sum(1 for word in self.sentiment_keywords['positive'] if word in text),
            'negative': sum(1 for word in self.sentiment_keywords['negative'] if word in text),
            'neutral': sum(1 for word in self.sentiment_keywords['neutral'] if word in text)
        }
        
        sentiment = max(sentiment_scores.items(), key=lambda x: x[1])[0]
        if sentiment_scores[sentiment] == 0:
            sentiment = 'neutral'
        
        # 提取主题
        topics = self._extract_topics(text)
        
        # 检查价格提及
        price_mention = self._extract_price_mention(text)
        
        # 判断是否重大事件
        is_major_event = self._is_major_event(text)
        event_type = self._get_event_type(text) if is_major_event else None
        
        return {
            'title': news.get('title', ''),
            'sentiment': sentiment,
            'sentiment_score': sentiment_scores[sentiment],
            'topics': topics,
            'price_mention': price_mention,
            'is_major_event': is_major_event,
            'event_type': event_type,
            'source': news.get('source', ''),
            'date': news.get('date', '')
        }
    
    def _extract_topics(self, text: str) -> List[str]:
        """提取关键主题"""
        topics = []
        topic_keywords = {
            'price_action': ['price', 'trading', 'chart', 'technical', 'support', 'resistance'],
            'regulation': ['regulation', 'sec', 'government', 'law', 'compliance', 'legal'],
            'adoption': ['adoption', 'institutional', 'company', 'accept', 'integrate', 'use'],
            'technology': ['upgrade', 'development', 'protocol', 'network', 'blockchain', 'defi'],
            'market': ['market', 'volume', 'liquidity', 'exchange', 'trading'],
            'partnership': ['partner', 'collaboration', 'alliance', 'deal', 'agreement'],
            'competition': ['competitor', 'versus', 'compare', 'alternative', 'rival']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(word in text for word in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_price_mention(self, text: str) -> Optional[str]:
        """提取价格提及"""
        import re
        
        # 查找价格模式 (如 $50,000 或 50k)
        price_patterns = [
            r'\$[\d,]+\.?\d*',  # $50,000.00
            r'[\d,]+\.?\d*\s*(?:usd|dollar)',  # 50000 usd
            r'[\d,]+k',  # 50k
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        
        return None
    
    def _is_major_event(self, text: str) -> bool:
        """判断是否为重大事件"""
        major_keywords = [
            'breaking', 'major', 'significant', 'milestone', 'record',
            'announce', 'launch', 'release', 'partnership', 'acquisition',
            'hack', 'exploit', 'crash', 'surge', 'regulation', 'ban'
        ]
        return any(word in text for word in major_keywords)
    
    def _get_event_type(self, text: str) -> str:
        """获取事件类型"""
        if any(word in text for word in ['hack', 'exploit', 'breach', 'attack']):
            return 'security'
        elif any(word in text for word in ['regulation', 'sec', 'law', 'ban']):
            return 'regulatory'
        elif any(word in text for word in ['partner', 'collaboration', 'deal']):
            return 'partnership'
        elif any(word in text for word in ['launch', 'release', 'upgrade']):
            return 'product'
        elif any(word in text for word in ['surge', 'rally', 'crash', 'plunge']):
            return 'price_movement'
        else:
            return 'other'
    
    def _calculate_overall_sentiment(self, sentiments: List[str]) -> str:
        """计算整体情感"""
        if not sentiments:
            return 'neutral'
        
        sentiment_counts = {
            'positive': sentiments.count('positive'),
            'negative': sentiments.count('negative'),
            'neutral': sentiments.count('neutral')
        }
        
        # 加权计算
        score = sentiment_counts['positive'] - sentiment_counts['negative']
        
        if score > len(sentiments) * 0.2:
            return 'positive'
        elif score < -len(sentiments) * 0.2:
            return 'negative'
        else:
            return 'neutral'
    
    def _get_sentiment_distribution(self, sentiments: List[str]) -> Dict[str, float]:
        """获取情感分布"""
        if not sentiments:
            return {'positive': 0, 'negative': 0, 'neutral': 0}
        
        total = len(sentiments)
        return {
            'positive': round(sentiments.count('positive') / total, 2),
            'negative': round(sentiments.count('negative') / total, 2),
            'neutral': round(sentiments.count('neutral') / total, 2)
        }


class NewsSummarizerAgent:
    """新闻总结代理 - 生成结构化的新闻分析报告"""
    
    def summarize(self, analysis: Dict[str, Any], symbol: str) -> str:
        """
        生成新闻分析总结报告
        
        Args:
            analysis: 分析结果
            symbol: 加密货币符号
            
        Returns:
            格式化的总结报告
        """
        try:
            if not analysis or analysis.get('total_news', 0) == 0:
                return self._generate_no_news_report(symbol)
            
            # 生成报告各部分
            header = self._generate_header(symbol, analysis)
            sentiment_section = self._generate_sentiment_section(analysis)
            topics_section = self._generate_topics_section(analysis)
            events_section = self._generate_events_section(analysis)
            price_section = self._generate_price_section(analysis)
            summary = self._generate_summary(analysis)
            
            # 组合报告
            report = f"""
{header}

{sentiment_section}

{topics_section}

{events_section}

{price_section}

{summary}
"""
            
            return report.strip()
            
        except Exception as e:
            logger.error(f"生成总结报告失败: {e}")
            return f"【{symbol} 新闻分析】\n分析过程中出现错误: {str(e)}"
    
    def _generate_no_news_report(self, symbol: str) -> str:
        """生成无新闻时的报告"""
        return f"""
【{symbol} 市场情绪分析】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 数据状态：暂无最新新闻数据

当前未能获取到关于 {symbol} 的最新新闻信息。这可能表明：
• 市场处于相对平静期，无重大事件发生
• 投资者情绪稳定，缺乏明显方向性
• 建议关注技术面指标和链上数据作为补充

建议操作：
• 保持观望，等待更多市场信号
• 关注其他数据源如链上活动和技术指标
• 留意即将发布的重要公告或事件
"""
    
    def _generate_header(self, symbol: str, analysis: Dict[str, Any]) -> str:
        """生成报告头部"""
        return f"""
【{symbol} 市场情绪分析】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
📰 新闻数量：{analysis['total_news']} 条
"""
    
    def _generate_sentiment_section(self, analysis: Dict[str, Any]) -> str:
        """生成情感分析部分"""
        sentiment = analysis.get('sentiment', 'neutral')
        distribution = analysis.get('sentiment_distribution', {})
        
        # 情感图标
        sentiment_icons = {
            'positive': '🟢 看涨',
            'negative': '🔴 看跌',
            'neutral': '🟡 中性'
        }
        
        # 生成情感条形图
        pos_bar = '█' * int(distribution.get('positive', 0) * 10)
        neg_bar = '█' * int(distribution.get('negative', 0) * 10)
        neu_bar = '█' * int(distribution.get('neutral', 0) * 10)
        
        return f"""
📈 市场情绪：{sentiment_icons.get(sentiment, '🟡 中性')}
├─ 积极 {distribution.get('positive', 0)*100:.0f}% {pos_bar}
├─ 消极 {distribution.get('negative', 0)*100:.0f}% {neg_bar}
└─ 中性 {distribution.get('neutral', 0)*100:.0f}% {neu_bar}
"""
    
    def _generate_topics_section(self, analysis: Dict[str, Any]) -> str:
        """生成主题分析部分"""
        topics = analysis.get('key_topics', [])
        
        if not topics:
            return "🏷️ 关键主题：暂无明显主题"
        
        # 主题映射到中文
        topic_names = {
            'price_action': '价格走势',
            'regulation': '监管动态',
            'adoption': '采用进展',
            'technology': '技术发展',
            'market': '市场动态',
            'partnership': '合作伙伴',
            'competition': '竞争格局'
        }
        
        topic_list = [topic_names.get(t, t) for t in topics[:5]]
        
        return f"""
🏷️ 关键主题：
{' | '.join(f'#{topic}' for topic in topic_list)}
"""
    
    def _generate_events_section(self, analysis: Dict[str, Any]) -> str:
        """生成重大事件部分"""
        events = analysis.get('major_events', [])
        
        if not events:
            return "⚡ 重大事件：近期无重大事件"
        
        event_type_names = {
            'security': '🔒 安全事件',
            'regulatory': '⚖️ 监管事件',
            'partnership': '🤝 合作事件',
            'product': '🚀 产品发布',
            'price_movement': '📊 价格异动',
            'other': '📌 其他事件'
        }
        
        events_text = []
        for event in events[:3]:
            type_name = event_type_names.get(event.get('type', 'other'), '📌 其他')
            title = event.get('title', '')[:50]  # 限制标题长度
            events_text.append(f"• {type_name}: {title}")
        
        return f"""
⚡ 重大事件：
{chr(10).join(events_text)}
"""
    
    def _generate_price_section(self, analysis: Dict[str, Any]) -> str:
        """生成价格提及部分"""
        price_mentions = analysis.get('price_mentions', [])
        
        if not price_mentions:
            return ""
        
        return f"""
💰 价格关注点：
{' / '.join(price_mentions[:3])}
"""
    
    def _generate_summary(self, analysis: Dict[str, Any]) -> str:
        """生成总结建议"""
        sentiment = analysis.get('sentiment', 'neutral')
        total_news = analysis.get('total_news', 0)
        
        if sentiment == 'positive':
            summary = """
📊 综合评估：
市场情绪偏向乐观，多数新闻传递积极信号。短期可能存在上涨动力，
但需关注是否存在过度乐观情绪。建议：
• 适度参与，但保持风险意识
• 关注支撑位和阻力位
• 留意获利回吐压力
"""
        elif sentiment == 'negative':
            summary = """
📊 综合评估：
市场情绪偏向悲观，负面消息占主导。短期可能面临下行压力，
需要谨慎对待。建议：
• 控制仓位，降低风险敞口
• 等待企稳信号
• 关注潜在支撑位
"""
        else:
            summary = """
📊 综合评估：
市场情绪相对平衡，多空双方暂时僵持。市场可能处于盘整阶段，
方向尚不明确。建议：
• 保持观望或小仓位试探
• 等待明确突破信号
• 关注成交量变化
"""
        
        return summary


class CryptoSwarmNewsService:
    """
    加密货币Swarm新闻服务主类
    协调三个代理完成新闻采集、分析和总结
    """
    
    def __init__(self):
        self.search_agent = NewsSearchAgent()
        self.analyzer_agent = NewsAnalyzerAgent()
        self.summarizer_agent = NewsSummarizerAgent()
        logger.info("CryptoSwarmNewsService 初始化完成")
    
    def get_crypto_news_analysis(self, symbol: str, max_news: int = 10) -> str:
        """
        获取加密货币新闻分析报告
        
        Args:
            symbol: 加密货币符号
            max_news: 最大新闻数量
            
        Returns:
            格式化的分析报告
        """
        try:
            logger.info(f"开始获取 {symbol} 的新闻分析，最大数量: {max_news}")
            
            # Step 1: 搜索代理获取新闻
            logger.info(f"Step 1: 搜索代理开始工作")
            raw_news = self.search_agent.search(symbol, max_news)
            
            if not raw_news:
                logger.warning(f"未找到关于 {symbol} 的新闻")
                return self.summarizer_agent._generate_no_news_report(symbol)
            
            # Step 2: 分析代理处理新闻
            logger.info(f"Step 2: 分析代理开始工作，处理 {len(raw_news)} 条新闻")
            analyzed_data = self.analyzer_agent.analyze(raw_news, symbol)
            
            # Step 3: 总结代理生成报告
            logger.info(f"Step 3: 总结代理生成最终报告")
            final_report = self.summarizer_agent.summarize(analyzed_data, symbol)
            
            logger.info(f"成功生成 {symbol} 的新闻分析报告")
            return final_report
            
        except Exception as e:
            logger.error(f"获取加密货币新闻分析失败: {e}")
            return f"获取 {symbol} 新闻分析时出错: {str(e)}"
    
    def test_connection(self) -> bool:
        """测试DuckDuckGo连接"""
        try:
            test_agent = NewsSearchAgent()
            results = test_agent.search("BTC", max_results=1)
            return len(results) > 0
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False


# 导出主服务类
__all__ = ['CryptoSwarmNewsService']