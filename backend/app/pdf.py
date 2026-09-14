from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(buffer: bytes) -> str:
    """PDF 文本提取（pypdf）。

    已知局限：与旧实现 pdf-parse 的文本输出可能有差异（断行、连字等），
    迁移完成后建议用 pypdf 对存量文档重新向量化。
    """
    reader = PdfReader(BytesIO(buffer))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
