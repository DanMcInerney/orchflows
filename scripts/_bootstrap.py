"""The two facts a caller must know before importing anything else here.

Only standard-library imports: a caller that cannot yet resolve the
``scripts`` package still reads these facts correctly.
``rules/visibility.md`` section 6 is the env-var name's one prose owner
and this is its one code owner; every other reader imports it from here.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ENV_VAR = "ORCHFLOWS_STATE_HOME"

# This repository's own root, derived once from this file's fixed location
# one level below it.
ROOT = Path(__file__).resolve().parent.parent

# Execution must not add bytecode to a content-trusted package. Keep source
# and dependency trees fully covered by trust rather than ignoring them.
_cache = str(Path(tempfile.gettempdir()) / "orchflows-python-cache")
sys.pycache_prefix = _cache
