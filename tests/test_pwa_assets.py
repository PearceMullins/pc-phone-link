from __future__ import annotations

import json
import re
import struct
from pathlib import Path


STATIC = Path(__file__).parents[1] / "phone_link" / "static"


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        assert handle.read(8) == b"\x89PNG\r\n\x1a\n"
        length = struct.unpack(">I", handle.read(4))[0]
        assert handle.read(4) == b"IHDR" and length >= 8
        return struct.unpack(">II", handle.read(8))


def test_manifest_and_icons_are_installable() -> None:
    manifest = json.loads((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    icons = {entry["sizes"]: entry for entry in manifest["icons"] if entry["purpose"] == "any"}
    for size in (192, 512):
        icon_path = STATIC / icons[f"{size}x{size}"]["src"].removeprefix("/assets/")
        assert icon_path.is_file()
        assert _png_size(icon_path) == (size, size)


def test_service_worker_caches_shell_not_authenticated_pages() -> None:
    worker = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert 'request.mode === "navigate"' in worker
    assert 'fetch(request).catch' in worker
    assert '"/"' not in worker.split("const SHELL = [", 1)[1].split("];", 1)[0]
    assert "/api/" not in worker.split("const SHELL = [", 1)[1].split("];", 1)[0]


def test_app_shell_declares_pwa_and_all_destinations() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in html
    for destination in ("viewer", "windows", "keyboard", "controls", "settings"):
        assert f'data-destination="{destination}"' in html


def test_app_shell_ids_match_javascript_references() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    script = (STATIC / "app.js").read_text(encoding="utf-8")
    element_ids = re.findall(r'id="([^"]+)"', html)
    references = re.findall(r'getElementById\("([^"]+)"\)', script)
    assert len(element_ids) == len(set(element_ids))
    assert set(references) <= set(element_ids)
