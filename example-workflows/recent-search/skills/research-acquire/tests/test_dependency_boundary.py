"""Dependency-boundary suite: what this package can reach, enumerated.

Criterion 2 is the one claim that cannot be made by testing behavior, because
its subject is what the code is *able* to do rather than what it did. A run
that never reached a browser proves nothing about whether one is reachable. So
every claim here is made by enumeration, in both directions, and every
enumeration is shown to reject a module beside the tree that breaks it.

Four things are enumerated, and only the first is transcribed by hand:

*The module set.* The core's eighteen modules are spelled out, so a new sibling
joins by editing this file or not at all. The count is in the sentence and in
`CORE_MODULES`, and a test below compares them: this docstring said eleven for
three modules longer than it was true. The adapter modules are not spelled
out — they are derived from ``runner.ADAPTER_IDS`` and checked against what is
on disk, because `test_router` and `test_adapters` already carry two
independent transcriptions of that roster and a third would only be a third
thing to forget.

*The dispatch.* Both literal ``if`` chains are read out of the source and
compared against the declared roster, in order, with the module each branch
reaches. A branch that goes missing, doubles, reorders, or calls the wrong
module is caught here rather than at the first live read.

*The imports.* Every intra-package edge among the core modules, and every
top-level module the package takes from outside itself. The second list is
then resolved against this interpreter's own standard library, and whatever
does not resolve there must be declared in the item's ``requirements.txt``:
"nothing undeclared, on the 3.9 floor" is answered by where each module
actually comes from and not by a name anybody recognized.

*The surfaces that would let it run something instead of read something.*
Dynamic import, computed dispatch, an SDK, a browser driver, a media
downloader, a shell spelling, a non-read verb.

The execution-surface vocabulary is imported from ``test_adapters`` rather
than restated: that suite pins the same names against the one adapter that
takes an argument, this one pins them against the whole package, and two
copies of one list is how the wider claim quietly stops covering something.
Which modules may spell a route and which may open a socket come from
``test_transport`` for the same reason, and they are two declarations rather
than one because admitting a module to the route table is not admitting it to
the network.
"""

import unittest

from .test_dependency_boundary_cases.import_edges import (
    BoundaryOracleCanFailTest,
    IntraPackageImportTest,
    NoRunSomethingSurfaceTest,
)
from .test_dependency_boundary_cases.loss_vocabulary import (
    LossVocabularyIsReadOffTheSourceTest,
)
from .test_dependency_boundary_cases.module_set import (
    ModuleSetTest,
    PrivateSupportOwnershipTest,
    ThisSuiteCountsItsOwnModuleSetTest,
)
from .test_dependency_boundary_cases.runner_dispatch import RunnerDispatchTest
from .test_dependency_boundary_cases.source_roster import RosterIsReadOffTheSourceTest
from .test_dependency_boundary_cases.declared_dependencies import (
    DeclaredDependenciesOnlyTest,
    TheHostMirrorResolvesFromAnyCheckoutTest,
)


__all__ = (
    "BoundaryOracleCanFailTest",
    "DeclaredDependenciesOnlyTest",
    "IntraPackageImportTest",
    "LossVocabularyIsReadOffTheSourceTest",
    "ModuleSetTest",
    "NoRunSomethingSurfaceTest",
    "PrivateSupportOwnershipTest",
    "RosterIsReadOffTheSourceTest",
    "RunnerDispatchTest",
    "TheHostMirrorResolvesFromAnyCheckoutTest",
    "ThisSuiteCountsItsOwnModuleSetTest",
)


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
