"""
i18n Messages Dictionary for When.Trade
支持多语言的消息字典系统
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 支持的语言列表
SUPPORTED_LANGUAGES = ["en-US", "zh-CN"]

# 消息字典 - 包含所有硬编码文本的翻译
MESSAGES: Dict[str, Dict[str, str]] = {
    "en-US": {
        # 系统相关
        "system": "System",
        "analysis_task_start": "Analysis task started",
        "analysis_complete": "Analysis execution complete, generating report...",
        "generating_report": "Generating report",
        "market_data_fetching": "Fetching market data...",
        
        # 阶段名称
        "phase1_name": "Data Analysis",
        "phase1_message": "Entering Phase 1: Data Collection & Analysis",
        "phase2_name": "Strategy Analysis",
        "phase2_message": "Entering Phase 2: Strategy Analysis",
        "phase3_name": "Risk Assessment",
        "phase3_message": "Entering Phase 3: Risk Assessment",
        
        # Agent 名称
        "market_analyst": "Market Analyst",
        "news_analyst": "News Analyst", 
        "social_media_analyst": "Social Media Analyst",
        "bull_researcher": "Bull Researcher",
        "bear_researcher": "Bear Researcher",
        "risk_manager": "Risk Manager",
        "research_manager": "Research Manager",
        "portfolio_manager": "Portfolio Manager",
        "trader": "Trader",
        "conservative_debator": "Conservative Analyst",
        "aggressive_debator": "Aggressive Analyst",
        "neutral_debator": "Neutral Analyst",
        
        # 进度消息
        "market_analyst_analyzing": "Market analyst is analyzing...",
        "getting_market_data": "Getting market data...",
        "data_collection_analysis": "Data collection and analysis",
        
        # 系统初始化消息 (Linus: unified system messages)
        "tool_config_init": "Tool configuration initialized",
        "selected_tools_label": "Selected tools",
        "selected_data_sources_label": "Selected data sources",
        
        # GraphSetup messages
        "using_standard_market_analyst": "Using standard market analyst",
        "using_standard_market_analyst_alibaba_openai": "Using standard market analyst (Alibaba OpenAI compatibility mode)",
        "using_standard_market_analyst_alibaba_native": "Using standard market analyst (Alibaba native mode)", 
        "using_standard_market_analyst_deepseek": "Using standard market analyst (DeepSeek)",
        "agent_registered_to_stop_signal": "Agent registered to stop signal system",
        "total_agents_registered": "Total agents registered to stop signal system",
        "adding_edge": "Adding edge",
        "last_analyst": "last analyst",
        "ensuring_connection": "Explicitly ensuring connection",
        
        # 工具相关
        "technical_indicators_report": "Technical Indicators Report",
        
        # 系统状态消息
        "analysis_stopped": "Analysis stopped",
        "analysis_cancelled": "Analysis cancelled", 
        "analysis_timeout": "Analysis timeout",
        "analysis_failed": "Analysis failed",
        "no_scope_selected": "No analysis scope selected, please select at least one scope",
        "graph_init_failed": "Analysis graph initialization failed",
        "graph_create_failed": "Failed to create analysis graph",
        "initializing_analysis": "Initializing analysis process...",
        "preparing_analysis": "Preparing to execute analysis...",
        "comprehensive_analysis": "Generating comprehensive analysis...",
        "analysis_complete_generating_report": "Analysis execution complete, generating report...",
        
        # 工具名称
        "unified_market_data": "Unified Market Data",
        "news_information": "News Information",
        "technical_indicators_report_tool": "Technical Indicators Report", 
        "fear_greed_index": "Fear & Greed Index",
        "trending_coins": "Trending Coins",
        "market_metrics": "Market Metrics",
        "calling_tool": "Calling tool",
        
        # 语言名称
        "language_name": "English",
        
        # 市场分析报告相关
        "crypto_price": "Cryptocurrency Price",
        "latest_price": "Latest Price",
        "current_price": "Current Price", 
        "price_change": "Price Change",
        "price_info": "Price Information",
        "data_interval": "Data Interval",
        "data_points": "Data Points",
        "period_change": "Period Change",
        "market_data_realtime": "Real-time Market Data",
        "historical_data": "Historical Data",
        "data_points_count": "Data Points Count",
        
        # 价格方向
        "rising": "Rising",
        "falling": "Falling", 
        "flat": "Flat",
        "upward": "Up",
        "downward": "Down",
        "sideways": "Sideways",
        
        # 技术指标
        "technical_analysis": "Technical Indicators Analysis",
        "moving_average_analysis": "Moving Average Analysis", 
        "momentum_strength_analysis": "Momentum and Strength Indicators Analysis",
        "volatility_analysis": "Volatility Indicators Analysis",
        "volume_analysis": "Volume Analysis",
        "macd_analysis": "MACD Analysis",
        
        # RSI状态
        "overbought": "Overbought",
        "oversold": "Oversold",
        "neutral": "Neutral",
        "area": "Area",
        
        # 布林带
        "bb_upper": "Bollinger Band Upper",
        "bb_middle": "Bollinger Band Middle",
        "bb_lower": "Bollinger Band Lower",
        
        # 成交量
        "total_volume_period": "Total Volume for Selected Period",
        "latest_24h_volume": "Latest 24H Volume", 
        "volume_data_points": "Volume Data Points",
        "volume_status": "Volume Status",
        "active": "Active",
        "sluggish": "Sluggish",
        
        # 数据提示
        "data_points_few_warning": "(Few data points, some long-term indicators may not be calculated)",
        "data_compressed": "(Data optimized and compressed)",
        "data_summary_compressed": "Data Summary (Compressed)",
        "data_obtained": "Data obtained",
        
        # 错误信息
        "error": "Error",
        "data_format_error": "Data format error",
        "expected_dict_got": "Expected dictionary, got",
        
        # 分析提示词
        "professional_stock_analyst": "You are a professional stock technical analyst. Analyze based on the following tool-acquired data.",
        "technical_indicators_values": "Technical Indicator Values:",
        "tool_data": "Tool Data:",
        "comprehensive_analysis_request": "Please conduct a comprehensive technical analysis based on the above data and provide clear investment advice: **Buy/Hold/Sell**. Please directly reference the specific values of the above technical indicators in your analysis.",
        
        # WebSocket事件消息
        "tool_execution_start": "Starting tools execution",
        "tool_execution_complete": "Tool execution complete",
        "tools_count": "tools", 
        "success_count": "succeeded",
        "failed_count": "failed",
        "time_spent": "took",
        "total_count": "total",
        "colon": ":",
        "comma": ",",
        
        # 工具名称
        "tool_crypto_price": "Cryptocurrency Price",
        "tool_indicators": "Technical Indicators", 
        "tool_market_data": "Real-time Market Data",
        "tool_historical_data": "Historical Data",
        "tool_finnhub_news": "Finnhub News",
        "tool_reddit_sentiment": "Reddit Sentiment",
        "tool_sentiment_batch": "Batch Sentiment Analysis",
        "tool_fear_greed": "Fear & Greed Index",
        
        # 🔴 新增：阶段名称
        "phase2_debate_name": "Investment Debate",
        "phase3_trading_name": "Trading Strategy",
        "phase4_risk_name": "Risk Assessment",
        "phase5_decision_name": "Portfolio Management",
        
        # 🔴 新增：进入阶段消息
        "entering_phase2": "Entering Phase 2: Investment Debate",
        "entering_phase3": "Entering Phase 3: Trading Strategy",
        "entering_phase4": "Entering Phase 4: Risk Assessment",
        "entering_phase5": "Entering Phase 5: Portfolio Management",
        
        # 🔴 新增：开始轮次消息（支持格式化）
        "starting_debate_round": "Starting debate round {current} (Total: {total} rounds)",
        "starting_risk_round": "Starting risk analysis round {current} (Total: {total} rounds)",
        
        # 🔴 新增：结束消息
        "debate_ended": "Investment debate ended, completed {rounds} rounds",
        "risk_assessment_ended": "Risk assessment ended, completed {rounds} rounds of analysis",
        
        # 🔴 新增：系统初始化消息
        "initializing_analysis_system": "Initializing analysis system...",
        "analysis_system_init_complete": "Analysis system initialization complete",
        "system_ready": "System ready"
    },
    "zh-CN": {
        # 系统相关
        "system": "系统",
        "analysis_task_start": "分析任务开始",
        "analysis_complete": "分析执行完成，生成报告...",
        "generating_report": "生成报告",
        "market_data_fetching": "正在获取市场数据...",
        
        # 阶段名称
        "phase1_name": "数据分析",
        "phase1_message": "进入第一阶段：数据收集与分析",
        "phase2_name": "策略分析",
        "phase2_message": "进入第二阶段：策略分析",
        "phase3_name": "风险评估", 
        "phase3_message": "进入第三阶段：风险评估",
        
        # Agent 名称
        "market_analyst": "市场分析师",
        "news_analyst": "新闻分析师",
        "social_media_analyst": "社交媒体分析师", 
        "bull_researcher": "看多研究员",
        "bear_researcher": "看空研究员",
        "risk_manager": "风险管理师",
        "research_manager": "研究经理",
        "portfolio_manager": "组合经理",
        "trader": "交易员",
        "conservative_debator": "保守分析师",
        "aggressive_debator": "激进分析师",
        "neutral_debator": "中立分析师",
        
        # 进度消息
        "market_analyst_analyzing": "市场分析师正在分析...",
        "getting_market_data": "正在获取市场数据...",
        "data_collection_analysis": "数据收集与分析",
        
        # 系统初始化消息 (Linus: unified system messages)
        "tool_config_init": "工具配置初始化",
        "selected_tools_label": "选中的工具",
        "selected_data_sources_label": "选中的数据源",
        
        # GraphSetup messages
        "using_standard_market_analyst": "使用标准市场分析师",
        "using_standard_market_analyst_alibaba_openai": "使用标准市场分析师（阿里百炼OpenAI兼容模式）",
        "using_standard_market_analyst_alibaba_native": "使用标准市场分析师（阿里百炼原生模式）",
        "using_standard_market_analyst_deepseek": "使用标准市场分析师（DeepSeek）",
        "agent_registered_to_stop_signal": "已注册到停止信号列表",
        "total_agents_registered": "总共注册了到停止信号系统",
        "adding_edge": "添加边",
        "last_analyst": "最后一个分析师",
        "ensuring_connection": "显式确保",
        
        # 工具相关
        "technical_indicators_report": "技术指标报告",
        
        # 系统状态消息
        "analysis_stopped": "分析已停止",
        "analysis_cancelled": "分析已取消", 
        "analysis_timeout": "分析超时",
        "analysis_failed": "分析失败",
        "no_scope_selected": "未选择任何分析范围，请至少选择一个分析范围",
        "graph_init_failed": "分析图初始化失败",
        "graph_create_failed": "创建分析图失败",
        "initializing_analysis": "初始化分析流程...",
        "preparing_analysis": "准备执行分析...",
        "comprehensive_analysis": "正在综合分析结果...",
        "analysis_complete_generating_report": "分析执行完成，生成报告...",
        
        # 工具名称
        "unified_market_data": "统一市场数据",
        "news_information": "新闻资讯获取",
        "technical_indicators_report_tool": "技术指标报告", 
        "fear_greed_index": "恐惧贪婪指数",
        "trending_coins": "热门币种",
        "market_metrics": "市场指标",
        "calling_tool": "调用工具",
        
        # 语言名称
        "language_name": "简体中文",
        
        # 市场分析报告相关
        "crypto_price": "加密货币价格",
        "latest_price": "最新价格",
        "current_price": "当前价格", 
        "price_change": "价格变化",
        "price_info": "价格信息",
        "data_interval": "数据间隔",
        "data_points": "数据点数",
        "period_change": "期间涨跌",
        "market_data_realtime": "实时市场数据",
        "historical_data": "历史数据",
        "data_points_count": "数据点数量",
        
        # 价格方向
        "rising": "上涨",
        "falling": "下跌", 
        "flat": "持平",
        "upward": "上涨",
        "downward": "下跌",
        "sideways": "持平",
        
        # 技术指标
        "technical_analysis": "技术指标分析",
        "moving_average_analysis": "移动平均线分析", 
        "momentum_strength_analysis": "动量和强度指标分析",
        "volatility_analysis": "波动率指标分析",
        "volume_analysis": "成交量分析",
        "macd_analysis": "MACD相关分析",
        
        # RSI状态
        "overbought": "超买",
        "oversold": "超卖",
        "neutral": "中性",
        "area": "区域",
        
        # 布林带
        "bb_upper": "布林带上轨",
        "bb_middle": "布林带中轨",
        "bb_lower": "布林带下轨",
        
        # 成交量
        "total_volume_period": "选定时间范围总成交量",
        "latest_24h_volume": "最新24小时成交量", 
        "volume_data_points": "成交量数据点数",
        "volume_status": "成交量状态",
        "active": "活跃",
        "sluggish": "低迷",
        
        # 数据提示
        "data_points_few_warning": "(数据点较少，部分长期指标可能无法计算)",
        "data_compressed": "(数据已优化压缩)",
        "data_summary_compressed": "数据摘要（已压缩）",
        "data_obtained": "已获取数据",
        
        # 错误信息
        "error": "错误",
        "data_format_error": "数据格式异常",
        "expected_dict_got": "期望字典，实际为",
        
        # 分析提示词
        "professional_stock_analyst": "你是一位专业的股票技术分析师。基于以下工具获取的数据进行分析。",
        "technical_indicators_values": "技术指标数值：",
        "tool_data": "工具数据：",
        "comprehensive_analysis_request": "请基于以上数据进行综合技术分析，并提供明确的投资建议：**买入/持有/卖出**。在分析中请直接引用上述技术指标的具体数值。",
        
        # WebSocket事件消息
        "tool_execution_start": "开始执行工具",
        "tool_execution_complete": "工具执行完成",
        "tools_count": "个工具",
        "success_count": "成功",
        "failed_count": "失败", 
        "time_spent": "耗时",
        "total_count": "共",
        "colon": "：",
        "comma": "，",
        
        # 工具名称
        "tool_crypto_price": "加密货币价格",
        "tool_indicators": "技术指标",
        "tool_market_data": "实时市场数据", 
        "tool_historical_data": "历史数据",
        "tool_finnhub_news": "Finnhub新闻",
        "tool_reddit_sentiment": "Reddit情绪",
        "tool_sentiment_batch": "批量情绪分析",
        "tool_fear_greed": "恐惧贪婪指数",
        
        # 🔴 新增：阶段名称
        "phase2_debate_name": "投资辩论",
        "phase3_trading_name": "交易策略", 
        "phase4_risk_name": "风险评估",
        "phase5_decision_name": "组合管理",
        
        # 🔴 新增：进入阶段消息
        "entering_phase2": "进入第二阶段：投资辩论",
        "entering_phase3": "进入第三阶段：交易策略",
        "entering_phase4": "进入第四阶段：风险评估",
        "entering_phase5": "进入第五阶段：组合管理",
        
        # 🔴 新增：开始轮次消息（支持格式化）
        "starting_debate_round": "开始第{current}轮辩论（总共：{total}轮）",
        "starting_risk_round": "开始第{current}轮风险分析（总共：{total}轮）",
        
        # 🔴 新增：结束消息
        "debate_ended": "投资辩论结束，完成{rounds}轮",
        "risk_assessment_ended": "风险评估结束，完成{rounds}轮分析",
        
        # 🔴 新增：系统初始化消息
        "initializing_analysis_system": "正在初始化分析系统...",
        "analysis_system_init_complete": "分析系统初始化完成",
        "system_ready": "系统就绪"
    }
}


def get_message(key: str, language: str = "zh-CN", fallback_language: str = "en-US", **format_args) -> str:
    """
    获取指定语言的消息文本，支持格式化参数
    
    Args:
        key: 消息键名
        language: 目标语言代码 (如 'zh-CN', 'en-US')
        fallback_language: 回退语言代码
        **format_args: 格式化参数 (如 current=1, total=3)
        
    Returns:
        翻译后的消息文本
    """
    # 验证语言支持
    if language not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language: {language}, falling back to {fallback_language}")
        language = fallback_language
    
    # 获取消息
    messages = MESSAGES.get(language, {})
    if key in messages:
        message = messages[key]
        # 如果有格式化参数，应用格式化
        if format_args:
            try:
                return message.format(**format_args)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to format message '{key}' with args {format_args}: {e}")
                return message
        return message
    
    # 回退到备用语言
    fallback_messages = MESSAGES.get(fallback_language, {})
    if key in fallback_messages:
        logger.warning(f"Message key '{key}' not found in {language}, using {fallback_language}")
        message = fallback_messages[key]
        # 如果有格式化参数，应用格式化
        if format_args:
            try:
                return message.format(**format_args)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to format fallback message '{key}' with args {format_args}: {e}")
                return message
        return message
    
    # 最终回退
    logger.error(f"Message key '{key}' not found in any language")
    return key  # 返回原始键名作为最后的回退


def get_agent_name(agent_type: str, language: str = "zh-CN") -> str:
    """
    获取Agent的本地化名称
    
    Args:
        agent_type: Agent类型 (如 'market', 'news', 'social_media')
        language: 语言代码
        
    Returns:
        本地化的Agent名称
    """
    # 映射Agent类型到消息键
    agent_key_mapping = {
        'market': 'market_analyst',
        'news': 'news_analyst',
        'social_media': 'social_media_analyst',
        'bull': 'bull_researcher',
        'bear': 'bear_researcher',
        'risk': 'risk_manager', 
        'research': 'research_manager',
        'trader': 'trader',
        'conservative': 'conservative_debator',
        'aggressive': 'aggressive_debator',
        'neutral': 'neutral_debator',
    }
    
    message_key = agent_key_mapping.get(agent_type, agent_type)
    return get_message(message_key, language)


def get_language_display_name(language: str) -> str:
    """
    获取语言的显示名称
    
    Args:
        language: 语言代码
        
    Returns:
        语言显示名称
    """
    return get_message("language_name", language)


def get_language_name_for_prompt(language: str) -> str:
    """
    获取用于Agent提示词的语言名称
    
    Args:
        language: 语言代码 (如 'zh-CN', 'en-US')
        
    Returns:
        语言名称 (如 'Simplified Chinese', 'English')
    """
    language_mapping = {
        'zh-CN': 'Simplified Chinese',
        'zh': 'Simplified Chinese', 
        'en-US': 'English',
        'en': 'English'
    }
    return language_mapping.get(language, 'English')


def get_tool_name(tool_id: str, language: str = "zh-CN") -> str:
    """
    获取工具的本地化名称
    
    Args:
        tool_id: 工具ID (如 'crypto_price', 'indicators')
        language: 语言代码
        
    Returns:
        本地化的工具名称
    """
    tool_key = f"tool_{tool_id}"
    return get_message(tool_key, language)


# Agent类型到英文名称的标准映射（用于提示词注入）
AGENT_TYPE_TO_ENGLISH_NAME = {
    'market': 'Market Analyst',
    'news': 'News Analyst', 
    'social_media': 'Social Media Analyst',
    'bull': 'Bull Researcher',
    'bear': 'Bear Researcher',
    'risk': 'Risk Manager',
    'research': 'Research Manager', 
    'trader': 'Trader',
    'conservative': 'Conservative Analyst',
    'aggressive': 'Aggressive Analyst',
    'neutral': 'Neutral Analyst',
}