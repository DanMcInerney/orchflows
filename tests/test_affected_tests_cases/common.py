"""Shared fixture repository for the affected-test resolver suite.

The fixture tree carries one file per edge kind the resolver must see, so a
regression names the edge it lost rather than a diffuse module-set mismatch.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AFFECTED_TESTS_PY = ROOT / "tools" / "affected_tests.py"

# Each fixture module carries exactly one edge kind. Nothing here is ever
# imported: the resolver reads these files with ``ast`` alone, which is why a
# deliberately unparsable module can sit beside the rest.
FIXTURE_SOURCES = {
    "scripts/mod_alpha.py": 'VALUE = "alpha"\n',
    "scripts/mod_beta.py": 'VALUE = "beta"\n',
    "scripts/mod_delta.py": 'VALUE = "delta"\n',
    "scripts/mod_epsilon.py": 'VALUE = "epsilon"\n',
    "scripts/mod_orphan.py": 'VALUE = "orphan"\n',
    "tools/mod_gamma.py": 'VALUE = "gamma"\n',
    "pkgdir/thing.md": "a document under a directory scope\n",
    ".dotdir/thing.md": "a document under a dot-directory scope\n",
    "dotdir_other/thing.md": "the decoy a mangled dot-directory scope would take\n",
    "tests/__init__.py": '"""Fixture suite package."""\n',
    "tests/test_import_edge.py": (
        '"""Fixture: a dotted package import edge."""\n'
        "import scripts.mod_alpha\n"
    ),
    "tests/test_from_edge.py": (
        '"""Fixture: a from-package import edge."""\n'
        "from scripts import mod_alpha\n"
    ),
    # The two literals such a call spells -- the file's base name and the
    # module stem it is loaded under -- are separate resolver mechanisms, so
    # they are graded apart. Here the loaded name is deliberately NOT the
    # stem, which leaves the base-name literal the only way in.
    "tests/test_spec_edge.py": (
        '"""Fixture: an importlib file-location edge, by base name."""\n'
        "import importlib.util\n"
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parent.parent\n"
        "SPEC = importlib.util.spec_from_file_location(\n"
        '    "beta_module", ROOT / "scripts" / "mod_beta.py"\n'
        ")\n"
    ),
    "tests/test_stem_edge.py": (
        '"""Fixture: a module named only by its stem, as a spec call spells it."""\n'
        'LOADED_AS = "mod_epsilon"\n'
    ),
    "tests/test_literal_edge.py": (
        '"""Fixture: a whole string-literal path edge."""\n'
        "from pathlib import Path\n"
        'GAMMA = Path("tools/mod_gamma.py")\n'
    ),
    "tests/test_cases_edge.py": (
        '"""Fixture: a facade whose case package carries the edge."""\n'
        "from tests.test_cases_edge_cases.inner import *  # noqa: F401,F403\n"
    ),
    "tests/test_cases_edge_cases/__init__.py": '"""Fixture case package."""\n',
    "tests/test_cases_edge_cases/inner.py": (
        '"""Fixture: the case module that owns its shard edge."""\n'
        "from scripts import mod_delta\n"
    ),
    "tests/test_dir_edge.py": (
        '"""Fixture: a module reading a literal under a directory scope."""\n'
        'NOTE = "pkgdir/thing.md"\n'
    ),
    "tests/test_dotdir_edge.py": (
        '"""Fixture: a literal under a dot-directory scope."""\n'
        'NOTE = ".dotdir/thing.md"\n'
    ),
    "tests/test_decoy_edge.py": (
        '"""Fixture: the shard a scope path stripped of its leading dot would\n'
        'wrongly select, and a directory scope must not."""\n'
        'NOTE = "dotdir_other/thing.md"\n'
    ),
    "tests/test_broken.py": (
        '"""Fixture: a module no parser can read."""\n'
        "def broken( :\n"
    ),
}


def build_tree(base) -> Path:
    """Write the fixture repository under ``base`` and return its root."""

    root = Path(base) / "repo"
    for relative, source in FIXTURE_SOURCES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def run_cli(*arguments):
    """Run ``tools/affected_tests.py`` the way a caller's shell would."""

    return subprocess.run(
        [sys.executable, str(AFFECTED_TESTS_PY), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
