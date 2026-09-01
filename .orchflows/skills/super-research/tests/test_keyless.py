"""Keyless suite: the whole roster answers with nothing in the environment.

This is the run's thesis, and the prior spec's measurement is what it
overturns: eight of eleven adapters were said to require a credential, and
measurement found two capabilities that genuinely do. Both were deferred. What
is left is a roster where every adapter reaches its declared capability with
no credential of any kind, and where the absence of one is never a refusal.

The claim is easy to prove by accident, so the emptiness is made rather than
assumed. A run that passed because this developer happened to have no keys
exported would be evidence about a laptop. So the environment is emptied for
the length of the dispatch and shown to be empty, a variable set outside the
guard is shown to be invisible inside it, every filesystem primitive is
refused for the duration so no credential file on disk can be read, and the
package is scanned for any name that could reach a credential store at all —
it imports `os` nowhere, so there is nothing to reach one with.

Then the roster runs: forty-eight steps, twenty-six adapters, every route the core
can reach, one artifact. Every step keeps rows, no step is refused, and the
string `auth_required` appears in nothing the run produced — though ten
adapters name it, six of them can say it, and the router says it too. The
rest bind the constant and load it nowhere: no status a documented-keyless
route can answer with is a report that a credential was needed. Both counts
are read off the source by `test_dependency_boundary`, which holds this
sentence against the same scan `protocol.md`'s loss tables answer to.

Four adapters written beside the tree hold the oracle honest: one that reads
the environment for a key and refuses when it finds none, one that says
`auth_required` outright, one that comes back empty while claiming success,
and one that simply is not run. Each is rejected, and the run that ships is
accepted.
"""

import unittest

from .test_keyless_cases.credentials import EnvironmentIsEmptyTest, OracleCanFailTest
from .test_keyless_cases.routes import KeylessRosterTest
from .test_keyless_cases.support import AUTH_REQUIRED, roster_manifest


__all__ = (
    "AUTH_REQUIRED",
    "EnvironmentIsEmptyTest",
    "KeylessRosterTest",
    "OracleCanFailTest",
    "roster_manifest",
)


if __name__ == "__main__":
    unittest.main()
