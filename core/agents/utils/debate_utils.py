"""
Analysis utility functions - Linus style: Clean data structures drive behavior
通过正确的数据结构设计，让系统行为自然正确

Core philosophy: 不设定对抗性辩论，只做角色化专业分析
- Bull analyst: 从看涨角度提供专业分析
- Bear analyst: 从看跌角度提供专业分析  
- 自然的观点交换，无需强制反驳或对抗
"""

from typing import Dict, List, Optional

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")


def generate_independent_analysis_prompt(
    role: str,
    company_name: str,
    available_data: Dict[str, str],
    available_data_types: List[str],
    market_info: Dict[str, str]
) -> str:
    """
    生成独立分析提示词 - 纯粹基于数据的专业角色分析
    Linus: No special cases, just data-driven behavior
    """
    # 构建数据内容
    data_sections = []
    for data_type in available_data_types:
        if data_type == "技术分析" and available_data.get("market"):
            data_sections.append(f"【技术分析数据】\n{available_data['market']}")
        elif data_type == "市场情绪" and available_data.get("sentiment"):
            data_sections.append(f"【市场情绪数据】\n{available_data['sentiment']}")
        elif data_type == "新闻资讯" and available_data.get("news"):
            data_sections.append(f"【新闻资讯数据】\n{available_data['news']}")
        elif data_type == "基本面" and available_data.get("fundamentals"):
            data_sections.append(f"【基本面数据】\n{available_data['fundamentals']}")
    
    data_content = "\n\n".join(data_sections) if data_sections else "暂无可用数据"
    
    # 构建角色特定的分析指导 - 无对抗性语言
    if role == "bull":
        analysis_guidance = "作为专业的看涨分析师，基于现有数据提供你的专业看涨分析。重点关注增长潜力、竞争优势和积极指标。"
        role_description = "专业看涨分析师"
    else:  # bear
        analysis_guidance = "作为专业的看跌分析师，基于现有数据提供你的专业看跌分析。重点关注潜在风险、挑战因素和负面指标。"
        role_description = "专业看跌分析师"
    
    prompt = f"""你是{company_name}的{role_description}。

当前市场：{market_info.get('market_name', '未知')}
货币单位：{market_info.get('currency', '未知')}（{market_info.get('currency_symbol', '')}）

【可用数据类型】
{', '.join(available_data_types) if available_data_types else '无'}

【数据内容】
{data_content}

【分析要求】
{analysis_guidance}

【专业约束】
1. 严格基于上述提供的数据进行分析
2. 每个观点必须有具体数据支撑
3. 禁止分析没有数据支持的领域
4. 提供独立的专业分析观点

请用中文提供你的专业分析。"""
    
    logger.debug(f"📝 [{role.upper()}] 生成独立分析提示词，数据类型: {available_data_types}")
    return prompt


def generate_viewpoint_exchange_prompt(
    role: str,
    company_name: str,
    available_data: Dict[str, str],
    available_data_types: List[str],
    other_analyst_view: str,
    my_previous_view: str,
    market_info: Dict[str, str]
) -> str:
    """
    生成观点交换提示词 - 基于同行观点的协作分析，非对抗性
    Linus: Clean separation of concerns - 协作而非对抗
    """
    # 构建数据内容
    data_sections = []
    for data_type in available_data_types:
        if data_type == "技术分析" and available_data.get("market"):
            data_sections.append(f"【技术分析数据】\n{available_data['market']}")
        elif data_type == "市场情绪" and available_data.get("sentiment"):
            data_sections.append(f"【市场情绪数据】\n{available_data['sentiment']}")
        elif data_type == "新闻资讯" and available_data.get("news"):
            data_sections.append(f"【新闻资讯数据】\n{available_data['news']}")
        elif data_type == "基本面" and available_data.get("fundamentals"):
            data_sections.append(f"【基本面数据】\n{available_data['fundamentals']}")
    
    data_content = "\n\n".join(data_sections) if data_sections else "暂无可用数据"
    
    role_description = "专业看涨分析师" if role == "bull" else "专业看跌分析师"
    other_role = "看跌分析师" if role == "bull" else "看涨分析师"
    
    prompt = f"""你是{company_name}的{role_description}。

当前市场：{market_info.get('market_name', '未知')}
货币单位：{market_info.get('currency', '未知')}（{market_info.get('currency_symbol', '')}）

【{other_role}的观点】
{other_analyst_view}

【你此前的分析】
{my_previous_view}

【可用数据类型】
{', '.join(available_data_types) if available_data_types else '无'}

【数据内容】
{data_content}

【分析任务】
现在你看到了{other_role}基于相同数据的专业分析。请：
1. 从你的专业角度，基于数据提供更深入的{'看涨' if role == 'bull' else '看跌'}分析
2. 如果发现数据可以支撑不同的解读角度，请阐述你的理解
3. 保持你的专业立场，提供有价值的分析补充

【专业约束】
1. 严格基于上述提供的数据进行分析
2. 每个观点必须有具体数据支撑
3. 禁止分析没有数据支持的领域
4. 专业协作，非对抗性交流

请用中文提供你的专业分析。"""
    
    logger.debug(f"🔄 [{role.upper()}] 生成观点交换提示词，参考同行分析")
    return prompt


