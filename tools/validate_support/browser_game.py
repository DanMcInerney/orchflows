"""Structural traceability for the canonical browser-game composition."""

from __future__ import annotations

from tools.validate_support import common as _common
from scripts import browser_game_validate as _instance_validator


Path = _common.Path
json = _common.json
re = _common.re
SKIPPED = _common.SKIPPED

TRACEABILITY_RELATIVE = Path("example-workflows/browser-game/traceability.json")
INTAKE_POLICY_RELATIVE = Path("example-workflows/references/browser-game-intake-policy.json")
INSTANCE_FIXTURES_RELATIVE = Path("example-workflows/references/browser-game-instance-fixtures.json")
SPECIFICATION_IDENTITY = (
    "document:sha256:e147d8609f74d25cf913b313d360c6fc1692dff2ed0f989d8f1168adee9a52e8"
)
IDENTITY_RE = re.compile(r"^(?:AUTH|U|CR|EX|PJ|D)-\d{2}$")
MARKER_RE = re.compile(
    r"BGW-TRACE\[(?P<surface>implementation|test|help):"
    r"(?P<behavior>[a-z][a-z0-9-]*)\|"
    r"(?P<identities>(?:AUTH|U|CR|EX|PJ|D)-\d{2}"
    r"(?:,(?:AUTH|U|CR|EX|PJ|D)-\d{2})*)\]"
)
SURFACES = ("implementation", "test", "help")
INVENTORY_GLOBS = {
    "implementation": (
        "example-workflows/browser-game/*.md",
        "example-workflows/browser-game/*.json",
        "scripts/browser_game_validate.py",
    ),
    "test": ("tests/test_browser_game*.py",),
    "help": ("example-workflows/browser-game/*.md",),
}


