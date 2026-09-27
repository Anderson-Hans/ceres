"""Проверка неизменности исходной спецификации (§15 execution-промпта)."""

from __future__ import annotations

import hashlib
from pathlib import Path

SPEC_PATH = Path("docs/source/CERES-spec-v0.2.md")
SPEC_SHA256 = "db04298fdf4653eeecbb86eba581159f25bb4f0f50a71c8bfea38c9f75d44167"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_spec(root: Path) -> tuple[bool, str]:
    path = root / SPEC_PATH
    if not path.exists():
        return False, f"missing: {SPEC_PATH}"
    actual = sha256_file(path)
    if actual != SPEC_SHA256:
        return False, f"sha256 mismatch for {SPEC_PATH}: {actual} != {SPEC_SHA256}"
    return True, f"{SPEC_PATH}: sha256 OK ({actual})"
