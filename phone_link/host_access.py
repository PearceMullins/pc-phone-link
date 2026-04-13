from __future__ import annotations

import os
import secrets
import string
from pathlib import Path

from .logging_utils import log_event


def _default_token_store_path() -> Path:
    if os.name == "nt":
        base_path = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base_path = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return base_path / "PC Phone Link" / "access_token.txt"


TOKEN_STORE_PATH = _default_token_store_path()


def generate_access_token() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2))


def resolve_access_token(explicit_token: str | None) -> str:
    if explicit_token:
        token = explicit_token.strip().upper()
        if not token:
            raise ValueError("The access token cannot be empty.")
        save_access_token(token)
        log_event(
            "host-access",
            "token-resolved",
            {"source": "explicit", "store_path": TOKEN_STORE_PATH},
        )
        return token

    saved_token = load_saved_access_token()
    if saved_token:
        log_event(
            "host-access",
            "token-resolved",
            {"source": "saved", "store_path": TOKEN_STORE_PATH},
        )
        return saved_token

    generated_token = generate_access_token()
    save_access_token(generated_token)
    log_event(
        "host-access",
        "token-resolved",
        {"source": "generated", "store_path": TOKEN_STORE_PATH},
    )
    return generated_token


def load_saved_access_token() -> str | None:
    if not TOKEN_STORE_PATH.is_file():
        log_event(
            "host-access",
            "token-load-missed",
            {"store_path": TOKEN_STORE_PATH},
        )
        return None

    token = TOKEN_STORE_PATH.read_text(encoding="utf-8").strip().upper()
    log_event(
        "host-access",
        "token-loaded",
        {"store_path": TOKEN_STORE_PATH, "found": bool(token)},
    )
    return token or None


def save_access_token(token: str) -> None:
    TOKEN_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_STORE_PATH.write_text(token, encoding="utf-8")
    log_event(
        "host-access",
        "token-saved",
        {"store_path": TOKEN_STORE_PATH},
    )
