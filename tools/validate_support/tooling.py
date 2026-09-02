"""Grade every library `tools.txt` against the grammar its readers parse.

A tooling declaration is checked at two doors -- `orchflows sync` before a
run and `orchflows check` over a ring -- and both read it through
`scripts/orchflows_tools.py`. So the grammar has exactly one owner and this
module is the validator's call into it: a line the parser cannot read is a
line `sync` would silently skip, and a silently skipped declaration is a
missing tool nobody is told about.

Its own module rather than a clause inside `packages.py`: that file grades
manifests, and this grades a sibling file that no manifest mentions, for
every kind at once. The seam is the file, so the growth goes sideways.

Nothing here runs a probe. Grammar is what a library can check; whether
ffmpeg is on this machine is a question about the machine, and `sync` and
`check` ask it where the answer means something.
"""

from __future__ import annotations

from tools.validate_support import common as __dep_common
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED

from tools.validate_support.packages import rel

# The library's own directory table and manifest names, imported rather than
# respelled: a kind that gains a home in `rings.py` gains it here at once.
from scripts.orchflows_tools import TOOLS_NAME, declarations
from scripts.rings import LIB_DIRS, MANIFESTS


def discover_declarations():
    """Every `(item manifest, tools.txt)` pair in this library, in read order."""

    found = []
    for kind, lib_dirs in sorted(LIB_DIRS.items()):
        for lib_dir in lib_dirs:
            root = ROOT / lib_dir
            if not root.is_dir():
                continue
            for directory in sorted(root.iterdir()):
                if not directory.is_dir():
                    continue
                manifest = directory / MANIFESTS[kind]
                tools = directory / TOOLS_NAME
                if manifest.is_file() and tools.is_file():
                    found.append({"manifest": manifest, "tools": tools})
    return found


def validate_tools_declarations(diag) -> None:
    """Every declaration parses, or the line that does not is named."""

    marker = ROOT / "packs"
    if not marker.is_dir():
        diag.warn(rel(marker), SKIPPED)
        return
    for declaration in discover_declarations():
        tools = declaration["tools"]
        try:
            _parsed, problems = declarations(tools)
        except (OSError, UnicodeDecodeError) as error:
            diag.error(rel(tools), f"unreadable {TOOLS_NAME}: {error}")
            continue
        for problem in problems:
            diag.error(rel(tools), f"line {problem['line']}: {problem['problem']}")


__all__ = ("discover_declarations", "validate_tools_declarations")
