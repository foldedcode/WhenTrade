"""
动态Agent工厂
根据模板和配置动态创建自定义agents
"""

import logging
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
import json

from .base import BaseAnalyst, ThoughtType
from .templates import AgentTemplate, TemplateType, global_template_library
from core.business.market_config import AnalysisDomain

logger = logging.getLogger(__name__)


class DynamicAgent(BaseAnalyst):
    """动态创建的Agent"""
    
    def __init__(self, llm: Any, template: AgentTemplate, custom_config: Optional[Dict[str, Any]] = None):
        """
        初始化动态Agent
        
        Args:
            llm: 语言模型实例
            template: Agent模板
            custom_config: 自定义配置，可覆盖模板默认值
        """
        # 应用自定义配置
        config = custom_config or {}
        name = config.get("name", template.name)
        domain = config.get("domain", template.default_domain)
        
        super().__init__(llm, name, domain)
        
        self.template = template
        self.custom_config = config
        self.expertise_areas = config.get("expertise_areas", template.expertise_areas)
        self.thought_patterns = config.get("thought_patterns", template.thought_patterns)
        self.analysis_structure = config.get("analysis_structure", template.analysis_structure)
        
    def get_expertise_areas(self) -> List[str]:
        """获取专长领域"""
        return self.expertise_areas
        
    def _get_default_domain(self) -> str:
        """获取默认分析领域"""
        return self.template.default_domain
        
    async def analyze(self, target: str, data: Dict[str, Any], depth: int = 3) -> Dict[str, Any]:
        """执行分析"""
        self.clear_thoughts()
        
        # 记录初始观察
        observation_pattern = self.thought_patterns.get("observation", "开始分析{target}")
        self.record_thought(
            ThoughtType.OBSERVATION,
            observation_pattern.format(target=target),
            confidence=0.9
        )
        
        # 准备分析数据
        analysis_data = self._prepare_analysis_data(data)
        
        # 构建分析提示
        prompt_params = {
            "target": target,
            "data": json.dumps(analysis_data, ensure_ascii=False, indent=2),
            "depth": depth,
            **self.custom_config.get("prompt_params", {})
        }
        
        # 处理模板中的行业等特定参数
        if "industry" in self.template.base_prompt:
            prompt_params["industry"] = self.custom_config.get("industry", "通用")
            
        analysis_prompt = self.template.base_prompt.format(**prompt_params)
        
        # 记录分析思考
        analysis_pattern = self.thought_patterns.get("analysis", "正在深入分析...")
        self.record_thought(
            ThoughtType.ANALYSIS,
            analysis_pattern,
            confidence=0.8
        )
        
        # 执行LLM分析
        response = await self.llm.generate(analysis_prompt)
        
        # 记录问题（如果有）
        if "question" in self.thought_patterns:
            self.record_thought(
                ThoughtType.QUESTION,
                self.thought_patterns["question"],
                confidence=0.7
            )
        
        # 记录结论
        conclusion_pattern = self.thought_patterns.get("conclusion", "分析完成")
        self.record_thought(
            ThoughtType.CONCLUSION,
            conclusion_pattern,
            confidence=0.85
        )
        
        return {
            "analyst_type": self.template.template_type.value,
            "analyst_role": "dynamic",
            "template_id": self.template.template_id,
            "analysis": response,
            "confidence_score": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
            "thought_stream": self.get_thought_stream()
        }
        
    def _prepare_analysis_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """准备分析数据"""
        # 根据模板的数据需求过滤和组织数据
        required_data = {}
        
        if "data_requirements" in self.analysis_structure:
            for requirement in self.analysis_structure["data_requirements"]:
                if requirement in raw_data:
                    required_data[requirement] = raw_data[requirement]
                    
        # 如果没有特定要求，返回所有数据
        return required_data if required_data else raw_data


