"""
市场情绪分析工具服务

提供新闻、社交媒体等情绪分析相关的工具
"""
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Reddit API
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    logger.warning("PRAW not available. Reddit functionality will be limited.")



class SentimentAnalysisTools:
    """市场情绪分析工具类"""
    
    # 加密货币符号映射
    CRYPTO_SYMBOLS = {
        'BTC': ['BTC', 'Bitcoin', 'bitcoin'],
        'ETH': ['ETH', 'Ethereum', 'ethereum'],
        'ADA': ['ADA', 'Cardano', 'cardano'],
        'SOL': ['SOL', 'Solana', 'solana'],
        'DOT': ['DOT', 'Polkadot', 'polkadot'],
        'AVAX': ['AVAX', 'Avalanche', 'avalanche'],
        'MATIC': ['MATIC', 'Polygon', 'polygon'],
        'LINK': ['LINK', 'Chainlink', 'chainlink'],
        'UNI': ['UNI', 'Uniswap', 'uniswap'],
        'ATOM': ['ATOM', 'Cosmos', 'cosmos'],
    }
    
    @classmethod
    def get_finnhub_crypto_news(
        cls,
        symbol: str,
        days_back: int = 7,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        获取FinnHub加密货币新闻
        
        Args:
            symbol: 加密货币符号
            days_back: 回溯天数
            max_results: 最大结果数
            
        Returns:
            包含新闻数据的字典
        """
        try:
            api_key = os.getenv('FINNHUB_API_KEY')
            if not api_key:
                return {"error": "FINNHUB_API_KEY not configured"}
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # FinnHub使用符号格式（如BTC, ETH）
            search_symbol = symbol.upper()
            
            # 构建API请求 - 使用通用新闻端点并筛选加密货币相关
            url = "https://finnhub.io/api/v1/news"
            params = {
                'category': 'crypto',
                'token': api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            news_data = response.json()
            
            if not news_data:
                return {
                    "symbol": symbol,
                    "news_count": 0,
                    "message": f"No news found for {symbol} in the past {days_back} days",
                    "articles": []
                }
            
            # 过滤与符号相关的新闻并限制结果数量
            articles = []
            search_terms = cls.CRYPTO_SYMBOLS.get(symbol.upper(), [symbol])
            
            for item in news_data:
                # 检查新闻是否与符号相关
                headline = item.get('headline', '').lower()
                summary = item.get('summary', '').lower()
                
                # 检查时间范围
                item_time = datetime.fromtimestamp(item.get('datetime', 0)) if item.get('datetime') else None
                if item_time and item_time < start_date:
                    continue
                
                # 检查是否包含相关关键词
                is_relevant = any(term.lower() in headline or term.lower() in summary 
                                 for term in search_terms)
                
                if is_relevant or not search_terms:  # 如果没有特定符号，返回所有加密新闻
                    articles.append({
                        "headline": item.get('headline', ''),
                        "summary": item.get('summary', ''),
                        "source": item.get('source', ''),
                        "url": item.get('url', ''),
                        "datetime": datetime.fromtimestamp(item.get('datetime', 0)).isoformat() if item.get('datetime') else None,
                        "category": item.get('category', ''),
                        "related": item.get('related', '')
                    })
                    
                    if len(articles) >= max_results:
                        break
            
            return {
                "symbol": symbol,
                "search_symbol": search_symbol,
                "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "news_count": len(articles),
                "articles": articles
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching FinnHub news for {symbol}: {e}")
            return {"error": f"Network error: {str(e)}", "symbol": symbol}
        except Exception as e:
            logger.error(f"Error fetching FinnHub news for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}
    
    
    @classmethod
    def get_crypto_reddit_sentiment(
        cls,
        symbol: str,
        days_back: int = 7,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        获取Reddit加密货币情绪数据（真实API实现）
        
        Args:
            symbol: 加密货币符号
            days_back: 回溯天数
            max_results: 最大结果数
            
        Returns:
            包含Reddit情绪数据的字典
        """
        try:
            if not PRAW_AVAILABLE:
                return {
                    "error": "PRAW library not installed",
                    "symbol": symbol,
                    "message": "Please install praw package and configure Reddit API credentials"
                }
            
            # 获取Reddit API配置
            client_id = os.getenv('REDDIT_CLIENT_ID')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET') 
            user_agent = os.getenv('REDDIT_USER_AGENT', 'whentrade/1.0')
            
            if not client_id or not client_secret:
                return {
                    "error": "Reddit API credentials not configured",
                    "symbol": symbol,
                    "required_env_vars": ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]
                }
            
            # 获取相关subreddit和搜索词
            search_terms = cls.CRYPTO_SYMBOLS.get(symbol.upper(), [symbol])
            
            # 相关subreddit列表
            subreddits = [
                'cryptocurrency',
                'bitcoin' if symbol.upper() == 'BTC' else None,
                'ethereum' if symbol.upper() == 'ETH' else None,
                'cardano' if symbol.upper() == 'ADA' else None,
                'solana' if symbol.upper() == 'SOL' else None
            ]
            subreddits = [s for s in subreddits if s]
            
            # 初始化Reddit API客户端
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            
            # 收集帖子数据
            posts_data = []
            posts_analyzed = 0
            bullish_count = 0
            bearish_count = 0 
            neutral_count = 0
            
            # 计算时间戳
            cutoff_time = datetime.now() - timedelta(days=days_back)
            
            # 遍历相关subreddit
            for subreddit_name in subreddits:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # 搜索相关帖子
                    for term in search_terms:
                        search_results = subreddit.search(
                            term, 
                            sort='new', 
                            time_filter='week',
                            limit=max_results // len(subreddits)
                        )
                        
                        for post in search_results:
                            if posts_analyzed >= max_results:
                                break
                                
                            # 检查时间范围
                            post_time = datetime.fromtimestamp(post.created_utc)
                            if post_time < cutoff_time:
                                continue
                                
                            # 简单情绪分析（基于关键词）
                            title_lower = post.title.lower()
                            text_lower = (post.selftext or "").lower()
                            full_text = title_lower + " " + text_lower
                            
                            sentiment = cls._analyze_crypto_sentiment(full_text, symbol.lower())
                            
                            if sentiment > 0.1:
                                bullish_count += 1
                            elif sentiment < -0.1:
                                bearish_count += 1
                            else:
                                neutral_count += 1
                            
                            posts_data.append({
                                "title": post.title,
                                "subreddit": subreddit_name,
                                "score": post.score,
                                "num_comments": post.num_comments,
                                "created_utc": post.created_utc,
                                "url": f"https://reddit.com{post.permalink}",
                                "sentiment": sentiment
                            })
                            
                            posts_analyzed += 1
                            
                        if posts_analyzed >= max_results:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error searching subreddit {subreddit_name}: {e}")
                    continue
            
            # 计算综合情绪分数
            total_posts = bullish_count + bearish_count + neutral_count
            sentiment_score = None
            if total_posts > 0:
                sentiment_score = (bullish_count - bearish_count) / total_posts
            
            # 排序帖子按分数
            posts_data.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                "symbol": symbol,
                "search_terms": search_terms,
                "subreddits": subreddits,
                "period": f"Past {days_back} days",
                "posts_analyzed": posts_analyzed,
                "sentiment_score": sentiment_score,
                "sentiment_summary": {
                    "bullish": bullish_count,
                    "bearish": bearish_count,
                    "neutral": neutral_count
                },
                "top_posts": posts_data[:5]  # 返回前5个热门帖子
            }
            
        except Exception as e:
            logger.error(f"Error fetching Reddit sentiment for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}
    
    @classmethod
    def _analyze_crypto_sentiment(cls, text: str, symbol: str) -> float:
        """
        简单的关键词情绪分析
        
        Args:
            text: 要分析的文本
            symbol: 加密货币符号
            
        Returns:
            情绪分数 (-1到1之间)
        """
        # 积极关键词
        positive_keywords = [
            'moon', 'bullish', 'buy', 'pump', 'rocket', 'hodl', 'long',
            'up', 'rise', 'gain', 'profit', 'bull', 'green', 'surge',
            'breakthrough', 'adoption', 'partnership', 'upgrade',
            'positive', 'optimistic', 'strong', 'growth', 'rally'
        ]
        
        # 消极关键词
        negative_keywords = [
            'crash', 'dump', 'bearish', 'sell', 'short', 'down', 'fall',
            'drop', 'loss', 'bear', 'red', 'decline', 'correction',
            'weakness', 'concern', 'problem', 'issue', 'risk', 'fear',
            'negative', 'pessimistic', 'bubble', 'scam', 'dead'
        ]
        
        text_words = text.lower().split()
        
        positive_count = sum(1 for word in text_words if any(pos in word for pos in positive_keywords))
        negative_count = sum(1 for word in text_words if any(neg in word for neg in negative_keywords))
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return 0.0  # 中性
        
        # 计算情绪分数
        sentiment = (positive_count - negative_count) / total_sentiment_words
        
        # 限制在-1到1之间
        return max(-1.0, min(1.0, sentiment))
    
    
    @classmethod
    def analyze_sentiment_batch(
        cls,
        symbol: str,
        sources: List[str] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        批量分析多个来源的市场情绪
        
        Args:
            symbol: 加密货币符号
            sources: 数据源列表 ['finnhub', 'reddit', 'google']
            days_back: 回溯天数
            
        Returns:
            综合情绪分析结果
        """
        if sources is None:
            sources = ['finnhub', 'reddit']
        
        results = {
            "symbol": symbol,
            "analysis_date": datetime.now().isoformat(),
            "period": f"Past {days_back} days",
            "sources": {}
        }
        
        # 收集各源数据
        for source in sources:
            try:
                if source == 'finnhub':
                    results["sources"]["finnhub"] = cls.get_finnhub_crypto_news(symbol, days_back)
                elif source == 'reddit':
                    results["sources"]["reddit"] = cls.get_crypto_reddit_sentiment(symbol, days_back)
                    
            except Exception as e:
                logger.error(f"Error analyzing sentiment from {source} for {symbol}: {e}")
                results["sources"][source] = {"error": str(e)}
        
        # 计算综合情绪分数（简单实现）
        total_news = sum(
            data.get("news_count", 0) if isinstance(data, dict) and "error" not in data 
            else 0 
            for data in results["sources"].values()
        )
        
        results["summary"] = {
            "total_news_articles": total_news,
            "sentiment_score": None,  # 需要实现情绪分析算法
            "recommendation": "NEUTRAL"  # 基于情绪分数给出建议
        }
        
        return results


# 便捷函数接口
def get_finnhub_crypto_news(symbol: str, days_back: int = 7, max_results: int = 10) -> Dict[str, Any]:
    """获取FinnHub加密货币新闻"""
    return SentimentAnalysisTools.get_finnhub_crypto_news(symbol, days_back, max_results)


def get_crypto_reddit_sentiment(symbol: str, days_back: int = 7, max_results: int = 10) -> Dict[str, Any]:
    """获取Reddit加密货币情绪"""
    return SentimentAnalysisTools.get_crypto_reddit_sentiment(symbol, days_back, max_results)




def analyze_sentiment_batch(symbol: str, sources: List[str] = None, days_back: int = 7) -> Dict[str, Any]:
    """批量分析市场情绪"""
    return SentimentAnalysisTools.analyze_sentiment_batch(symbol, sources, days_back)