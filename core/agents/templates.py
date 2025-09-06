"""
Agent模板系统
定义各种可动态创建的agent模板
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass


class TemplateType(str, Enum):
    """Template types"""
    ANALYST = "analyst"          # Analyst template
    RESEARCHER = "researcher"    # Researcher template
    SPECIALIST = "specialist"    # Specialist template
    STRATEGIST = "strategist"    # Strategist template
    VALIDATOR = "validator"      # Validator template


@dataclass
class AgentTemplate:
    """Agent template definition"""
    template_id: str
    name: str
    description: str
    template_type: TemplateType
    base_prompt: str
    expertise_areas: List[str]
    default_domain: str
    thought_patterns: Dict[str, str]  # Thought patterns
    analysis_structure: Dict[str, Any]  # Analysis structure
    required_capabilities: List[str]  # Required capabilities
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type.value,
            "base_prompt": self.base_prompt,
            "expertise_areas": self.expertise_areas,
            "default_domain": self.default_domain,
            "thought_patterns": self.thought_patterns,
            "analysis_structure": self.analysis_structure,
            "required_capabilities": self.required_capabilities
        }


class TemplateLibrary:
    """Template Library - manages all available agent templates"""
    
    def __init__(self):
        self.templates: Dict[str, AgentTemplate] = {}
        self._initialize_default_templates()
        
    def _initialize_default_templates(self):
        """Initialize default templates"""
        
        # 1. Industry Expert Template
        self.add_template(AgentTemplate(
            template_id="industry_expert",
            name="Industry Expert",
            description="Expert with deep understanding of specific industries",
            template_type=TemplateType.SPECIALIST,
            base_prompt="""
            作为{industry}行业的资深专家，你需要：
            1. 分析行业发展趋势和周期位置
            2. 评估竞争格局和市场份额变化
            3. 识别行业特有的风险和机会
            4. 预测政策和技术变革的影响
            
            请基于以下数据进行分析：
            {data}
            
            重点关注：
            - 行业增长驱动因素
            - 供需平衡状况
            - 技术创新影响
            - 监管政策变化
            - 竞争格局演变
            """,
            expertise_areas=["industry_analysis", "competitive_landscape", "trend_prediction"],
            default_domain="Industry Analysis",
            thought_patterns={
                "observation": "识别行业现状和关键数据",
                "analysis": "深入分析行业动态和驱动因素",
                "conclusion": "总结行业前景和投资机会",
                "question": "提出需要进一步调研的问题"
            },
            analysis_structure={
                "sections": ["行业概况", "竞争分析", "增长动力", "风险因素", "投资建议"],
                "data_requirements": ["industry_data", "competitor_data", "market_share"],
                "output_format": "structured_json"
            },
            required_capabilities=["industry_knowledge", "trend_analysis", "competitive_intelligence"]
        ))
        
        # 2. 量化分析师模板
        self.add_template(AgentTemplate(
            template_id="quant_analyst",
            name="量化分析师",
            description="使用数学模型和统计方法分析市场",
            template_type=TemplateType.ANALYST,
            base_prompt="""
            作为量化分析师，运用数学和统计方法分析{target}：
            
            数据概览：
            {data}
            
            请进行以下量化分析：
            1. 统计特征分析（均值、方差、偏度、峰度）
            2. 相关性和协整性检验
            3. 时间序列分析（趋势、季节性、周期性）
            4. 风险度量（VaR、CVaR、最大回撤）
            5. 因子暴露和归因分析
            
            使用的模型：
            - GARCH模型（波动率预测）
            - 均值回归模型
            - 动量因子模型
            - 配对交易模型
            
            输出量化指标和交易信号。
            """,
            expertise_areas=["quantitative_analysis", "statistical_modeling", "risk_metrics"],
            default_domain="量化分析",
            thought_patterns={
                "observation": "识别数据的统计特征",
                "analysis": "应用量化模型进行深入分析",
                "conclusion": "生成量化交易信号",
                "question": "模型假设是否成立？"
            },
            analysis_structure={
                "models": ["time_series", "factor_model", "risk_model"],
                "metrics": ["sharpe_ratio", "information_ratio", "maximum_drawdown"],
                "output_format": "quantitative_report"
            },
            required_capabilities=["statistical_analysis", "mathematical_modeling", "programming"]
        ))
        
        # 3. ESG分析专家模板
        self.add_template(AgentTemplate(
            template_id="esg_specialist",
            name="ESG分析专家",
            description="评估环境、社会和治理因素",
            template_type=TemplateType.SPECIALIST,
            base_prompt="""
            作为ESG分析专家，评估{target}的可持续发展表现：
            
            ESG数据：
            {data}
            
            请分析：
            1. 环境因素（E）
               - 碳排放和气候风险
               - 资源使用效率
               - 环境合规性
            
            2. 社会因素（S）
               - 员工福利和多样性
               - 供应链责任
               - 社区影响
            
            3. 治理因素（G）
               - 董事会结构
               - 股东权益保护
               - 透明度和道德标准
            
            4. ESG风险和机会
            5. 对财务表现的影响
            
            提供ESG评分和改进建议。
            """,
            expertise_areas=["esg_analysis", "sustainability", "corporate_governance"],
            default_domain="ESG分析",
            thought_patterns={
                "observation": "收集ESG相关数据和事件",
                "analysis": "评估ESG表现和风险",
                "conclusion": "总结ESG评分和影响",
                "question": "是否存在未披露的ESG风险？"
            },
            analysis_structure={
                "categories": ["environmental", "social", "governance"],
                "scoring_method": "weighted_average",
                "risk_factors": ["climate_risk", "regulatory_risk", "reputation_risk"]
            },
            required_capabilities=["esg_knowledge", "sustainability_analysis", "risk_assessment"]
        ))
        
        # 4. 宏观经济学家模板
        self.add_template(AgentTemplate(
            template_id="macro_economist",
            name="宏观经济学家",
            description="分析宏观经济环境和政策影响",
            template_type=TemplateType.SPECIALIST,
            base_prompt="""
            作为宏观经济学家，分析当前经济环境对{target}的影响：
            
            宏观数据：
            {data}
            
            请评估：
            1. 经济周期位置和趋势
            2. 货币政策影响
               - 利率走向
               - 流动性状况
               - 汇率波动
            
            3. 财政政策影响
               - 政府支出
               - 税收政策
               - 产业政策
            
            4. 全球经济联动
               - 贸易关系
               - 地缘政治
               - 供应链风险
            
            5. 对特定资产的影响机制
            
            提供宏观视角的投资建议。
            """,
            expertise_areas=["macroeconomics", "monetary_policy", "global_markets"],
            default_domain="宏观分析",
            thought_patterns={
                "observation": "识别关键宏观指标变化",
                "analysis": "分析经济传导机制",
                "conclusion": "评估对投资标的的影响",
                "question": "是否存在未被市场认识的宏观风险？"
            },
            analysis_structure={
                "indicators": ["gdp", "inflation", "interest_rates", "unemployment"],
                "policy_tools": ["monetary", "fiscal", "regulatory"],
                "transmission_channels": ["credit", "wealth_effect", "exchange_rate"]
            },
            required_capabilities=["economic_theory", "policy_analysis", "global_perspective"]
        ))
        
        # 5. 技术创新评估师模板
        self.add_template(AgentTemplate(
            template_id="tech_innovation_assessor",
            name="技术创新评估师",
            description="评估技术创新和颠覆性潜力",
            template_type=TemplateType.RESEARCHER,
            base_prompt="""
            作为技术创新评估师，分析{target}的技术竞争力：
            
            技术相关数据：
            {data}
            
            请评估：
            1. 核心技术实力
               - 专利组合
               - 研发投入
               - 技术壁垒
            
            2. 创新能力
               - 新产品开发
               - 技术迭代速度
               - 创新文化
            
            3. 技术趋势把握
               - 新兴技术布局
               - 技术路线选择
               - 生态系统构建
            
            4. 颠覆性风险和机会
               - 被颠覆风险
               - 颠覆他人潜力
               - 转型能力
            
            5. 技术商业化能力
            
            提供技术视角的竞争力评估。
            """,
            expertise_areas=["technology_assessment", "innovation_analysis", "disruption_risk"],
            default_domain="技术分析",
            thought_patterns={
                "observation": "识别关键技术指标和创新动态",
                "analysis": "评估技术竞争优势和风险",
                "conclusion": "预测技术发展对业务的影响",
                "question": "是否存在潜在的技术颠覆？"
            },
            analysis_structure={
                "metrics": ["r&d_intensity", "patent_count", "innovation_index"],
                "assessment_areas": ["core_tech", "innovation_capability", "commercialization"],
                "risk_factors": ["disruption", "obsolescence", "competition"]
            },
            required_capabilities=["technology_understanding", "innovation_assessment", "trend_analysis"]
        ))
        
    def add_template(self, template: AgentTemplate):
        """添加模板到库"""
        self.templates[template.template_id] = template
        
    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """获取指定模板"""
        return self.templates.get(template_id)
        
    def list_templates(self, template_type: Optional[TemplateType] = None) -> List[AgentTemplate]:
        """列出模板"""
        templates = list(self.templates.values())
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]
        return templates
        
    def search_templates(self, keyword: str) -> List[AgentTemplate]:
        """搜索模板"""
        keyword_lower = keyword.lower()
        results = []
        
        for template in self.templates.values():
            # 搜索名称、描述和专长领域
            if (keyword_lower in template.name.lower() or
                keyword_lower in template.description.lower() or
                any(keyword_lower in area.lower() for area in template.expertise_areas)):
                results.append(template)
                
        return results


# 创建全局模板库实例
global_template_library = TemplateLibrary()