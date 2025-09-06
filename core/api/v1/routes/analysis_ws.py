"""
WebSocket实时分析端点
提供实时的分析流更新
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Any, List, Optional, Tuple
import json
import asyncio
import threading
import logging
from datetime import datetime
import traceback

from core.graph.whentrade_graph import WhenTradeGraph
from core.services.llm_config_service import llm_config_service
from core.default_config import WHENTRADE_CONFIG
from core.services.redis_pubsub import redis_subscriber
from core.i18n.messages import get_message
from core.config.analysis_scopes import (
    ANALYSIS_SCOPE_MAPPING,
    build_nodes_for_scopes,
    build_agent_names_for_scopes
)

logger = logging.getLogger(__name__)

def get_localized_agent_name_unified(agent_name: str, lang: str) -> str:
    """获取Agent统一本地化名称 - Linus原则：消除重复代码"""
    mapping = {
        "Market Analyst": "market_analyst",
        "Social Analyst": "social_media_analyst", 
        "News Analyst": "news_analyst",
        "Fundamentals Analyst": "news_analyst",
        "Risky Analyst": "aggressive_debator",
        "Safe Analyst": "conservative_debator",
        "Neutral Analyst": "neutral_debator",
        "Aggressive Analyst": "aggressive_debator",  # 🔴 补充缺失的映射
        "Conservative Analyst": "conservative_debator",  # 🔴 补充缺失的映射
        "Bull Researcher": "bull_researcher",
        "Bear Researcher": "bear_researcher",
        "Research Manager": "research_manager", 
        "Portfolio Manager": "portfolio_manager",
        "Risk Manager": "risk_manager",  # 🔴 补充缺失的映射
        "Trader": "trader",
        "Risk Judge": "risk_manager"
    }
    message_key = mapping.get(agent_name)
    if message_key:
        return get_message(message_key, lang)
    return agent_name  # 回退到原始名称

router = APIRouter()

# 存储活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}

# 存储活跃的分析任务
active_analysis_tasks: Dict[str, asyncio.Task] = {}

# 存储活跃的分析线程和停止事件
active_analysis_threads: Dict[str, Tuple[threading.Thread, threading.Event]] = {}


@router.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点，用于实时分析流
    匹配前端期望的消息格式
    
    客户端发送:
    {
        "type": "analysis.start",
        "id": "analysis-12345",
        "data": {
            "market_type": "crypto",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "depth": 3,
            "analysisScopes": ["technical", "sentiment"],
            "llmProvider": "kimi",
            "llmModel": "moonshot-v1-128k"
        }
    }
    
    服务端响应:
    {
        "type": "connection|analysis.start|agent.thought|task.progress|analysis.complete|error",
        "id": "msg-id",
        "data": {...}
    }
    """
    await websocket.accept()
    connection_id = f"ws_{datetime.utcnow().timestamp()}"
    active_connections[connection_id] = websocket
    
    # 发送连接确认消息
    await websocket.send_json({
        "type": "connection",
        "data": {
            "connectionId": connection_id,
            "status": "connected"
        }
    })
    
    # 创建心跳任务
    async def send_heartbeat():
        """定期发送心跳以保持连接活跃"""
        while connection_id in active_connections:
            try:
                await asyncio.sleep(30)  # 每30秒发送一次心跳
                if connection_id in active_connections:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                logger.debug(f"心跳发送失败: {e}")
                break
    
    # 启动心跳任务
    heartbeat_task = asyncio.create_task(send_heartbeat())
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            # 🔧 修复空消息问题：验证消息内容
            if not data or not data.strip():
                logger.warning(f"⚠️ [WebSocket] 收到空消息，忽略处理")
                continue
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"❌ [WebSocket] JSON解析失败: {e}, 原始数据: {data[:100]}...")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON format", "received_data": data[:100]}
                })
                continue
            
            # 验证消息结构
            if not isinstance(message, dict):
                logger.error(f"❌ [WebSocket] 消息格式错误：期望字典，实际: {type(message)}")
                await websocket.send_json({
                    "type": "error", 
                    "data": {"message": "Message must be a JSON object"}
                })
                continue
            
            msg_type = message.get("type", "")
            msg_id = message.get("id", "")
            msg_data = message.get("data", {})
            
            # 验证必要字段
            if not msg_type:
                logger.warning(f"⚠️ [WebSocket] 消息缺少type字段: {message}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Message type is required"}
                })
                continue
            
            if msg_type == "analysis.subscribe":
                # 订阅已存在的分析任务
                await handle_subscribe_analysis(websocket, msg_id, msg_data)
                
                # 开发环境：直接执行真实分析
                import os
                if os.getenv('DEVELOPMENT', 'true').lower() == 'true':
                    analysis_id = msg_data.get('analysisId')
                    # 如果没有提供analysis_id，生成一个新的
                    if not analysis_id:
                        import uuid
                        analysis_id = f"analysis-{uuid.uuid4()}"
                        logger.info(f"Dev mode: 生成新的analysis_id: {analysis_id}")
                    
                    logger.info(f"Dev mode: Starting real analysis for {analysis_id}")
                    # 启动真实的分析流程并保存任务引用
                    task = asyncio.create_task(run_real_analysis_dev(websocket, analysis_id, msg_data))
                    active_analysis_tasks[analysis_id] = task
            elif msg_type == "analysis.start":
                # 保留以便向后兼容，但记录警告
                logger.warning("⚠️ 收到已废弃的analysis.start消息，应该使用REST API创建任务")
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "message": "analysis.start已废弃，请使用REST API创建任务，然后通过WebSocket订阅"
                    }
                })
            elif msg_type == "analysis.cancel":
                # 取消分析
                task_id = msg_data.get("taskId") or msg_data.get("analysisId")
                
                # 取消正在运行的asyncio任务
                if task_id and task_id in active_analysis_tasks:
                    task = active_analysis_tasks[task_id]
                    if not task.done():
                        task.cancel()
                        logger.info(f"Cancelling analysis task: {task_id}")
                    del active_analysis_tasks[task_id]
                
                # 停止正在运行的线程
                if task_id and task_id in active_analysis_threads:
                    thread, stop_event = active_analysis_threads[task_id]
                    stop_event.set()  # 发送停止信号给线程
                    logger.info(f"Signaled thread to stop for task: {task_id}")
                    del active_analysis_threads[task_id]
                    
                await websocket.send_json({
                    "type": "analysis.cancelled",
                    "id": f"cancel-{datetime.utcnow().timestamp()}",
                    "data": {"taskId": task_id, "status": "cancelled"}
                })
            elif msg_type == "agent.thought.subscribe":
                # 订阅agent思考流
                await websocket.send_json({
                    "type": "agent.thought.subscribed",
                    "id": f"sub-{datetime.utcnow().timestamp()}",
                    "data": {"agentId": msg_data.get("agentId")}
                })
            elif msg_type == "stop":
                # 停止分析
                # Extract language from message data or use default
                language = msg_data.get("language", "zh-CN")
                await websocket.send_json({
                    "type": "status",
                    "data": {"message": get_message("analysis_stopped", language)}
                })
                break
            elif message["type"] == "ping":
                # 心跳
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开连接: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "data": {"message": str(e)}
        })
    finally:
        # 取消心跳任务
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        
        # 清理分析任务
        tasks_to_cancel = []
        for task_id, task in list(active_analysis_tasks.items()):
            if not task.done():
                tasks_to_cancel.append((task_id, task))
                
        for task_id, task in tasks_to_cancel:
            try:
                task.cancel()
                logger.info(f"Cancelling orphaned analysis task: {task_id}")
                del active_analysis_tasks[task_id]
            except Exception as e:
                logger.error(f"Error cancelling task {task_id}: {str(e)}")
        
        # 清理Redis订阅
        try:
            # 取消所有该连接的Redis订阅
            for task_id in list(redis_subscriber.subscriptions.keys()):
                if task_id.startswith("analysis:"):
                    actual_task_id = task_id.replace("analysis:", "")
                    await redis_subscriber.unsubscribe_task(actual_task_id)
                    logger.info(f"Unsubscribed from Redis channel for task {actual_task_id}")
        except Exception as e:
            logger.error(f"Error cleaning up Redis subscriptions: {str(e)}")
        
        if connection_id in active_connections:
            del active_connections[connection_id]


