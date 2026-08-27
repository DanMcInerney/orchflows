"""Generate the current-format integration gate for one root."""
from __future__ import annotations

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_format import GATE_EXECUTORS, ROOT_EXECUTOR, _extract_flag, _parse_frontmatter, _sections, _split_commas, ticket_defects
    from .tickets_issue import NEW_DEFAULT_BOUND, _distinct_gate_lenses
    from .tickets_issue_render import _render_ticket
    from .tickets_packet import GATE_CRITIQUE_ID, GATE_REPAIR_ID, GATE_VERIFY_ID
    from .tickets_store import NO_SINK_ERROR, _create_text_exclusively, _load_ticket, _run_lock, _segment_error, _tickets_root
else:
    from tickets_admission import ADMISSION_PENDING
    from tickets_format import GATE_EXECUTORS, ROOT_EXECUTOR, _extract_flag, _parse_frontmatter, _sections, _split_commas, ticket_defects
    from tickets_issue import NEW_DEFAULT_BOUND, _distinct_gate_lenses
    from tickets_issue_render import _render_ticket
    from tickets_packet import GATE_CRITIQUE_ID, GATE_REPAIR_ID, GATE_VERIFY_ID
    from tickets_store import NO_SINK_ERROR, _create_text_exclusively, _load_ticket, _run_lock, _segment_error, _tickets_root

GATE_USAGE = "gate <run> <root-id> [--lens <name>[,<name>] | --ordered-lens-bundle <name>[,<name>]]"


def _pack_domain(pack) -> str:
    name = str(pack or "").removeprefix("orch-").removesuffix("-pack")
    return name or "code"


def _input_name(line: str):
    return str(line).strip().lstrip("- ").split(":", 1)[0].strip()


def _gate_input(name: str, **values) -> str:
    facts = ", ".join(f"{key}={value}" for key, value in sorted(values.items()) if value is not None)
    return f"- {name}: {facts}"


def _listed_items(values) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "[]"


def _gate_body(kind: str, root_id: str, lens: str = "", units=None,
               repaired_by=None):
    units = list(units or [])
    if kind == "critique":
        return [
            ("Goal", f"Review `{root_id}` and its delivered members under the `{lens or 'default'}` lens; enumerate every evidence-backed material blocker to the root Goal, then synthesize the smallest architectural repair set covering the most blockers."),
            ("Context", _listed_items([f"root ticket: {root_id}", *(f"member ticket: {item}" for item in units), "Critique is read-only; Suggested files do not define review authority."])),
        ]
    if kind == "repair":
        return [
            ("Goal", f"Resolve accepted blockers for `{root_id}`, mechanically detect actual overlapping candidate diffs and ordinary Git conflicts, resolve them, and regenerate shared derived artifacts once."),
            ("Context", _listed_items([*(f"critique ticket: {item}" for item in units), "The integrator may edit or create any repository file needed for the root Goal."])),
        ]
    return [
        ("Goal", f"Verify `{root_id}`'s Goal on the integrated tip after `{repaired_by or GATE_REPAIR_ID.format(root=root_id)}` and report the repository-global deterministic gate result."),
        ("Context", _listed_items([f"root ticket: {root_id}", f"integrated result ticket: {repaired_by or GATE_REPAIR_ID.format(root=root_id)}", "Verification chooses checks from Goal and repository law; no authored test list limits it."])),
    ]


def _gate_sections(*args, **kwargs):
    return _gate_body(*args, **kwargs) + [("Result", ""), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]")]


def _gate_stub(run: str, ticket_id: str, executor: str, depends_on: list,
               _suggested=None, sections=None, pack=None, **metadata) -> str:
    fields = {
        "id": ticket_id, "run": run, "status": "pending",
        "admission": ADMISSION_PENDING, "executor": executor,
        "sequence": metadata.get("sequence"), "pack": pack,
        "independence": "gate", "depends_on": list(depends_on),
        "isolation": metadata.get("isolation"), "bound": NEW_DEFAULT_BOUND,
        "review_order": metadata.get("review_order"),
        "claimed_by": "", "claimed_at": "",
        "root_generation": metadata.get("root_generation"),
    }
    return _render_ticket(fields, sections or [])


