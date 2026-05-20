from typing import Annotated

from fastapi import Depends, Header


async def get_current_user() -> dict:
    # TODO: 实现 JWT 认证后替换
    return {"user_id": "anonymous", "role": "engineer"}


async def get_current_tenant(
    x_tenant_id: Annotated[int | None, Header()] = None,
) -> int:
    # TODO: 实现租户解析中间件后替换
    return x_tenant_id or 1


CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentTenant = Annotated[int, Depends(get_current_tenant)]
