"""Lifecycle/record-prefix literal lint (report P7/P8, spec U6a).

An AST-level check, not a textual one: it parses each scanned Python
source and refuses a bare string constant matching a closed set of
lifecycle-status, record-id-prefix, and workspace-field-name literals
outside the one module report P7/P8 name as that literal's declared
owner. A comment is never a parsed node and a docstring is excluded by
its position in the body, so quoting one of these words in prose never
trips this check -- only a literal used as a value (a comparison, a dict
value, a call argument, an f-string prefix) does. Ruling 3: one owner,
every other reader imports.
"""

from __future__ import annotations

from tools.validate_support import common as __dep_common
ast = __dep_common.ast
Path = __dep_common.Path
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED

from tools.validate_support import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics

# Each literal's declared owner: the module whose own module-level
# assignment defines it (report P7/P8's "owns"). Every other scanned site
# must import the name instead of respelling the string.
LIFECYCLE_LITERAL_OWNERS = {
    "pending": "scripts/tickets_admission.py",         # ADMISSION_PENDING
    "claimed": "scripts/tickets_transitions.py",        # CLAIMED
    "suspended": "scripts/tickets_transitions.py",       # SUSPENDED
    "workspace_branch": "scripts/workspace_git.py",      # BRANCH_KEY
    "workspace_baseline": "scripts/workspace_git.py",    # BASELINE_KEY
    "workspace_path": "scripts/workspace_record.py",     # PATH_KEY
    "receipt.json": "scripts/orchflows_home.py",          # RECEIPT_FILENAME
}
# Record-id namespace prefixes: matched by `startswith`, since a live
# record id is never the bare prefix alone (`"join:" + outcome_record_id`,
# `f"lifecycle:{...}"`, `record_id.startswith("lifecycle:")`) but every one
# of those forms carries an exact-prefix string constant an AST walk sees.
LIFECYCLE_PREFIX_OWNERS = {
    "join:": "scripts/tickets_dispatch_identity.py",       # JOIN_RECORD_PREFIX
    "lifecycle:": "scripts/tickets_dispatch_identity.py",  # LIFECYCLE_RECORD_PREFIX
}
# Generated from contracts/shapes.json by tools/render_shapes.py and
# drift-checked by tools/regen.py (also ENUM_OWNER_MODULES's exemption, one
# package over, for the same reason): every value it carries is the
# schema's own, not a second hand-typed copy, so it never enters this scan.
LIFECYCLE_LITERAL_EXEMPT_FILES = frozenset({"scripts/tickets_shapes.py"})
# A literal that matches by spelling but names a different fact, kept as
# an explicit, reasoned exemption rather than a silent file skip -- so a
# real future bypass in the same file still gets caught, and a reader can
# see why this one site does not convert. Keyed by (file, literal, a
# sibling dict key, that sibling's value) rather than by line number or
# text: an edit that moves the site, or drops the sibling that marks it
# as a different protocol's envelope, leaves the exemption matching
# nothing rather than silently sliding onto the wrong site.
LIFECYCLE_LITERAL_EXEMPT_SITES = frozenset({
    # search-advance/v1's own response envelope carries a "status" field
    # of its own -- a different protocol than the ticket's, sharing only
    # the English word. The "schema" sibling is what tells the two apart.
    (
        "scripts/search_plan_advance.py", "pending",
        "schema", "search-advance/v1",
    ),
})
# Top-level modules only, per the site lists in P7/P8: the fact this check
# grades is ticket/workspace/installer state, never a nested package's own
# business, and every real site found lives at this depth.
LIFECYCLE_LITERAL_SCAN_DIRS = ("scripts", "installer")


