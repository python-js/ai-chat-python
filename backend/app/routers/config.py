"""系统配置读写：GET 返回「默认值 + 覆盖值」，PUT 全量校验保存。"""
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from ..app_config import DEFAULTS, load_config, save_config
from ..auth import get_user_id

router = APIRouter(prefix="/api")


@router.get("/config")
async def get_config(user_id: Annotated[str, Depends(get_user_id)]):
    return {"values": await load_config(), "defaults": DEFAULTS}


@router.put("/config")
async def put_config(
    user_id: Annotated[str, Depends(get_user_id)],
    body: dict = Body(...),
):
    values = body.get("values")
    if not isinstance(values, dict):
        raise HTTPException(status_code=400, detail="缺少 values 字段")
    try:
        saved = await save_config(values)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"values": saved, "defaults": DEFAULTS}
