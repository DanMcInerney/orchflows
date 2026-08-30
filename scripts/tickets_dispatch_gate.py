"""Generate the current-format integration gate for one root."""
from __future__ import annotations

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_format import ROOT_EXECUTOR, _executor_of, _extract_flag, _parse_frontmatter, _sections, _set_frontmatter_field, _split_commas, dequote, ticket_defects
    from .tickets_generations import assignment_digest, seal_findings
    from .tickets_dispatch_schema import state as _dispatch_state
    from .tickets_issue import NEW_DEFAULT_BOUND, _distinct_gate_lenses
    from .tickets_issue_render import _render_ticket
    from .tickets_ordinary_review import ordinary_stage_matches, ordinary_stages
    from .tickets_packet import GATE_CRITIQUE_ID, GATE_REPAIR_ID, GATE_VERIFY_ID
    from .tickets_review import ReviewError, review_records, state_from_text
    from .tickets_store import NO_SINK_ERROR, TicketWriteRefused, _create_text_exclusively, _load_ticket, _segment_error, _tickets_root, locked_ticket_write
else:
    from tickets_admission import ADMISSION_PENDING
    from tickets_format import ROOT_EXECUTOR, _executor_of, _extract_flag, _parse_frontmatter, _sections, _set_frontmatter_field, _split_commas, dequote, ticket_defects
    from tickets_generations import assignment_digest, seal_findings
    from tickets_dispatch_schema import state as _dispatch_state
    from tickets_issue import NEW_DEFAULT_BOUND, _distinct_gate_lenses
    from tickets_issue_render import _render_ticket
    from tickets_ordinary_review import ordinary_stage_matches, ordinary_stages
    from tickets_packet import GATE_CRITIQUE_ID, GATE_REPAIR_ID, GATE_VERIFY_ID
    from tickets_review import ReviewError, review_records, state_from_text
    from tickets_store import NO_SINK_ERROR, TicketWriteRefused, _create_text_exclusively, _load_ticket, _segment_error, _tickets_root, locked_ticket_write

GATE_USAGE = "gate <run> <root-or-checked-id> [--lens <name>[,<name>] | --ordered-lens-bundle <name>[,<name>]]"
CHECKER_STAGE_USAGE = "checker-stage <run> <id>"


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
        "independence": metadata.get("independence") or "gate",
        "depends_on": list(depends_on),
        "isolation": metadata.get("isolation"), "bound": NEW_DEFAULT_BOUND,
        "review_order": metadata.get("review_order"),
        "review_kind": metadata.get("review_kind"),
        "claimed_by": "", "claimed_at": "",
        "root_generation": metadata.get("root_generation"),
    }
    return _render_ticket(fields, sections or [])


def _cmd_gate(rest):
    probe = list(rest)
    for flag in ("--lens", "--ordered-lens-bundle"):
        _extract_flag(probe, flag)
    if len(probe) != 2:
        return {"error": f"usage: {GATE_USAGE}"}
    try:
        with locked_ticket_write(probe[0], probe[1]):
            return _gate_under_run_lock(rest)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {"error": f"unable to create gate: {error}"}


def _cmd_checker_stage(rest):
    if len(rest) != 2:
        return {"error": f"usage: {CHECKER_STAGE_USAGE}"}
    try:
        with locked_ticket_write(rest[0], rest[1]) as target_path:
            return _checker_stage_under_run_lock(rest, target_path=target_path)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {"error": f"unable to create checker stage: {error}"}