def _label(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _load_json(path: Path, root: Path, diag):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        diag.error(_label(path, root), f"cannot read structural JSON: {exc}")
        return None


def _owned_path(root: Path, token, owner: Path, field: str, diag):
    if not isinstance(token, str) or not token:
        diag.error(_label(owner, root), f"{field} must name one repository-relative path")
        return None
    relative = Path(token)
    if relative.is_absolute():
        diag.error(_label(owner, root), f"{field} must be repository-relative, got {token!r}")
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        diag.error(_label(owner, root), f"{field} escapes the repository: {token!r}")
        return None
    return candidate


def _marker_inventory(root: Path, diag) -> dict[str, dict[str, list[tuple[Path, list[str]]]]]:
    inventory = {surface: {} for surface in SURFACES}
    scanned: set[Path] = set()
    permitted: dict[str, set[Path]] = {surface: set() for surface in SURFACES}
    for surface, patterns in INVENTORY_GLOBS.items():
        for pattern in patterns:
            permitted[surface].update(path.resolve() for path in root.glob(pattern) if path.is_file())
            scanned.update(path.resolve() for path in root.glob(pattern) if path.is_file())
    for path in sorted(scanned):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            diag.error(_label(path, root), f"cannot inventory traceability markers: {exc}")
            continue
        for match in MARKER_RE.finditer(text):
            surface = match.group("surface")
            behavior = match.group("behavior")
            identities = match.group("identities").split(",")
            if path not in permitted[surface]:
                diag.error(
                    _label(path, root),
                    f"{surface} marker for {behavior} appears outside its admitted inventory surface",
                )
            inventory[surface].setdefault(behavior, []).append((path, identities))
    return inventory


def _validate_behaviors(manifest: dict, manifest_path: Path, root: Path, diag) -> None:
    behaviors = manifest.get("behaviors")
    if not isinstance(behaviors, list) or not behaviors:
        diag.error(_label(manifest_path, root), "behaviors must be a non-empty list")
        return

    seen = set()
    valid_rows = {}
    for index, row in enumerate(behaviors):
        where = f"behaviors[{index}]"
        if not isinstance(row, dict):
            diag.error(_label(manifest_path, root), f"{where} must be an object")
            continue
        behavior = row.get("behavior")
        identities = row.get("identities")
        if not isinstance(behavior, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", behavior):
            diag.error(_label(manifest_path, root), f"{where}.behavior is not a stable kebab-case id")
            continue
        if behavior in seen:
            diag.error(_label(manifest_path, root), f"behavior {behavior!r} is repeated")
        seen.add(behavior)
        if (
            not isinstance(identities, list)
            or not identities
            or any(not isinstance(identity, str) or not IDENTITY_RE.fullmatch(identity) for identity in identities)
            or len(set(identities)) != len(identities)
        ):
            diag.error(
                _label(manifest_path, root),
                f"{behavior} must name one or more unique AUTH, U, CR, EX, PJ, or D normative identity",
            )
            continue
        canonical = sorted(identities)
        if identities != canonical:
            diag.error(_label(manifest_path, root), f"{behavior} identities must be sorted: {canonical}")
        valid_rows[behavior] = row

    inventory = _marker_inventory(root, diag)
    for surface in SURFACES:
        marker_behaviors = set(inventory[surface])
        manifest_behaviors = set(valid_rows)
        for behavior in sorted(marker_behaviors - manifest_behaviors):
            diag.error(
                _label(manifest_path, root),
                f"{surface} marker {behavior!r} is not declared by the manifest",
            )
        for behavior in sorted(manifest_behaviors - marker_behaviors):
            diag.error(
                _label(manifest_path, root),
                f"manifest behavior {behavior!r} has no inventoried {surface} marker",
            )

    for behavior, row in valid_rows.items():
        identities = sorted(row["identities"])
        for surface in SURFACES:
            surface_path = _owned_path(root, row.get(surface), manifest_path, f"{behavior}.{surface}", diag)
            if surface_path is None:
                continue
            actual = inventory[surface].get(behavior, [])
            expected = [(surface_path.resolve(), identities)]
            normalized = [(path.resolve(), sorted(found)) for path, found in actual]
            if normalized != expected:
                diag.error(
                    _label(surface_path, root),
                    f"{surface} surface for {behavior} must have one marker at the manifest path "
                    f"with identities {identities}; found "
                    f"{[(_label(path, root), found) for path, found in normalized]}",
                )


def _validate_program_record(manifest: dict, manifest_path: Path, root: Path, diag) -> None:
    contract = manifest.get("program_record_contract")
    if not isinstance(contract, dict):
        diag.error(_label(manifest_path, root), "program_record_contract must be an object")
        return
    schema_path = _owned_path(root, contract.get("schema"), manifest_path, "program_record_contract.schema", diag)
    if schema_path is None:
        return
    schema = _load_json(schema_path, root, diag)
    if not isinstance(schema, dict):
        return

    common = contract.get("common_revision_fields")
    if not isinstance(common, list) or not common or any(not isinstance(field, str) for field in common):
        diag.error(_label(manifest_path, root), "common_revision_fields must be a non-empty string list")
        common = []
    base_required = set(schema.get("$defs", {}).get("recordRevision", {}).get("required", []))
    missing_common = sorted(set(common) - base_required)
    if missing_common:
        diag.error(_label(schema_path, root), f"record revision is missing required field(s): {missing_common}")

    rows = contract.get("minimum_schema_rows")
    if not isinstance(rows, list) or not rows:
        diag.error(_label(manifest_path, root), "minimum_schema_rows must be a non-empty list")
        return
    valid_rows = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            diag.error(_label(manifest_path, root), f"minimum_schema_rows[{index}] must be an object")
            continue
        record = row.get("record")
        if not isinstance(record, str) or not record:
            diag.error(_label(manifest_path, root), f"minimum_schema_rows[{index}] lacks record")
            continue
        if record in valid_rows:
            diag.error(_label(manifest_path, root), f"minimum schema row {record!r} is repeated")
        valid_rows[record] = row

    records = schema.get("properties", {}).get("records", {})
    schema_records = set(records.get("properties", {}))
    required_records = set(records.get("required", []))
    expected_records = set(valid_rows)
    if schema_records != expected_records or required_records != expected_records:
        diag.error(
            _label(schema_path, root),
            "program-record roster must exactly match governed minimum rows; "
            f"rows={sorted(expected_records)}, properties={sorted(schema_records)}, required={sorted(required_records)}",
        )

    definitions = schema.get("$defs", {})
    for record, row in valid_rows.items():
        definition_name = row.get("definition")
        identities = row.get("identities")
        required_fields = row.get("required_fields")
        if not isinstance(definition_name, str) or not definition_name:
            diag.error(_label(manifest_path, root), f"{record} lacks a schema definition")
            continue
        if not isinstance(identities, list) or not identities:
            diag.error(_label(manifest_path, root), f"{record} lacks governing identities")
            identities = []
        if not isinstance(required_fields, list) or not required_fields:
            diag.error(_label(manifest_path, root), f"{record} lacks governed required fields")
            required_fields = []
        definition = definitions.get(definition_name, {})
        observed_identities = definition.get("x-governing-identities", [])
        if identities != observed_identities:
            diag.error(
                _label(schema_path, root),
                f"{record} governing identities disagree: expected {identities}, found {observed_identities}",
            )
        missing = sorted(set(required_fields) - set(definition.get("required", [])))
        if missing:
            diag.error(_label(schema_path, root), f"{record} is missing governed required field(s): {missing}")
        refs = {
            part.get("$ref")
            for part in definition.get("allOf", [])
            if isinstance(part, dict)
        }
        if "#/$defs/recordRevision" not in refs:
            diag.error(_label(schema_path, root), f"{record} does not inherit the common record revision")
        collection = records.get("properties", {}).get(record, {})
        try:
            observed_ref = collection["oneOf"][0]["properties"]["entries"]["items"]["$ref"]
        except (KeyError, IndexError, TypeError):
            observed_ref = None
        expected_ref = f"#/$defs/{definition_name}"
        if observed_ref != expected_ref:
            diag.error(
                _label(schema_path, root),
                f"{record} present-state entries must use {expected_ref}, found {observed_ref!r}",
            )


def _validate_instance_contracts(manifest: dict, manifest_path: Path, root: Path, diag) -> None:
    contract = manifest.get("program_record_contract", {})
    schema_path = _owned_path(
        root, contract.get("schema"), manifest_path, "program_record_contract.schema", diag
    )
    if schema_path is None:
        return
    policy_path = root / INTAKE_POLICY_RELATIVE
    fixtures_path = root / INSTANCE_FIXTURES_RELATIVE
    schema = _load_json(schema_path, root, diag)
    policy = _load_json(policy_path, root, diag)
    fixtures = _load_json(fixtures_path, root, diag)
    if not all(isinstance(value, dict) for value in (schema, policy, fixtures)):
        return
    for error in _instance_validator.validate_authority_contract(policy, schema):
        diag.error(_label(policy_path, root), error)
    program_record = fixtures.get("program_record")
    checkpoint = fixtures.get("checkpoint")
    if not isinstance(program_record, dict) or not isinstance(checkpoint, dict):
        diag.error(
            _label(fixtures_path, root),
            "fixture must contain program_record and checkpoint objects",
        )
        return
    for error in _instance_validator.validate_instances(program_record, checkpoint, policy):
        diag.error(_label(fixtures_path, root), error)


def validate_browser_game_traceability(diag, *, root: Path | None = None) -> None:
    """Reject drift between browser-game behaviors, surfaces, and schema rows."""

    root = (root or Path(__file__).resolve().parents[2]).resolve()
    manifest_path = root / TRACEABILITY_RELATIVE
    composition = manifest_path.parent
    if not composition.is_dir():
        diag.warn(str(TRACEABILITY_RELATIVE).replace("\\", "/"), SKIPPED)
        return
    manifest = _load_json(manifest_path, root, diag)
    if not isinstance(manifest, dict):
        return
    if manifest.get("format") != "orchflows.browser-game-traceability.v1":
        diag.error(_label(manifest_path, root), "format must be orchflows.browser-game-traceability.v1")
    if manifest.get("specification") != SPECIFICATION_IDENTITY:
        diag.error(_label(manifest_path, root), "specification identity does not match the admitted browser-game authority")
    _validate_behaviors(manifest, manifest_path, root, diag)
    _validate_program_record(manifest, manifest_path, root, diag)
    _validate_instance_contracts(manifest, manifest_path, root, diag)


__all__ = ("validate_browser_game_traceability",)
