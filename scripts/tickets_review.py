"""Sealed review ownership at mint and admission; prose owns the review loop.

Rounds count substantive judge tickets, never repairs or scoped verification.
No mutable counter: the run's issued tickets are the durable ledger, including
failed launches. Historical tickets without this policy remain historical.
"""
from __future__ import annotations

if __package__:
    from .tickets_format import TERMINAL_STATES, _parse_frontmatter, _read_utf8, declared_parent, is_frame, round_of
else:
    from tickets_format import TERMINAL_STATES, _parse_frontmatter, _read_utf8, declared_parent, is_frame, round_of

FIELDS = ("review_owner", "review_rounds", "review_phase", "review_of",
          "review_round", "review_new_work", "review_independent")


def refusal(detail):
    return {"error": detail, "code": "review-policy"}


def snapshot(run_dir):
    rows = {}
    for path in sorted(run_dir.glob("*.md")):
        text, failure = _read_utf8(path, "review ticket")
        if failure:
            return None, failure
        rows[path.stem] = _parse_frontmatter(text)
    return rows, None


def valid_rounds(value):
    value = str(value or "")
    return value == "until_pass" or (value.isascii() and value.isdigit()
                                      and int(value) > 0 and str(int(value)) == value)


def ordinal(row):
    value = str(row.get("review_round") or "")
    return int(value) if value.isascii() and value.isdigit() else 0


def completion_repair_ancestor(ticket_id, rows):
    """Recognize the existing generated-round grammar through declared ancestry."""
    seen = set()
    while ticket_id and ticket_id not in seen:
        seen.add(ticket_id)
        row = rows.get(ticket_id, {})
        repair = round_of(ticket_id)
        if repair and repair[0] in rows and row.get("executor") == "orch-do":
            return ticket_id
        ticket_id = declared_parent(row)
    return None


def prepare(ticket_id, fields, rows):
    """Return sealed fields or refusal while the caller holds the run lock."""
    fields = dict(fields)
    parent = rows.get(str(fields.get("parent") or ""), {})
    owner = str(parent.get("review_owner") or "")
    rounds = fields.get("review_rounds")
    new = fields.get("review_new_work")
    independent = fields.get("review_independent")
    reference = fields.get("review_of")
    judge = fields.get("executor") == "orch-judge"
    if any("\n" in str(value) or "\r" in str(value) for key, value in fields.items()
           if key in FIELDS):
        return None, refusal("review settings and reasons must be single-line values")
    if rounds is not None and not valid_rounds(rounds):
        return None, refusal("--review-rounds requires a positive integer or until_pass")
    if completion_repair_ancestor(declared_parent(fields), rows) and (new or (judge and not reference)):
        return None, refusal("completion repair descendants cannot reset ownership or open delivery critique")
    if new and (not is_frame(fields) or parent.get("review_phase") in {"repair", "verify"}):
        return None, refusal("new review work requires a frame outside a repair/verification subtree")
    if owner and rounds is not None and not new:
        return None, refusal("nested calls inherit review rounds; only explicit new work may own another policy")
    if new or (not owner and not judge):
        owner = ticket_id
        fields.update(review_owner=owner, review_rounds=str(rounds or "1"))
    elif owner:
        fields.update(review_owner=owner, review_rounds=str(parent["review_rounds"]))
    elif rounds is not None or reference:
        return None, refusal("review settings require an owning delivery frame")
    if independent:
        if not judge or reference or parent.get("review_phase") in {"repair", "verify"}:
            return None, refusal("independent judging requires a judge outside repair/verification and no --review-of")
        fields["review_phase"] = "independent"
    elif reference:
        fields["review_phase"] = "verify" if judge else "repair"
    elif judge and owner:
        fields["review_phase"] = "critique"
        critiques = [row for row in rows.values() if row.get("review_owner") == owner
                     and row.get("review_phase") == "critique"]
        fields["review_round"] = str(len(critiques) + 1)
    elif parent.get("review_phase") in {"repair", "verify"}:
        fields.update(review_phase=parent["review_phase"], review_of=parent["review_of"])
    reference = fields.get("review_of")
    if fields.get("review_phase") == "critique":
        previous = [row for row in rows.values() if row.get("review_owner") == owner
                    and row.get("review_phase") in {"critique", "repair", "verify"}]
        if any(row.get("status") not in TERMINAL_STATES for row in previous):
            return None, refusal("finish the previous review round before another substantive critique")
    if reference:
        target = rows.get(reference, {})
        if target.get("status") not in TERMINAL_STATES:
            return None, refusal("land the substantive critique before its repair or verification")
        round_number = target.get("review_round")
        if any(row.get("review_owner") == owner and row.get("review_phase") == "critique"
               and row.get("review_round") != round_number
               and ordinal(row) > ordinal(target)
               for row in rows.values()):
            return None, refusal("repair/verification must reference the current substantive round")
        linked = [row for row in rows.values() if row.get("review_owner") == owner
                  and row.get("review_of") == reference]
        if not judge and any(row.get("review_phase") == "verify" for row in linked):
            return None, refusal("the repair wave is closed by verification; no second repair wave")
        if judge and any(row.get("review_phase") == "repair"
                         and row.get("status") not in TERMINAL_STATES for row in linked):
            return None, refusal("land every parallel repair before verification")
    failure = validate(ticket_id, fields, dict(rows, **{ticket_id: fields}))
    return (None, failure) if failure else (fields, None)


