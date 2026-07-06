"""Connect code generation and dual-approval phone pairing."""

from __future__ import annotations

import secrets
import socket
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from .host_access import register_paired_browser
from .logging_utils import log_event

PAIRING_REQUEST_TTL_SECONDS = 300


def generate_connect_code() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(4))


def regenerate_connect_code(app: FastAPI) -> str:
    app.state.connect_code = generate_connect_code()
    log_event("host", "connect-code-regenerated", {})
    return app.state.connect_code


def build_connect_info(app: FastAPI) -> dict[str, str]:
    return {
        "connect_code": app.state.connect_code,
        "device_name": socket.gethostname(),
    }


def normalize_connect_code(value: str | None) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())[:4]


def validate_connect_code(app: FastAPI, provided: str | None) -> None:
    normalized = normalize_connect_code(provided)
    expected = normalize_connect_code(getattr(app.state, "connect_code", ""))
    if len(normalized) != 4 or normalized != expected:
        log_event(
            "host",
            "connect-code-rejected",
            {"provided_length": len(normalized)},
            level="error",
        )
        raise HTTPException(
            status_code=403,
            detail="Connect code does not match. Check the code on your PC.",
        )


def request_pairing(
    app: FastAPI,
    request: Request,
    device_name: str,
    connect_code: str,
) -> dict[str, Any]:
    validate_connect_code(app, connect_code)
    _cleanup_expired_pairings(app)
    normalized_name = _normalize_pairing_device_name(device_name)
    pairing = _create_pairing(app, request, normalized_name)
    pairing["phone_approved"] = True
    pairing["phone_approved_at"] = time.time()
    if _should_auto_approve_pc(app):
        pairing["pc_state"] = "approved"
        pairing["pc_approved_at"] = time.time()
    app.state.pending_pairings[pairing["id"]] = pairing
    log_event(
        "host",
        "pairing-request-created",
        {
            "pairing_id": pairing["id"],
            "device_name": normalized_name,
            "remote_address": pairing["remote_address"],
            "pc_auto_approved": pairing.get("pc_state") == "approved",
        },
    )
    result = serialize_pairing_for_client(app, pairing)
    if result.get("status") == "approved":
        regenerate_connect_code(app)
    return result


def approve_pairing(app: FastAPI, pairing_id: str, approval_code: str) -> dict[str, Any]:
    _cleanup_expired_pairings(app)
    pairing = get_pairing(app, pairing_id)
    if _pairing_status(pairing) == "expired":
        raise HTTPException(status_code=410, detail="That connection request expired. Try again.")
    if pairing.get("pc_state") == "approved":
        return serialize_pairing_for_client(app, pairing)

    normalized = normalize_connect_code(approval_code)
    expected = normalize_connect_code(pairing.get("approval_code", ""))
    if len(normalized) != 4 or normalized != expected:
        log_event(
            "host",
            "pairing-approval-rejected",
            {
                "pairing_id": pairing_id,
                "device_name": pairing.get("device_name"),
            },
            level="error",
        )
        raise HTTPException(
            status_code=403,
            detail="Approval code does not match that device.",
        )

    pairing["pc_state"] = "approved"
    pairing["pc_approved_at"] = time.time()
    log_event(
        "host",
        "pairing-pc-approved",
        {
            "pairing_id": pairing_id,
            "device_name": pairing.get("device_name"),
            "remote_address": pairing.get("remote_address"),
        },
    )
    result = serialize_pairing_for_client(app, pairing)
    if result.get("status") == "approved":
        regenerate_connect_code(app)
    return result


def list_pending_pairings(app: FastAPI) -> list[dict[str, Any]]:
    _cleanup_expired_pairings(app)
    pending: list[dict[str, Any]] = []
    for pairing in app.state.pending_pairings.values():
        if _pairing_status(pairing) != "pending":
            continue
        if not pairing.get("phone_approved"):
            continue
        pending.append(serialize_pairing_for_gui(pairing))
    pending.sort(
        key=lambda entry: float(entry.get("created_at", 0)),
        reverse=True,
    )
    return pending


def _should_auto_approve_pc(app: FastAPI) -> bool:
    return not bool(getattr(app.state, "gui_enabled", True))


def _cleanup_expired_pairings(app: FastAPI) -> None:
    now = time.time()
    expired_pairing_ids = [
        pairing_id
        for pairing_id, pairing in app.state.pending_pairings.items()
        if now >= float(pairing.get("expires_at", 0))
    ]
    for pairing_id in expired_pairing_ids:
        app.state.pending_pairings.pop(pairing_id, None)