def _cmd_gate(rest):
    probe = list(rest)
    for flag in ("--lens", "--ordered-lens-bundle"):
        _extract_flag(probe, flag)
    if len(probe) != 2 or _segment_error("run id", probe[0]) is not None:
        return _gate_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _gate_under_run_lock(rest)
    except OSError as error:
        return {"error": f"unable to create gate: {error}"}


def _gate_under_run_lock(rest, _head_probe=None):
    args = list(rest)
    lens_arg = _extract_flag(args, "--lens")
    ordered_arg = _extract_flag(args, "--ordered-lens-bundle")
    if len(args) != 2 or (lens_arg is not None and ordered_arg is not None):
        return {"error": f"usage: {GATE_USAGE}"}
    run, root_id = args
    for kind, value in (("run id", run), ("ticket id", root_id)):
        held = _segment_error(kind, value)
        if held is not None:
            return held
    root = _tickets_root()
    if root is None:
        return {"error": NO_SINK_ERROR}
    directory = root / run
    root_path = directory / f"{root_id}.md"
    if not root_path.is_file():
        return {"error": f"root ticket not found: {run}/{root_id}"}
    root_ticket = _load_ticket(root_path)
    if "error" in root_ticket:
        return {"error": root_ticket["error"]}
    if str(root_ticket.get("executor") or "").strip() != ROOT_EXECUTOR:
        return {"error": f"gate requires decomposed root executor {ROOT_EXECUTOR}: {run}/{root_id}"}
    root_generation = str(root_ticket.get("root_generation") or "")
    if not root_generation:
        return {"error": "gate requires a stamped root generation"}
    units = []
    for path in sorted(directory.glob(f"{root_id}.*.md")):
        if ".gate." not in path.stem:
            units.append(path.stem)
    if len(units) < 2:
        return {"error": "composite gate requires two or more executor results"}
    lenses = _split_commas(ordered_arg if ordered_arg is not None else lens_arg)
    if not lenses:
        lenses = [_pack_domain(root_ticket.get("pack"))]
    try:
        lenses = _distinct_gate_lenses(lenses)
    except ValueError as error:
        return {"error": str(error)}
    rendered = []
    critique_ids = []
    gate_pack = root_ticket.get("pack")
    for review_order, lens in enumerate(lenses):
        critique_id = GATE_CRITIQUE_ID.format(root=root_id, lens=lens)
        critique_ids.append(critique_id)
        sections = _gate_sections("critique", root_id, lens, units=units)
        rendered.append((critique_id, _gate_stub(
            run, critique_id, GATE_EXECUTORS["critique"], units,
            sections=sections, root_generation=root_generation, pack=gate_pack,
            isolation="none", review_order=review_order,
        )))
    repaired_by = GATE_REPAIR_ID.format(root=root_id)
    sections = _gate_sections("repair", root_id, units=critique_ids)
    rendered.append((repaired_by, _gate_stub(
        run, repaired_by, GATE_EXECUTORS["repair"], critique_ids,
        sections=sections, root_generation=root_generation, pack=gate_pack,
        isolation="none",
    )))
    verify_id = GATE_VERIFY_ID.format(root=root_id)
    sections = _gate_sections("verify", root_id, units=units, repaired_by=repaired_by)
    rendered.append((verify_id, _gate_stub(
        run, verify_id, GATE_EXECUTORS["verify"], [repaired_by],
        sections=sections, root_generation=root_generation, pack=gate_pack,
        isolation="none",
    )))
    for ticket_id, text in rendered:
        defects = ticket_defects(text)
        if defects:
            return {"error": f"gate stub {ticket_id} is off contract: " + "; ".join(defects)}
        if (directory / f"{ticket_id}.md").exists():
            return {"error": f"gate ticket already exists: {ticket_id}"}
    written = []
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for ticket_id, text in rendered:
            path = directory / f"{ticket_id}.md"
            _create_text_exclusively(path, text)
            written.append(path)
    except OSError as error:
        for path in written:
            path.unlink(missing_ok=True)
        return {"error": f"unable to create gate: {error}"}
    return {"gate": {"run": run, "root": root_id, "tickets": [ticket_id for ticket_id, _ in rendered]}}


__all__ = (
    "GATE_USAGE", "_cmd_gate", "_gate_body", "_gate_input", "_gate_sections",
    "_gate_stub", "_gate_under_run_lock", "_input_name", "_listed_items",
    "_pack_domain",
)