def _checker_stage_under_run_lock(rest, *, target_path=None):
    if len(rest) != 2:
        return {"error": f"usage: {CHECKER_STAGE_USAGE}"}
    run, target_id = rest
    for kind, value in (("run id", run), ("ticket id", target_id)):
        held = _segment_error(kind, value)
        if held is not None:
            return held
    root = _tickets_root()
    if root is None:
        return {"error": NO_SINK_ERROR}
    directory = root / run
    if target_path is None:
        target_path = directory / f"{target_id}.md"
    if not target_path.is_file():
        return {"error": f"checker target not found: {run}/{target_id}"}
    target = _load_ticket(target_path)
    if "error" in target:
        return {"error": target["error"]}
    if str(target.get("independence") or "checker") != "checker":
        return {"error": f"ticket {run}/{target_id} defers independence to its downstream gate"}
    if str(target.get("checked_by") or "").strip():
        return {"error": f"ticket {run}/{target_id} is already checked"}
    if not dequote(target.get("pack")):
        return {"error": "checker-stage requires target pack authority"}
    root_generation = str(target.get("root_generation") or "")
    if not root_generation:
        return {"error": "checker-stage requires one stamped target assignment"}
    stage_id = f"{target_id}.check"
    stage_path = directory / f"{stage_id}.md"
    if stage_path.exists():
        loaded = _load_ticket(stage_path)
        try:
            stage_text = stage_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            stage_text = ""
        if (
            "error" not in loaded
            and list(loaded.get("depends_on") or []) == [target_id]
            and _executor_of(loaded) == "orch-check"
            and str(loaded.get("review_kind") or "") == "critique"
            and str(loaded.get("root_generation") or "") == root_generation
            and not seal_findings(stage_id, stage_text)
        ):
            return {"checker_stage": {"run": run, "target": target_id, "ticket": stage_id, "outcome": "replayed"}}
        return {"error": f"checker stage already exists with different content: {stage_id}"}
    sections = _gate_sections("critique", target_id, "checker", units=[target_id])
    text = _gate_stub(
        run, stage_id, "orch-check", [target_id],
        sections=sections, root_generation=root_generation,
        pack=target.get("pack"), isolation="none", review_order=0,
        independence="gate", review_kind="critique",
    )
    cut_generation = str(target.get("cut_generation") or "")
    if not cut_generation:
        return {"error": "checker-stage requires one sealed target cut"}
    text = _set_frontmatter_field(text, "cut_generation", cut_generation)
    text = _set_frontmatter_field(
        text, "assignment_seal", assignment_digest(stage_id, text),
    )
    defects = ticket_defects(text)
    if defects:
        return {"error": f"checker stage {stage_id} is off contract: " + "; ".join(defects)}
    try:
        _create_text_exclusively(stage_path, text)
    except OSError as error:
        return {"error": f"unable to create checker stage: {error}"}
    return {"checker_stage": {"run": run, "target": target_id, "ticket": stage_id, "outcome": "created"}}


