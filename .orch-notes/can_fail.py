import sys, io, unittest, json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path.cwd()))
from scripts import standards, tickets_mint
from tests.test_callable_context import CallableContextTest
pin = standards.resolve_standard('orch-code', canonical_root=Path.cwd() / 'standards')
installed = standards.resolve_standard('orch-code', canonical_root=Path('C:/Users/danhm/.orchflows/lib/standards'))
assert pin['digest'] == installed['digest'] == 'sha256:8049030d7cef517e5d6dbc09a1ece092c43841521cd76665022132bded12ddf6', (pin, installed)
original = tickets_mint._context
with patch.object(tickets_mint, '_context', side_effect=lambda parent, artifacts, supplied=None: original(parent, artifacts)):
    result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([CallableContextTest('test_context_survives_builder_frame_planner_maker_and_judge')]))
assert len(result.failures) == 1 and len(result.errors) == 0, (result.failures, result.errors)
print(json.dumps({'standard_pin': pin['digest'], 'source_installed_match': True, 'context_carrier_removed_in_memory': {'failures':len(result.failures), 'errors':len(result.errors)}, 'failure': result.failures[0][1]}))
