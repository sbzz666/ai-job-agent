import os

import pytest

from app.services import credential_store


@pytest.mark.skipif(os.name != "nt", reason="DPAPI is available only on Windows")
def test_deepseek_config_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(credential_store, "_config_path", lambda: tmp_path / "config.bin")

    credential_store.save_deepseek_config("sk-secret-test", "deepseek-chat")

    raw = (tmp_path / "config.bin").read_bytes()
    assert b"sk-secret-test" not in raw
    assert credential_store.load_deepseek_config() == credential_store.DeepSeekConfig(
        "sk-secret-test", "deepseek-chat"
    )

    credential_store.delete_deepseek_config()
    assert credential_store.load_deepseek_config() is None
