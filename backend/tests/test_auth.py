"""鉴权解密测试：用 next-auth 真实签发的 token 验证 Python 侧 JWE 解密。"""
import subprocess
import time
import types
from pathlib import Path

import pytest

from app.auth import decrypt_session_token
from app.config import settings

ROOT_DIR = Path(__file__).resolve().parents[2]  # 项目根目录


def gen_token(cookie_name: str = "authjs.session-token", sub: str = "test-user-123", max_age: int | None = None) -> str:
    # Windows 下 pnpm 为 .cmd 脚本，subprocess 需经 shell 执行
    args = ["pnpm", "exec", "tsx", "scripts/gen-test-token.ts", cookie_name, sub]
    if max_age is not None:
        args.append(str(max_age))
    result = subprocess.run(
        " ".join(args), cwd=ROOT_DIR, shell=True, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"token 生成失败: {result.stderr}"
    return result.stdout.strip()


def test_decrypt_real_token():
    token = gen_token()
    payload = decrypt_session_token(token, "authjs.session-token")
    assert payload["sub"] == "test-user-123"
    assert payload["exp"] is not None


def test_decrypt_secure_cookie_name():
    # 生产环境 cookie 名（__Secure- 前缀）对应不同 salt，解密逻辑一致
    token = gen_token("__Secure-authjs.session-token")
    payload = decrypt_session_token(token, "__Secure-authjs.session-token")
    assert payload["sub"] == "test-user-123"


def test_wrong_salt_fails():
    # salt 不匹配（cookie 名不同）→ 派生密钥不同 → 解密失败
    token = gen_token("authjs.session-token")
    with pytest.raises(Exception):
        decrypt_session_token(token, "__Secure-authjs.session-token")


def test_wrong_secret_fails(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "wrong-secret")
    token = gen_token()
    with pytest.raises(Exception):
        decrypt_session_token(token, "authjs.session-token")


def test_expired_token_fails(monkeypatch):
    token = gen_token(max_age=1)
    # 模拟时钟前进超过 CLOCK_TOLERANCE（15s），避免真实等待
    monkeypatch.setattr("app.auth.time", types.SimpleNamespace(time=lambda: time.time() + 30))
    with pytest.raises(Exception, match="会话已过期"):
        decrypt_session_token(token, "authjs.session-token")


def test_malformed_token_fails():
    with pytest.raises(Exception):
        decrypt_session_token("not-a-jwe", "authjs.session-token")