def validate(ticket_id, data, rows):
    """Recheck sealed policy on every admission, including resumed dispatch."""
    owner = str(data.get("review_owner") or "")
    parent = rows.get(declared_parent(data), {})
    inherited = str(parent.get("review_owner") or "")
    phase = data.get("review_phase")
    if completion_repair_ancestor(declared_parent(data), rows) and (
        data.get("review_new_work") or phase in {"critique", "independent"}
    ):
        return refusal("completion repair descendants cannot reset ownership or open delivery critique")
    if not owner:
        if not inherited and data.get("executor") == "orch-judge" and phase == "independent":
            return None if data.get("review_independent") else refusal("independent judging needs a reason")
        if inherited or any(data.get(key) for key in FIELDS):
            return refusal("review ownership is missing; descendants cannot discard their parent's policy")
        return None
    policy = rows.get(owner)
    if not policy or policy.get("review_owner") != owner or not valid_rounds(policy.get("review_rounds")):
        return refusal("review owner or rounds are invalid")
    if owner != ticket_id and inherited != owner:
        return refusal("review owner must be inherited from the declared parent")
    if data.get("review_new_work") and not (owner == ticket_id and is_frame(data)):
        return refusal("explicit new work belongs only to its owning frame")
    if data.get("review_of") and phase not in {"repair", "verify"}:
        return refusal("review_of belongs only to repair or verification")
    if data.get("review_round") and phase != "critique":
        return refusal("review_round belongs only to substantive critique")
    if data.get("review_independent") and phase != "independent":
        return refusal("independent reason belongs only to independent judging")
    if str(data.get("review_rounds")) != str(policy.get("review_rounds")):
        return refusal("review rounds differ from the sealed owner")
    if inherited and owner != inherited:
        if not (owner == ticket_id and is_frame(data) and data.get("review_new_work")):
            return refusal("nested review owner reset requires explicit new work on a frame")
        if parent.get("review_phase") in {"repair", "verify"}:
            return refusal("repair/verification descendants cannot reset review ownership")
    if parent.get("review_phase") in {"repair", "verify"}:
        if phase not in {"repair", "verify"} or data.get("review_of") != parent.get("review_of"):
            return refusal("repair/verification descendants cannot reopen substantive critique")
        if parent.get("review_phase") == "verify" and data.get("executor") == "orch-do":
            return refusal("verification cannot dispatch another repair wave")
    critiques = {key: row for key, row in rows.items()
                 if row.get("review_owner") == owner and row.get("review_phase") == "critique"}
    if phase == "critique":
        if data.get("executor") != "orch-judge":
            return refusal("only a judge consumes a substantive review round")
        number = str(data.get("review_round") or "")
        if not number.isascii() or not number.isdigit() or int(number) < 1:
            return refusal("substantive review requires its issued round")
        number = int(number)
        allowance = str(policy["review_rounds"])
        if allowance != "until_pass" and number > int(allowance):
            return refusal("substantive review allowance exhausted; verify listed repairs or report unresolved findings")
        earlier = [row for key, row in critiques.items() if key != ticket_id
                   and ordinal(row) < number]
        if len(earlier) != number - 1 or any(
            key != ticket_id and str(row.get("review_round")) == str(number)
            for key, row in critiques.items()
        ):
            return refusal("review rounds must be unique and contiguous")
        if any(row.get("standards") != data.get("standards") for row in earlier):
            return refusal("review criteria must retain the first critique's pinned standards")
    elif phase in {"repair", "verify"}:
        reference = str(data.get("review_of") or "")
        target = critiques.get(reference)
        if target is None:
            return refusal("--review-of must name a substantive judge under the same owner")
        if data.get("executor") == "orch-judge" and phase != "verify":
            return refusal("a repair judge must be scoped verification")
        if phase == "verify" and data.get("executor") == "orch-judge":
            if target.get("standards") != data.get("standards"):
                return refusal("repair verification must retain the critique's pinned standards")
    elif phase == "independent":
        if data.get("executor") != "orch-judge" or not data.get("review_independent"):
            return refusal("independent judging needs an explicit reason")
    elif phase or data.get("executor") == "orch-judge":
        return refusal("governed judge must declare critique, scoped verification, or independent judging")
    return None


def admission_findings(ticket_id, data, siblings):
    rows = {key: _parse_frontmatter(text) for key, text in siblings.items()}
    rows[ticket_id] = data
    failure = validate(ticket_id, data, rows)
    return ([{"code": "review-policy", "field": "review_owner", "detail": failure["error"]}]
            if failure else [])
