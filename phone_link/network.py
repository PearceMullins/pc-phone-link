from __future__ import annotations

import socket

from .logging_utils import log_event


def discover_access_urls(port: int, token: str | None = None) -> list[str]:
    """Return LAN-friendly URLs that can be opened from the phone."""
    candidates: list[str] = []
    discovered_addresses: list[str] = []
    seen: set[str] = set()

    def add_address(ip_address: str) -> None:
        if not ip_address or ip_address.startswith("127.") or "%" in ip_address:
            return
        if ip_address in seen:
            return
        seen.add(ip_address)
        discovered_addresses.append(ip_address)
        candidates.append(_build_access_url(ip_address, port, token))

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            add_address(info[4][0])
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe_socket:
            probe_socket.connect(("8.8.8.8", 80))
            add_address(probe_socket.getsockname()[0])
    except OSError:
        pass

    used_loopback = False
    if not candidates:
        used_loopback = True
        candidates.append(_build_access_url("127.0.0.1", port, token))

    log_event(
        "network",
        "access-urls-discovered",
        {
            "port": port,
            "candidate_count": len(candidates),
            "addresses": discovered_addresses or ["127.0.0.1"],
            "used_loopback": used_loopback,
        },
    )
    return candidates


def _build_access_url(ip_address: str, port: int, token: str | None) -> str:
    base_url = f"http://{ip_address}:{port}/"
    if not token:
        return base_url
    return f"{base_url}?token={token}"
