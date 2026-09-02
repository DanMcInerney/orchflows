"""State-root compatibility seam for the partitioned regression cases."""

import sys
from pathlib import Path

# S1 exception: computed locally, not imported from tests._repo_root.
# This is the file that arms the guard `tests` package import a bare
# `unittest discover -s tests` run never triggers on its own -- so the
# walk here must not itself depend on `tests` (or any of its
# submodules, tests._repo_root included) already being importable.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests import ensure_temporary_sink  # noqa: E402

# ``python -m unittest discover -s tests`` does not import ``tests`` as a
# package, so this public seam must still arm the guard before case modules
# import any state writers.
ensure_temporary_sink()

from tests.test_state_root_cases.environment import (  # noqa: E402, F401
    TestNoTestReachesTheRealSink,
    TestOneResolverOwnsBothFacts,
    TestTheEnvVarNameIsThisLiteral,
    TestTheOverrideAndTheDefault,
)
from tests.test_state_root_cases.fallback import (  # noqa: E402, F401
    TestEveryWriterLandsInTheSink,
    TestThereIsNoFallback,
)
from tests.test_state_root_cases.repository import (  # noqa: E402, F401
    TestFindRepoRootNamesTheProject,
)


if __name__ == "__main__":
    import unittest

    unittest.main()