def get_other_analyst_view(analysis_state: Dict, my_role: str) -> str:
    """
    获取同行分析师的最新观点
    Linus: Single source of truth for peer analyst views
    """
    other_role = "bear" if my_role == "bull" else "bull"
    
    # 从观点交换获取  
    viewpoint_exchanges = analysis_state.get("viewpoint_exchanges", []) or analysis_state.get("debate_exchanges", [])
    if viewpoint_exchanges:
        # 获取最后一轮的同行观点
        last_exchange = viewpoint_exchanges[-1]
        return last_exchange.get(other_role, "")
    
    # Fallback: 从独立分析获取
    return analysis_state.get("initial_analyses", {}).get(other_role, "")


def get_my_previous_view(debate_state: Dict, my_role: str) -> str:
    """
    获取自己的上一个观点
    Linus: Consistent data access pattern
    """
    # 先尝试从辩论交流获取
    debate_exchanges = debate_state.get("debate_exchanges", [])
    if debate_exchanges:
        # 获取最后一轮的自己观点
        last_exchange = debate_exchanges[-1]
        if my_role in last_exchange:
            return last_exchange[my_role]
    
    # 否则从初始分析获取
    return debate_state.get("initial_analyses", {}).get(my_role, "")


def update_analysis_state(
    analysis_state: Dict,
    role: str,
    content: str,
    phase: str
) -> Dict:
    """
    更新分析状态 - 根据阶段正确更新数据结构
    Linus: Phase-aware state management - 协作分析而非对抗辩论
    """
    if phase == "initial":
        # 存储独立分析
        if "initial_analyses" not in analysis_state:
            analysis_state["initial_analyses"] = {}
        analysis_state["initial_analyses"][role] = content
        
        # 检查是否双方都完成独立分析
        if len(analysis_state["initial_analyses"]) == 2:
            # 转换到观点交换阶段
            analysis_state["current_phase"] = "viewpoint_exchange"
            analysis_state["round_number"] = 1
            logger.info("🔄 转换到观点交换阶段")
    
    else:  # viewpoint_exchange 
        # 更新观点交换
        if "viewpoint_exchanges" not in analysis_state:
            analysis_state["viewpoint_exchanges"] = []
        # Legacy compatibility
        if "debate_exchanges" not in analysis_state:
            analysis_state["debate_exchanges"] = []
        
        # 查找或创建当前轮次的交流记录
        current_round = analysis_state.get("round_number", 1)
        
        # 如果是新一轮，创建新的交流记录
        if len(analysis_state["viewpoint_exchanges"]) < current_round:
            analysis_state["viewpoint_exchanges"].append({})
        # Legacy compatibility
        if len(analysis_state["debate_exchanges"]) < current_round:
            analysis_state["debate_exchanges"].append({})
        
        # 更新当前轮次的分析
        analysis_state["viewpoint_exchanges"][current_round - 1][role] = content
        # Legacy compatibility
        analysis_state["debate_exchanges"][current_round - 1][role] = content
        
        # 检查是否双方都提供了分析
        current_exchange = analysis_state["viewpoint_exchanges"][current_round - 1]
        if "bull" in current_exchange and "bear" in current_exchange:
            # 轮次递增
            analysis_state["round_number"] = current_round + 1
            logger.info(f"🔄 完成第{current_round}轮观点交换")
    
    # 更新兼容字段
    analysis_state["count"] = analysis_state.get("count", 0) + 1
    
    return analysis_state