def _checker_gate_under_run_lock(
    run: str, target_id: str, target: dict, directory, *, has_lens_options: bool,
):
    if has_lens_options:
        return {"error": "ordinary checker continuation uses its fixed checker lens; gate lens options require a decomposed root"}
    if str(target.get("independence") or "checker") != "checker":
        return {"error": f"gate requires decomposed root executor {ROOT_EXECUTOR}: {run}/{target_id}"}
    stage_id = f"{target_id}.check"
    if (
        str(target.get("status") or "") != "complete"
        or not str(target.get("checked_by") or "").strip()
        or str(target.get("review_stage") or "") != stage_id
    ):
        return {"error": f"gate requires decomposed root executor {ROOT_EXECUTOR} or one completed ordinary checker anchor: {run}/{target_id}"}
    stage_path = directory / f"{stage_id}.md"
    try:
        stage_text = stage_path.read_text(encoding="utf-8")
        records = review_records(state_from_text(stage_text, required=True))
    except (OSError, UnicodeDecodeError, ReviewError) as error:
        return {"error": f"ordinary checker continuation has no valid adjudication: {error}"}
    if (
        [record["kind"] for record in records]
        != ["GatePlan", "CritiqueAdjudication"]
        or records[0]["mode"] != "checker"
        or records[0]["root"] != target_id
        or [item["ticket"] for item in records[0]["criteria"]] != [stage_id]
        or records[1]["lens"] != "checker"
    ):
        return {"error": "ordinary checker continuation ledger names a different target or stage"}
    dispatch_state, dispatch_failure = _dispatch_state(_parse_frontmatter(stage_text))
    if dispatch_failure is not None:
        return dispatch_failure
    joined = next((
        attempt for attempt in dispatch_state["attempts"]
        if any(record.get("kind") == "join" for record in attempt["records"])
    ), None)
    if (
        joined is None
        or joined["owner"] != records[1]["adjudicated_by"]
        or joined["owner"] != str(target.get("checked_by") or "")
    ):
        return {"error": "ordinary checker continuation is not owned by its accepted receiver"}
    if not records[1]["accepted"]:
        return {"error": "ordinary checker accepted no blockers; repair and fresh verification are not materialized"}
    root_generation = str(target.get("root_generation") or "")
    cut_generation = str(target.get("cut_generation") or "")
    if not root_generation or not cut_generation:
        return {"error": "ordinary checker continuation requires one sealed target assignment"}
    rendered = ordinary_stages(run, target_id, target)
    existing = [directory / f"{ticket_id}.md" for ticket_id, _ in rendered]
    if any(path.exists() for path in existing):
        if not all(path.exists() for path in existing):
            return {"error": "ordinary checker continuation is partial; refusing to guess the missing stage"}
        for (ticket_id, expected), path in zip(rendered, existing):
            loaded = _load_ticket(path)
            try:
                actual_text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                actual_text = ""
            if (
                "error" in loaded
                or not ordinary_stage_matches(
                    ticket_id, actual_text, expected,
                )
            ):
                return {"error": f"ordinary checker continuation stage already exists with different content: {ticket_id}"}
        return {"gate": {
            "run": run, "root": target_id,
            "tickets": [ticket_id for ticket_id, _ in rendered],
            "mode": "checker", "outcome": "replayed",
        }}
    for ticket_id, text in rendered:
        defects = ticket_defects(text)
        if defects:
            return {"error": f"gate stub {ticket_id} is off contract: " + "; ".join(defects)}
    written = []
    try:
        for ticket_id, text in rendered:
            path = directory / f"{ticket_id}.md"
            _create_text_exclusively(path, text)
            written.append(path)
    except OSError as error:
        for path in written:
            path.unlink(missing_ok=True)
        return {"error": f"unable to create ordinary checker continuation: {error}"}
    return {"gate": {
        "run": run, "root": target_id,
        "tickets": [ticket_id for ticket_id, _ in rendered],
        "mode": "checker", "outcome": "created",
    }}


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
    if str(root_ticket.get("independence") or "checker") == "checker":
        return _checker_gate_under_run_lock(
            run, root_id, root_ticket, directory,
            has_lens_options=lens_arg is not None or ordered_arg is not None,
        )
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
            run, critique_id, "orch-check", units,
            sections=sections, root_generation=root_generation, pack=gate_pack,
            isolation="none", review_order=review_order, review_kind="critique",
        )))
    repaired_by = GATE_REPAIR_ID.format(root=root_id)
    sections = _gate_sections("repair", root_id, units=critique_ids)
    rendered.append((repaired_by, _gate_stub(
        run, repaired_by, "orch-execute", critique_ids,
        sections=sections, root_generation=root_generation, pack=gate_pack,
        isolation="none", review_kind="repair",
    )))
    verify_id = GATE_VERIFY_ID.format(root=root_id)
    sections = _gate_sections("verify", root_id, units=units, repaired_by=repaired_by)
    rendered.append((verify_id, _gate_stub(
        run, verify_id, "orch-check", [repaired_by],
        sections=sections, root_generation=root_generation, pack=gate_pack,
        isolation="none", review_kind="verify",
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
    "CHECKER_STAGE_USAGE", "GATE_USAGE", "_cmd_checker_stage", "_cmd_gate",
    "_checker_gate_under_run_lock",
    "_gate_body", "_gate_input", "_gate_sections",
    "_gate_stub", "_gate_under_run_lock", "_input_name", "_listed_items",
    "_pack_domain",
)
