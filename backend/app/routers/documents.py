"""GET/POST /api/documents：文档列表 / multipart 上传（校验同现有 Next route）。"""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile

from ..auth import get_user_id
from ..documents import (
    MAX_UPLOAD_BYTES,
    create_document_record,
    delete_document,
    list_documents,
    process_document,
    reprocess_document,
    sweep_stale,
)
from ..pdf import extract_pdf_text

router = APIRouter(prefix="/api")


@router.get("/documents")
async def documents(user_id: Annotated[str, Depends(get_user_id)]):
    # 懒收敛：顺带把心跳超时的死任务判死（幂等条件写，成本可忽略）
    await sweep_stale()
    return await list_documents()


@router.delete("/documents/{doc_id}")
async def remove_document(
    doc_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
):
    if not await delete_document(doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"ok": True}


@router.post("/documents")
# background_tasks: BackgroundTasks 为FastAPI 提供的依赖注入对象，用来注册"响应返回之后再执行"的任务。
async def upload(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_user_id)],
):
    name = file.filename or ""
    lower = name.lower()
    is_pdf = lower.endswith(".pdf")
    is_md = lower.endswith(".md") or lower.endswith(".markdown")
    if not is_pdf and not is_md:
        raise HTTPException(status_code=400, detail="仅支持 PDF 和 Markdown 文件")

    buffer = await file.read()
    if len(buffer) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件超过大小限制（4.5MB）")

    # 与 TS 行为对齐：非 UTF-8 字节以替换符处理而非报错
    text = extract_pdf_text(buffer) if is_pdf else buffer.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    doc = await create_document_record(name, "pdf" if is_pdf else "markdown", text)
    # fire-and-forget 向量化：响应不等待（与现状一致）
    background_tasks.add_task(process_document, doc["id"], text)
    return {"id": doc["id"], "filename": doc["filename"], "status": doc["status"]}


@router.post("/documents/{doc_id}/reprocess")
async def reprocess(
    doc_id: str,
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_user_id)],
):
    """人工重试失败文档：重新入队向量化（仅 error 状态可重试）。"""
    content = await reprocess_document(doc_id)
    background_tasks.add_task(process_document, doc_id, content)
    return {"id": doc_id, "status": "processing"}
