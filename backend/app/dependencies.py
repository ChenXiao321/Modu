from typing import Annotated

from fastapi import Depends, Header, HTTPException


async def get_current_user() -> dict:
    # TODO: 实现 JWT 认证后替换
    return {"user_id": "anonymous", "role": "engineer"}


async def get_current_tenant(
    x_tenant_id: Annotated[int | None, Header()] = None,
) -> int:
    # TODO: 实现租户解析中间件后替换
    return x_tenant_id or 1


def _validate_document_id(document_id: str) -> str:
    """Validate that document_id length does not exceed DB column limit (36)."""
    if len(document_id) > 36:
        raise HTTPException(status_code=400, detail="document_id 长度不能超过 36 个字符") from None
    return document_id


CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentTenant = Annotated[int, Depends(get_current_tenant)]
