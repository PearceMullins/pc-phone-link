"""Deprecated launcher module — use phone_link.app instead."""
from __future__ import annotations

from .app import create_app, main

__all__ = ["create_app", "main"]
