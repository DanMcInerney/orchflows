"""Capability-limited Python for the JSON solve admission profile, not host isolation.

Only data operations and named pure-library exports enter candidate globals.
AST admission forbids reflection, arbitrary imports and authority-bearing attributes.
Unsupported Python is UNVERIFIED; it is never executed and called a target failure.
"""
import ast
import __future__
import bisect
import builtins
import collections
import copy
import functools
import heapq
import itertools
import math
import types
import typing

MODULES = {
    '__future__': (__future__, 'annotations'),
    'typing': (typing, 'Any Optional Union List Dict Set Tuple Iterable Sequence Mapping MutableMapping DefaultDict Deque Callable Literal'),
    'heapq': (heapq, 'heapify heappush heappop heappushpop heapreplace nlargest nsmallest merge'),
    'bisect': (bisect, 'bisect bisect_left bisect_right insort insort_left insort_right'),
    'collections': (collections, 'Counter defaultdict deque OrderedDict'),
    'copy': (copy, 'copy deepcopy'),
    'functools': (functools, 'reduce lru_cache cache cmp_to_key'),
    'itertools': (itertools, 'accumulate chain combinations combinations_with_replacement count cycle dropwhile filterfalse groupby islice pairwise permutations product repeat starmap takewhile tee zip_longest'),
    'math': (math, 'ceil floor trunc sqrt isqrt gcd lcm prod fsum factorial comb perm isclose isfinite isinf isnan inf nan e pi tau log log2 log10 exp pow fabs fmod copysign'),
}
BUILTINS = 'abs all any ascii bin bool bytearray bytes callable chr dict divmod enumerate filter float frozenset hash hex int isinstance issubclass iter len list map max min next oct ord pow print range repr reversed round set slice sorted str sum tuple zip Exception ValueError TypeError IndexError KeyError RuntimeError ZeroDivisionError OverflowError StopIteration AssertionError NotImplementedError'
METHODS = set('append extend insert pop remove clear index count sort reverse copy get keys values items update setdefault popitem add discard union intersection difference symmetric_difference issubset issuperset isdisjoint intersection_update difference_update symmetric_difference_update move_to_end most_common elements total appendleft popleft extendleft rotate maxlen lower upper casefold strip lstrip rstrip split rsplit splitlines join replace startswith endswith find rfind partition rpartition isalpha isalnum isdigit isdecimal isspace islower isupper isascii capitalize title swapcase zfill center ljust rjust encode decode args real imag numerator denominator bit_length bit_count as_integer_ratio cache_clear cache_info'.split())
ATTRIBUTES = METHODS | {name for _, names in MODULES.values() for name in names.split()}
FORBIDDEN_NAMES = set('eval exec compile open input globals locals vars dir getattr setattr delattr type object super breakpoint help exit quit'.split())
UNSUPPORTED_NODES = (ast.ClassDef, ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith,
                     ast.With, ast.Global, ast.Nonlocal)


class UnsupportedSource(ValueError):
    """The source needs capabilities outside this verified evaluator profile."""


def inspect_source(source):
    tree = ast.parse(source)
    if len(source) > 200000:
        raise UnsupportedSource('source exceeds bounded Python profile')
    for node in ast.walk(tree):
        if isinstance(node, UNSUPPORTED_NODES):
            raise UnsupportedSource('unsupported Python node: ' + type(node).__name__)
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or (node.id.startswith('__') and node.id != '__name__')):
            raise UnsupportedSource('reflection or authority name: ' + node.id)
        if isinstance(node, ast.Attribute) and (node.attr not in ATTRIBUTES or not isinstance(node.ctx, ast.Load)):
            raise UnsupportedSource('unsupported attribute: ' + node.attr)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in MODULES:
                    raise UnsupportedSource('unsupported import: ' + alias.name)
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module not in MODULES:
                raise UnsupportedSource('unsupported import: ' + str(node.module))
            exports = MODULES[node.module][1].split()
            if any(alias.name not in exports for alias in node.names):
                raise UnsupportedSource('unsupported import member')
    return tree


def load_source(source):
    tree = inspect_source(source)
    facades = {name: types.SimpleNamespace(**{key: getattr(module, key) for key in names.split() if hasattr(module, key)})
               for name, (module, names) in MODULES.items()}

    def import_allowed(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name not in facades:
            raise UnsupportedSource('unsupported runtime import')
        return facades[name]

    safe = {name: getattr(builtins, name) for name in BUILTINS.split()}
    safe['__import__'] = import_allowed
    namespace = {'__builtins__': safe, '__name__': 'candidate'}
    exec(compile(tree, '<candidate>', 'exec'), namespace)
    return namespace
