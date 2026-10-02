"""Run the unit tests that example libraries ship with their skills and trials.

Core discovery only scans tests/, so this module loads `example-workflows/*/skills/*/tests/test*.py` and
`example-workflows/*/trials/*/tests/test*.py` itself. Each file is imported under a name built from its path,
so equal file names in different libraries never collide, and each file puts what it imports on sys.path.
"""

import importlib.util
from pathlib import Path
import sys
import traceback
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ("*/skills/*/tests/test*.py", "*/trials/*/tests/test*.py")
LOADED = []


def library_test_files() -> list[Path]:
    return sorted({path for pattern in PATTERNS for path in (ROOT / "example-workflows").glob(pattern)})


def module_name(path: Path) -> str:
    relative = path.relative_to(ROOT / "example-workflows").with_suffix("")
    return "exlib_" + "_".join(part.replace("-", "_").replace(".", "_") for part in relative.parts)


def failed_import(path: Path, error: Exception) -> unittest.TestCase:
    name, detail = path.relative_to(ROOT).as_posix(), traceback.format_exc()

    def fail():
        if isinstance(error, unittest.SkipTest):
            raise error
        raise AssertionError(f"{name} could not be imported:\n{detail}")
    return unittest.FunctionTestCase(fail, description=f"import {name}")


def load_tests(loader, standard, pattern):
    suite = unittest.TestSuite(standard)
    LOADED.clear()
    for path in library_test_files():
        name = module_name(path)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as error:
            del sys.modules[name]
            suite.addTest(failed_import(path, error))
            continue
        LOADED.append(path.relative_to(ROOT).as_posix())
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


class ExampleLibraryTests(unittest.TestCase):
    def test_at_least_one_library_test_module_loads(self):
        self.assertTrue(LOADED, "no example library test module was found or imported")


if __name__ == "__main__":
    unittest.main()
