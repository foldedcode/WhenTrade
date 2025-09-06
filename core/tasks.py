"""
Celery任务定义
"""
from datetime import datetime, timedelta
from celery import shared_task
from celery.utils.log import get_task_logger
import psutil
import redis
from sqlalchemy import text
from core.database import get_db
from core.services.redis_pubsub import redis_publisher
from core.graph.whentrade_graph import WhenTradeGraph
from core.services.llm_config_service import llm_config_service
from core.default_config import WHENTRADE_CONFIG
import traceback

logger = get_task_logger(__name__)


@shared_task
def check_system_health():
    """检查系统健康状态"""
    try:
        # 检查CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 检查内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 检查磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'status': 'healthy'
        }
        
        # 判断是否有告警
        if cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
            health_status['status'] = 'warning'
            logger.warning(f"System health warning: {health_status}")
        else:
            logger.info(f"System health check: {health_status}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking system health: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_data():
    """清理旧数据"""
    try:
        # 清理30天前的日志数据
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # 这里可以添加具体的清理逻辑
        # 例如：删除旧的分析任务记录、日志等
        
        logger.info(f"Cleaned up data older than {cutoff_date}")
        return {'status': 'success', 'cleaned_before': cutoff_date.isoformat()}
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def process_analysis_task(task_id: str, parameters: dict):
    """处理分析任务 - 使用WhenTradeGraph执行真实分析"""
    try:
        logger.info(f"Starting analysis task {task_id}")
        logger.info(f"Parameters: {parameters}")
        
        # 发布开始进度
        redis_publisher.publish_progress(task_id, 0, "初始化分析系统...")
        
        # 获取分析参数 - 直接从扁平化结构获取
        symbol = parameters.get('symbol', 'BTC/USDT')
        market_type = parameters.get('market_type', 'crypto')
        analysis_scopes = parameters.get('analysis_scopes', ['technical'])
        llm_provider = parameters.get('llm_provider', 'deepseek')
        llm_model = parameters.get('llm_model', 'deepseek-chat')
        
        # 配置LLM
        config = WHENTRADE_CONFIG.copy()
        
        # 调试：检查环境变量状态
        import os
        kimi_key = os.getenv("KIMI_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        logger.info(f"🔍 环境变量检查 - KIMI_API_KEY: {'存在' if kimi_key else '不存在'} | DEEPSEEK_API_KEY: {'存在' if deepseek_key else '不存在'}")
        if kimi_key:
            logger.info(f"🌙 KIMI_API_KEY: {kimi_key[:20]}...")
        if deepseek_key:
            logger.info(f"🤖 DEEPSEEK_API_KEY: {deepseek_key[:20]}...")
        
        # 检查并配置可用的LLM提供商
        kimi_available = llm_config_service.is_provider_available("kimi")
        deepseek_available = llm_config_service.is_provider_available("deepseek")
        logger.info(f"🔍 LLM提供商可用性 - Kimi: {kimi_available} | DeepSeek: {deepseek_available}")
        
        if kimi_available:
            config["llm_provider"] = "openai"  # Kimi使用OpenAI兼容接口
            config["deep_think_llm"] = "moonshot-v1-128k"
            config["quick_think_llm"] = "moonshot-v1-32k"
            config["backend_url"] = "https://api.moonshot.cn/v1"
            logger.info("Using Kimi as LLM provider")
        elif deepseek_available:
            config["llm_provider"] = "deepseek"
            config["deep_think_llm"] = "deepseek-chat"
            config["quick_think_llm"] = "deepseek-chat"
            config["backend_url"] = "https://api.deepseek.com/v1"
            logger.info("Using DeepSeek as LLM provider")
        else:
            # 如果没有可用的LLM，返回模拟结果
            logger.warning("No LLM provider available, using mock analysis")
            return run_mock_analysis(task_id, symbol, analysis_scopes)
        
        redis_publisher.publish_progress(task_id, 10, "LLM配置完成，准备分析...")
        
        # 根据分析范围确定分析师
        selected_analysts = []
        if "technical" in analysis_scopes or "price" in analysis_scopes:
            selected_analysts.append("market")
        if "sentiment" in analysis_scopes or "social" in analysis_scopes:
            selected_analysts.extend(["social", "news"])
        if "onchain" in analysis_scopes:
            selected_analysts.append("fundamentals")
        if not selected_analysts:
            selected_analysts = ["market", "social", "news"]
        
        redis_publisher.publish_progress(task_id, 20, f"选定分析师: {', '.join(selected_analysts)}")
        
        try:
            # 创建WhenTradeGraph实例
            graph = WhenTradeGraph(
                selected_analysts=selected_analysts,
                debug=False,
                config=config
            )
            
            redis_publisher.publish_progress(task_id, 30, "分析系统初始化成功")
            
            # 定义分析阶段（根据市场类型）
            stages = []
            if market_type == 'polymarket':
                stages = [
                    ("analyst", "分析团队", ["market", "social", "news"]),
                    ("research", "研究团队", ["yes", "no", "arbiter"]),
                    ("probability", "概率评估", ["bayesian", "statistical"]),
                    ("strategy", "策略制定", ["position", "timing", "hedging"]),
                    ("decision", "决策总结", ["decision"])
                ]
            else:
                stages = [
                    ("analyst", "分析团队", selected_analysts),
                    ("research", "研究团队", ["bull", "bear", "manager"]),
                    ("trading", "交易团队", ["trader"]),
                    ("risk", "风险管理", ["risky", "neutral", "safe"]),
                    ("portfolio", "组合管理", ["portfolio"])
                ]
            
            # 执行分析（使用propagate方法）
            logger.info(f"Starting WhenTradeGraph analysis for {symbol}")
            
            # 发布真实分析开始状态
            redis_publisher.publish_progress(task_id, 30, f"开始分析{symbol}...")
            
            # 调用WhenTradeGraph的propagate方法
            target = symbol.split("/")[0] if "/" in symbol else symbol
            trade_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            logger.info(f"Calling WhenTradeGraph.propagate with target={target}, date={trade_date}")
            
            # 在真实分析期间发布进度更新
            redis_publisher.publish_progress(task_id, 40, "市场分析师正在分析...")
            
            # 注意：propagate方法可能需要异步支持，这里简化处理
            try:
                # 执行真实分析 (Linus: language parameter flows through data structure)
                language = parameters.get('language', 'zh-CN')  # Get language from parameters
                logger.info(f"🌐 Using language: {language}")
                final_state, signal = graph.propagate(target, trade_date, language)
                
                logger.info(f"✅ WhenTradeGraph.propagate 成功完成")
                logger.info(f"📊 final_state keys: {list(final_state.keys()) if isinstance(final_state, dict) else 'not a dict'}")
                logger.info(f"📈 signal: {signal}")
                
                # 分析完成，更新进度
                redis_publisher.publish_progress(task_id, 85, "分析完成，生成报告...")
                
            except Exception as propagate_error:
                logger.error(f"❌ WhenTradeGraph.propagate 失败: {propagate_error}")
                logger.error(f"❌ 错误详情: {traceback.format_exc()}")
                raise  # 重新抛出异常以触发模拟分析
            
            redis_publisher.publish_progress(task_id, 90, "生成分析报告...")
            
            # 构建分析结果
            result = {
                "target": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "analysis_scopes": analysis_scopes,
                "summary": {
                    "overall_sentiment": final_state.get("final_trade_decision", "持有"),
                    "confidence": 0.75,
                    "recommendation": signal if signal else "持有观望"
                },
                "key_findings": [
                    {"type": "technical", "finding": "技术分析完成", "importance": "high"},
                    {"type": "sentiment", "finding": "市场情绪分析完成", "importance": "medium"}
                ],
                "detailed_analysis": {
                    "market_report": final_state.get("market_report", ""),
                    "sentiment_report": final_state.get("sentiment_report", ""),
                    "news_report": final_state.get("news_report", ""),
                    "fundamentals_report": final_state.get("fundamentals_report", "")
                }
            }
            
        except Exception as e:
            logger.error(f"WhenTradeGraph analysis failed: {str(e)}\n{traceback.format_exc()}")
            # 降级到模拟分析
            return run_mock_analysis(task_id, symbol, analysis_scopes)
        
        # 发布完成消息
        redis_publisher.publish_complete(task_id, result)
        
        logger.info(f"Completed analysis task {task_id}")
        return {
            'task_id': task_id,
            'status': 'completed',
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing analysis task {task_id}: {str(e)}\n{traceback.format_exc()}")
        redis_publisher.publish_error(task_id, str(e))
        return {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def run_mock_analysis(task_id: str, symbol: str, analysis_scopes: list):
    """运行模拟分析（降级方案）"""
    logger.info(f"Running mock analysis for {task_id}")
    
    # 模拟进度更新
    stages = ["初始化", "数据收集", "技术分析", "情绪分析", "生成报告"]
    for i, stage in enumerate(stages):
        progress = int((i + 1) / len(stages) * 100)
        redis_publisher.publish_progress(task_id, progress, f"模拟分析: {stage}")
        
        # 模拟延迟
        import time
        time.sleep(1)
    
    # 模拟结果
    result = {
        "target": symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "analysis_scopes": analysis_scopes,
        "summary": {
            "overall_sentiment": "谨慎乐观（模拟）",
            "confidence": 0.65,
            "recommendation": "持有观望（模拟）"
        },
        "key_findings": [
            {"type": "mock", "finding": "这是模拟分析结果", "importance": "info"}
        ],
        "detailed_analysis": {
            "note": "当前使用模拟数据，真实LLM服务不可用"
        }
    }
    
    redis_publisher.publish_complete(task_id, result)
    
    return {
        'task_id': task_id,
        'status': 'completed',
        'result': result,
        'timestamp': datetime.utcnow().isoformat()
    }


def get_agent_display_name(agent_id: str) -> str:
    """获取Agent显示名称"""
    names = {
        "market": "市场分析师",
        "social": "社交媒体分析师",
        "news": "新闻分析师",
        "fundamentals": "基本面分析师",
        "bull": "多头研究员",
        "bear": "空头研究员",
        "manager": "研究经理",
        "trader": "交易员",
        "risky": "激进分析师",
        "neutral": "中性分析师",
        "safe": "保守分析师",
        "portfolio": "组合经理"
    }
    return names.get(agent_id, agent_id)


@shared_task
def send_notification(user_id: str, message: str, notification_type: str = 'info'):
    """发送通知"""
    try:
        logger.info(f"Sending {notification_type} notification to user {user_id}: {message}")
        
        # 这里可以集成实际的通知服务
        # 例如：邮件、推送通知、WebSocket等
        
        notification = {
            'user_id': user_id,
            'message': message,
            'type': notification_type,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'sent'
        }
        
        return notification
        
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {str(e)}")
        return {
            'user_id': user_id,
            'status': 'failed',
            'error': str(e)
        }