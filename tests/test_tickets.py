"""Compatibility discovery seam for all ticket-script regression cases."""

import sys
import unittest

if __name__ == "test_tickets":
    sys.modules["tests.test_tickets"] = sys.modules[__name__]
    from tests.test_tickets_cases.readiness import *  # noqa: F401,F403
    from tests.test_tickets_cases.admission_v1 import *  # noqa: F401,F403
    from tests.test_tickets_cases.admission_v2 import *  # noqa: F401,F403
    from tests.test_tickets_cases.cohort_seal import *  # noqa: F401,F403
    from tests.test_tickets_cases.family_fixture import *  # noqa: F401,F403
    from tests.test_tickets_cases.file_payloads import *  # noqa: F401,F403
else:
    from .test_tickets_cases.readiness import *  # noqa: F401,F403
    from .test_tickets_cases.admission_v1 import *  # noqa: F401,F403
    from .test_tickets_cases.admission_v2 import *  # noqa: F401,F403
    from .test_tickets_cases.cohort_seal import *  # noqa: F401,F403
    from .test_tickets_cases.family_fixture import *  # noqa: F401,F403
    from .test_tickets_cases.file_payloads import *  # noqa: F401,F403


if __name__ == "__main__":
    unittest.main()
