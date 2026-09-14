"""文本分块：结构感知切割（标题/段落/表格为原子段，贪心组装，硬切兜底）。

对齐旧 chunker.ts 的 800/100 参数语义，但目标从「严格等长」改为
「尽量保持段落与表格语义完整」。已知取舍：``` 代码块不特殊处理，
内部含空行时会被拆散（当前场景表格优先，代码块场景少）。
"""

CHUNK_TARGET = 800  # 贪心组装的目标块长（字符，尽量不超过）
CHUNK_MAX = 1600  # 原子段超过该长度才触发硬切兜底
CHUNK_OVERLAP = 100  # 硬切滑窗的重叠（对齐旧 chunker.ts）


def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def _split_atomic(text: str) -> list[str]:
    """切成原子段：表格（连续表格行合一）、段落（空行分隔）。"""
    blocks: list[str] = []
    buf: list[str] = []
    in_table = False
    for line in text.splitlines():
        if _is_table_line(line):
            if buf and not in_table:  # 非表格内容被打断，先落段
                blocks.append("\n".join(buf))
                buf = []
            buf.append(line)
            in_table = True
        else:
            if in_table:  # 表格结束
                blocks.append("\n".join(buf))
                buf = []
                in_table = False
            if line.strip() == "":  # 空行 = 段落边界
                if buf:
                    blocks.append("\n".join(buf))
                    buf = []
            else:
                buf.append(line)
    if buf:
        blocks.append("\n".join(buf))
    return [b for b in (block.strip() for block in blocks) if b]


def _hard_split(text: str, size: int = CHUNK_TARGET, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """滑窗硬切（与旧 chunker.ts 行为等价），仅用于超长原子段兜底。"""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def chunk_text(text: str) -> list[str]:
    """结构感知分块：原子段贪心组装到目标长度，超长段（>CHUNK_MAX）硬切兜底。"""
    chunks: list[str] = []
    current = ""
    for block in _split_atomic(text):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= CHUNK_TARGET:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(block) <= CHUNK_MAX:
            current = block  # 完整语义优先，允许块长超出目标
        else:
            pieces = _hard_split(block)
            chunks.extend(pieces[:-1])
            current = pieces[-1]  # 最后一片与后续原子段继续组装
    if current:
        chunks.append(current)
    return chunks
