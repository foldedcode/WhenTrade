"""
简单的认证模块
用于开发和测试
"""

from typing import Dict, Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict:
    """
    获取当前用户（简化版本）
    在生产环境中应该验证JWT token
    """
    # 开发环境：基于凭证生成用户信息
    if not credentials:
        user_id = "dev_user_anonymous"
        email = "anonymous@when.trade"
        role = "user"
    else:
        # 基于token生成用户信息（开发环境模拟）
        token_hash = hash(credentials.credentials) % 10000
        user_id = f"dev_user_{token_hash}"
        email = f"user_{token_hash}@when.trade"
        role = "admin" if token_hash % 10 == 0 else "user"
    
    return {
        "id": user_id,
        "email": email,
        "role": role
    }


async def require_admin(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """需要管理员权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user