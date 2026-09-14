"""chunker 结构感知分块测试：段落/表格完整性、标题聚合、硬切兜底。"""

from app.chunker import CHUNK_OVERLAP, CHUNK_TARGET, chunk_text


def test_empty_text_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_single_chunk():
    text = "一句话回答。"
    assert chunk_text(text) == [text]


def test_paragraphs_kept_intact():
    p1, p2 = "甲" * 500, "乙" * 500
    chunks = chunk_text(f"{p1}\n\n{p2}")
    assert len(chunks) == 2
    assert chunks[0] == p1  # 段落不跨块、不残缺
    assert chunks[1] == p2


def test_table_stays_atomic():
    para = "正文" * 300  # 600 字符
    table = "\n".join(f"| 行{i} | 数据{i} |" for i in range(30))
    chunks = chunk_text(f"{para}\n\n{table}")
    assert len(chunks) == 2
    assert chunks[1] == table  # 表格整体成块不被拆


def test_title_grouped_with_body():
    chunks = chunk_text("# 价格说明\n\n正文内容 " + "详细" * 50)
    assert chunks[0].startswith("# 价格说明")  # 标题随内容进同一块


def test_oversized_plain_text_hard_split_with_overlap():
    text = "字" * 2000
    chunks = chunk_text(text)
    assert all(len(c) <= CHUNK_TARGET for c in chunks)  # 硬切按目标长度
    for a, b in zip(chunks, chunks[1:]):
        assert a[-CHUNK_OVERLAP:] == b[:CHUNK_OVERLAP]  # 相邻重叠 100


def test_oversized_table_hard_split():
    table = "\n".join(f"| 行{i} | 数据{i} |" for i in range(500))  # 远超 CHUNK_MAX
    chunks = chunk_text(table)
    assert all(len(c) <= CHUNK_TARGET for c in chunks)  # 超大表格兜底切分
    assert len(chunks) > 1
