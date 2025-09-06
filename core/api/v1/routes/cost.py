from fastapi import APIRouter
from typing import Dict, Any, List

from core.services.llm_config_service import llm_config_service

router = APIRouter(prefix="/api/v1/cost", tags=["cost"])


_PROVIDER_CURRENCY: Dict[str, str] = {
    "openai": "USD",
    "google": "USD",
    "anthropic": "USD",
    "deepseek": "CNY",
    "kimi": "CNY",
}


@router.get("/models/pricing")
async def get_models_pricing() -> Dict[str, Any]:
    """Expose model pricing with currencies by provider.

    Falls back to sensible defaults when pricing is missing.
    """
    results: List[Dict[str, Any]] = []
    for provider_id, provider in llm_config_service.providers.items():
        currency = _PROVIDER_CURRENCY.get(provider_id.lower(), "USD")
        for model in provider.models:
            pricing = getattr(model, "pricing", None) or {}
            input_price = float(pricing.get("input", 0))
            output_price = float(pricing.get("output", 0))
            results.append(
                {
                    "provider": provider_id,
                    "provider_name": provider.name,
                    "model": model.id,
                    "model_name": model.name,
                    "input_price_per_1k": input_price,
                    "output_price_per_1k": output_price,
                    "currency": currency,
                }
            )

    return {"models": results}

