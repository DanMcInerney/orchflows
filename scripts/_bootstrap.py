"""The two facts a caller must know before it can safely import anything
else in this tree -- including ``scripts/state_root.py`` itself.

Zero imports beyond ``pathlib``: a caller that cannot yet resolve the
``scripts`` package (an installer running from a bare clone, a guard
watching a tree that may not carry this module at all) still reads these
two facts correctly, because reading them never requires the rest of
``scripts/`` to already be safe to import.

``rules/visibility.md`` section 6 is the env-var name's one prose owner;
this is its one code owner. Every other reader imports it from here,
directly or through ``scripts.state_root``'s re-export, and never
redeclares the string.
"""

from __future__ import annotations

from pathlib import Path

ENV_VAR = "ORCHFLOWS_STATE_HOME"

# This repository's own root, derived once from this file's fixed
# location one level below it -- the fact every independent
# ``Path(__file__).resolve().parent...`` chain elsewhere re-derives.
ROOT = Path(__file__).resolve().parent.parent
