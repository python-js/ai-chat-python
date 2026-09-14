from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
