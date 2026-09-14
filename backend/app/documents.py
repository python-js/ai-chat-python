"""文档数据访问与向量化：对齐 document.service.ts（含 fire-and-forget 局限）。"""
import logging
import uuid

from .chunker import chunk_text
from .db import get_pool
from .llm import embed_texts

logger = logging.getLogger(__name__)

# Vercel Functions 请求体上限 4.5MB，超限文件拒绝上传
MAX_UPLOAD_BYTES = 4_500_000


def to_vector_str(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def create_document_record(filename: str, file_type: str, text: str) -> dict:
    pool = await get_pool()
    doc_id = str(uuid.uuid4())
    await pool.execute(
        'INSERT INTO "Document" (id, filename, "fileType", content, status, "createdAt") VALUES ($1, $2, $3, $4, $5, NOW())',
        doc_id,
        filename,
        file_type,
        text,
        "processing",
    )
    return {"id": doc_id, "filename": filename, "status": "processing"}


async def process_document(doc_id: str, text: str) -> None:
    """分块 → 批量 embedding → 写入向量库 → 置 ready；失败置 error。

    已知局限：fire-and-forget，进程重启会丢失处理中任务（与现状一致）。
    """
    pool = await get_pool()
    try:
        chunks = chunk_text(text)
        embeddings = await embed_texts(chunks)
        for i, chunk in enumerate(chunks):
            await pool.execute(
                'INSERT INTO "DocumentChunk" (id, "documentId", content, embedding, "createdAt") VALUES ($1, $2, $3, $4::vector, NOW())',
                str(uuid.uuid4()),
                doc_id,
                chunk,
                to_vector_str(embeddings[i]),
            )
        await pool.execute('UPDATE "Document" SET status = $2 WHERE id = $1', doc_id, "ready")
    except Exception:
        logger.exception("文档向量化失败: %s", doc_id)
        await pool.execute('UPDATE "Document" SET status = $2 WHERE id = $1', doc_id, "error")


async def delete_document(doc_id: str) -> bool:
    """删除文档；DocumentChunk 经外键 ON DELETE CASCADE 一并删除。"""
    pool = await get_pool()
    row = await pool.fetchrow('DELETE FROM "Document" WHERE id = $1 RETURNING id', doc_id)
    return row is not None


async def list_documents() -> list[dict]:
    """文档列表（字段与 DocumentDto 对齐）。"""
    pool = await get_pool()
    rows = await pool.fetch(
        'SELECT id, filename, "fileType", status, "createdAt" FROM "Document" ORDER BY "createdAt" DESC'
    )
    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "fileType": r["fileType"],
            "status": r["status"],
            "createdAt": r["createdAt"].isoformat(),
        }
        for r in rows
    ]
