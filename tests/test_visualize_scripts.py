"""Compatibility seam for the visualization script regression collection.

Cases live by executable seam under :mod:`tests.test_visualize_scripts_cases`;
these explicit imports preserve ``tests.test_visualize_scripts`` as the complete
discovery target used by local and CI runners.
"""

from tests.test_visualize_scripts_cases.command_line import (  # noqa: F401
    TestCommandLineEntry,
)
from tests.test_visualize_scripts_cases.preview import (  # noqa: F401
    TestPreviewBindsWithoutResolving,
    TestPreviewFailureCleanup,
    TestPreviewReadinessAndExactFile,
    TestPreviewSkillContract,
)
from tests.test_visualize_scripts_cases.renderer import (  # noqa: F401
    TestKitAndChartFences,
    TestRendererHasNoCdnMode,
    TestRenderHtml,
    TestRenderHtmlBoundaryInputs,
    TestSvgIdSalting,
)
from tests.test_visualize_scripts_cases.verifier import (  # noqa: F401
    TestBoundaryInputs,
    TestElkFrontmatter,
    TestLegibilityLint,
    TestStaticFences,
    TestVerifierRequiresTheMermaidCli,
)


if __name__ == "__main__":
    import unittest

    unittest.main()
