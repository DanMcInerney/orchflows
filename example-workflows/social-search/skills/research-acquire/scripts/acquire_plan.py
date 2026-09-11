"""Closed two-stage research plan: validate bounds, present candidates, bind choices.

No keyword floor, ranking, route inference, fallback, or semantic selection.
The caller names discovery and depth routes; a model supplies record IDs and
reasons after inspecting the complete capped candidate batch.
"""

from dataclasses import asdict, replace
from datetime import datetime
import hashlib
import json
import re

from super_research import coverage, normalize, runner, schema, transport


class PlanError(ValueError):
    """Invalid scope, dates, bounds, or a choice outside the frozen candidate set."""


def digest(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def keys(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise PlanError("expected fields: " + ", ".join(required) + "; optional: " + ", ".join(optional))


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise PlanError(name + " must be nonempty text")
    return value


def positive(value, name):
    if type(value) is not int or value < 1:
        raise PlanError(name + " must be a positive integer")
    return value


def instant(value):
    try:
        parsed = datetime.strptime(value, schema.INSTANT_FORMAT)
        if parsed.strftime(schema.INSTANT_FORMAT) != value:
            raise ValueError("noncanonical instant")
    except (ValueError, TypeError):
        raise PlanError("invalid UTC instant: " + str(value))
    return value


def validate(plan):
    try:
        return _validate(plan)
    except PlanError:
        raise
    except (TypeError, ValueError, KeyError) as error:
        raise PlanError("malformed plan value: " + str(error)) from error


def _validate(plan):
    keys(plan, ("version", "plan_id", "question", "as_of", "window", "allowed_adapters",
                "limits", "discovery", "depth"))
    if type(plan["version"]) is not int or plan["version"] != 1:
        raise PlanError("plan version must be 1")
    for name in ("plan_id", "question"):
        text(plan[name], name)
    instant(plan["as_of"])
    window = plan["window"]
    if window is not None:
        keys(window, ("start", "end"))
        if not instant(window["start"]) <= instant(window["end"]) <= plan["as_of"]:
            raise PlanError("window must satisfy start <= end <= as_of")
    allowed = plan["allowed_adapters"]
    if (not isinstance(allowed, list) or not allowed or any(not isinstance(name, str) for name in allowed)
            or len(set(allowed)) != len(allowed)
            or any(name not in runner.ADAPTER_IDS or name == "fake" for name in allowed)):
        raise PlanError("allowed_adapters must explicitly name distinct public keyless adapters")
    limits = plan["limits"]
    keys(limits, ("max_steps", "max_requests", "max_records", "max_seconds"))
    for name, value in limits.items():
        positive(value, name)
    if not isinstance(plan["discovery"], list) or not plan["discovery"]:
        raise PlanError("discovery must contain explicit steps")
    steps = []
    for raw in plan["discovery"]:
        keys(raw, ("step_id", "adapter_id", "query", "max_items"))
        text(raw["query"], "query")
        if text(raw["step_id"], "step_id").startswith("depth-"):
            raise PlanError("depth- is reserved for selected hydration step IDs")
        steps.append(dict(raw, kind="discovery", **window_fields(plan)))
        # Embedded date operators create a second date owner. The adapters
        # derive origin bounds from the plan's instants where supported.
        if re.search(r"(?:since:|until:|after:|before:|after=|before=)\d{4}", raw["query"]):
            raise PlanError("put date bounds in window, not embedded query operators")
    try:
        manifest = schema.parse_manifest(dict(schema_version=2, manifest_id=plan["plan_id"],
                                             mode="fused", as_of=plan["as_of"], steps=steps))
    except schema.ManifestError as error:
        raise PlanError(str(error)) from error
    ids = {step.step_id for step in manifest.steps}
    if any(step.adapter_id not in allowed for step in manifest.steps):
        raise PlanError("discovery adapter is outside allowed_adapters")
    if not isinstance(plan["depth"], list):
        raise PlanError("depth must be a list, [] when none")
    depth_ids = set()
    for route in plan["depth"]:
        keys(route, ("depth_id", "adapter_id", "operation", "from_steps", "max_items", "max_targets"))
        text(route["depth_id"], "depth_id")
        text(route["adapter_id"], "adapter_id")
        if not isinstance(route["operation"], str):
            raise PlanError("depth operation must be a string")
        if route["depth_id"] in depth_ids or route["adapter_id"] not in allowed:
            raise PlanError("depth IDs must be unique and adapters authorized")
        depth_ids.add(route["depth_id"])
        if (not isinstance(route["from_steps"], list) or not route["from_steps"]
                or any(name not in ids for name in route["from_steps"])):
            raise PlanError("depth must name existing from_steps")
        for name in ("max_items", "max_targets"):
            positive(route[name], name)
        try:
            coverage.plan_depth((), route["adapter_id"], route["operation"], "validate", route["max_items"])
        except coverage.CoverageError as error:
            raise PlanError(str(error)) from error
    if len(steps) + sum(row["max_targets"] for row in plan["depth"]) > limits["max_steps"]:
        raise PlanError("declared steps exceed max_steps")
    if sum(step.max_items for step in manifest.steps) + sum(
            row["max_items"] * row["max_targets"] for row in plan["depth"]) > limits["max_records"]:
        raise PlanError("declared retained-record ceiling exceeds max_records")
    return manifest


def window_fields(plan):
    return {} if plan["window"] is None else {
        "window_start": plan["window"]["start"], "window_end": plan["window"]["end"]}


def depth_step(plan, route, record, step_id):
    if route["adapter_id"] == "open_page":
        try:
            if transport.open_read_refusal(record.normalized_locator):
                return None
        except ValueError:
            return None
    built = coverage.plan_depth((record,), route["adapter_id"], route["operation"],
                                step_id, route["max_items"], limit=1)
    if built.skipped or not built.steps or not (built.steps[0].selected_hits or built.steps[0].query):
        return None
    return replace(built.steps[0], **window_fields(plan))


def candidates(plan, records):
    rows = []
    seen = {}
    for record in records:
        # Same locator can have different text, dates, operators, or counts.
        # Group for presentation; preserve each record for semantic inspection.
        group = normalize.strong_identity(record) or (record.normalized_locator,)
        duplicate = seen.get(group, "")
        seen.setdefault(group, record.record_id)
        options = []
        for route in plan["depth"]:
            if record.step_id in route["from_steps"] and depth_step(plan, route, record, "candidate"):
                options.append(route["depth_id"])
        row = asdict(record)
        try:
            instant(record.published_at)
            date_eligibility = "dated" if plan["window"] is None else "in_window"
        except PlanError:
            date_eligibility = "unknown"
        row.update(options=options, duplicate_of=duplicate, date_eligibility=date_eligibility)
        rows.append(row)
    return rows


def selections(plan, records, selection, candidate_id):
    keys(selection, ("candidate_id", "choices", "omission_reason"))
    if selection["candidate_id"] != candidate_id:
        raise PlanError("selection names a different candidate checkpoint")
    text(selection["omission_reason"], "omission_reason")
    if not isinstance(selection["choices"], list):
        raise PlanError("choices must be a list")
    by_id = {row.record_id: row for row in records}
    routes = {row["depth_id"]: row for row in plan["depth"]}
    counts, targets, steps = {}, set(), []
    for index, choice in enumerate(selection["choices"]):
        keys(choice, ("record_id", "depth_id", "reason"))
        text(choice["record_id"], "record_id")
        text(choice["depth_id"], "depth_id")
        text(choice["reason"], "selection reason")
        record, route = by_id.get(choice["record_id"]), routes.get(choice["depth_id"])
        if record is None or route is None or record.step_id not in route["from_steps"]:
            raise PlanError("choice is outside the authorized candidate/depth set")
        step = depth_step(plan, route, record, "depth-" + str(index + 1))
        if step is None:
            raise PlanError("choice is incompatible with the selected source route")
        key = (route["adapter_id"], route["operation"],
               step.selected_hits[0].target_id if step.selected_hits else step.query)
        if key in targets:
            raise PlanError("duplicate hydration target; select one discovery provenance")
        targets.add(key)
        counts[choice["depth_id"]] = counts.get(choice["depth_id"], 0) + 1
        if counts[choice["depth_id"]] > route["max_targets"]:
            raise PlanError("selection exceeds max_targets")
        if step.step_id in {row["step_id"] for row in plan["discovery"]}:
            raise PlanError("discovery step ID collides with reserved depth IDs")
        steps.append(step)
    return tuple(steps)
