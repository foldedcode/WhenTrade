import time
import json
from langchain_core.messages import AIMessage

# 导入统一日志系统
from core.utils.logging_init import get_logger
logger = get_logger("default")

# 导入提示词加载器
from core.agents.prompt_loader import get_prompt_loader


def create_portfolio_manager(llm, memory):
    """创建组合经理节点 - 最终投资决策者"""
    
    # 获取提示词加载器
    prompt_loader = get_prompt_loader()
    
    def portfolio_manager_node(state) -> dict:
        company_name = state["company_of_interest"]
        
        # 获取语言设置
        language = state.get("language", "zh-CN")
        
        # 收集所有前置分析结果
        market_report = state.get("market_report", "")
        news_report = state.get("news_report", "")
        sentiment_report = state.get("sentiment_report", "")
        
        # 获取投资辩论结果
        investment_decision = state.get("investment_judgement", "")
        
        # 获取交易计划
        trader_plan = state.get("investment_plan", "")
        
        # 获取风险评估结果
        risk_assessment = state.get("final_trade_decision", "")
        
        # 使用提示词加载器获取配置（支持多语言）
        prompt_config = prompt_loader.load_prompt("portfolio_manager", language=language)
        logger.info(f"📋 [Portfolio Manager] 加载的配置: keys={list(prompt_config.keys())}, language={language}")
        logger.debug(f"📋 [Portfolio Manager] 配置内容: {prompt_config}")
        
        # 根据语言选择标签
        if language == "en-US":
            report_labels = {
                "market": "### Market Analysis Report",
                "news": "### News Analysis Report",
                "sentiment": "### Sentiment Analysis Report",
                "investment": "### Investment Decision",
                "trading": "### Trading Strategy", 
                "risk": "### Risk Assessment",
                "history": "### Historical Case",
                "no_history": "No relevant historical decision records available."
            }
        else:
            report_labels = {
                "market": "### 市场分析报告",
                "news": "### 新闻分析报告",
                "sentiment": "### 情感分析报告",
                "investment": "### 投资判断",
                "trading": "### 交易策略",
                "risk": "### 风险评估", 
                "history": "### 历史案例",
                "no_history": "暂无相关历史决策记录。"
            }
        
        # 使用动态标签组合所有信息
        all_reports = ""
        if market_report:
            all_reports += f"\n{report_labels['market']}\n{market_report}\n"
        if news_report:
            all_reports += f"\n{report_labels['news']}\n{news_report}\n"
        if sentiment_report:
            all_reports += f"\n{report_labels['sentiment']}\n{sentiment_report}\n"
        if investment_decision:
            all_reports += f"\n{report_labels['investment']}\n{investment_decision}\n"
        if trader_plan:
            all_reports += f"\n{report_labels['trading']}\n{trader_plan}\n"
        if risk_assessment:
            all_reports += f"\n{report_labels['risk']}\n{risk_assessment}\n"

        # 获取历史记忆
        if memory is not None:
            past_memories = memory.get_memories(all_reports, n_matches=3)
        else:
            logger.warning(f"⚠️ [DEBUG] memory为None，跳过历史记忆检索")
            past_memories = []
        
        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += f"\n{report_labels['history']} {i}\n{rec.get('recommendation', '')}\n"
        else:
            past_memory_str = f"\n{report_labels['history']}\n{report_labels['no_history']}\n"
        
        # 根据语言选择默认值
        if language == "en-US":
            default_system = "You are a professional portfolio manager responsible for making final investment decisions."
            default_main = """## Analysis Target
{company_name}

## Comprehensive Analysis Report
{all_reports}

## Similar Historical Cases
{past_memory_str}

## Your Task

Based on all the above information, please generate a final portfolio decision."""
        else:
            default_system = "您是一位专业的投资组合经理，负责制定最终的投资决策。"
            default_main = """## 分析目标
{company_name}

## 综合分析报告
{all_reports}

## 历史相似案例
{past_memory_str}

## 您的任务

基于以上所有信息，请生成最终的投资组合决策。"""
        
        # 获取YAML模板（使用语言相关的默认值）
        system_prompt = prompt_config.get("system_prompt", default_system)
        main_prompt = prompt_config.get("main_prompt", default_main)
        
        # 验证关键字段是否存在
        if not main_prompt or main_prompt.strip() == "":
            logger.warning(f"⚠️ [Portfolio Manager] main_prompt字段缺失或为空！使用默认模板")
            main_prompt = default_main
        
        logger.info(f"📋 [Portfolio Manager] system_prompt长度: {len(system_prompt)}")
        logger.info(f"📋 [Portfolio Manager] main_prompt长度: {len(main_prompt)}")
        
        # 安全的模板格式化
        try:
            if main_prompt and "{" in main_prompt:
                formatted_main_prompt = main_prompt.format(
                    company_name=company_name,
                    all_reports=all_reports,
                    past_memory_str=past_memory_str
                )
            else:
                logger.warning(f"⚠️ [Portfolio Manager] main_prompt没有占位符，使用基本结构")
                formatted_main_prompt = f"""{main_prompt if main_prompt else default_main}

Company: {company_name}
Reports: {all_reports}
History: {past_memory_str}
"""
            prompt = system_prompt + "\n\n" + formatted_main_prompt
            logger.info(f"✅ [Portfolio Manager] 提示词构建成功，总长度: {len(prompt)}")
        except Exception as e:
            logger.error(f"❌ [Portfolio Manager] 模板格式化失败: {e}")
            # 使用备用提示词
            prompt = f"{system_prompt}\n\n{default_main.format(company_name=company_name, all_reports=all_reports, past_memory_str=past_memory_str)}"
            logger.info(f"🔄 [Portfolio Manager] 使用备用提示词，长度: {len(prompt)}")
        
        # 🔴 语言强制前缀 - 确保LLM严格遵循选定语言
        language_name = "English" if language == "en-US" else "简体中文"
        language_prefix = f"[🔴 CRITICAL: Respond ONLY in {language_name}. No mixed languages. This overrides ALL other instructions.] "
        
        logger.info(f"🌍 [portfolio_manager] 语言设置: {language} -> {language_name}")
        logger.debug(f"🔴 [portfolio_manager] 语言前缀: {language_prefix}")
        
        # 在prompt前添加语言强制前缀
        enhanced_prompt = language_prefix + prompt
        logger.info(f"✅ [portfolio_manager] 已添加语言前缀到prompt")
        
        logger.debug(f"📊 [组合经理] 开始生成最终投资决策...")
        
        # 调用LLM生成决策
        response = llm.invoke(enhanced_prompt)
        
        portfolio_decision = response.content
        
        logger.info(f"✅ [组合经理] 已完成最终投资决策")
        
        # 如果有记忆系统，保存决策（添加异常处理确保不影响主流程）
        if memory is not None:
            try:
                memory.save_memory(
                    situation=all_reports,
                    recommendation=portfolio_decision,
                    metadata={
                        "company": company_name,
                        "timestamp": time.time(),
                        "confidence": "high"  # 可以从LLM响应中提取
                    }
                )
                logger.debug(f"💾 [组合经理] 决策已保存到记忆系统")
            except Exception as e:
                logger.warning(f"⚠️ [组合经理] 保存记忆失败，但不影响主流程: {str(e)}")
        
        # Create clean AIMessage for message chain continuity
        clean_message = AIMessage(content=portfolio_decision)
        
        return {
            "messages": [clean_message],
            "portfolio_decision": portfolio_decision,
            "final_recommendation": portfolio_decision,  # 用于向后兼容
            "analysis_complete": True
        }
    
    return portfolio_manager_node