"""Windows-user-bound storage for the optional DeepSeek configuration."""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path


class CredentialStoreError(RuntimeError):
    """Raised when encrypted credentials cannot be read or written."""


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str = "deepseek-flash"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "AIJobAssistant" / "deepseek-config.bin"


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    value = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return value, buffer


def _protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise CredentialStoreError("安全保存功能仅支持 Windows。")
    source, source_buffer = _blob(data)
    result = _DataBlob()
    description = "AI Job Assistant DeepSeek configuration"
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(
        ctypes.byref(source), description, None, None, None, 0, ctypes.byref(result)
    ):
        raise CredentialStoreError("Windows 无法加密 DeepSeek 配置。")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)
        del source_buffer


def _unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise CredentialStoreError("安全读取功能仅支持 Windows。")
    source, source_buffer = _blob(data)
    result = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result)
    ):
        raise CredentialStoreError("DeepSeek 配置无法解密，可能属于其他 Windows 账户。")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)
        del source_buffer


def save_deepseek_config(api_key: str, model: str = "deepseek-flash") -> None:
    key = api_key.strip()
    if not key:
        raise CredentialStoreError("API Key 不能为空。")
    payload = json.dumps(
        {"api_key": key, "model": model.strip() or "deepseek-flash"},
        ensure_ascii=False,
    ).encode("utf-8")
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(_protect(payload))
    temporary.replace(path)


def load_deepseek_config() -> DeepSeekConfig | None:
    path = _config_path()
    if not path.exists():
        return None
    try:
        value = json.loads(_unprotect(path.read_bytes()).decode("utf-8"))
        key = str(value.get("api_key", "")).strip()
        if not key:
            return None
        return DeepSeekConfig(key, str(value.get("model", "deepseek-flash")))
    except (OSError, ValueError, UnicodeError, AttributeError) as exc:
        raise CredentialStoreError("DeepSeek 配置文件已损坏，请删除后重新保存。") from exc


def delete_deepseek_config() -> None:
    _config_path().unlink(missing_ok=True)
