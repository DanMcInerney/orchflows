"""Load the UI-owned compact semantic summaries for Workflows."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "docs" / "ui" / "workflow-summary-manifest.json"


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    """Read one UTF-8 workflow summary manifest."""

    return json.loads(path.read_text(encoding="utf-8"))
