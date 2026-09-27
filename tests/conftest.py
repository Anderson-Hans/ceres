from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture(autouse=True)
def _chdir_root(monkeypatch):
    monkeypatch.chdir(ROOT)
