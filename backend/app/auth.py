"""鉴权：解密 next-auth v5 签发的 JWE 会话 token，取出 userId。

与 @auth/core@0.41.3（next-auth v5.0.0-beta.32 内置）的 jwt.js 对齐：
- 加密算法：dir + A256CBC-HS512（新版本默认；旧版本 A256GCM 仍兼容解密）
- 密钥派生：HKDF-SHA256，ikm = AUTH_SECRET 字符串 UTF-8（不做 base64 解码），
  salt = cookie 名，info = "Auth.js Generated Encryption Key ({cookie名})"
- 注意：规划文档中「SHA-256 摘要派生」描述与实际实现不符，以本文件为准
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException, Request

from .config import settings

# next-auth 会话 cookie 名：开发环境（http://localhost）无前缀，生产（https）加 __Secure-
COOKIE_NAMES = ("authjs.session-token", "__Secure-authjs.session-token")

# 与 @auth/core jwt.js 的 clockTolerance 对齐（15 秒）
CLOCK_TOLERANCE = 15


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _derive_key(cookie_name: str, length: int) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=cookie_name.encode("utf-8"),
        info=f"Auth.js Generated Encryption Key ({cookie_name})".encode("utf-8"),
    )
    return hkdf.derive(settings.auth_secret.encode("utf-8"))


def _decrypt_a256cbc_hs512(key: bytes, iv: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
    """JWE A256CBC-HS512（RFC 7518 5.2.5）：CEK 前 32 字节为 MAC 密钥，后 32 字节为加密密钥。"""
    mac_key, enc_key = key[:32], key[32:]
    al = (len(aad) * 8).to_bytes(8, "big")  # AL：AAD 位数，64 位大端
    mac_input = aad + iv + ciphertext + al
    expected = hmac.new(mac_key, mac_input, hashlib.sha512).digest()[:32]
    if not hmac.compare_digest(expected, tag):
        raise ValueError("JWE MAC 校验失败")
    decryptor = Cipher(algorithms.AES(enc_key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return padded[: -padded[-1]]  # PKCS7 去填充


def decrypt_session_token(token: str, cookie_name: str) -> dict[str, Any]:
    """解密 next-auth JWE 会话 token，返回 payload（含 sub = userId）。"""
    parts = token.split(".")
    if len(parts) != 5:
        raise ValueError("JWE compact 格式非法")
    protected_b64, encrypted_key_b64, iv_b64, ciphertext_b64, tag_b64 = parts
    if encrypted_key_b64:
        raise ValueError("仅支持 dir 密钥管理模式")
    protected = json.loads(_b64url_decode(protected_b64))
    enc = protected.get("enc")
    aad = protected_b64.encode("ascii")  # RFC 7516：AAD = protected header 的 base64url 原文

    if enc == "A256CBC-HS512":
        plaintext = _decrypt_a256cbc_hs512(
            _derive_key(cookie_name, 64),
            _b64url_decode(iv_b64),
            _b64url_decode(ciphertext_b64),
            _b64url_decode(tag_b64),
            aad,
        )
    elif enc == "A256GCM":
        # 兼容旧版本 token（@auth/core decode 亦兼容）
        data = _b64url_decode(ciphertext_b64) + _b64url_decode(tag_b64)
        plaintext = AESGCM(_derive_key(cookie_name, 32)).decrypt(_b64url_decode(iv_b64), data, aad)
    else:
        raise ValueError(f"不支持的 JWE 加密算法: {enc}")

    payload = json.loads(plaintext)
    if payload.get("exp") is not None and payload["exp"] < time.time() - CLOCK_TOLERANCE:
        raise ValueError("会话已过期")
    return payload


async def get_user_id(request: Request) -> str:
    """FastAPI 依赖：从请求 cookie 解密会话，返回 userId；未登录/非法 → 401。

    注意：token 远小于 cookie 上限（~4KB），next-auth 分块场景（多块 cookie）未处理。
    """
    for name in COOKIE_NAMES:
        token = request.cookies.get(name)
        if not token:
            continue
        try:
            payload = decrypt_session_token(token, name)
        except Exception:
            continue  # 该 cookie 名解密失败则尝试下一个
        sub = payload.get("sub")
        if sub:
            return sub
    raise HTTPException(status_code=401, detail="未登录")
