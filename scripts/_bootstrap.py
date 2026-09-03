"""The two facts a caller must know before importing anything else here.

Zero imports beyond ``pathlib``: a caller that cannot yet resolve the
``scripts`` package still reads these two facts correctly.
``rules/visibility.md`` section 6 is the env-var name's one prose owner
and this is its one code owner; every other reader imports it from here.
"""

from __future__ import annotations

from pathlib import Path

ENV_VAR = "ORCHFLOWS_STATE_HOME"

# This repository's own root, derived once from this file's fixed location
# one level below it.
ROOT = Path(__file__).resolve().parent.parent
