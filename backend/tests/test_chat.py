"""聊天编排纯函数测试：消息文本提取与模型消息转换。"""
import pytest

from app.chat import extract_text, to_model_messages


def test_extract_text_joins_only_text_parts():
    msg = {
        "parts": [
            {"type": "text", "text": "你好"},
            {"type": "reasoning", "text": "思考过程"},
            {"type": "text", "text": "世界"},
        ]
    }
    assert extract_text(msg) == "你好世界"


def test_extract_text_empty_parts():
    assert extract_text({}) == ""
    assert extract_text({"parts": []}) == ""


def test_extract_text_compat_content_string():
    assert extract_text({"content": "纯文本"}) == "纯文本"


def test_to_model_messages_filters_reasoning_and_unknown_roles():
    msgs = [
        {"role": "user", "parts": [{"type": "text", "text": "问题"}]},
        {"role": "assistant", "parts": [{"type": "reasoning", "text": "思考"}, {"type": "text", "text": "回答"}]},
        {"role": "system", "parts": [{"type": "text", "text": "系统"}]},  # 前端不产生 system，防御性过滤
        {"role": "user", "parts": []},  # 空消息跳过
    ]
    assert to_model_messages(msgs) == [
        {"role": "user", "content": "问题"},
        {"role": "assistant", "content": "回答"},
    ]


def test_to_model_messages_rejects_empty_last_text():
    # 空文本消息会被过滤掉（实际空消息校验在 stream_chat_sse 入口）
    assert to_model_messages([{"role": "user", "parts": [{"type": "reasoning", "text": "x"}]}]) == []