def _docstring_ids(tree) -> set:
    """id() of every Constant node that is a module/class/function docstring."""

    ids = set()
    nodes = [tree] + [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    for node in nodes:
        body = getattr(node, "body", ())
        if (
            body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            ids.add(id(body[0].value))
    return ids


def _parents(tree) -> dict:
    """id(child) -> parent node, one pass, for the structural exemption below."""

    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _structurally_exempt(node, parent) -> bool:
    """A dict key, or the probed side of a key-membership test, names a
    different fact than the value the owner declares: `{"pending":
    check_id}` is a result-envelope key, and `"pending" in reading` asks
    whether that key is present -- neither is the ticket's own `status`
    field, which is always a dict *value* or a direct comparison operand.
    """

    if isinstance(parent, ast.Dict):
        return any(key is node for key in parent.keys)
    if isinstance(parent, ast.Compare):
        return parent.left is node and any(
            isinstance(op, (ast.In, ast.NotIn)) for op in parent.ops
        )
    return False


def _dict_sibling(node, parent, key_name: str):
    """The literal value of sibling key `key_name` in the dict that holds
    `node` as one of its values, or None if `node` is not a dict value or
    carries no such sibling."""

    if not isinstance(parent, ast.Dict) or all(key is not node for key in parent.values):
        return None
    for key, value in zip(parent.keys, parent.values):
        if (
            isinstance(key, ast.Constant) and key.value == key_name
            and isinstance(value, ast.Constant) and isinstance(value.value, str)
        ):
            return value.value
    return None


def _reasoned_exempt(file_label: str, value: str, node, parent) -> bool:
    return any(
        file_label == label and value == literal
        and _dict_sibling(node, parent, sibling_key) == sibling_value
        for label, literal, sibling_key, sibling_value in LIFECYCLE_LITERAL_EXEMPT_SITES
    )


def _owner(value: str):
    owner = LIFECYCLE_LITERAL_OWNERS.get(value)
    if owner is not None:
        return owner
    for prefix, prefix_owner in LIFECYCLE_PREFIX_OWNERS.items():
        if value.startswith(prefix):
            return prefix_owner
    return None


def _scan_file(source: Path, label: str, diag: Diagnostics) -> None:
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    try:
        tree = ast.parse(text, filename=label)
    except SyntaxError:
        return
    docstrings = _docstring_ids(tree)
    parents = _parents(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstrings:
            continue
        owner = _owner(node.value)
        if owner is None or owner == label:
            continue
        parent = parents.get(id(node))
        if _structurally_exempt(node, parent):
            continue
        if _reasoned_exempt(label, node.value, node, parent):
            continue
        diag.error(
            label,
            f"line {node.lineno}: bare literal {node.value!r} bypasses its "
            f"declared owner ({owner}); import the name instead of "
            "respelling the string",
        )


def validate_lifecycle_literals(diag: Diagnostics, root=None) -> None:
    """Refuse a bare lifecycle/record-prefix/field-name string literal
    outside the one module report P7/P8 name as its declared owner.

    Reverting a converted site to its bare literal is exactly what this
    check exists to catch: `git checkout` one owner-import back to its
    original string and this fails on that file and line alone.
    """

    root = ROOT if root is None else root
    seen_a_dir = False
    for name in LIFECYCLE_LITERAL_SCAN_DIRS:
        directory = root / name
        if not directory.is_dir():
            continue
        seen_a_dir = True
        for source in sorted(directory.glob("*.py")):
            label = f"{name}/{source.name}"
            if label in LIFECYCLE_LITERAL_EXEMPT_FILES:
                continue
            _scan_file(source, label, diag)
    if not seen_a_dir:
        diag.warn(LIFECYCLE_LITERAL_SCAN_DIRS[0], SKIPPED)


__all__ = (
    'LIFECYCLE_LITERAL_OWNERS', 'LIFECYCLE_PREFIX_OWNERS',
    'LIFECYCLE_LITERAL_EXEMPT_FILES', 'LIFECYCLE_LITERAL_EXEMPT_SITES',
    'LIFECYCLE_LITERAL_SCAN_DIRS', 'validate_lifecycle_literals',
)