def _normalize_pairing_device_name(device_name: str | None) -> str:
    normalized = (device_name or "").strip()
    return normalized[:80] or "This phone"


def _generate_unique_approval_code(app: FastAPI) -> str:
    for _ in range(100):
        code = generate_connect_code()
        if not _approval_code_in_use(app, code):
            return code
    raise HTTPException(status_code=503, detail="Could not create an approval code. Try again.")


def _approval_code_in_use(app: FastAPI, code: str) -> bool:
    for pairing in app.state.pending_pairings.values():
        if _pairing_status(pairing) != "pending":
            continue
        if normalize_connect_code(pairing.get("approval_code")) == normalize_connect_code(code):
            return True
    return False


def _create_pairing(app: FastAPI, request: Request, device_name: str) -> dict[str, Any]:
    now = time.time()
    return {
        "id": secrets.token_urlsafe(24),
        "device_name": device_name,
        "remote_address": request.client.host if request.client else None,
        "created_at": now,
        "expires_at": now + PAIRING_REQUEST_TTL_SECONDS,
        "approval_code": _generate_unique_approval_code(app),
        "pc_state": "pending",
        "phone_approved": False,
        "phone_approved_at": None,
        "approved_token": None,
    }


def _pairing_status(pairing: dict[str, Any]) -> str:
    if time.time() >= float(pairing.get("expires_at", 0)):
        return "expired"
    if pairing.get("approved_token"):
        return "approved"
    if pairing.get("phone_approved") and pairing.get("pc_state") == "approved":
        return "approved"
    return "pending"


def _complete_pairing_if_ready(app: FastAPI, pairing: dict[str, Any]) -> None:
    if pairing.get("approved_token"):
        return
    if not pairing.get("phone_approved"):
        return
    if pairing.get("pc_state") != "approved":
        return

    browser_entry = register_paired_browser(pairing.get("device_name") or "This phone")
    pairing["approved_token"] = browser_entry["token"]
    app.state.paired_browsers = [
        entry
        for entry in app.state.paired_browsers
        if str(entry.get("token", "")).strip() != browser_entry["token"]
    ]
    app.state.paired_browsers.append(browser_entry)
    log_event(
        "host",
        "pairing-completed",
        {
            "pairing_id": pairing["id"],
            "device_name": pairing["device_name"],
            "remote_address": pairing.get("remote_address"),
        },
    )


def serialize_pairing_for_gui(pairing: dict[str, Any]) -> dict[str, Any]:
    expires_in = max(int(float(pairing.get("expires_at", 0)) - time.time()), 0)
    return {
        "pairing_id": pairing["id"],
        "device_name": pairing["device_name"],
        "remote_address": pairing.get("remote_address"),
        "approval_code": pairing.get("approval_code"),
        "phone_approved": bool(pairing.get("phone_approved")),
        "pc_approved": pairing.get("pc_state") == "approved",
        "created_at": pairing.get("created_at"),
        "expires_in_seconds": expires_in,
    }


def serialize_pairing_for_client(app: FastAPI, pairing: dict[str, Any]) -> dict[str, Any]:
    _complete_pairing_if_ready(app, pairing)
    status = _pairing_status(pairing)
    expires_in = max(int(float(pairing.get("expires_at", 0)) - time.time()), 0)
    return {
        "pairing_id": pairing["id"],
        "device_name": pairing["device_name"],
        "status": status,
        "phone_approved": bool(pairing.get("phone_approved")),
        "pc_approved": pairing.get("pc_state") == "approved",
        "expires_in_seconds": expires_in,
        "message": _pairing_message(status, pairing),
        "approval_code": pairing.get("approval_code") if status == "pending" else None,
        "access_token": pairing.get("approved_token") if status == "approved" else None,
    }


def _pairing_message(status: str, pairing: dict[str, Any]) -> str:
    if status == "approved":
        return f"{pairing['device_name']} is connected."
    if status == "expired":
        return "That connection request expired. Try again."
    if pairing.get("phone_approved") and pairing.get("pc_state") != "approved":
        return f"Waiting for PC approval of {pairing['device_name']}. Use the device-specific code shown on the PC."
    if pairing.get("pc_state") == "approved" and not pairing.get("phone_approved"):
        return "Waiting for phone. Tap Connect on your phone."
    return "Connecting..."


def get_pairing(app: FastAPI, pairing_id: str) -> dict[str, Any]:
    pairing = app.state.pending_pairings.get(pairing_id)
    if pairing is None:
        raise HTTPException(status_code=404, detail="That connection request was not found.")
    return pairing
