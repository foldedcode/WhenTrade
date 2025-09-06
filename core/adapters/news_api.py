"""
NewsAPI 数据适配器

提供全球新闻数据，支持关键词搜索、分类筛选等
"""

import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
import logging

from .base import (
    BaseDataAdapter,
    DataType,
    DataFrequency,
    DataSourceInfo,
    DataRequest,
    DataResponse,
    DataPoint
)

logger = logging.getLogger(__name__)


class NewsAPIAdapter(BaseDataAdapter):
    """NewsAPI 数据适配器"""
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "NewsAPI"
        self.api_key = config.get("api_key") if config else None
        self.session = None
        
    async def get_info(self) -> DataSourceInfo:
        """获取数据源信息"""
        return DataSourceInfo(
            id="newsapi",
            name="NewsAPI",
            description="Global news data API with 80,000+ sources",
            provider="NewsAPI.org",
            version="2.0.0",
            data_types=[
                DataType.NEWS,
                DataType.SOCIAL
            ],
            frequencies=[
                DataFrequency.REALTIME,
                DataFrequency.DAILY
            ],
            markets=["GLOBAL"],
            requires_auth=True,
            rate_limits={
                "requests_per_day_free": 100,
                "requests_per_day_paid": 250000
            },
            metadata={
                "api_docs": "https://newsapi.org/docs",
                "categories": ["business", "technology", "finance", "general"],
                "languages": ["en", "zh", "es", "fr", "de", "ja"],
                "countries": ["us", "cn", "gb", "jp", "de", "fr"]
            }
        )
    
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """认证API密钥"""
        api_key = credentials.get("api_key") or self.api_key
        if not api_key:
            logger.error("NewsAPI key not provided")
            return False
            
        self.api_key = api_key
        
        # 测试API密钥
        try:
            test_url = f"{self.BASE_URL}/top-headlines"
            params = {
                "apiKey": self.api_key,
                "sources": "bbc-news",
                "pageSize": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(test_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "ok":
                            self._authenticated = True
                            return True
        except Exception as e:
            logger.error(f"NewsAPI authentication failed: {e}")
            
        return False
    
    async def fetch_data(self, request: DataRequest) -> DataResponse:
        """获取新闻数据"""
        if not self._authenticated:
            return DataResponse(
                request=request,
                data_points=[],
                errors=["Not authenticated. Please provide API key."]
            )
        
        try:
            # 验证请求
            errors = await self.validate_request(request)
            if errors:
                return DataResponse(
                    request=request,
                    data_points=[],
                    errors=errors
                )
            
            # 创建会话
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            data_points = []
            warnings = []
            
            # 处理每个查询关键词
            for symbol in request.symbols:
                try:
                    if request.frequency == DataFrequency.REALTIME:
                        # 获取最新头条
                        points = await self._fetch_headlines(
                            symbol,
                            request.options.get("category", "business"),
                            request.options.get("country", "us")
                        )
                    else:
                        # 搜索历史新闻
                        points = await self._fetch_everything(
                            symbol,
                            request.start_date,
                            request.end_date,
                            request.options
                        )
                    
                    data_points.extend(points)
                    
                except Exception as e:
                    warnings.append(f"Failed to fetch news for {symbol}: {str(e)}")
                    logger.error(f"Error fetching news for {symbol}: {e}")
            
            return DataResponse(
                request=request,
                data_points=data_points,
                warnings=warnings,
                metadata={
                    "source": "newsapi",
                    "fetch_time": datetime.now().isoformat(),
                    "total_articles": len(data_points)
                }
            )
            
        except Exception as e:
            logger.error(f"NewsAPI fetch error: {e}")
            return DataResponse(
                request=request,
                data_points=[],
                errors=[str(e)]
            )
    
    async def _fetch_headlines(self, 
                              query: str,
                              category: str = "business",
                              country: str = "us") -> List[DataPoint]:
        """获取头条新闻"""
        url = f"{self.BASE_URL}/top-headlines"
        params = {
            "apiKey": self.api_key,
            "q": query,
            "category": category,
            "country": country,
            "pageSize": 20
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"API request failed with status {response.status}")
            
            data = await response.json()
            
            if data.get("status") != "ok":
                raise Exception(data.get("message", "Unknown error"))
        
        return self._parse_articles(query, data.get("articles", []))
    
    async def _fetch_everything(self,
                               query: str,
                               start_date: Optional[date],
                               end_date: Optional[date],
                               options: Dict[str, Any]) -> List[DataPoint]:
        """搜索所有新闻"""
        url = f"{self.BASE_URL}/everything"
        
        # 设置日期范围（NewsAPI限制：最多1个月前的数据）
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=7))
        
        # 确保不超过API限制
        max_start = date.today() - timedelta(days=30)
        if start < max_start:
            start = max_start
        
        params = {
            "apiKey": self.api_key,
            "q": query,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "sortBy": options.get("sort_by", "relevancy"),  # relevancy, popularity, publishedAt
            "language": options.get("language", "en"),
            "pageSize": min(options.get("page_size", 50), 100)
        }
        
        # 添加可选参数
        if "domains" in options:
            params["domains"] = options["domains"]
        if "exclude_domains" in options:
            params["excludeDomains"] = options["exclude_domains"]
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"API request failed with status {response.status}")
            
            data = await response.json()
            
            if data.get("status") != "ok":
                raise Exception(data.get("message", "Unknown error"))
        
        return self._parse_articles(query, data.get("articles", []))
    
    def _parse_articles(self, query: str, articles: List[Dict]) -> List[DataPoint]:
        """解析新闻文章为数据点"""
        data_points = []
        
        for article in articles:
            # 解析发布时间
            published_at = article.get("publishedAt", "")
            if published_at:
                try:
                    timestamp = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # 创建数据点
            data_point = DataPoint(
                symbol=query,
                timestamp=timestamp,
                data={
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "content": article.get("content", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "source_id": article.get("source", {}).get("id", ""),
                    "author": article.get("author", ""),
                    "image_url": article.get("urlToImage", ""),
                    
                    # 情感分析占位（可以后续集成）
                    "sentiment": None,
                    "sentiment_score": None
                },
                metadata={
                    "source": "newsapi",
                    "data_type": "news",
                    "published_at": published_at
                }
            )
            data_points.append(data_point)
        
        # 按时间排序
        data_points.sort(key=lambda x: x.timestamp, reverse=True)
        return data_points
    
    async def validate_request(self, request: DataRequest) -> List[str]:
        """验证请求参数"""
        errors = await super().validate_request(request)
        
        # NewsAPI特定验证
        if request.data_type not in [DataType.NEWS, DataType.SOCIAL]:
            errors.append(f"NewsAPI only supports NEWS and SOCIAL data types")
        
        # 检查日期范围（免费版只能获取1个月内的数据）
        if request.start_date:
            max_start = date.today() - timedelta(days=30)
            if request.start_date < max_start:
                errors.append("Free tier can only access articles from the last 30 days")
        
        return errors
    
    async def get_available_symbols(self, market: Optional[str] = None) -> List[str]:
        """返回一些常见的搜索关键词"""
        # 金融相关关键词
        finance_keywords = [
            "stock market", "cryptocurrency", "bitcoin", "ethereum",
            "federal reserve", "inflation", "earnings", "IPO",
            "merger", "acquisition", "trading", "investment",
            "economic growth", "recession", "interest rates"
        ]
        
        # 公司关键词
        company_keywords = [
            "Apple", "Google", "Microsoft", "Amazon", "Tesla",
            "Meta", "Netflix", "NVIDIA", "JPMorgan", "Goldman Sachs",
            "Berkshire Hathaway", "Bank of America", "Wells Fargo"
        ]
        
        return finance_keywords + company_keywords
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None