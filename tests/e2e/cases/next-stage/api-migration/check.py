"""Exercise both generations of consumer against the delivered API."""
import importlib.util


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(c):
    workspace = c.stage()
    for name in ('api.py', 'client.py', 'compatibility.md'):
        c.require((workspace / name).is_file(), 'Deliver the compatible change and explanation', name)
    if not all((workspace / name).is_file() for name in ('api.py', 'client.py')):
        return
    api = load(workspace / 'api.py', 'delivered_api')
    client = load(workspace / 'client.py', 'delivered_client')
    legacy = load(workspace / 'reference/legacy_client.py', 'legacy_client')
    for identifier, name in [('a', 'Ada'), ('β', '  Renée ☀  '), ('empty', '')]:
        original = {'id': identifier, 'name': name, 'ignored': 'unchanged'}
        before = original.copy()
        try:
            result = api.get_profile(original)
            passed = (result == {'id': identifier, 'name': name, 'display_name': name}
                      and original == before
                      and client.label({'id': identifier, 'display_name': name}) == 'Hello, ' + name
                      and legacy.label(result) == 'Welcome back, ' + name)
        except Exception:
            passed = False
        c.require(passed, 'New and legacy clients retain exact compatible behavior', identifier)
