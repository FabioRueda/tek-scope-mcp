import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_requirements_list_names_only():
    lines = [
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert lines
    pinned = [line for line in lines if not re.fullmatch(r"[A-Za-z0-9._-]+", line)]
    assert pinned == []
