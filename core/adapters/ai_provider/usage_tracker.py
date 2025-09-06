"""
AI 使用量追踪适配器
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Any
from dataclasses import dataclass

from core.config import settings


@dataclass
class ModelPricing:
    """模型定价信息"""
    input_price_per_1k: Decimal  # 每1000个输入token的价格
    output_price_per_1k: Decimal  # 每1000个输出token的价格
    currency: str = "USD"


class UsageTracker:
    """AI 使用量追踪器"""
    
    # 模型定价信息（2024年的参考价格）
    MODEL_PRICING = {
        # OpenAI 模型
        "gpt-4": ModelPricing(
            input_price_per_1k=Decimal("0.03"),
            output_price_per_1k=Decimal("0.06")
        ),
        "gpt-4-turbo": ModelPricing(
            input_price_per_1k=Decimal("0.01"),
            output_price_per_1k=Decimal("0.03")
        ),
        "gpt-3.5-turbo": ModelPricing(
            input_price_per_1k=Decimal("0.0005"),
            output_price_per_1k=Decimal("0.0015")
        ),
        "gpt-3.5-turbo-16k": ModelPricing(
            input_price_per_1k=Decimal("0.003"),
            output_price_per_1k=Decimal("0.004")
        ),
        
        # Anthropic 模型
        "claude-3-opus": ModelPricing(
            input_price_per_1k=Decimal("0.015"),
            output_price_per_1k=Decimal("0.075")
        ),
        "claude-3-sonnet": ModelPricing(
            input_price_per_1k=Decimal("0.003"),
            output_price_per_1k=Decimal("0.015")
        ),
        "claude-3-haiku": ModelPricing(
            input_price_per_1k=Decimal("0.00025"),
            output_price_per_1k=Decimal("0.00125")
        ),
        "claude-2.1": ModelPricing(
            input_price_per_1k=Decimal("0.008"),
            output_price_per_1k=Decimal("0.024")
        ),
        
        # DeepSeek 模型
        "deepseek-chat": ModelPricing(
            input_price_per_1k=Decimal("0.0001"),
            output_price_per_1k=Decimal("0.0002")
        ),
        "deepseek-coder": ModelPricing(
            input_price_per_1k=Decimal("0.0001"),
            output_price_per_1k=Decimal("0.0002")
        ),
        
        # 其他模型
        "llama-2-70b": ModelPricing(
            input_price_per_1k=Decimal("0.001"),
            output_price_per_1k=Decimal("0.001")
        ),
        "mixtral-8x7b": ModelPricing(
            input_price_per_1k=Decimal("0.0007"),
            output_price_per_1k=Decimal("0.0007")
        ),
    }
    
    def __init__(self, custom_pricing: Optional[Dict[str, ModelPricing]] = None):
        """初始化使用量追踪器
        
        Args:
            custom_pricing: 自定义模型定价，会覆盖默认定价
        """
        self.pricing = self.MODEL_PRICING.copy()
        if custom_pricing:
            self.pricing.update(custom_pricing)
    
    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """计算使用成本
        
        Args:
            model_name: 模型名称
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            
        Returns:
            成本金额（USD）
        """
        # 标准化模型名称
        normalized_model = self._normalize_model_name(model_name)
        
        # 获取定价信息
        pricing = self.pricing.get(normalized_model)
        if not pricing:
            # 未知模型使用默认定价
            pricing = ModelPricing(
                input_price_per_1k=Decimal("0.001"),
                output_price_per_1k=Decimal("0.001")
            )
        
        # 计算成本
        input_cost = (Decimal(input_tokens) / 1000) * pricing.input_price_per_1k
        output_cost = (Decimal(output_tokens) / 1000) * pricing.output_price_per_1k
        
        total_cost = input_cost + output_cost
        
        # 保留6位小数
        return total_cost.quantize(Decimal("0.000001"))
    
    def _normalize_model_name(self, model_name: str) -> str:
        """标准化模型名称
        
        将各种变体的模型名称标准化为定价表中的键
        """
        model_lower = model_name.lower()
        
        # GPT-4 变体
        if "gpt-4" in model_lower:
            if "turbo" in model_lower or "1106" in model_lower:
                return "gpt-4-turbo"
            return "gpt-4"
        
        # GPT-3.5 变体
        if "gpt-3.5" in model_lower:
            if "16k" in model_lower:
                return "gpt-3.5-turbo-16k"
            return "gpt-3.5-turbo"
        
        # Claude 变体
        if "claude" in model_lower:
            if "opus" in model_lower:
                return "claude-3-opus"
            elif "sonnet" in model_lower:
                return "claude-3-sonnet"
            elif "haiku" in model_lower:
                return "claude-3-haiku"
            elif "2.1" in model_lower:
                return "claude-2.1"
        
        # DeepSeek 变体
        if "deepseek" in model_lower:
            if "coder" in model_lower:
                return "deepseek-coder"
            return "deepseek-chat"
        
        # 其他模型
        if "llama" in model_lower and "70b" in model_lower:
            return "llama-2-70b"
        if "mixtral" in model_lower:
            return "mixtral-8x7b"
        
        # 返回原始名称
        return model_name
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            包含模型名称、定价等信息的字典
        """
        normalized_model = self._normalize_model_name(model_name)
        pricing = self.pricing.get(normalized_model)
        
        if not pricing:
            pricing = ModelPricing(
                input_price_per_1k=Decimal("0.001"),
                output_price_per_1k=Decimal("0.001")
            )
        
        return {
            "model_name": model_name,
            "normalized_name": normalized_model,
            "input_price_per_1k": float(pricing.input_price_per_1k),
            "output_price_per_1k": float(pricing.output_price_per_1k),
            "currency": pricing.currency,
            "is_custom_pricing": normalized_model not in self.MODEL_PRICING
        }
    
    def estimate_cost(
        self,
        model_name: str,
        estimated_tokens: int,
        input_ratio: float = 0.3
    ) -> Dict[str, Decimal]:
        """估算成本
        
        Args:
            model_name: 模型名称
            estimated_tokens: 预估的总token数
            input_ratio: 输入token占比（默认30%）
            
        Returns:
            包含预估成本信息的字典
        """
        input_tokens = int(estimated_tokens * input_ratio)
        output_tokens = estimated_tokens - input_tokens
        
        cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        
        return {
            "estimated_input_tokens": input_tokens,
            "estimated_output_tokens": output_tokens,
            "estimated_total_tokens": estimated_tokens,
            "estimated_cost": cost,
            "currency": "USD"
        }
    
    def get_all_model_pricing(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的定价信息"""
        result = {}
        for model_name, pricing in self.pricing.items():
            result[model_name] = {
                "input_price_per_1k": float(pricing.input_price_per_1k),
                "output_price_per_1k": float(pricing.output_price_per_1k),
                "currency": pricing.currency
            }
        return result
    
    def update_model_pricing(
        self,
        model_name: str,
        input_price_per_1k: Decimal,
        output_price_per_1k: Decimal,
        currency: str = "USD"
    ):
        """更新模型定价
        
        允许动态更新模型的定价信息
        """
        self.pricing[model_name] = ModelPricing(
            input_price_per_1k=input_price_per_1k,
            output_price_per_1k=output_price_per_1k,
            currency=currency
        )