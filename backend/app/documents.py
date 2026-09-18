"""文档数据访问与向量化：对齐 document.service.ts（含 fire-and-forget 局限）。"""
import logging
import uuid
from datetime import timedelta

from fastapi import HTTPException

from .chunker import chunk_text
from .db import get_pool
from .llm import EMBEDDING_BATCH_SIZE, embed_texts

logger = logging.getLogger(__name__)

# Vercel Functions 请求体上限 4.5MB，超限文件拒绝上传
MAX_UPLOAD_BYTES = 4_500_000

# 心跳容忍时长（3 × 10s 心跳间隔）：processing 超时未刷新心跳即判死（sweep 依据）
HEARTBEAT_TIMEOUT = timedelta(seconds=30)


def to_vector_str(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def create_document_record(filename: str, file_type: str, text: str) -> dict:
    pool = await get_pool()
    doc_id = str(uuid.uuid4())
    await pool.execute(
        'INSERT INTO "Document" (id, filename, "fileType", content, status, "lastProgressAt", "createdAt") '
        "VALUES ($1, $2, $3, $4, $5, NOW(), NOW())",
        doc_id,
        filename,
        file_type,
        text,
        "processing",
    )
    return {"id": doc_id, "filename": filename, "status": "processing"}


async def _touch_progress(pool, doc_id: str, epoch: int) -> bool:
    """心跳：刷新 lastProgressAt；返回 False 表示处理权已丧失（被重试/删除），调用方应中止。"""
    row = await pool.fetchrow(
        'UPDATE "Document" SET "lastProgressAt" = NOW() '
        'WHERE id = $1 AND "retryCount" = $2 AND status = $3 RETURNING id',
        doc_id,
        epoch,
        "processing",
    )
    return row is not None


async def process_document(doc_id: str, text: str) -> None:
    """分块 → 批量 embedding → 写入向量库 → 置 ready；失败置 error。

    fire-and-forget 缺陷由 sweep_stale + 人工重试兜底：
    - retryCount 为处理权代数（fence）：状态写全部条件化，旧任务复活无法覆盖新任务
    - 每批 embedding 后刷新心跳，心跳失权（被重试/删除）立即中止止损
    - 开跑前清空旧分块，保证重试幂等
    """
    pool = await get_pool()
    row = await pool.fetchrow('SELECT "retryCount" FROM "Document" WHERE id = $1', doc_id)
    if row is None:
        return  # 文档已被删除
    epoch: int = row["retryCount"]
    try:
        # 幂等：清掉上次残留分块（首跑为空操作，重试时防止重复内容）
        await pool.execute('DELETE FROM "DocumentChunk" WHERE "documentId" = $1', doc_id)
        chunks = chunk_text(text)
        embeddings: list[list[float]] = []
        # 按批调用并在批间刷新心跳：embedding 是耗时主体，必须有活性锚点
        for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            embeddings.extend(await embed_texts(chunks[i : i + EMBEDDING_BATCH_SIZE]))
            if not await _touch_progress(pool, doc_id, epoch):
                logger.info("文档处理权已丧失（被重试或删除），中止: %s", doc_id)
                return
        for i, chunk in enumerate(chunks):
            await pool.execute(
                'INSERT INTO "DocumentChunk" (id, "documentId", content, embedding, "createdAt") VALUES ($1, $2, $3, $4::vector, NOW())',
                str(uuid.uuid4()),
                doc_id,
                chunk,
                to_vector_str(embeddings[i]),
            )
        await pool.execute(
            'UPDATE "Document" SET status = $2, "lastError" = NULL '
            'WHERE id = $1 AND "retryCount" = $3 AND status = $4',
            doc_id,
            "ready",
            epoch,
            "processing",
        )
    except Exception as e:
        logger.exception("文档向量化失败: %s", doc_id)
        # 条件写：失权（已被重试接管/已删除）时不覆盖状态
        await pool.execute(
            'UPDATE "Document" SET status = $2, "lastError" = $3 '
            'WHERE id = $1 AND "retryCount" = $4 AND status = $5',
            doc_id,
            "error",
            str(e)[:500],
            epoch,
            "processing",
        )


async def sweep_stale() -> int:
    """懒收敛：把心跳超时的 processing 文档判死（置 error 待人工重试）。

    由列表接口顺带调用；单条条件 UPDATE 天然幂等，多实例并发安全。
    返回本轮判死条数。
    """
    pool = await get_pool()
    status = await pool.execute(
        'UPDATE "Document" SET status = $1, "lastError" = $2 '
        'WHERE status = $3 AND ("lastProgressAt" IS NULL OR "lastProgressAt" < NOW() - $4::interval)',
        "error",
        "处理超时（心跳中断），可点击重试",
        "processing",
        HEARTBEAT_TIMEOUT,
    )
    return int(status.split()[-1])


async def reprocess_document(doc_id: str) -> str:
    """人工重试：仅 error 状态可重新入队，返回原文供重新向量化。

    条件写（仅 error 生效）保证并发点击只生效一次；retryCount+1 换发处理权，
    fence 掉可能仍未咽气的旧任务的一切写入。
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        'UPDATE "Document" SET status = $2, "retryCount" = "retryCount" + 1, '
        '"lastProgressAt" = NOW(), "lastError" = NULL '
        'WHERE id = $1 AND status = $3 RETURNING content',
        doc_id,
        "processing",
        "error",
    )
    if row is None:
        exists = await pool.fetchrow('SELECT id FROM "Document" WHERE id = $1', doc_id)
        if exists is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        raise HTTPException(status_code=409, detail="仅失败的文档可以重试")
    content = row["content"] or ""
    if not content.strip():
        # 边界：历史数据无原文时无法重跑，回退为 error 并给出明确指引
        await pool.execute(
            'UPDATE "Document" SET status = $2, "lastError" = $3 WHERE id = $1 AND status = $4',
            doc_id,
            "error",
            "原始文本缺失，请删除后重新上传",
            "processing",
        )
        raise HTTPException(status_code=409, detail="原始文本缺失，请删除后重新上传")
    return content


async def delete_document(doc_id: str) -> bool:
    """删除文档；DocumentChunk 经外键 ON DELETE CASCADE 一并删除。"""
    pool = await get_pool()
    row = await pool.fetchrow('DELETE FROM "Document" WHERE id = $1 RETURNING id', doc_id)
    return row is not None


async def list_documents() -> list[dict]:
    """文档列表（字段与 DocumentDto 对齐）。"""
    pool = await get_pool()
    rows = await pool.fetch(
        'SELECT id, filename, "fileType", status, "lastError", "createdAt" FROM "Document" ORDER BY "createdAt" DESC'
    )
    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "fileType": r["fileType"],
            "status": r["status"],
            "lastError": r["lastError"],
            "createdAt": r["createdAt"].isoformat(),
        }
        for r in rows
    ]
