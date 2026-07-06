"""Native Windows desktop GUI for connect code and connected phone management."""

from __future__ import annotations

import json
import os
import tkinter as tk
import urllib.error
import urllib.request
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException

from .connect import approve_pairing, list_pending_pairings
from .host_access import load_paired_browsers, revoke_paired_browser

REFRESH_INTERVAL_MS = 1500
APPROVE_BUTTON_BG = "#3159df"
APPROVE_BUTTON_ACTIVE_BG = "#3159df"


def _host_port(app: FastAPI) -> int:
    port = getattr(app.state, "port", None)
    if isinstance(port, int) and port > 0:
        return port
    access_urls = getattr(app.state, "access_urls", []) or []
    for url in access_urls:
        parsed = urlparse(str(url))
        if parsed.port:
            return parsed.port
    return 8765


def _fetch_json(
    path: str,
    *,
    method: str = "GET",
    port: int = 8765,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload) if payload else {}


def run_desktop_gui(app: FastAPI) -> None:
    if os.name != "nt":
        raise OSError("The PC Phone Link desktop GUI is only supported on Windows.")

    root = tk.Tk()
    root.title("PC Phone Link")
    root.minsize(460, 580)
    root.configure(bg="#060a12")
    app.state.pc_connect_ready = True

    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")

    container = ttk.Frame(root, padding=16)
    container.pack(fill="both", expand=True)

    title = ttk.Label(container, text="PC Phone Link", font=("Segoe UI", 16, "bold"))
    title.pack(anchor="w")

    instruction = ttk.Label(
        container,
        text=(
            "When a phone taps Connect, it appears below with its own approval code. "
            "Approve only the devices you want to allow."
        ),
        wraplength=420,
    )
    instruction.pack(anchor="w", pady=(8, 12))

    session_code_label = ttk.Label(container, text="Session code · ----", font=("Segoe UI", 12, "bold"))
    session_code_label.pack(anchor="w", pady=(0, 4))

    session_hint = ttk.Label(
        container,
        text="Phones must match this session code before they can request access.",
        wraplength=420,
    )
    session_hint.pack(anchor="w", pady=(0, 12))

    pending_frame = ttk.LabelFrame(container, text="Waiting to connect", padding=10)
    pending_frame.pack(fill="x", pady=(0, 12))

    pending_list = ttk.Frame(pending_frame)
    pending_list.pack(fill="x")

    empty_pending_label = ttk.Label(
        pending_frame,
        text="No phones are waiting to connect.",
    )

    urls_frame = ttk.LabelFrame(container, text="Open on your phone", padding=10)
    urls_frame.pack(fill="x", pady=(0, 12))

    urls_label = ttk.Label(urls_frame, text="", wraplength=420, justify="left")
    urls_label.pack(anchor="w")

    devices_frame = ttk.LabelFrame(container, text="Connected phones", padding=10)
    devices_frame.pack(fill="both", expand=True)

    devices_list = ttk.Frame(devices_frame)
    devices_list.pack(fill="both", expand=True)

    empty_devices_label = ttk.Label(
        devices_frame,
        text="No phones connected yet.",
    )

    state: dict[str, Any] = {
        "device_rows": [],
        "pending_rows": [],
        "approve_in_flight": set(),
    }

    def format_timestamp(value: str) -> str:
        if not value:
            return "Never"
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed.strftime("%b %d, %Y %I:%M %p")
        except ValueError:
            return value

    def clear_rows(key: str, container_frame: ttk.Frame) -> None:
        for row in state[key]:
            row.destroy()
        state[key] = []

    def remove_device(token: str, device_name: str) -> None:
        prompt = f"Remove {device_name} from connected phones?"
        if not messagebox.askyesno("Remove phone", prompt, parent=root):
            return

        removed, _entry = revoke_paired_browser(token)
        if not removed:
            messagebox.showerror("Remove phone", "That phone could not be removed.", parent=root)
            return

        app.state.paired_browsers = load_paired_browsers()
        refresh_view()

    def approve_device(pairing_id: str, device_name: str, approval_code: str) -> None:
        if pairing_id in state["approve_in_flight"]:
            return
        state["approve_in_flight"].add(pairing_id)
        refresh_view()
        try:
            approve_pairing(app, pairing_id, approval_code)
        except HTTPException as error:
            messagebox.showerror(
                "Approve phone",
                f"Could not approve {device_name}.\n\n{error.detail}",
                parent=root,
            )
        except Exception as error:
            messagebox.showerror(
                "Approve phone",
                f"Could not approve {device_name}.\n\n{error}",
                parent=root,
            )
        finally:
            state["approve_in_flight"].discard(pairing_id)
            refresh_view()

    def render_devices(devices: list[dict[str, Any]]) -> None:
        clear_rows("device_rows", devices_list)
        if not devices:
            empty_devices_label.pack(anchor="w")
            return

        empty_devices_label.pack_forget()
        for entry in devices:
            token = str(entry.get("token", "")).strip()
            device_name = str(entry.get("device_name", "This phone")).strip() or "This phone"
            last_seen = format_timestamp(str(entry.get("last_seen_at", "")).strip())

            row = ttk.Frame(devices_list)
            row.pack(fill="x", pady=4)
            state["device_rows"].append(row)

            text = ttk.Label(
                row,
                text=f"{device_name}\nLast seen: {last_seen}",
                wraplength=260,
                justify="left",
            )
            text.pack(side="left", fill="x", expand=True)

            remove_button = ttk.Button(
                row,
                text="Remove",
                command=lambda entry_token=token, entry_name=device_name: remove_device(entry_token, entry_name),
            )
            remove_button.pack(side="right")

    def render_pending_pairings(pairings: list[dict[str, Any]]) -> None:
        clear_rows("pending_rows", pending_list)
        if not pairings:
            empty_pending_label.pack(anchor="w")
            return

        empty_pending_label.pack_forget()
        for entry in pairings:
            pairing_id = str(entry.get("pairing_id", "")).strip()
            device_name = str(entry.get("device_name", "This phone")).strip() or "This phone"
            approval_code = str(entry.get("approval_code", "----")).strip() or "----"
            remote_address = str(entry.get("remote_address", "")).strip()
            details = f"Device: {device_name}"
            if remote_address:
                details = f"{details}\nFrom: {remote_address}"
            details = f"{details}\nAccess code for this device:"

            row = ttk.Frame(pending_list)
            row.pack(fill="x", pady=6)
            state["pending_rows"].append(row)

            info = ttk.Label(
                row,
                text=details,
                wraplength=220,
                justify="left",
            )
            info.pack(side="left", fill="x", expand=True)

            code_label = tk.Label(
                row,
                text=approval_code,
                font=("Segoe UI", 20, "bold"),
                fg="#f8faff",
                bg="#1b2438",
                padx=12,
                pady=8,
            )
            code_label.pack(side="left", padx=(8, 8))

            in_flight = pairing_id in state["approve_in_flight"]
            approve_button = tk.Button(
                row,
                text="Approving..." if in_flight else "Approve",
                font=("Segoe UI", 11, "bold"),
                fg="#f8faff",
                bg=APPROVE_BUTTON_BG,
                activebackground=APPROVE_BUTTON_ACTIVE_BG,
                activeforeground="#f8faff",
                relief="flat",
                padx=14,
                pady=8,
                borderwidth=0,
                highlightthickness=0,
                state="disabled" if in_flight else "normal",
                cursor="arrow" if in_flight else "hand2",
                command=lambda entry_id=pairing_id, entry_name=device_name, entry_code=approval_code: approve_device(
                    entry_id,
                    entry_name,
                    entry_code,
                ),
            )
            approve_button.pack(side="right")

    def refresh_view() -> None:
        connect_code = str(getattr(app.state, "connect_code", "") or "----")
        session_code_label.config(text=f"Session code · {connect_code}")

        pending_pairings = [
            entry
            for entry in list_pending_pairings(app)
            if entry.get("phone_approved") and not entry.get("pc_approved")
        ]
        render_pending_pairings(pending_pairings)

        access_urls = getattr(app.state, "access_urls", []) or []
        if access_urls:
            urls_label.config(text="\n".join(access_urls))
        else:
            urls_label.config(text="No LAN address found.")

        app.state.paired_browsers = load_paired_browsers()
        render_devices(app.state.paired_browsers)

    def schedule_refresh() -> None:
        if not root.winfo_exists():
            return
        refresh_view()
        root.after(REFRESH_INTERVAL_MS, schedule_refresh)

    def close_window() -> None:
        app.state.pc_connect_ready = False
        root.destroy()

    refresh_view()
    schedule_refresh()
    root.protocol("WM_DELETE_WINDOW", close_window)
    try:
        root.mainloop()
    finally:
        app.state.pc_connect_ready = False