def gather_available_data(state: Dict) -> Dict[str, str]:
    """
    收集所有可用的数据
    Linus: Single function to gather all data
    """
    available_data = {}
    
    if state.get("market_report"):
        available_data["market"] = state["market_report"]
    
    if state.get("sentiment_report"):
        available_data["sentiment"] = state["sentiment_report"]
    
    if state.get("news_report"):
        available_data["news"] = state["news_report"]
    
    if state.get("fundamentals_report"):
        available_data["fundamentals"] = state["fundamentals_report"]
    
    return available_data


def identify_data_types(available_data: Dict[str, str]) -> List[str]:
    """
    识别可用的数据类型
    Linus: Clear mapping from data to types
    """
    data_types = []
    
    if available_data.get("market"):
        data_types.append("技术分析")
    
    if available_data.get("sentiment"):
        data_types.append("市场情绪")
    
    if available_data.get("news"):
        data_types.append("新闻资讯")
    
    if available_data.get("fundamentals"):
        data_types.append("基本面")
    
    return data_types


def is_first_round_analysis(debate_turns: List, current_speaker: str) -> bool:
    """
    判断当前是否为分析师的首轮分析
    Linus: Simple data structure check - 通过数据结构自然判断阶段
    
    Args:
        debate_turns: 辩论轮次列表
        current_speaker: 当前发言者 (bull, bear, risky, safe, neutral)
    
    Returns:
        bool: 如果是首轮分析返回True，否则返回False
    """
    # 如果没有辩论轮次，肯定是首轮
    if not debate_turns:
        return True
    
    # 检查当前发言者是否已经发过言
    for turn in debate_turns:
        if turn.get("speaker") == current_speaker:
            return False
    
    return True


def has_other_analysts_input(debate_turns: List, current_speaker: str) -> bool:
    """
    判断是否有其他分析师的输入可供参考
    Linus: Data-driven behavior - 根据数据决定行为模式
    
    Args:
        debate_turns: 辩论轮次列表  
        current_speaker: 当前发言者
    
    Returns:
        bool: 如果有其他分析师的输入返回True
    """
    if not debate_turns:
        return False
    
    # 检查是否有其他分析师的发言
    for turn in debate_turns:
        if turn.get("speaker") != current_speaker:
            return True
    
    return False


def get_analysis_context_for_prompt(
    debate_turns: List,
    current_speaker: str,
    other_speaker_content: str = ""
) -> Dict[str, str]:
    """
    根据轮次生成上下文信息用于提示词
    Linus: Phase-aware prompt generation - 根据阶段生成合适的上下文
    
    Args:
        debate_turns: 辩论轮次列表
        current_speaker: 当前发言者
        other_speaker_content: 其他发言者内容（兼容旧接口）
    
    Returns:
        Dict: 包含上下文信息的字典
    """
    is_first = is_first_round_analysis(debate_turns, current_speaker)
    has_others = has_other_analysts_input(debate_turns, current_speaker)
    
    if is_first and not has_others:
        # 首轮独立分析
        return {
            "analysis_mode": "independent",
            "context_description": "这是首轮分析，请提供独立的专业分析",
            "other_views": "",
            "interaction_instruction": "无需参考其他观点，专注于你的专业角度"
        }
    else:
        # 后续轮次或有其他观点可参考
        other_views = []
        for turn in debate_turns:
            if turn.get("speaker") != current_speaker:
                speaker_name = turn.get("speaker", "其他分析师")
                content = turn.get("content", "")
                if content:
                    other_views.append(f"【{speaker_name}观点】: {content[:200]}...")
        
        other_views_text = "\n".join(other_views) if other_views else other_speaker_content
        
        return {
            "analysis_mode": "collaborative", 
            "context_description": "有其他分析师观点可供参考，可以在此基础上深化分析",
            "other_views": other_views_text,
            "interaction_instruction": "可以指出不同观点，但保持专业和建设性"
        }