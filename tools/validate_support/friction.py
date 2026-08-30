"""Validate friction owner and fallback copies."""

from __future__ import annotations


def rel(path):
    from tools.validate_support.packages import rel as relative
    return relative(path)


def _read_source(path):
    from tools.validate_support.packages import _read_source as read_source
    return read_source(path)

from tools.validate_support import common as __dep_common
Path = __dep_common.Path
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
ast = __dep_common.ast
re = __dep_common.re

FRICTION_CHECKED_COPIES = ("templates/host-block.md",)
FRICTION_OWNER = ROOT / "scripts" / "state_root.py"
FRICTION_RESOLVER = "friction_root"
FRICTION_IN_REPOSITORY = ".orch/"
FRICTION_TERM_RE = re.compile(r"^- \*\*friction log\*\*.*?(?=\n- \*\*|\Z)", re.MULTILINE | re.DOTALL)
# The managed host block carries the refusal-safe sink instruction verbatim;
# this check only validates its destination against scripts/state_root.py.
FRICTION_FALLBACK_RE = re.compile(r"If the logger cannot run.*?never skip (?:the log|it)\.")


def _friction_join_tree(node) -> str:
    """The tree a `<sink root> / "name"` expression names, spelled as a
    copy spells it -- 'name/'. None when the expression is not such a
    join."""
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
        return None
    name = node.right
    if not (isinstance(name, ast.Constant) and isinstance(name.value, str)):
        return None
    return name.value + "/"


def _friction_owner_tree(diag: Diagnostics):
    """The sink tree scripts/state_root.py resolves the log into, or None
    with the defect reported."""
    label = rel(FRICTION_OWNER)
    try:
        tree = ast.parse(_read_source(FRICTION_OWNER))
    except SyntaxError as exc:
        diag.error(label, f"does not parse, so the friction log location cannot be read: {exc}")
        return None
    resolver = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == FRICTION_RESOLVER),
        None,
    )
    if resolver is None:
        diag.error(label, f"no `{FRICTION_RESOLVER}` to read the friction log location from")
        return None
    found = []
    for node in ast.walk(resolver):
        if isinstance(node, ast.Return) and node.value is not None:
            location = _friction_join_tree(node.value)
            if location is not None:
                found.append(location)
    if len(found) != 1:
        diag.error(
            label,
            f"`{FRICTION_RESOLVER}` must resolve exactly one sink tree for the copies to be "
            f"checked against; read {sorted(found)}",
        )
        return None
    return found[0]


def _friction_validate_term(tree: str, diag: Diagnostics) -> None:
    path = ROOT / "docs" / "vocabulary.md"
    if not path.is_file():
        diag.warn(rel(path), SKIPPED)  # not this check's tree (isolated fixtures)
        return
    match = FRICTION_TERM_RE.search(_read_source(path))
    if match is None:
        diag.error(rel(path), "could not locate the **friction log** term entry to check against scripts/state_root.py")
        return
    entry = re.sub(r"\s+", " ", match.group(0))
    if tree not in entry:
        diag.error(
            rel(path),
            f"**friction log** entry does not name {tree} -- scripts/state_root.py resolves "
            f"the log into that tree of the sink",
        )


def _friction_validate_fallback_copy(path: Path, tree: str, diag: Diagnostics) -> None:
    file_label = rel(path)
    if not path.is_file():
        diag.error(file_label, "friction fallback copy is missing")
        return
    match = FRICTION_FALLBACK_RE.search(re.sub(r"\s+", " ", _read_source(path)))
    if match is None:
        diag.error(
            file_label,
            "could not locate the blocked-case friction sentence ('If the logger cannot "
            "run ... never skip it.') to check against scripts/state_root.py",
        )
        return
    sentence = match.group(0)
    if tree not in sentence:
        diag.error(
            file_label,
            f"blocked-case friction fallback does not spell {tree}, the sink tree "
            f"scripts/state_root.py resolves outside every worktree",
        )
    if FRICTION_IN_REPOSITORY in sentence:
        diag.error(
            file_label,
            f"blocked-case friction fallback sends the entry to {FRICTION_IN_REPOSITORY}, inside "
            f"the worktree whose writes the refusal may cover",
        )


def validate_friction_locations(diag: Diagnostics) -> None:
    """Every copy of the friction log's location against their owner,
    scripts/state_root.py."""
    if not FRICTION_OWNER.is_file():
        diag.warn(rel(FRICTION_OWNER), SKIPPED)  # not this check's tree
        return
    tree = _friction_owner_tree(diag)
    if tree is None:
        return
    _friction_validate_term(tree, diag)
    for name in FRICTION_CHECKED_COPIES:
        _friction_validate_fallback_copy(ROOT / name, tree, diag)

__all__ = (
    'FRICTION_CHECKED_COPIES', 'FRICTION_OWNER', 'FRICTION_RESOLVER', 'FRICTION_IN_REPOSITORY',
    'FRICTION_TERM_RE', 'FRICTION_FALLBACK_RE', '_friction_join_tree', '_friction_owner_tree',
    '_friction_validate_term', '_friction_validate_fallback_copy', 'validate_friction_locations',
)