class DynamicAgentFactory:
    """动态Agent工厂类"""
    
    def __init__(self, llm_factory: Any):
        self.llm_factory = llm_factory
        self.template_library = global_template_library
        self.created_agents: Dict[str, DynamicAgent] = {}
        
    def create_agent_from_template(
        self,
        template_id: str,
        custom_config: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ) -> Optional[DynamicAgent]:
        """
        从模板创建Agent
        
        Args:
            template_id: 模板ID
            custom_config: 自定义配置
            agent_id: 指定的agent ID，用于缓存
            
        Returns:
            创建的DynamicAgent实例，如果失败则返回None
        """
        # 获取模板
        template = self.template_library.get_template(template_id)
        if not template:
            logger.error(f"未找到模板: {template_id}")
            return None
            
        # 创建LLM实例
        llm = self.llm_factory.create_llm()
        
        # 创建动态Agent
        agent = DynamicAgent(llm, template, custom_config)
        
        # 缓存agent（如果提供了ID）
        if agent_id:
            self.created_agents[agent_id] = agent
            
        logger.info(f"成功创建动态Agent: {agent.name} (模板: {template_id})")
        return agent
        
    def create_custom_agent(
        self,
        name: str,
        domain: str,
        base_prompt: str,
        expertise_areas: List[str],
        thought_patterns: Optional[Dict[str, str]] = None,
        agent_id: Optional[str] = None
    ) -> DynamicAgent:
        """
        创建完全自定义的Agent（不使用模板）
        
        Args:
            name: Agent名称
            domain: 分析领域
            base_prompt: 基础提示词
            expertise_areas: 专长领域列表
            thought_patterns: 思考模式
            agent_id: 指定的agent ID
            
        Returns:
            创建的DynamicAgent实例
        """
        # 创建临时模板
        temp_template = AgentTemplate(
            template_id=f"custom_{agent_id or name}",
            name=name,
            description=f"自定义{name}",
            template_type=TemplateType.ANALYST,
            base_prompt=base_prompt,
            expertise_areas=expertise_areas,
            default_domain=domain,
            thought_patterns=thought_patterns or {
                "observation": f"开始进行{domain}分析",
                "analysis": "正在深入分析数据...",
                "conclusion": "分析完成，已生成见解"
            },
            analysis_structure={},
            required_capabilities=[]
        )
        
        # 创建LLM实例
        llm = self.llm_factory.create_llm()
        
        # 创建动态Agent
        agent = DynamicAgent(llm, temp_template)
        
        # 缓存agent
        if agent_id:
            self.created_agents[agent_id] = agent
            
        logger.info(f"成功创建自定义Agent: {name}")
        return agent
        
    def batch_create_agents(
        self,
        specifications: List[Dict[str, Any]]
    ) -> List[DynamicAgent]:
        """
        批量创建Agents
        
        Args:
            specifications: Agent规格列表，每个包含template_id和custom_config
            
        Returns:
            创建的Agent列表
        """
        agents = []
        
        for spec in specifications:
            template_id = spec.get("template_id")
            custom_config = spec.get("custom_config", {})
            agent_id = spec.get("agent_id")
            
            if template_id:
                agent = self.create_agent_from_template(template_id, custom_config, agent_id)
                if agent:
                    agents.append(agent)
            else:
                # 如果没有模板ID，尝试创建自定义agent
                if all(key in spec for key in ["name", "domain", "base_prompt", "expertise_areas"]):
                    agent = self.create_custom_agent(
                        name=spec["name"],
                        domain=spec["domain"],
                        base_prompt=spec["base_prompt"],
                        expertise_areas=spec["expertise_areas"],
                        thought_patterns=spec.get("thought_patterns"),
                        agent_id=agent_id
                    )
                    agents.append(agent)
                    
        logger.info(f"批量创建了{len(agents)}个Agents")
        return agents
        
    def get_created_agent(self, agent_id: str) -> Optional[DynamicAgent]:
        """获取已创建的Agent"""
        return self.created_agents.get(agent_id)
        
    def list_available_templates(self, template_type: Optional[TemplateType] = None) -> List[Dict[str, Any]]:
        """列出可用的模板"""
        templates = self.template_library.list_templates(template_type)
        return [t.to_dict() for t in templates]
        
    def recommend_agents_for_scenario(
        self,
        scenario: str,
        market_type: str,
        analysis_goals: List[str]
    ) -> List[Dict[str, Any]]:
        """
        根据场景推荐合适的Agents
        
        Args:
            scenario: 分析场景描述
            market_type: 市场类型
            analysis_goals: 分析目标列表
            
        Returns:
            推荐的Agent配置列表
        """
        recommendations = []
        
        # 基于场景关键词推荐
        scenario_lower = scenario.lower()
        
        # 行业分析场景
        if "行业" in scenario or "sector" in scenario_lower:
            recommendations.append({
                "template_id": "industry_expert",
                "custom_config": {
                    "industry": self._extract_industry(scenario)
                },
                "reason": "需要深入的行业专业知识"
            })
            
        # 量化分析场景
        if "量化" in scenario or "quant" in scenario_lower or "统计" in scenario:
            recommendations.append({
                "template_id": "quant_analyst",
                "reason": "需要数学模型和统计分析"
            })
            
        # ESG相关场景
        if "esg" in scenario_lower or "可持续" in scenario or "环境" in scenario:
            recommendations.append({
                "template_id": "esg_specialist",
                "reason": "需要评估ESG因素"
            })
            
        # 宏观分析场景
        if "宏观" in scenario or "经济" in scenario or "政策" in scenario:
            recommendations.append({
                "template_id": "macro_economist",
                "reason": "需要宏观经济视角"
            })
            
        # 技术创新场景
        if "技术" in scenario or "创新" in scenario or "科技" in scenario:
            recommendations.append({
                "template_id": "tech_innovation_assessor",
                "reason": "需要评估技术创新能力"
            })
            
        # 如果没有匹配的推荐，基于分析目标推荐
        if not recommendations:
            for goal in analysis_goals:
                if "风险" in goal:
                    recommendations.append({
                        "template_id": "quant_analyst",
                        "custom_config": {"focus": "risk_analysis"},
                        "reason": "需要量化风险分析"
                    })
                elif "长期" in goal or "价值" in goal:
                    recommendations.append({
                        "template_id": "industry_expert",
                        "reason": "需要长期价值评估"
                    })
                    
        return recommendations
        
    def _extract_industry(self, text: str) -> str:
        """从文本中提取行业信息"""
        # 简单的行业关键词匹配
        industries = {
            "科技": ["科技", "互联网", "软件", "半导体", "芯片"],
            "金融": ["金融", "银行", "保险", "证券"],
            "医药": ["医药", "医疗", "生物", "制药"],
            "消费": ["消费", "零售", "食品", "饮料"],
            "能源": ["能源", "石油", "电力", "新能源"],
            "制造": ["制造", "工业", "机械", "汽车"]
        }
        
        text_lower = text.lower()
        for industry, keywords in industries.items():
            if any(keyword in text for keyword in keywords):
                return industry
                
        return "通用"