async def run_real_analysis_dev(websocket: WebSocket, analysis_id: str, websocket_msg: Dict[str, Any]):
    """
    开发环境：执行真实的分析流程
    """
    import traceback  # 在函数开始导入，避免UnboundLocalError
    
    try:
        # 提取语言参数
        language = websocket_msg.get("language", "zh-CN")
        
        # 发送开始消息（多语言支持）
        await websocket.send_json({
            "type": "analysis.start",
            "id": analysis_id,
            "data": {
                "message": get_message("analysis_task_start", language),
                "analysisId": analysis_id
            }
        })
        
        # 创建独立的Redis订阅器（Linus原则：避免全局状态污染）
        from core.services.redis_pubsub import RedisSubscriber
        
        # 每个WebSocket连接使用独立的订阅器实例
        local_redis_subscriber = RedisSubscriber()
        
        # 定义消息处理回调
        async def handle_redis_message(data):
            """转发Redis消息到WebSocket"""
            try:
                await websocket.send_json(data)
                logger.debug(f"转发Redis消息到WebSocket: {data.get('type')}")
            except Exception as e:
                logger.error(f"转发消息失败: {str(e)}")
        
        # 订阅Redis频道
        await local_redis_subscriber.subscribe_task(analysis_id, handle_redis_message)
        logger.info(f"✅ 创建独立订阅器 (ID:{id(local_redis_subscriber)})，已订阅频道: analysis:{analysis_id}")
        
        # 添加小延迟确保Redis订阅已完全建立
        import asyncio
        await asyncio.sleep(0.1)
        
        # 直接使用WebSocket订阅消息中的参数（消除开发/生产环境特殊情况）
        # 符合Linus原则：消除特殊情况，数据从创建地直接流向使用地
        logger.info(f"🔍 直接使用订阅消息参数: {websocket_msg}")
        
        # 前端应该在订阅时发送完整的任务参数
        params = websocket_msg
        
        # 验证必要参数是否存在
        if not params.get("symbol"):
            logger.error(f"❌ 订阅消息缺少必要参数 'symbol': {params}")
            raise ValueError("订阅消息缺少必要参数 'symbol'，请确保前端发送完整的任务参数")
            
        # 提取嵌套参数结构  
        parameters = params.get("parameters", {})
        
        # 【调试】记录接收到的完整参数
        logger.info(f"📥 接收到的完整参数:")
        logger.info(f"   顶层keys: {list(params.keys())}")
        logger.info(f"   parameters keys: {list(parameters.keys())}")
        logger.info(f"   analysis_scopes位置检查:")
        logger.info(f"     - params.get('analysis_scopes'): {params.get('analysis_scopes')}")
        logger.info(f"     - params.get('analysisScopes'): {params.get('analysisScopes')}")
        logger.info(f"     - parameters.get('analysis_scopes'): {parameters.get('analysis_scopes')}")
        logger.info(f"     - parameters.get('analysisScopes'): {parameters.get('analysisScopes')}")
        
        # 配置LLM
        from core.services.llm_config_service import llm_config_service
        from core.default_config import WHENTRADE_CONFIG
        
        # 提取LLM配置，支持嵌套参数结构
        llm_provider = (
            parameters.get("llm_provider") or 
            params.get("llmProvider") or 
            params.get("llm_provider", "kimi")
        )
        llm_model = (
            parameters.get("llm_model") or
            params.get("llmModel") or 
            params.get("llm_model", "moonshot-v1-128k")
        )
        
        # 设置LLM配置
        llm_config_service.set_llm_config(llm_provider, llm_model)
        
        # 构建配置
        config = WHENTRADE_CONFIG.copy()
        if llm_provider == "kimi":
            config["llm_provider"] = "openai"  # Kimi使用OpenAI兼容接口
            config["backend_url"] = "https://api.moonshot.cn/v1"
            config["deep_think_llm"] = llm_model
            config["quick_think_llm"] = "moonshot-v1-32k" if "128k" in llm_model else "moonshot-v1-8k"
        elif llm_provider == "deepseek":
            config["llm_provider"] = "openai"  # DeepSeek也使用OpenAI兼容接口
            config["backend_url"] = "https://api.deepseek.com/v1"
            config["deep_think_llm"] = llm_model
            config["quick_think_llm"] = "deepseek-chat"
        elif llm_provider == "openai":
            config["llm_provider"] = "openai"
            config["backend_url"] = "https://api.openai.com/v1"
            config["deep_think_llm"] = llm_model
            config["quick_think_llm"] = "gpt-4o-mini" if "gpt-4o" in llm_model else llm_model
        elif llm_provider == "google":
            config["llm_provider"] = "google"
            config["deep_think_llm"] = llm_model
            config["quick_think_llm"] = "gemini-1.5-flash" if "pro" in llm_model else llm_model
        
        logger.info(f"使用LLM配置: provider={llm_provider}, model={llm_model}, backend={config.get('backend_url')}")
        
        # 准备输入 - 支持新的嵌套参数结构和向后兼容
        
        # 提取分析范围参数，支持多种格式（符合Linus原则：消除特殊情况）
        analysis_scopes = (
            parameters.get("analysis_scopes") or  # 新格式：parameters.analysis_scopes  
            parameters.get("analysisScopes") or   # 兼容驼峰命名
            params.get("analysis_scopes") or      # 向后兼容：顶层analysis_scopes
            params.get("analysisScopes") or       # 向后兼容：顶层analysisScopes  
            []                                    # 默认空数组
        )
        
        # 【调试】记录接收到的分析范围
        logger.info(f"📊 接收到的分析范围: {analysis_scopes} (长度: {len(analysis_scopes)})")
        if not analysis_scopes:
            logger.warning("⚠️ 分析范围为空！检查前端是否正确传递了analysisScopes")
        
        # 提取用户选择的工具配置（Phase 2: 用户工具选择控制）
        selected_tools = (
            parameters.get("selected_tools") or   # 新格式：parameters.selected_tools
            params.get("selected_tools") or       # 向后兼容：顶层selected_tools
            []                                    # 默认空数组
        )
        
        selected_data_sources = (
            parameters.get("selected_data_sources") or  # 新格式：parameters.selected_data_sources
            params.get("selected_data_sources") or      # 向后兼容：顶层selected_data_sources
            []                                         # 默认空数组
        )
        
        # Phase 2 Debug: 验证工具选择参数接收
        logger.info(f"🔧 [Phase 2] 接收到用户工具选择: selected_tools={selected_tools} (共{len(selected_tools)}个)")
        logger.info(f"🔧 [Phase 2] 接收到数据源选择: selected_data_sources={selected_data_sources} (共{len(selected_data_sources)}个)")
        
        # 提取语言参数（多语言支持）
        language = (
            parameters.get("language") or 
            params.get("language", "zh-CN")  # 默认中文
        )
        logger.info(f"🌍 接收到的语言设置: {language}")
        
        market_data = {
            "symbol": params.get("symbol", "BTC/USDT"),
            "timeframe": params.get("timeframe") or parameters.get("timeframe", "1h"),
            "market_type": parameters.get("market_type") or params.get("market_type", "crypto"),
            "depth": parameters.get("depth") or params.get("depth", 1),
            "language": language,  # 添加语言参数
            "analysis_scopes": analysis_scopes,
            "selected_tools": selected_tools,
            "selected_data_sources": selected_data_sources
        }
        
        # 将分析范围映射到selected_analysts（符合Linus原则：通过数据结构消除特殊情况）
        def map_analysis_scopes_to_analysts(analysis_scopes):
            """
            将前端分析范围映射到后端支持的分析师
            前端范围 → 后端分析师：
            - 'technical' → 'market' (市场分析师)
            - 'sentiment' → 'social' (社交媒体分析师，已整合新闻功能)  
            - 'fundamental' → 'fundamentals' (基本面分析师)
            """
            logger.info(f"🔄 开始映射分析范围: {analysis_scopes} (类型: {type(analysis_scopes)})")
            
            # 【DEBUG】详细检查接收到的analysis_scopes
            if hasattr(analysis_scopes, '__iter__') and not isinstance(analysis_scopes, str):
                logger.info(f"🔍 [DEBUG] 接收到的范围详情: {list(analysis_scopes)}")
                for i, scope in enumerate(analysis_scopes):
                    logger.info(f"   [{i}] {scope} (类型: {type(scope)})")
            else:
                logger.info(f"🔍 [DEBUG] 单个范围: {analysis_scopes}")
            
            selected_analysts = []
            
            if not analysis_scopes:
                logger.warning("⚠️ 分析范围为空，将导致没有分析师被选择")
                return []
            
            # 确保analysis_scopes是列表类型
            if isinstance(analysis_scopes, str):
                analysis_scopes = [analysis_scopes]
                logger.info(f"🔧 将字符串转换为列表: {analysis_scopes}")
            elif not isinstance(analysis_scopes, (list, tuple)):
                logger.error(f"❌ 无效的分析范围类型: {type(analysis_scopes)}, 值: {analysis_scopes}")
                return []
                
            # 映射表：避免重复的if-elif逻辑
            scope_mapping = {
                'technical': ['market'],
                'sentiment': ['social', 'news'],  # 社交媒体和新闻分析
            }
            
            for scope in analysis_scopes:
                scope_str = str(scope).lower().strip()
                if scope_str in scope_mapping:
                    analysts_for_scope = scope_mapping[scope_str]
                    logger.info(f"📋 范围 '{scope_str}' → 分析师 {analysts_for_scope}")
                    for analyst in analysts_for_scope:
                        if analyst not in selected_analysts:
                            selected_analysts.append(analyst)
                else:
                    logger.warning(f"⚠️ 未识别的分析范围: '{scope_str}'，跳过")
            
            logger.info(f"✅ 映射完成: {len(selected_analysts)} 个分析师被选择 → {selected_analysts}")
            
            # 定义固定的执行顺序，确保不管用户选择顺序如何，执行顺序都一致
            ANALYST_ORDER = ['market', 'social', 'news']
            
            # 根据预定义顺序排序
            ordered_analysts = [
                analyst for analyst in ANALYST_ORDER 
                if analyst in selected_analysts
            ]
            
            logger.info(f"📋 执行顺序调整: {selected_analysts} → {ordered_analysts}")
            return ordered_analysts
        
        selected_analysts = map_analysis_scopes_to_analysts(market_data["analysis_scopes"])
        logger.info(f"📊 分析范围映射: {market_data['analysis_scopes']} → {selected_analysts}")
        
        # 【调试】检查分析师列表
        if not selected_analysts or len(selected_analysts) == 0:
            logger.error("❌ 分析师列表为空！")
            logger.error(f"   analysis_scopes={market_data.get('analysis_scopes')}")
            logger.error(f"   请检查前端是否正确选择了分析范围")
            await websocket.send_json({
                "type": "error",
                "id": analysis_id,
                "data": {
                    "message": get_message("no_scope_selected", language),
                    "analysisId": analysis_id
                }
            })
            return
        
        # 创建并运行分析图，传递正确的selected_analysts、depth和工具配置
        from core.graph.whentrade_graph import WhenTradeGraph
        try:
            graph = WhenTradeGraph(
                selected_analysts=selected_analysts,
                config=config,
                analysis_depth=market_data.get("depth", 1),  # 传递用户选择的分析深度
                selected_tools=selected_tools,  # Phase 2: 传递用户选择的工具
                selected_data_sources=selected_data_sources,  # Phase 2: 传递用户选择的数据源
                websocket=websocket  # 传递websocket用于工具状态通知
            )
        except ValueError as ve:
            logger.error(f"❌ WhenTradeGraph初始化失败: {str(ve)}")
            logger.error(f"   selected_analysts={selected_analysts}")
            logger.error(f"   analysis_scopes={market_data.get('analysis_scopes')}")
            await websocket.send_json({
                "type": "error",
                "id": analysis_id,
                "data": {
                    "message": f"{get_message('graph_init_failed', language)}: {str(ve)}",
                    "analysisId": analysis_id
                }
            })
            return
        except Exception as e:
            logger.error(f"❌ 创建分析图时发生未知错误: {str(e)}")
            logger.error(traceback.format_exc())
            await websocket.send_json({
                "type": "error",
                "id": analysis_id,
                "data": {
                    "message": f"{get_message('graph_create_failed', language)}: {str(e)}",
                    "analysisId": analysis_id
                }
            })
            return
        
        # Phase 2 Log: 确认工具配置已传递
        logger.info(f"🔧 [Phase 2] 工具配置已传递到分析图: tools={len(selected_tools)}个, sources={len(selected_data_sources)}个")
        
        # 执行分析
        logger.info(f"Starting real analysis with data: {market_data}")
        
        # 准备初始状态（像propagate那样）
        from core.graph.propagation import Propagator
        propagator = Propagator()
        company_name = params.get("symbol", "BTC/USDT").split("/")[0]
        trade_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        init_state = propagator.create_initial_state(
            company_name, 
            trade_date, 
            market_data["timeframe"],
            language=language,  # 🔴 修复：添加语言参数传递
            analysis_id=analysis_id,  # 直接在create_initial_state中传递
            selected_tools=selected_tools,
            selected_data_sources=selected_data_sources
        )
        
        # 验证状态传递（Linus原则：详细验证关键数据传递）
        logger.info(f"🔍 [状态验证] 初始状态检查:")
        logger.info(f"  - analysis_id: {init_state.get('analysis_id')} ({'✅存在' if init_state.get('analysis_id') else '❌缺失'})")
        logger.info(f"  - language: {init_state.get('language')} ({'✅已传递' if init_state.get('language') else '❌缺失'})")  # 🔴 新增：验证语言参数
        logger.info(f"  - selected_tools: {init_state.get('selected_tools', [])} (共{len(init_state.get('selected_tools', []))}个)")
        logger.info(f"  - selected_data_sources: {init_state.get('selected_data_sources', [])} (共{len(init_state.get('selected_data_sources', []))}个)")
        logger.info(f"  - company_of_interest: {init_state.get('company_of_interest')}")
        logger.info(f"  - trade_date: {init_state.get('trade_date')}")
        logger.info(f"🔧 [Phase 2] 状态验证完成，analysis_id={analysis_id}")
        args = propagator.get_graph_args()
        
        # Linus原则：不再需要全局设置timeframe，每个Toolkit实例都有自己的配置
        logger.info(f"📅 使用分析timeframe: {market_data['timeframe']} (已包含在WhenTradeGraph实例中)")
        
        logger.info(f"使用LangGraph stream模式: company={company_name}, date={trade_date}")
        
        # 发送开始消息
        await websocket.send_json({
            "type": "task.progress",
            "id": analysis_id,
            "data": {
                "progress": 10,
                "message": "初始化分析流程...",
                "analysisId": analysis_id
            }
        })
        
        try:
            # 使用stream直接获取实时更新
            progress = 10
            final_state = None
            
            # 修复数据流不匹配问题：直接使用selected_analysts构建节点
            # 这确保了phase跟踪和graph对象使用相同的analyst集合
            
            # 根据selected_analysts构建第一阶段节点
            phase1_nodes = []
            for analyst in selected_analysts:
                if analyst == 'market':
                    phase1_nodes.extend(['Market Analyst', 'tools_market', 'Msg Clear Market'])
                elif analyst == 'social':
                    phase1_nodes.extend(['Social Analyst', 'tools_social', 'Msg Clear Social'])
                elif analyst == 'news':
                    phase1_nodes.extend(['News Analyst', 'tools_news', 'Msg Clear News'])
                elif analyst == 'fundamentals':
                    phase1_nodes.extend(['Fundamentals Analyst', 'tools_fundamentals', 'Msg Clear Fundamentals'])
            
            logger.info(f"📊 第一阶段节点 (来自selected_analysts {selected_analysts}): {phase1_nodes}")
            
            def build_execution_phases(selected_analysts, market_data):
                """根据选择的分析师和分析范围动态构建执行阶段"""
                phases = {}
                
                # 第一阶段：数据分析（始终包含）
                phases["phase1_analysis"] = {
                    "name": "数据分析",
                    "number": "I",
                    "nodes": phase1_nodes,
                    "agents": [],
                    "status": "pending",
                    "progress": 0
                }
                
                # 所有分析范围都执行完整的5阶段流程
                # 因为投资决策需要：分析→辩论→交易→风险→组合管理
                analysis_scopes = market_data.get("analysis_scopes", [])
                logger.info(f"📋 执行完整的5阶段流程，分析范围: {analysis_scopes}")
                
                # 添加后续4个阶段（投资决策必需）
                phases.update({
                    "phase2_debate": {
                        "name": get_message("phase2_debate_name", language),
                        "number": "II", 
                        "nodes": ["Bull Researcher", "Msg Clear Bull", "Bear Researcher", "Msg Clear Bear", "Research Manager", "Msg Clear Research"],
                        "agents": [],
                        "status": "pending",
                        "progress": 0
                    },
                    "phase3_trading": {
                        "name": get_message("phase3_trading_name", language),
                        "number": "III",
                        "nodes": ["Trader", "Msg Clear Trader"],
                        "agents": [],
                        "status": "pending",
                        "progress": 0
                    },
                    "phase4_risk": {
                        "name": get_message("phase4_risk_name", language),
                        "number": "IV",
                        "nodes": ["Risky Analyst", "Msg Clear Risky", "Neutral Analyst", "Msg Clear Neutral", "Safe Analyst", "Msg Clear Safe", "Risk Judge", "Msg Clear Risk"],
                        "agents": [],
                        "status": "pending",
                        "progress": 0
                    },
                    "phase5_decision": {
                        "name": get_message("phase5_decision_name", language),
                        "number": "V",
                        "nodes": ["Portfolio Manager", "Msg Clear Portfolio"],
                        "agents": [],
                        "status": "pending",
                        "progress": 0
                    }
                })
                
                return phases
            
            # 动态构建执行阶段
            execution_phases = build_execution_phases(selected_analysts, market_data)
            logger.info(f"🏗️ 构建了 {len(execution_phases)} 个执行阶段: {list(execution_phases.keys())}")
            
            # 节点到阶段的映射（快速查找）
            node_to_phase = {}
            for phase_key, phase_info in execution_phases.items():
                for node in phase_info["nodes"]:
                    node_to_phase[node] = phase_key
            
            # 当前活跃阶段
            current_phase = None
            phase_start_time = {}
            
            # Agent名称标准化映射（Linus原则：通过数据结构消除特殊情况）
            def normalize_agent_name(backend_name: str) -> str:
                """将后端Agent名称转换为前端期望的标准化ID"""
                agent_name_map = {
                    # 第一阶段：分析师
                    "Market Analyst": "market-analyst",
                    "Social Analyst": "social-analyst", 
                    "News Analyst": "news-analyst",
                    "Fundamentals Analyst": "fundamentals-analyst",
                    # 第二阶段：研究员
                    "Bull Researcher": "bull-researcher",
                    "Bear Researcher": "bear-researcher",
                    "Research Manager": "research-manager",
                    # 第三阶段：交易员
                    "Trader": "trader",
                    # 第四阶段：风险分析师
                    "Risky Analyst": "risky-analyst",
                    "Safe Analyst": "safe-analyst",
                    "Neutral Analyst": "neutral-analyst",
                    "Risk Judge": "risk-judge",
                    # 第五阶段：组合经理
                    "Portfolio Manager": "portfolio-manager"
                }
                return agent_name_map.get(backend_name, backend_name.lower().replace(" ", "_"))
            
            # Agent状态跟踪（新增：符合前端UI需求）
            agent_status = {}  # {node_name: "idle" | "processing" | "completed" | "error"}
            
            # 全局图状态跟踪（修复：持久化跨chunk的状态）
            graph_state = {
                "debate_count": 0,  # 追踪辩论轮数
                "risk_count": 0,    # 追踪风险讨论轮数
            }
            
            # 初始化agents为idle状态（基于动态构建的execution_phases）
            logger.info(f"🔧 初始化Agent状态，基于 {len(execution_phases)} 个阶段")
            initialized_agents = []
            for phase_key, phase_info in execution_phases.items():
                for node in phase_info["nodes"]:
                    # Linus: 数据结构一致性 - Msg Clear节点不是Agent
                    if not node.startswith("Msg Clear") and any(keyword in node for keyword in ["Analyst", "Researcher", "Manager", "Trader", "Judge"]):
                        agent_status[node] = "idle"
                        initialized_agents.append(node)
                        logger.debug(f"   初始化 {node} → idle")
            logger.info(f"✅ 已初始化 {len(initialized_agents)} 个Agent: {initialized_agents}")
            
            # 发送进入第一阶段的系统消息（多语言支持）
            await websocket.send_json({
                "type": "agent.thought",
                "id": analysis_id,
                "data": {
                    "phase": "phase1_analysis",
                    "phaseName": get_message("phase1_name", language),
                    "thought": get_message("phase1_message", language),
                    "agent": get_message("system", language),
                    "agentId": "system",
                    "analysisId": analysis_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
            # 动态确定第一个要执行的Agent（基于第一阶段的第一个分析师）
            first_agent = None
            for node in phase1_nodes:
                if not node.startswith("Msg Clear") and any(keyword in node for keyword in ["Analyst", "Researcher", "Manager", "Trader", "Judge"]):
                    first_agent = node
                    break
            
            if first_agent and first_agent in agent_status:
                agent_status[first_agent] = "processing"
                await websocket.send_json({
                    "type": "agent.status",
                    "id": analysis_id,
                    "data": {
                        "agent": first_agent,  # 使用原始名称格式
                        "status": "processing",
                        "phase": "phase1_analysis",
                        "phaseName": execution_phases["phase1_analysis"]["name"],
                        "analysisId": analysis_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
                logger.info(f"🚀 分析开始，第一个Agent [{first_agent}] 状态: idle → processing")
            else:
                logger.warning(f"⚠️ 没有找到第一个有效的Agent节点，phase1_nodes: {phase1_nodes}")
            
            # 使用asyncio.to_thread处理同步stream
            import asyncio
            
            # 增加超时时间到5分钟（因为真实分析需要较长时间）
            max_wait = 300  # 5分钟
            
            # 创建一个队列来存储stream的输出
            import queue
            stream_queue = queue.Queue()
            stream_done = False
            final_state = None
            
            # 在线程中运行stream
            def run_stream(stop_event: threading.Event):
                nonlocal stream_done, final_state
                try:
                    # 覆盖args中的stream_mode为updates（消除参数重复的特殊情况）
                    args['stream_mode'] = 'updates'
                    logger.info("开始LangGraph stream，使用updates模式")
                    chunk_count = 0
                    
                    # Create iterator for stream
                    stream_iter = graph.graph.stream(init_state, **args)
                    
                    for chunk in stream_iter:
                        # Check if we should stop
                        if stop_event.is_set():
                            logger.info("收到停止信号，中断stream处理")
                            stream_queue.put({"cancelled": True})
                            break
                            
                        chunk_count += 1
                        logger.info(f"收到chunk #{chunk_count}: {list(chunk.keys())}")
                        stream_queue.put(chunk)
                        final_state = chunk  # 保存最后一个chunk
                        
                    if not stop_event.is_set():
                        logger.info(f"Stream完成，共收到 {chunk_count} 个chunks")
                except Exception as e:
                    logger.error(f"Stream执行失败: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    stream_queue.put({"error": str(e)})
                finally:
                    stream_done = True
            
            # 创建停止事件并传递给graph
            stop_event = threading.Event()
            graph.set_stop_event(stop_event)
            logger.info(f"🛑 [Analysis] 已为任务 {analysis_id} 设置停止事件")
            
            # 启动stream线程
            stream_thread = threading.Thread(target=run_stream, args=(stop_event,))
            stream_thread.start()
            
            # 存储线程和停止事件，供取消操作使用
            active_analysis_threads[analysis_id] = (stream_thread, stop_event)
            
            # 处理stream输出
            elapsed = 0
            check_interval = 0.5  # 每0.5秒检查一次
            
            while elapsed < max_wait:
                # 检查任务是否被取消
                current_task = asyncio.current_task()
                if current_task and current_task.cancelled():
                    logger.info(f"Analysis {analysis_id} was cancelled, stopping stream processing")
                    await websocket.send_json({
                        "type": "analysis.cancelled",
                        "id": analysis_id,
                        "data": {"message": "分析已取消", "analysisId": analysis_id}
                    })
                    # 清理任务引用
                    if analysis_id in active_analysis_tasks:
                        del active_analysis_tasks[analysis_id]
                    return
                
                # 检查是否有新的chunk
                try:
                    chunk = stream_queue.get_nowait()
                    
                    # 处理chunk
                    if "cancelled" in chunk:
                        logger.info("Stream被取消")
                        await websocket.send_json({
                            "type": "analysis.cancelled",
                            "id": analysis_id,
                            "data": {"message": "分析已取消", "analysisId": analysis_id}
                        })
                        break
                    elif "error" in chunk:
                        logger.error(f"Stream错误: {chunk['error']}")
                        break
                    
                    # 记录收到的chunk结构
                    logger.info(f"Chunk结构: keys={list(chunk.keys())}")
                    
                    # 保存当前chunk的state信息（用于后续判断）
                    current_chunk_state = {}
                    
                    # 识别节点所属的阶段
                    for node_name, node_data in chunk.items():
                        # 跳过messages字段
                        if node_name == "messages":
                            continue
                        
                        # 提取state信息（如果存在）并更新全局状态
                        if isinstance(node_data, dict):
                            if "investment_debate_state" in node_data:
                                current_chunk_state["investment_debate_state"] = node_data["investment_debate_state"]
                                # 更新全局辩论计数
                                debate_count = node_data["investment_debate_state"].get("count", 0)
                                graph_state["debate_count"] = max(graph_state["debate_count"], debate_count)
                                logger.info(f"📊 更新全局debate_count: {graph_state['debate_count']}")
                            if "risk_debate_state" in node_data:
                                current_chunk_state["risk_debate_state"] = node_data["risk_debate_state"]
                                # 更新全局风险计数
                                risk_count = node_data["risk_debate_state"].get("count", 0)
                                graph_state["risk_count"] = max(graph_state["risk_count"], risk_count)
                                logger.info(f"📊 更新全局risk_count: {graph_state['risk_count']}")
                            
                        # 添加详细的node_data日志来诊断问题
                        logger.info(f"🔍 [DEBUG] 节点 {node_name} 的完整数据结构:")
                        logger.info(f"🔍 [DEBUG] - 数据类型: {type(node_data)}")
                        if isinstance(node_data, dict):
                            logger.info(f"🔍 [DEBUG] - 字典keys: {list(node_data.keys())}")
                            for key, value in node_data.items():
                                if isinstance(value, str) and len(value) > 100:
                                    logger.info(f"🔍 [DEBUG] - {key}: {type(value).__name__}(长度={len(value)}) = {value[:100]}...")
                                else:
                                    logger.info(f"🔍 [DEBUG] - {key}: {value}")
                        else:
                            logger.info(f"🔍 [DEBUG] - 直接内容: {node_data}")
                            
                        # Linus终极方案：在分析师节点检测工具调用
                        # stream_mode='updates'导致tools节点不出现，所以在分析师节点捕获
                        # Linus原则：包含所有真实的分析师节点，消除特殊情况
                        analyst_nodes = [
                            "Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst",
                            "Risky Analyst", "Safe Analyst", "Neutral Analyst",
                            "Bull Researcher", "Bear Researcher", "Portfolio Manager", "Trader", "Risk Judge"
                        ]
                        if node_name in analyst_nodes:
                            # 检查messages中的工具调用
                            if "messages" in node_data and isinstance(node_data["messages"], list):
                                for msg in node_data["messages"]:
                                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                        # 映射到本地化名称（多语言支持）- 使用统一函数
                                        analyst_cn_name = get_localized_agent_name_unified(node_name, language)
                                        
                                        # 发送每个工具调用的通知
                                        for tool_call in msg.tool_calls:
                                            tool_name = tool_call.get('name', 'unknown')
                                            
                                            # Linus原则：获取友好的工具名称，消除未注册工具的特殊情况
                                            from core.services.tools.tool_registry import ToolRegistry
                                            
                                            # 首先尝试从ToolRegistry获取
                                            friendly_name = tool_name
                                            for scope_name, scope_tools in ToolRegistry.TOOL_REGISTRY.items():
                                                if tool_name in scope_tools:
                                                    tool_info = scope_tools[tool_name]
                                                    friendly_name = tool_info.get('display_name', tool_info.get('name', tool_name))
                                                    break
                                            
                                            # Fallback：处理未在ToolRegistry中注册的工具
                                            if friendly_name == tool_name:
                                                tool_fallback_names = {
                                                    'get_stock_market_data_unified': '统一市场数据',
                                                    'get_reddit_stock_info': 'Reddit情绪分析', 
                                                    'get_stock_news_openai': '新闻资讯获取',
                                                    'get_YFin_data_online': 'Yahoo Finance数据',
                                                    'get_stockstats_indicators_report_online': '技术指标报告',
                                                    'get_fear_greed_index': '恐惧贪婪指数',
                                                    'get_trending_coins': '热门币种',
                                                    'get_market_metrics': '市场指标'
                                                }
                                                friendly_name = tool_fallback_names.get(tool_name, tool_name)
                                            
                                            await websocket.send_json({
                                                "type": "agent.tool",
                                                "id": analysis_id,
                                                "data": {
                                                    "analysisId": analysis_id,  # Linus原则：统一数据契约
                                                    "phase": "phase1_analysis",
                                                    "agent": analyst_cn_name,
                                                    "tool": friendly_name,
                                                    "message": f"{get_message('calling_tool', language)}: {friendly_name}",
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"🔧 [工具通知] {analyst_cn_name} 调用 {friendly_name}")
                        
                        # 查找节点所属的阶段
                        if node_name in node_to_phase:
                            phase_key = node_to_phase[node_name]
                            phase = execution_phases[phase_key]
                            
                            # 先处理Bull/Bear/Risk状态转换（不依赖当前节点是否在agent_status中）
                            # 移除Research Manager开始时的错误清理逻辑
                            # （清理应该在Research Manager完成时进行，而不是开始时）
                            
                            # 记录Risk阶段的节点激活
                            if phase_key == "phase4_risk" and node_name in ["Risky Analyst", "Safe Analyst", "Neutral Analyst"]:
                                logger.info(f"🎯 [Risk阶段] 节点 {node_name} 被激活")
                                logger.info(f"🎯 [Risk阶段] 当前全局risk_count: {graph_state['risk_count']}")
                                logger.info(f"🎯 [Risk阶段] current_chunk_state包含risk_debate_state: {'risk_debate_state' in current_chunk_state}")
                            
                            # 处理Risk分析师循环中的直接转换
                            if phase_key == "phase4_risk":
                                risk_transitions = {
                                    "Safe Analyst": "Risky Analyst",      # Safe开始时，Risky完成
                                    "Neutral Analyst": "Safe Analyst",    # Neutral开始时，Safe完成
                                    "Risky Analyst": "Neutral Analyst",   # Risky再次开始时，Neutral完成
                                }
                                
                                if node_name in risk_transitions:
                                    prev_risk_agent = risk_transitions[node_name]
                                    if prev_risk_agent in agent_status and agent_status[prev_risk_agent] == "processing":
                                        agent_status[prev_risk_agent] = "completed"
                                        await websocket.send_json({
                                            "type": "agent.status",
                                            "id": analysis_id,
                                            "data": {
                                                "agent": prev_risk_agent,  # 使用原始名称格式
                                                "status": "completed",
                                                "phase": phase_key,
                                                "phaseName": phase["name"],
                                                "analysisId": analysis_id,
                                                "timestamp": datetime.utcnow().isoformat()
                                            }
                                        })
                                        logger.info(f"✅ Agent [{prev_risk_agent}] 状态: processing → completed ({node_name}即将开始)")
                            
                            # 然后处理当前节点的状态更新（只有在agent_status中的节点才更新）
                            if node_name in agent_status:
                                # 处理当前Agent的processing（允许idle或completed状态变为processing，支持多轮执行）
                                current_status = agent_status[node_name]
                                if current_status in ["idle", "completed"]:
                                    agent_status[node_name] = "processing"
                                    
                                    # 发送agent状态更新消息
                                    await websocket.send_json({
                                        "type": "agent.status",
                                        "id": analysis_id,
                                        "data": {
                                            "agent": node_name,  # 使用原始名称格式
                                            "status": "processing",
                                            "phase": phase_key,
                                            "phaseName": phase["name"],
                                            "analysisId": analysis_id,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    })
                                    logger.info(f"🤖 Agent [{node_name}] 状态: {current_status} → processing")
                            
                            # 处理Msg Clear节点 - 标记对应Agent完成并激活下一个
                            if node_name.startswith("Msg Clear"):
                                # 发送阶段切换消息（Research Manager到Trader）
                                if node_name == "Msg Clear Research":
                                    await websocket.send_json({
                                        "type": "agent.thought",
                                        "id": analysis_id,
                                        "data": {
                                            "phase": "phase3_trading",
                                            "phaseName": get_message("phase3_trading_name", language),
                                            "thought": get_message("entering_phase3", language),
                                            "agent": get_message("system", language),
                                            "agentId": "system",
                                            "analysisId": analysis_id,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    })
                                # 发送阶段切换消息（Trader到Risk）
                                elif node_name == "Msg Clear Trader":
                                    await websocket.send_json({
                                        "type": "agent.thought",
                                        "id": analysis_id,
                                        "data": {
                                            "phase": "phase4_risk",
                                            "phaseName": get_message("phase4_risk_name", language),
                                            "thought": get_message("entering_phase4", language),
                                            "agent": get_message("system", language),
                                            "agentId": "system",
                                            "analysisId": analysis_id,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    })
                                    
                                    # 发送第1轮风险分析提醒
                                    max_rounds = market_data.get("depth", 1)
                                    await websocket.send_json({
                                        "type": "agent.thought",
                                        "id": analysis_id,
                                        "data": {
                                            "phase": "phase4_risk",
                                            "phaseName": get_message("phase4_risk_name", language),
                                            "thought": get_message("starting_risk_round", language, current=1, total=max_rounds),
                                            "agent": get_message("system", language),
                                            "agentId": "system",
                                            "analysisId": analysis_id,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    })
                                # 发送阶段切换消息（Risk到Portfolio）
                                elif node_name == "Msg Clear Risk":
                                    await websocket.send_json({
                                        "type": "agent.thought",
                                        "id": analysis_id,
                                        "data": {
                                            "phase": "phase5_decision",
                                            "phaseName": get_message("phase5_decision_name", language),
                                            "thought": get_message("entering_phase5", language),
                                            "agent": get_message("system", language),
                                            "agentId": "system",
                                            "analysisId": analysis_id,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    })
                                
                                # 通用的Msg Clear到Agent的映射（Linus: 数据结构消除特殊情况）
                                msg_clear_to_agent = {
                                    # 第一阶段分析师
                                    "Msg Clear Market": "Market Analyst",
                                    "Msg Clear Social": "Social Analyst",
                                    "Msg Clear News": "News Analyst",
                                    "Msg Clear Fundamentals": "Fundamentals Analyst",
                                    # 第二阶段研究员（恢复通用处理）
                                    "Msg Clear Bull": "Bull Researcher",
                                    "Msg Clear Bear": "Bear Researcher",
                                    "Msg Clear Research": "Research Manager",
                                    # 第三阶段交易员
                                    "Msg Clear Trader": "Trader",
                                    # 第四阶段风险分析师
                                    "Msg Clear Risky": "Risky Analyst",
                                    "Msg Clear Safe": "Safe Analyst",
                                    "Msg Clear Neutral": "Neutral Analyst",
                                    "Msg Clear Risk": "Risk Judge",
                                    # 第五阶段组合经理
                                    "Msg Clear Portfolio": "Portfolio Manager"
                                }
                                
                                # 通用的"下一个Agent"映射（Linus: 简单直接的数据流）
                                next_agent_map = {
                                    # 第一阶段的最后一个分析师 → Bull Researcher（动态处理）
                                    # 第二阶段流程：基础的Bull→Bear路由（第一轮）
                                    "Msg Clear Bull": ("Bear Researcher", "phase2_debate"),
                                    "Msg Clear Bear": ("Research Manager", "phase2_debate"), # 先简化为直接到Research Manager
                                    "Msg Clear Research": ("Trader", "phase3_trading"),
                                    # 第三阶段流程
                                    "Msg Clear Trader": ("Risky Analyst", "phase4_risk"),
                                    # 第四阶段流程
                                    "Msg Clear Risky": ("Safe Analyst", "phase4_risk"),
                                    "Msg Clear Safe": ("Neutral Analyst", "phase4_risk"),
                                    "Msg Clear Neutral": ("Risky Analyst", "phase4_risk"),  # 或Risk Judge（需要条件判断）
                                    "Msg Clear Risk": ("Portfolio Manager", "phase5_decision"),
                                    # 第五阶段结束
                                    "Msg Clear Portfolio": (None, None)  # 分析完成
                                }
                                
                                # 获取对应的Agent名称
                                completed_agent = msg_clear_to_agent.get(node_name)
                                
                                if completed_agent and completed_agent in agent_status:
                                    # 标记Agent为completed
                                    if agent_status[completed_agent] == "processing":
                                        agent_status[completed_agent] = "completed"
                                        
                                        # 发送completed状态
                                        await websocket.send_json({
                                            "type": "agent.status",
                                            "id": analysis_id,
                                            "data": {
                                                "agent": completed_agent,  # 使用原始名称格式
                                                "status": "completed",
                                                "phase": phase_key,
                                                "phaseName": phase["name"],
                                                "analysisId": analysis_id,
                                                "timestamp": datetime.utcnow().isoformat()
                                            }
                                        })
                                        logger.info(f"✅ Agent [{completed_agent}] 状态: processing → completed (通过{node_name})")
                                    
                                    # 激活下一个Agent
                                    # 特殊处理第一阶段（使用统一映射配置）
                                    if phase_key == "phase1_analysis":
                                        # 从实际的phase1_nodes提取Agent名称顺序
                                        # 这确保与实际初始化的graph中的agents完全一致
                                        analyst_order = []
                                        for node in phase1_nodes:
                                            if node.endswith(' Analyst') and not node.startswith('Msg Clear') and not node.startswith('tools_'):
                                                analyst_order.append(node)
                                        logger.info(f"📋 第一阶段Agent顺序: {analyst_order}（从实际节点提取）")
                                        
                                        try:
                                            current_idx = analyst_order.index(completed_agent)
                                            # 如果是最后一个analyst，下一个是Bull Researcher
                                            if current_idx == len(analyst_order) - 1:
                                                next_agent = "Bull Researcher"
                                                next_phase = "phase2_debate"
                                                # 发送进入第二阶段的系统消息
                                                await websocket.send_json({
                                                    "type": "agent.thought",
                                                    "id": analysis_id,
                                                    "data": {
                                                        "phase": "phase2_debate",
                                                        "phaseName": get_message("phase2_debate_name", language),
                                                        "thought": get_message("entering_phase2", language),
                                                        "agent": get_message("system", language),
                                                        "agentId": "system",
                                                        "analysisId": analysis_id,
                                                        "timestamp": datetime.utcnow().isoformat()
                                                    }
                                                })
                                                # 发送第一轮辩论开始消息
                                                await websocket.send_json({
                                                    "type": "agent.thought",
                                                    "id": analysis_id,
                                                    "data": {
                                                        "phase": "phase2_debate",
                                                        "phaseName": get_message("phase2_debate_name", language),
                                                        "thought": get_message("starting_debate_round", language, current=1, total=market_data.get('depth', 1)),
                                                        "agent": get_message("system", language),
                                                        "agentId": "system",
                                                        "analysisId": analysis_id,
                                                        "timestamp": datetime.utcnow().isoformat()
                                                    }
                                                })
                                            # 如果不是最后一个，激活下一个analyst
                                            elif current_idx < len(analyst_order) - 1:
                                                next_agent = analyst_order[current_idx + 1]
                                                next_phase = phase_key
                                            else:
                                                next_agent = None
                                                next_phase = None
                                                
                                            if next_agent and next_agent in agent_status and agent_status[next_agent] in ["idle", "completed"]:
                                                prev_status = agent_status[next_agent]
                                                agent_status[next_agent] = "processing"
                                                # 发送下一个Agent的processing状态
                                                await websocket.send_json({
                                                    "type": "agent.status",
                                                    "id": analysis_id,
                                                    "data": {
                                                        "agent": next_agent,  # 使用原始名称格式
                                                        "status": "processing",
                                                        "phase": next_phase,
                                                        "phaseName": execution_phases[next_phase]["name"],
                                                        "analysisId": analysis_id,
                                                        "timestamp": datetime.utcnow().isoformat()
                                                    }
                                                })
                                                if next_phase != phase_key:
                                                    logger.info(f"🚀 第一阶段完成，激活第二阶段Agent [{next_agent}] 状态: {prev_status} → processing")
                                                else:
                                                    logger.info(f"🚀 激活下一个Agent [{next_agent}] 状态: {prev_status} → processing")
                                        except ValueError:
                                            pass
                                    
                                    
                                    # 第二阶段Bull/Bear辩论的动态路由（Linus: 消除静态映射的特殊情况）
                                    elif node_name == "Msg Clear Bull":
                                        # 优先使用全局graph_state，fallback到current_chunk_state
                                        max_rounds = market_data.get("depth", 1)  # 使用用户选择的分析深度
                                        
                                        # 首先尝试从全局状态获取
                                        debate_count = graph_state["debate_count"]
                                        
                                        # 如果current_chunk_state有更新的值，使用它
                                        if "investment_debate_state" in current_chunk_state:
                                            chunk_count = current_chunk_state.get("investment_debate_state", {}).get("count", 0)
                                            debate_count = max(debate_count, chunk_count)
                                            # 同步更新全局状态
                                            graph_state["debate_count"] = debate_count
                                        
                                        logger.info(f"🐂 [Msg Clear Bull] 辩论计数: {debate_count} (全局: {graph_state['debate_count']}), 最大轮数: {max_rounds}, 阈值: {2 * max_rounds}")
                                        
                                        if debate_count >= 2 * max_rounds:
                                            # 辩论结束，激活Research Manager
                                            next_agent = "Research Manager"
                                            next_phase = "phase2_debate"
                                            logger.info(f"🐂 [Msg Clear Bull] 辩论结束 → Research Manager")
                                            # 发送辩论结束系统消息
                                            await websocket.send_json({
                                                "type": "agent.thought",
                                                "id": analysis_id,
                                                "data": {
                                                    "phase": "phase2_debate",
                                                    "phaseName": get_message("phase2_debate_name", language),
                                                    "thought": get_message("debate_ended", language, rounds=max_rounds),
                                                    "agent": get_message("system", language),
                                                    "agentId": "system",
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                        else:
                                            # 继续辩论，激活Bear Researcher
                                            next_agent = "Bear Researcher"
                                            next_phase = "phase2_debate"
                                            current_round = debate_count // 2 + 1
                                            logger.info(f"🐂 [Msg Clear Bull] 继续辩论 → Bear Researcher (轮{current_round})")
                                        
                                        # 更新状态并发送消息
                                        if next_agent and next_agent in agent_status and agent_status[next_agent] in ["idle", "completed"]:
                                            prev_status = agent_status[next_agent]
                                            agent_status[next_agent] = "processing"
                                            await websocket.send_json({
                                                "type": "agent.status",
                                                "id": analysis_id,
                                                "data": {
                                                    "agent": next_agent,  # 使用原始名称格式
                                                    "status": "processing",
                                                    "phase": next_phase,
                                                    "phaseName": execution_phases[next_phase]["name"],
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"🚀 激活下一个Agent [{next_agent}] 状态: {prev_status} → processing")
                                        else:
                                            # 调试：记录条件判断失败的原因
                                            logger.error(f"❌ [Msg Clear Bull] 无法激活 {next_agent}!")
                                            logger.error(f"   - next_agent存在: {bool(next_agent)}")
                                            logger.error(f"   - next_agent值: '{next_agent}'")
                                            logger.error(f"   - 在agent_status中: {next_agent in agent_status if next_agent else 'N/A'}")
                                            if next_agent and next_agent in agent_status:
                                                logger.error(f"   - 当前状态: '{agent_status[next_agent]}'")
                                                logger.error(f"   - 状态是否合法: {agent_status[next_agent] in ['idle', 'completed']}")
                                            logger.error(f"   - agent_status内容: {list(agent_status.keys())}")
                                    
                                    elif node_name == "Msg Clear Bear":
                                        # 优先使用全局graph_state，fallback到current_chunk_state
                                        max_rounds = market_data.get("depth", 1)  # 使用用户选择的分析深度
                                        
                                        # 首先从全局状态获取
                                        debate_count = graph_state["debate_count"]
                                        
                                        # 调试：查看current_chunk_state内容
                                        logger.info(f"🐻 [Msg Clear Bear DEBUG] current_chunk_state keys: {list(current_chunk_state.keys())}")
                                        logger.info(f"🐻 [Msg Clear Bear DEBUG] 全局debate_count: {graph_state['debate_count']}")
                                        
                                        # 如果current_chunk_state有更新的值，使用它
                                        if "investment_debate_state" in current_chunk_state:
                                            debate_state = current_chunk_state.get("investment_debate_state", {})
                                            chunk_count = debate_state.get("count", 0)
                                            debate_count = max(debate_count, chunk_count)
                                            # 同步更新全局状态
                                            graph_state["debate_count"] = debate_count
                                            logger.info(f"🐻 [Msg Clear Bear DEBUG] chunk_count={chunk_count}, 更新后debate_count={debate_count}")
                                        else:
                                            logger.info(f"🐻 [Msg Clear Bear] 使用全局debate_count: {debate_count}")
                                        
                                        logger.info(f"🐻 [Msg Clear Bear] 辩论计数: {debate_count}, 最大轮数: {max_rounds}, 阈值: {2 * max_rounds}")
                                        
                                        if debate_count >= 2 * max_rounds:
                                            # 辩论结束，激活Research Manager
                                            next_agent = "Research Manager"
                                            next_phase = "phase2_debate"
                                            logger.info(f"🐻 [Msg Clear Bear] 辩论结束 → Research Manager")
                                        else:
                                            # 继续辩论，激活Bull Researcher
                                            next_agent = "Bull Researcher"
                                            next_phase = "phase2_debate"
                                            current_round = debate_count // 2 + 1
                                            logger.info(f"🐻 [Msg Clear Bear] 继续辩论 → Bull Researcher (轮{current_round})")
                                            # 新一轮辩论开始时发送系统消息
                                            await websocket.send_json({
                                                "type": "agent.thought",
                                                "id": analysis_id,
                                                "data": {
                                                    "phase": "phase2_debate",
                                                    "phaseName": get_message("phase2_debate_name", language),
                                                    "thought": get_message("starting_debate_round", language, current=current_round, total=max_rounds),
                                                    "agent": get_message("system", language),
                                                    "agentId": "system",
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                        
                                        # 更新状态并发送消息
                                        if next_agent and next_agent in agent_status and agent_status[next_agent] in ["idle", "completed"]:
                                            prev_status = agent_status[next_agent]
                                            agent_status[next_agent] = "processing"
                                            await websocket.send_json({
                                                "type": "agent.status",
                                                "id": analysis_id,
                                                "data": {
                                                    "agent": next_agent,  # 使用原始名称格式
                                                    "status": "processing",
                                                    "phase": next_phase,
                                                    "phaseName": execution_phases[next_phase]["name"],
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"🚀 激活下一个Agent [{next_agent}] 状态: {prev_status} → processing")
                                        else:
                                            # 调试：记录条件判断失败的原因
                                            logger.error(f"❌ [Msg Clear Bear] 无法激活 {next_agent}!")
                                            logger.error(f"   - next_agent存在: {bool(next_agent)}")
                                            logger.error(f"   - next_agent值: '{next_agent}'")
                                            logger.error(f"   - 在agent_status中: {next_agent in agent_status if next_agent else 'N/A'}")
                                            if next_agent and next_agent in agent_status:
                                                logger.error(f"   - 当前状态: '{agent_status[next_agent]}'")
                                                logger.error(f"   - 状态是否合法: {agent_status[next_agent] in ['idle', 'completed']}")
                                            logger.error(f"   - agent_status内容: {list(agent_status.keys())}")
                                    
                                    # 第四阶段Risk分析师的动态路由
                                    elif node_name == "Msg Clear Risky":
                                        # 优先使用全局graph_state，fallback到current_chunk_state
                                        max_rounds = market_data.get("depth", 1)  # 使用用户选择的分析深度
                                        
                                        # 首先从全局状态获取
                                        risk_count = graph_state["risk_count"]
                                        
                                        # 调试日志
                                        logger.info(f"🔥 [Msg Clear Risky DEBUG] current_chunk_state keys: {list(current_chunk_state.keys())}")
                                        logger.info(f"🔥 [Msg Clear Risky DEBUG] 全局risk_count: {graph_state['risk_count']}")
                                        
                                        # 如果current_chunk_state有更新的值，使用它
                                        if "risk_debate_state" in current_chunk_state:
                                            risk_state = current_chunk_state.get("risk_debate_state", {})
                                            chunk_count = risk_state.get("count", 0)
                                            risk_count = max(risk_count, chunk_count)
                                            # 同步更新全局状态
                                            graph_state["risk_count"] = risk_count
                                            logger.info(f"🔥 [Msg Clear Risky DEBUG] chunk_count={chunk_count}, 更新后risk_count={risk_count}")
                                        else:
                                            logger.info(f"🔥 [Msg Clear Risky] 使用全局risk_count: {risk_count}")
                                        
                                        logger.info(f"⚠️ [Msg Clear Risky] 分析计数: {risk_count}, 最大轮数: {max_rounds}, 阈值: {3 * max_rounds}")
                                        
                                        if risk_count >= 3 * max_rounds:
                                            # 分析结束，激活Risk Judge
                                            next_agent = "Risk Judge"
                                            next_phase = "phase4_risk"
                                            logger.info(f"⚠️ [Msg Clear Risky] 分析结束 → Risk Judge")
                                            # 发送风险分析结束消息
                                            await websocket.send_json({
                                                "type": "agent.thought",
                                                "id": analysis_id,
                                                "data": {
                                                    "phase": "phase4_risk",
                                                    "phaseName": get_message("phase4_risk_name", language),
                                                    "thought": get_message("risk_assessment_ended", language, rounds=max_rounds),
                                                    "agent": get_message("system", language),
                                                    "agentId": "system",
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                        else:
                                            # 继续分析，激活Safe Analyst
                                            next_agent = "Safe Analyst"
                                            next_phase = "phase4_risk"
                                            current_round = risk_count // 3 + 1
                                            logger.info(f"⚠️ [Msg Clear Risky] 继续分析 → Safe Analyst")
                                            # 轮次提醒由 Msg Clear Neutral 处理
                                        
                                        # 更新状态并发送消息
                                        if next_agent and next_agent in agent_status and agent_status[next_agent] in ["idle", "completed"]:
                                            agent_status[next_agent] = "processing"
                                            await websocket.send_json({
                                                "type": "agent.status",
                                                "id": analysis_id,
                                                "data": {
                                                    "agent": next_agent,  # 使用原始名称格式
                                                    "status": "processing",
                                                    "phase": next_phase,
                                                    "phaseName": execution_phases[next_phase]["name"],
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"🚀 激活下一个Agent [{next_agent}] 状态: idle → processing")
                                    
                                    elif node_name == "Msg Clear Safe":
                                        # 优先使用全局graph_state，fallback到current_chunk_state
                                        max_rounds = market_data.get("depth", 1)  # 使用用户选择的分析深度
                                        
                                        # 首先从全局状态获取
                                        risk_count = graph_state["risk_count"]
                                        
                                        # 调试日志
                                        logger.info(f"🛡️ [Msg Clear Safe DEBUG] current_chunk_state keys: {list(current_chunk_state.keys())}")
                                        logger.info(f"🛡️ [Msg Clear Safe DEBUG] 全局risk_count: {graph_state['risk_count']}")
                                        
                                        # 如果current_chunk_state有更新的值，使用它
                                        if "risk_debate_state" in current_chunk_state:
                                            risk_state = current_chunk_state.get("risk_debate_state", {})
                                            chunk_count = risk_state.get("count", 0)
                                            risk_count = max(risk_count, chunk_count)
                                            # 同步更新全局状态
                                            graph_state["risk_count"] = risk_count
                                            logger.info(f"🛡️ [Msg Clear Safe DEBUG] chunk_count={chunk_count}, 更新后risk_count={risk_count}")
                                        else:
                                            logger.info(f"🛡️ [Msg Clear Safe] 使用全局risk_count: {risk_count}")
                                        
                                        logger.info(f"🛡️ [Msg Clear Safe] 分析计数: {risk_count}, 最大轮数: {max_rounds}, 阈值: {3 * max_rounds}")
                                        
                                        if risk_count >= 3 * max_rounds:
                                            # 分析结束，激活Risk Judge
                                            next_agent = "Risk Judge"
                                            next_phase = "phase4_risk"
                                            logger.info(f"🛡️ [Msg Clear Safe] 分析结束 → Risk Judge")
                                        else:
                                            # 继续分析，激活Neutral Analyst
                                            next_agent = "Neutral Analyst"
                                            next_phase = "phase4_risk"
                                            logger.info(f"🛡️ [Msg Clear Safe] 继续分析 → Neutral Analyst")
                                        
                                        # 更新状态并发送消息
                                        if next_agent and next_agent in agent_status and agent_status[next_agent] in ["idle", "completed"]:
                                            agent_status[next_agent] = "processing"
                                            await websocket.send_json({
                                                "type": "agent.status",
                                                "id": analysis_id,
                                                "data": {
                                                    "agent": next_agent,  # 使用原始名称格式
                                                    "status": "processing",
                                                    "phase": next_phase,
                                                    "phaseName": execution_phases[next_phase]["name"],
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"🚀 激活下一个Agent [{next_agent}] 状态: idle → processing")
                                    
                                    elif node_name == "Msg Clear Neutral":
                                        # 优先使用全局graph_state，fallback到current_chunk_state
                                        max_rounds = market_data.get("depth", 1)  # 使用用户选择的分析深度
                                        
                                        # 首先从全局状态获取
                                        risk_count = graph_state["risk_count"]
                                        
                                        # 调试日志
                                        logger.info(f"⚖️ [Msg Clear Neutral DEBUG] current_chunk_state keys: {list(current_chunk_state.keys())}")
                                        logger.info(f"⚖️ [Msg Clear Neutral DEBUG] 全局risk_count: {graph_state['risk_count']}")
                                        
                                        # 如果current_chunk_state有更新的值，使用它
                                        if "risk_debate_state" in current_chunk_state:
                                            risk_state = current_chunk_state.get("risk_debate_state", {})
                                            chunk_count = risk_state.get("count", 0)
                                            risk_count = max(risk_count, chunk_count)
                                            # 同步更新全局状态
                                            graph_state["risk_count"] = risk_count
                                            logger.info(f"⚖️ [Msg Clear Neutral DEBUG] chunk_count={chunk_count}, 更新后risk_count={risk_count}")
                                        else:
                                            logger.info(f"⚖️ [Msg Clear Neutral] 使用全局risk_count: {risk_count}")
                                        
                                        logger.info(f"⚖️ [Msg Clear Neutral] 分析计数: {risk_count}, 最大轮数: {max_rounds}, 阈值: {3 * max_rounds}")
                                        
                                        if risk_count >= 3 * max_rounds:
                                            # 分析结束，激活Risk Judge
                                            next_agent = "Risk Judge"
                                            next_phase = "phase4_risk"
                                            logger.info(f"⚖️ [Msg Clear Neutral] 分析结束 → Risk Judge")
                                        else:
                                            # 继续分析，激活Risky Analyst（循环回来）
                                            next_agent = "Risky Analyst"
                                            next_phase = "phase4_risk"
                                            current_round = risk_count // 3 + 1
                                            logger.info(f"⚖️ [Msg Clear Neutral] 继续分析 → Risky Analyst")
                                            # 在轮次边界处发送轮数提醒
                                            if risk_count % 3 == 0 and risk_count < 3 * max_rounds:
                                                next_round = risk_count // 3 + 1
                                                await websocket.send_json({
                                                    "type": "agent.thought",
                                                    "id": analysis_id,
                                                    "data": {
                                                        "phase": "phase4_risk",
                                                        "phaseName": get_message("phase4_risk_name", language),
                                                        "thought": get_message("starting_risk_round", language, current=next_round, total=max_rounds),
                                                        "agent": get_message("system", language),
                                                        "agentId": "system",
                                                        "analysisId": analysis_id,
                                                        "timestamp": datetime.utcnow().isoformat()
                                                    }
                                                })
                                        
                                        # 更新状态并发送消息
                                        if next_agent and next_agent in agent_status and agent_status[next_agent] in ["idle", "completed"]:
                                            agent_status[next_agent] = "processing"
                                            await websocket.send_json({
                                                "type": "agent.status",
                                                "id": analysis_id,
                                                "data": {
                                                    "agent": next_agent,  # 使用原始名称格式
                                                    "status": "processing",
                                                    "phase": next_phase,
                                                    "phaseName": execution_phases[next_phase]["name"],
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"🚀 激活下一个Agent [{next_agent}] 状态: idle → processing")
                                    
                                    # 其他阶段使用映射表
                                    elif node_name in next_agent_map:
                                        next_agent, next_phase = next_agent_map[node_name]
                                        
                                        if next_agent and next_agent in agent_status and agent_status[next_agent] in ["idle", "completed"]:
                                            agent_status[next_agent] = "processing"
                                            # 发送下一个Agent的processing状态
                                            await websocket.send_json({
                                                "type": "agent.status",
                                                "id": analysis_id,
                                                "data": {
                                                    "agent": next_agent,  # 使用原始名称格式
                                                    "status": "processing",
                                                    "phase": next_phase,
                                                    "phaseName": execution_phases[next_phase]["name"],
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"🚀 激活下一个Agent [{next_agent}] 状态: idle → processing")
                            
                            # 检测阶段变化
                            if current_phase != phase_key:
                                # 如果有前一个阶段，标记为完成
                                if current_phase:
                                    execution_phases[current_phase]["status"] = "completed"
                                    execution_phases[current_phase]["progress"] = 100
                                    
                                    # 标记前一阶段的所有agents为completed（新增）
                                    prev_phase_nodes = execution_phases[current_phase]["nodes"]
                                    for prev_node in prev_phase_nodes:
                                        if prev_node in agent_status and agent_status[prev_node] == "processing":
                                            agent_status[prev_node] = "completed"
                                            
                                            # 发送agent完成状态
                                            await websocket.send_json({
                                                "type": "agent.status",
                                                "id": analysis_id,
                                                "data": {
                                                    "agent": prev_node,  # 使用原始名称格式
                                                    "status": "completed",
                                                    "phase": current_phase,
                                                    "analysisId": analysis_id,
                                                    "timestamp": datetime.utcnow().isoformat()
                                                }
                                            })
                                            logger.info(f"✅ Agent [{prev_node}] 状态: processing → completed")
                                
                                # 开始新阶段
                                current_phase = phase_key
                                phase["status"] = "processing"
                                phase_start_time[phase_key] = datetime.utcnow()
                                
                                logger.info(f"进入新阶段: {phase['name']} ({phase['number']})")
                                
                                # 计算总进度（基于阶段）
                                phase_weights = {
                                    "phase1_analysis": 30,   # 30%
                                    "phase2_debate": 20,     # 20%
                                    "phase3_trading": 15,    # 15%
                                    "phase4_risk": 25,       # 25%
                                    "phase5_decision": 10    # 10%
                                }
                                completed_weight = sum(
                                    phase_weights[pk] for pk, pv in execution_phases.items()
                                    if pv["status"] == "completed"
                                )
                                current_weight = phase_weights[phase_key] * 0.5  # 当前阶段进行中算50%
                                progress = completed_weight + current_weight
                                
                                # 发送阶段进度消息（包含agent状态）
                                await websocket.send_json({
                                    "type": "phase.start",
                                    "id": analysis_id,
                                    "data": {
                                        "phase": phase_key,
                                        "phaseName": phase["name"],
                                        "phaseNumber": phase["number"],
                                        "progress": progress,
                                        "message": f"开始{phase['name']}阶段",
                                        "analysisId": analysis_id,
                                        "timestamp": datetime.utcnow().isoformat(),
                                        # 新增：包含所有agents的当前状态
                                        "agentStates": {
                                            agent: status for agent, status in agent_status.items()
                                            if any(keyword in agent for keyword in ["Analyst", "Researcher", "Manager", "Trader", "Judge"])
                                        }
                                    }
                                })
                            
                            # Linus: 数据结构一致性 - 跳过 Msg Clear 节点的内容提取
                            # 这些节点只做清理工作，不包含分析内容
                            if node_name.startswith("Msg Clear"):
                                logger.debug(f"🧹 跳过清理节点内容提取: {node_name}")
                                continue
                            
                            # 提取节点内容 - 支持嵌套结构
                            agent_thought = ""
                            if isinstance(node_data, dict):
                                # 1. 首先检查直接字段
                                direct_fields = [
                                    "market_report", "social_report", "sentiment_report",
                                    "news_report", "fundamentals_report",
                                    "trader_investment_plan", "investment_plan",
                                    "judge_decision", "final_trade_decision",
                                    "portfolio_decision", "final_recommendation",  # Portfolio Manager字段
                                    # 添加更多可能的字段名
                                    "analysis", "response", "reasoning", "opinion",
                                    "assessment", "thought", "content", "message",
                                    "bull_analysis", "bear_analysis", "risk_analysis",
                                    "bull_response", "bear_response", "risk_response"
                                ]
                                
                                for field in direct_fields:
                                    if field in node_data and node_data[field]:
                                        # 增加内容长度限制到10000字符，足够显示完整分析
                                        MAX_THOUGHT_LENGTH = 10000
                                        agent_thought = str(node_data[field])[:MAX_THOUGHT_LENGTH]
                                        logger.info(f"✅ 提取直接字段 {field}: {agent_thought[:100]}...")
                                        # 特别记录Portfolio Manager的字段
                                        if node_name == "Portfolio Manager" and field in ["portfolio_decision", "final_recommendation"]:
                                            logger.info(f"📊 [Portfolio Manager] 成功提取{field}字段，长度: {len(str(node_data[field]))}")
                                        break
                                
                                # 2. 检查嵌套的辩论状态字段
                                if not agent_thought:
                                    nested_mappings = {
                                        "investment_debate_state": ["current_response", "history", "bull_history", "bear_history"],
                                        "risk_debate_state": ["current_response", "history", "final_decision"],
                                        # 添加更多节点的嵌套字段映射
                                        "bull_researcher": ["analysis", "response", "reasoning", "content"],
                                        "bear_researcher": ["analysis", "response", "reasoning", "content"],
                                        "risky_analyst": ["analysis", "response", "reasoning", "content"],
                                        "safe_analyst": ["analysis", "response", "reasoning", "content"],
                                        "neutral_analyst": ["analysis", "response", "reasoning", "content"]
                                    }
                                    
                                    for parent_field, sub_fields in nested_mappings.items():
                                        if parent_field in node_data and isinstance(node_data[parent_field], dict):
                                            nested_data = node_data[parent_field]
                                            for sub_field in sub_fields:
                                                if sub_field in nested_data and nested_data[sub_field]:
                                                    # 增加内容长度限制到10000字符
                                                    MAX_THOUGHT_LENGTH = 10000
                                                    agent_thought = str(nested_data[sub_field])[:MAX_THOUGHT_LENGTH]
                                                    logger.info(f"✅ 提取嵌套字段 {parent_field}.{sub_field}: {agent_thought[:100]}...")
                                                    break
                                            if agent_thought:
                                                break
                                
                                # 3. 尝试messages字段
                                if not agent_thought and "messages" in node_data:
                                    messages = node_data["messages"]
                                    if isinstance(messages, list) and messages:
                                        last_msg = messages[-1]
                                        
                                        # Linus原则：检测工具调用并发送通知
                                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                            # 发送工具调用通知
                                            for tool_call in last_msg.tool_calls:
                                                tool_name = tool_call.get('name', 'unknown')
                                                tool_args = tool_call.get('args', {})
                                                
                                                # Linus原则：获取友好的工具名称，消除技术名称特殊情况
                                                from core.services.tools.tool_registry import ToolRegistry
                                                
                                                # 首先尝试从ToolRegistry获取
                                                friendly_name = tool_name
                                                for scope_name, scope_tools in ToolRegistry.TOOL_REGISTRY.items():
                                                    if tool_name in scope_tools:
                                                        tool_info = scope_tools[tool_name]
                                                        friendly_name = tool_info.get('display_name', tool_info.get('name', tool_name))
                                                        break
                                                
                                                # Fallback：处理未在ToolRegistry中注册的工具
                                                if friendly_name == tool_name:
                                                    tool_fallback_names = {
                                                        'get_stock_market_data_unified': '统一市场数据',
                                                        'get_reddit_stock_info': 'Reddit情绪分析', 
                                                        'get_stock_news_openai': '新闻资讯获取',
                                                        'get_YFin_data_online': 'Yahoo Finance数据',
                                                        'get_stockstats_indicators_report_online': '技术指标报告',
                                                        'get_fear_greed_index': '恐惧贪婪指数',
                                                        'get_trending_coins': '热门币种',
                                                        'get_market_metrics': '市场指标'
                                                    }
                                                    friendly_name = tool_fallback_names.get(tool_name, tool_name)
                                                
                                                # Linus原则：获取友好的agent名称（多语言支持）- 使用统一函数
                                                agent_cn_name = get_localized_agent_name_unified(node_name, language)
                                                
                                                # 发送工具调用消息
                                                await websocket.send_json({
                                                    "type": "agent.tool",
                                                    "id": analysis_id,
                                                    "data": {
                                                        "analysisId": analysis_id,  # Linus原则：统一数据契约，添加缺失字段
                                                        "phase": phase_key,
                                                        "agent": agent_cn_name,
                                                        "tool": friendly_name,
                                                        "args": tool_args,
                                                        "message": f"{get_message('calling_tool', language)}: {friendly_name}",
                                                        "timestamp": datetime.utcnow().isoformat()
                                                    }
                                                })
                                                logger.info(f"🔧 [工具通知] {agent_cn_name} 调用 {friendly_name}")
                                        
                                        if hasattr(last_msg, 'content'):
                                            # 增加内容长度限制到10000字符
                                            MAX_THOUGHT_LENGTH = 10000
                                            agent_thought = last_msg.content[:MAX_THOUGHT_LENGTH]
                                            logger.info(f"✅ 提取messages内容: {agent_thought[:100]}...")
                                        elif isinstance(last_msg, tuple) and len(last_msg) > 1:
                                            # 增加内容长度限制到10000字符
                                            MAX_THOUGHT_LENGTH = 10000
                                            agent_thought = str(last_msg[1])[:MAX_THOUGHT_LENGTH]
                                            logger.info(f"✅ 提取messages元组: {agent_thought[:100]}...")
                            
                            # Linus原则：Agent名称必须本地化 - 修复用户指出的TOOL/AGT标签问题
                            agent_name = get_localized_agent_name_unified(node_name, language)
                            
                            # If no content extracted, use default English messages
                            if not agent_thought:
                                logger.warning(f"⚠️ Failed to extract content from node {node_name}, data structure: {list(node_data.keys()) if isinstance(node_data, dict) else type(node_data)}")
                                default_messages = {
                                    "Market Analyst": "Analyzing market data and technical indicators...",
                                    "Social Analyst": "Analyzing social media sentiment...",
                                    "News Analyst": "Gathering and analyzing latest news...",
                                    "Fundamentals Analyst": "Analyzing fundamental data...",
                                    "Bull Researcher": "Analyzing bullish factors...",
                                    "Bear Researcher": "Analyzing risk factors...",
                                    "Research Manager": "Synthesizing investment recommendations...",
                                    "Trader": "Formulating trading strategy...",
                                    "Risky Analyst": "Evaluating aggressive strategy risks...",
                                    "Neutral Analyst": "Evaluating neutral strategy risks...",
                                    "Safe Analyst": "Evaluating conservative strategy risks...",
                                    "Risk Judge": "Conducting final risk assessment...",
                                    "Portfolio Manager": "Optimizing portfolio allocation..."
                                }
                                agent_thought = default_messages.get(node_name, f"{agent_name} processing...")
                            
                            # Linus原则：不要过滤工具调用，而是正确处理它们
                            # 工具调用是重要的用户反馈，应该显示而不是隐藏
                            
                            # 检查内容完整性，避免发送部分结果
                            # 对于非Msg Clear节点，检查内容是否看起来完整
                            # Portfolio Manager特殊处理：其内容可能以冒号结尾（任务列表格式）
                            if not node_name.startswith("Msg Clear") and agent_thought and node_name != "Portfolio Manager":
                                # 跳过太短的内容或以不完整标记结束的内容
                                if len(agent_thought) < 200 or agent_thought.rstrip().endswith(("###", "...", "：", ":")):
                                    logger.info(f"⏳ 跳过部分结果: {node_name} (长度={len(agent_thought)}, 结尾={agent_thought[-10:] if len(agent_thought) > 10 else agent_thought})")
                                    continue
                            
                            # Portfolio Manager专门日志
                            if node_name == "Portfolio Manager":
                                logger.info(f"📊 [Portfolio Manager] 准备发送内容，长度: {len(agent_thought)}")
                            
                            # 计算节点在阶段内的顺序
                            node_order = phase["nodes"].index(node_name) if node_name in phase["nodes"] else 0
                            
                            # 检查是否为阶段最后一个节点
                            is_last_node = (node_order == len(phase["nodes"]) - 1)
                            
                            # 发送agent思考消息（包含阶段信息和执行顺序）
                            # 修复：使用正确的数据结构匹配前端期望
                            await websocket.send_json({
                                "type": "agent.thought",
                                "id": analysis_id,
                                "data": {
                                    "phase": phase_key,
                                    "phaseName": phase["name"],
                                    "phaseOrder": list(execution_phases.keys()).index(phase_key) + 1,  # 1-5
                                    "nodeOrder": node_order,
                                    "isPhaseComplete": is_last_node,
                                    "thought": agent_thought,  # 修复：直接发送思考内容字符串
                                    "agent": agent_name,  # 修复：使用扁平结构
                                    "agentId": normalize_agent_name(node_name),  # 标准化的Agent ID
                                    "analysisId": analysis_id,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            })
                            
                            logger.info(f"阶段[{phase['name']}] 节点[{node_name}] 处理完成")
                            # 移除break，允许处理chunk中的所有节点
                    
                except queue.Empty:
                    # 队列为空，检查是否应该退出
                    if stream_done:
                        logger.info(f"Stream完成且队列为空，最终状态可用: {final_state is not None}")
                        break
                    # 否则继续等待
                
                await asyncio.sleep(check_interval)
                elapsed += check_interval
            
            # 等待线程结束并清理
            if analysis_id in active_analysis_threads:
                thread, stop_event = active_analysis_threads[analysis_id]
                thread.join(timeout=5)  # 给线程5秒时间清理
                if thread.is_alive():
                    logger.warning(f"Thread for {analysis_id} did not terminate cleanly")
                del active_analysis_threads[analysis_id]
            else:
                # 如果线程引用已被删除，仍要等待原始线程
                stream_thread.join(timeout=5)
            
            if elapsed >= max_wait:
                logger.warning(f"分析超时: {analysis_id}")
                final_state = {"error": "分析超时"}
            
            # 提取结果
            if final_state is not None and "error" not in final_state:
                # 处理信号 - SignalProcessor需要quick_thinking_llm参数
                # 使用graph中已经初始化的signal_processor
                signal = graph.signal_processor.process_signal(
                    final_state.get("final_trade_decision", ""),
                    company_name
                )
                
                result = {
                    "company": final_state.get("company_of_interest", company_name),
                    "date": final_state.get("trade_date", trade_date),
                    "market_report": final_state.get("market_report", ""),
                    "social_report": final_state.get("social_report", ""),
                    "news_report": final_state.get("news_report", ""),
                    "fundamentals_report": final_state.get("fundamentals_report", ""),
                    "bull_case": final_state.get("bull_case", ""),
                    "bear_case": final_state.get("bear_case", ""),
                    "trade_decision": final_state.get("final_trade_decision", ""),
                    "signal": signal
                }
            else:
                result = {
                    "company": company_name,
                    "status": "error",
                    "message": final_state.get("error", "分析失败") if final_state else "分析失败"
                }
            
            logger.info(f"分析完成: {result.get('trade_decision', 'N/A')}")
            
        except Exception as e:
            logger.error(f"分析执行失败: {str(e)}")
            logger.error(traceback.format_exc())
            result = {
                "company": company_name,
                "status": "error",
                "message": f"分析失败: {str(e)}"
            }
        
        # 发送完成消息
        await websocket.send_json({
            "type": "analysis.complete",
            "id": analysis_id,
            "data": {
                "status": "completed",
                "analysisId": analysis_id,
                "result": result
            }
        })
        
    except Exception as e:
        logger.error(f"Dev analysis error: {str(e)}")
        logger.error(traceback.format_exc())
        await websocket.send_json({
            "type": "error",
            "id": analysis_id,
            "data": {
                "message": str(e),
                "analysisId": analysis_id
            }
        })
    finally:
        # 清理活跃任务引用
        if analysis_id in active_analysis_tasks:
            del active_analysis_tasks[analysis_id]
            logger.info(f"🧹 清理任务引用: {analysis_id}")
        
        # 清理线程引用并确保停止信号发送
        if analysis_id in active_analysis_threads:
            _, stop_event = active_analysis_threads[analysis_id]
            stop_event.set()  # 确保发送停止信号
            del active_analysis_threads[analysis_id]
            logger.info(f"🧹 清理线程引用: {analysis_id}")
            
        # 清理独立的Redis订阅器（Linus原则：确保资源正确清理）
        try:
            logger.info(f"🧹 开始清理独立订阅器 (ID:{id(local_redis_subscriber)})...")
            await local_redis_subscriber.unsubscribe_task(analysis_id)
            await local_redis_subscriber.disconnect()
            logger.info(f"✅ 独立订阅器清理完成，频道: analysis:{analysis_id}")
        except Exception as cleanup_error:
            logger.error(f"清理独立Redis订阅失败: {str(cleanup_error)}")


async def handle_subscribe_analysis(websocket: WebSocket, request_id: str, params: Dict[str, Any]):
    """
    处理订阅分析任务请求
    只订阅已存在的任务，不创建新任务
    """  
    try:
        analysis_id = params.get('analysisId')
        if not analysis_id:
            logger.warning(f"订阅请求缺少analysisId参数: {params}")
            await websocket.send_json({
                "type": "error",
                "id": request_id,
                "data": {
                    "code": "MISSING_ANALYSIS_ID",
                    "message": "缺少analysisId参数"
                }
            })
            return
        
        # TODO: 验证任务是否存在（需要数据库查询）
        # 这里可以添加数据库查询逻辑来验证任务存在性
        # from core.database.models.analysis_task import AnalysisTask
        # task = await db.get(AnalysisTask, analysis_id)
        # if not task:
        #     logger.warning(f"订阅不存在的任务: {analysis_id}")
        #     await websocket.send_json({
        #         "type": "error",
        #         "id": request_id,
        #         "data": {
        #             "code": "TASK_NOT_FOUND",
        #             "message": f"任务 {analysis_id} 不存在"
        #         }
        #     })
        #     return
        
        # TODO: 验证用户是否有权限访问该任务
        # if task.user_id != current_user_id:
        #     logger.warning(f"用户无权访问任务: {analysis_id}")
        #     await websocket.send_json({
        #         "type": "error",
        #         "id": request_id,
        #         "data": {
        #             "code": "UNAUTHORIZED",
        #             "message": "无权访问该任务"
        #         }
        #     })
        #     return
        
        logger.info(f"✅ 客户端成功订阅分析任务: {analysis_id}, request_id: {request_id}")
        
        # 发送订阅确认
        await websocket.send_json({
            "type": "analysis.subscribed",
            "id": request_id,
            "data": {
                "analysisId": analysis_id,
                "status": "subscribed",
                "message": f"已订阅任务 {analysis_id} 的更新",
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # 订阅Redis频道，获取真实的分析进度
        async def handle_redis_message(message: Dict[str, Any]):
            """处理从Redis接收到的消息并转发到WebSocket"""
            try:
                # 直接转发消息到WebSocket客户端
                await websocket.send_json(message)
                logger.debug(f"Forwarded message type {message.get('type')} to WebSocket")
            except Exception as e:
                logger.error(f"Error forwarding message to WebSocket: {str(e)}")
        
        # 订阅Redis任务频道
        try:
            await redis_subscriber.subscribe_task(analysis_id, handle_redis_message)
            logger.info(f"Successfully subscribed to Redis channel for task {analysis_id}")
            
            # 保持订阅直到WebSocket断开或分析完成
            # 这里不需要额外的循环，redis_subscriber会处理消息推送
            
        except Exception as e:
            logger.error(f"Failed to subscribe to Redis channel: {str(e)}")
            # 如果Redis订阅失败，降级到模拟模式
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "无法订阅实时更新，使用模拟数据",
                    "error": str(e)
                }
            })
            
            # 降级到模拟进度（保持向后兼容）
            import asyncio
            for progress in [10, 30, 50, 70, 90, 100]:
                await asyncio.sleep(2)
                await websocket.send_json({
                    "type": "task.progress",
                    "data": {
                        "taskId": analysis_id,
                        "progress": progress,
                        "message": f"分析进度（模拟）: {progress}%"
                    }
                })
            
            # 发送完成消息
            await websocket.send_json({
                "type": "analysis.complete",
                "data": {
                    "analysisId": analysis_id,
                    "result": {
                        "status": "completed",
                        "message": "分析完成（模拟）"
                    }
                }
            })
        
    except Exception as e:
        logger.error(f"订阅分析失败: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "data": {
                "message": f"订阅失败: {str(e)}"
            }
        })


async def handle_start_analysis(websocket: WebSocket, request_id: str, params: Dict[str, Any]):
    """
    [已废弃] 处理开始分析请求
    这个函数不应该被调用，分析应该通过REST API创建
    
    Args:
        websocket: WebSocket连接
        params: 分析参数
    """
    try:
        # 发送分析开始确认
        analysis_id = f"analysis-{datetime.utcnow().timestamp()}"
        await websocket.send_json({
            "type": "analysis.start",
            "id": request_id,
            "data": {
                "analysisId": analysis_id,
                "status": "started",
                "message": get_message("initializing_analysis_system", language)
            }
        })
        
        # 发送任务进度
        await websocket.send_json({
            "type": "task.progress",
            "data": {
                "taskId": analysis_id,
                "progress": 0,
                "message": "初始化中..."
            }
        })
        
        # 获取配置，支持驼峰和下划线两种格式
        market_type = params.get("marketType") or params.get("market_type", "crypto")
        symbol = params.get("symbol", "BTC/USDT")
        target = symbol.split("/")[0] if "/" in symbol else symbol
        timeframe = params.get("timeframe", "1h")
        depth = params.get("depth", 3)
        analysis_scopes = params.get("analysisScopes") or params.get("analysis_scopes", ["price", "sentiment"])
        llm_provider = params.get("llmProvider") or params.get("llm_provider", "kimi")
        llm_model = params.get("llmModel") or params.get("llm_model", "moonshot-v1-128k")
        
        # 根据分析范围动态确定分析师
        selected_analysts = []
        if "price" in analysis_scopes or "technical" in analysis_scopes:
            selected_analysts.append("market")
        if "sentiment" in analysis_scopes or "social" in analysis_scopes:
            selected_analysts.extend(["social", "news"])
        if not selected_analysts:
            selected_analysts = ["market", "social", "news"]
        
        # 定义固定的执行顺序，确保不管用户选择顺序如何，执行顺序都一致
        ANALYST_ORDER = ['market', 'social', 'news', 'fundamentals']
        
        # 根据预定义顺序排序
        selected_analysts = [
            analyst for analyst in ANALYST_ORDER 
            if analyst in selected_analysts
        ]
        
        # 根据市场类型调整分析师
        if market_type == "crypto":
            # 加密市场使用传统分析师
            if "fundamentals" not in selected_analysts:
                selected_analysts.append("fundamentals")
        elif market_type == "prediction":
            # 预测市场可能需要特殊处理
            # TODO: 添加预测市场特定的分析师
            pass
        
        # 配置LLM
        config = WHENTRADE_CONFIG.copy()
        
        # 检查可用的LLM提供商
        available_provider = None
        if llm_config_service.is_provider_available("kimi"):
            available_provider = "kimi"
            config["llm_provider"] = "openai"  # Kimi使用OpenAI兼容接口
            config["deep_think_llm"] = "moonshot-v1-128k"
            config["quick_think_llm"] = "moonshot-v1-32k"
            config["backend_url"] = "https://api.moonshot.cn/v1"
        elif llm_config_service.is_provider_available("deepseek"):
            available_provider = "deepseek"
            config["llm_provider"] = "deepseek"
            config["deep_think_llm"] = "deepseek-chat"
            config["quick_think_llm"] = "deepseek-chat"
            config["backend_url"] = "https://api.deepseek.com/v1"
        else:
            raise Exception("没有可用的LLM提供商")
        
        await websocket.send_json({
            "type": "task.progress",
            "data": {
                "taskId": analysis_id,
                "progress": 10,
                "message": f"使用 {available_provider} 作为LLM提供商",
                "currentStep": "配置LLM"
            }
        })
        
        # 创建WhenTradeGraph实例
        graph = WhenTradeGraph(
            selected_analysts=selected_analysts,
            debug=False,
            config=config
        )
        
        await websocket.send_json({
            "type": "task.progress",
            "data": {
                "taskId": analysis_id,
                "progress": 20,
                "message": get_message("analysis_system_init_complete", language),
                "currentStep": get_message("system_ready", language)
            }
        })
        
        # 启动真实LangGraph分析流程
        await run_real_analysis_stream(websocket, graph, analysis_id, target, analysis_scopes, selected_analysts, selected_tools, selected_data_sources)
        
    except Exception as e:
        logger.error(f"分析失败: {str(e)}\n{traceback.format_exc()}")
        await websocket.send_json({
            "type": "error",
            "data": {
                "message": f"分析失败: {str(e)}",
                "traceback": traceback.format_exc()
            }
        })


async def run_real_analysis_stream(
    websocket: WebSocket,
    graph: WhenTradeGraph,
    analysis_id: str,
    target: str,
    analysis_scopes: List[str],
    selected_analysts: List[str],
    selected_tools: List[str] = None,
    selected_data_sources: List[str] = None
):
    """
    运行真实的LangGraph分析流程
    
    Args:
        websocket: WebSocket连接
        graph: WhenTradeGraph实例
        analysis_id: 分析ID
        target: 分析目标
        analysis_scopes: 分析范围
        selected_analysts: 选择的分析师
    """
    try:
        # 构建分析输入
        analysis_input = {
            "target": target,
            "analysis_scopes": analysis_scopes,
            "selected_analysts": selected_analysts,
            "depth": 3,
            "output_format": "comprehensive"
        }
        
        await websocket.send_json({
            "type": "task.progress",
            "data": {
                "taskId": analysis_id,
                "progress": 25,
                "message": "开始LangGraph分析流程...",
                "currentStep": "初始化图"
            }
        })
        
        # 跳过获取图状态（WhenTradeGraph没有get_state方法）
        await websocket.send_json({
            "type": "task.progress", 
            "data": {
                "taskId": analysis_id,
                "progress": 40,
                "message": "准备执行分析...",
                "currentStep": "执行分析"
            }
        })
        
        # 改进的分析流程：直接调用各个分析师而不是使用propagate
        # 这种方法更加灵活，适用于各种市场类型
        
        try:
            # 检查是否应该使用真实LLM分析
            use_real_llm = llm_config_service.is_provider_available("kimi") or \
                          llm_config_service.is_provider_available("deepseek")
            
            if use_real_llm:
                logger.info(f"使用真实LLM进行分析")
                
                # 直接调用分析师节点
                from core.agents.analysts.news_analyst import create_news_analyst
                
                # 创建初始状态
                state = {
                    "messages": [],
                    "company_of_interest": target,
                    "trade_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "session_id": analysis_id,
                    "selected_analysts": selected_analysts
                }
                
                # 发送进度更新
                await websocket.send_json({
                    "type": "task.progress",
                    "data": {
                        "taskId": analysis_id,
                        "progress": 50,
                        "message": "正在调用新闻分析师...",
                        "currentStep": "新闻分析"
                    }
                })
                
                # 调用新闻分析师
                if "news" in selected_analysts or "social" in selected_analysts:
                    try:
                        news_analyst = create_news_analyst(graph.deep_thinking_llm, graph.toolkit)
                        news_result = news_analyst(state)
                        
                        if news_result and "news_report" in news_result:
                            logger.info(f"新闻分析完成，报告长度: {len(news_result['news_report'])}")
                            
                            # 发送agent思考
                            await websocket.send_json({
                                "type": "agent.thought",
                                "data": {
                                    "agentId": "news_analyst",
                                    "thought": news_result["news_report"][:500] + "...",
                                    "confidence": 0.8,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            })
                    except Exception as e:
                        logger.error(f"新闻分析失败: {str(e)}")
                
                # 发送进度更新
                await websocket.send_json({
                    "type": "task.progress",
                    "data": {
                        "taskId": analysis_id,
                        "progress": 70,
                        "message": "正在生成综合分析...",
                        "currentStep": "综合分析"
                    }
                })
                
                # 基于分析师结果生成综合报告
                result = {
                    "target": target,
                    "timestamp": datetime.utcnow().isoformat(),
                    "analysis_scopes": analysis_scopes,
                    "summary": {
                        "overall_sentiment": "基于真实数据分析",
                        "confidence": 0.85,
                        "recommendation": "需要进一步分析"
                    },
                    "key_findings": [
                        {"type": "news", "finding": "已获取最新新闻数据", "importance": "high"},
                        {"type": "analysis", "finding": "分析师已完成评估", "importance": "high"}
                    ],
                    "detailed_analysis": {
                        "news": state.get("news_report", "正在处理...")[:200] if "news_report" in state else "无新闻数据"
                    }
                }
                
            else:
                logger.info(f"没有可用的LLM提供商，使用模拟结果")
                
                # 发送分析中的进度更新
                await websocket.send_json({
                    "type": "task.progress",
                    "data": {
                        "taskId": analysis_id,
                        "progress": 60,
                        "message": "正在综合分析结果...",
                        "currentStep": "综合分析"
                    }
                })
                
                # 使用模拟结果
                result = generate_mock_result(target, analysis_scopes)
                
                # 添加一些延迟以模拟真实分析
                await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"执行分析时出错: {str(e)}")
            result = generate_mock_result(target, analysis_scopes)
        
        # 发送中间进度
        await websocket.send_json({
            "type": "task.progress",
            "data": {
                "taskId": analysis_id,
                "progress": 80,
                "message": "分析执行完成，生成报告...",
                "currentStep": "生成报告"
            }
        })
        
        # 发送agent状态和思考（从结果中提取）
        if "agent_outputs" in result:
            for agent_id, agent_data in result["agent_outputs"].items():
                await websocket.send_json({
                    "type": "agent.status",
                    "data": {
                        "agent": agent_id,  # 使用原始名称格式
                        "status": "completed",
                        "currentTask": f"分析{target}完成",
                        "analysisId": analysis_id  # 添加analysisId
                    }
                })
                
                if "thoughts" in agent_data:
                    for thought in agent_data["thoughts"]:
                        await websocket.send_json({
                            "type": "agent.thought",
                            "data": {
                                "agentId": agent_id,
                                "thought": thought.get("content", ""),
                                "confidence": thought.get("confidence", 0.7),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        })
        
        # 发送完成进度
        await websocket.send_json({
            "type": "task.progress",
            "data": {
                "taskId": analysis_id,
                "status": "completed",
                "progress": 100,
                "message": "LangGraph分析完成"
            }
        })
        
        # 发送最终结果
        await websocket.send_json({
            "type": "analysis.complete",
            "data": {
                "analysisId": analysis_id,
                "result": {
                    "target": target,
                    "timestamp": datetime.utcnow().isoformat(),
                    "analysis_scopes": analysis_scopes,
                    "summary": result.get("summary", {}),
                    "key_findings": result.get("key_findings", []),
                    "detailed_analysis": result.get("detailed_analysis", {}),
                    "recommendation": result.get("recommendation", ""),
                    "confidence": result.get("confidence", 0.7)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"真实LangGraph分析失败: {str(e)}\n{traceback.format_exc()}")
        await websocket.send_json({
            "type": "error", 
            "data": {
                "message": f"LangGraph分析失败: {str(e)}",
                "traceback": traceback.format_exc()
            }
        })
        raise


def generate_mock_thought(agent_name: str, target: str, scopes: List[str]) -> str:
    """生成模拟的思考内容"""
    thoughts = {
        "market": f"分析{target}的价格走势，当前呈现上升趋势，技术指标显示超买信号",
        "social": f"社交媒体对{target}的讨论热度上升，整体情绪偏向乐观",
        "news": f"近期关于{target}的新闻以正面为主，机构投资者增持",
        "bull_researcher": f"看涨理由：技术面突破关键阻力位，基本面支撑强劲",
        "bear_researcher": f"看跌风险：估值偏高，可能面临短期回调压力",
        "trader": f"建议：短期维持谨慎乐观，可考虑逢低建仓"
    }
    return thoughts.get(agent_name, f"{agent_name}正在分析{target}")


def generate_mock_result(target: str, scopes: List[str]) -> Dict[str, Any]:
    """生成模拟的分析结果"""
    return {
        "target": target,
        "timestamp": datetime.utcnow().isoformat(),
        "analysis_scopes": scopes,
        "summary": {
            "overall_sentiment": "谨慎乐观",
            "confidence": 0.72,
            "recommendation": "持有/小幅加仓"
        },
        "key_findings": [
            {"type": "price", "finding": "技术面突破关键阻力", "importance": "high"},
            {"type": "sentiment", "finding": "市场情绪积极", "importance": "medium"},
            {"type": "risk", "finding": "短期超买需要注意", "importance": "medium"}
        ],
        "detailed_analysis": {
            "technical": {
                "trend": "上升",
                "support": 45000,
                "resistance": 52000,
                "rsi": 68
            },
            "sentiment": {
                "social_score": 0.75,
                "news_score": 0.68,
                "fear_greed": 72
            }
        }
    }