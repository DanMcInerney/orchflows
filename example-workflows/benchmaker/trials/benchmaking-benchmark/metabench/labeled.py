"""Labelled submissions for measuring a delivered verifier (M6).

`build_submissions` turns a domain's labelled outputs into final workspaces under
`dest/<task>/<submission>/`, the input of the package's `grade` command, and returns the labels. They are
never written beside the submissions, and submission ids are random so nothing in the tree names a label.
`score_labels` compares the grade rows the package produced with those labels.

A submission is accepted when its grade is scored, full success, and free of critical failures. `valid`
outputs should be accepted and `invalid` or `suboptimal` ones should not; any other label, such as
`lenient`, is counted and left out of both rates. A grade that is missing or unscored is not an
acceptance: it is a false reject for a valid output and listed under `ungraded` either way.

Labels: `{"submissions": {task: {submission: {"label", "kind"}}}, "uncovered": [task, ...]}`. A task is
uncovered when the domain did not recognize it or has no labelled outputs for it. Needs `benchkit` on
`sys.path`.
"""

import secrets
import shutil
from pathlib import Path

from benchkit import aggregate

from .metrics import proportion

POSITIVE = ("valid",)
NEGATIVE = ("invalid", "suboptimal")


def _safe_task(task: str) -> str:
    if not task or task in (".", "..") or "/" in task or "\\" in task:
        raise ValueError(f"task id {task!r} is not a plain name")
    return task


def _safe_files(files: dict) -> dict[str, bytes]:
    out = {}
    for rel, data in files.items():
        path = Path(rel)
        if not rel or path.is_absolute() or path.root or path.drive or rel.startswith(("/", "\\")) or ".." in path.parts:
            raise ValueError(f"submission file {rel!r} must be a relative path inside the workspace")
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError(f"submission file {rel!r} must be bytes")
        out[rel] = bytes(data)
    return out


def _new_id(taken: dict) -> str:
    while True:
        sub = "s" + secrets.token_hex(3)
        if sub not in taken:
            return sub


def build_submissions(domain, recognized: dict[str, dict | None], dest: Path, *,
                      workspaces: dict[str, Path] | None = None) -> dict:
    """Write each recognized task's labelled outputs as final workspaces and return the labels.

    `recognized` maps every delivered task to its instance, or None where the domain did not recognize
    it. With `workspaces` (task -> staged public workspace) each submission starts as a copy of that
    workspace, as a solver's final workspace would; outputs are written through `domain.apply` when the
    domain has it, else directly.
    """
    dest = Path(dest)
    apply = getattr(domain, "apply", None)
    labels: dict = {"submissions": {}, "uncovered": []}
    for task, instance in recognized.items():
        _safe_task(task)
        entries = domain.labeled(instance) if instance is not None else []
        if not entries:
            labels["uncovered"].append(task)
            continue
        subs = labels["submissions"][task] = {}
        for entry in entries:
            files = _safe_files(entry["files"])
            sub = _new_id(subs)
            target = dest / task / sub
            source = (workspaces or {}).get(task)
            if source is not None:
                shutil.copytree(source, target)
            else:
                target.mkdir(parents=True)
            if apply:
                apply(target, files)
            else:
                for rel, data in files.items():
                    path = target / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            subs[sub] = {"label": entry["label"], "kind": entry.get("kind")}
    return labels


def _row_key(row: dict) -> tuple:
    sub = next((row[k] for k in ("submission", "submission_id", "sub") if row.get(k) is not None), None)
    return row.get("task"), sub


def _rate(k: int, n: int) -> tuple[float | None, list | None]:
    rate = proportion(k, n)
    return (rate["estimate"], [rate["low"], rate["high"]]) if rate else (None, None)


def score_labels(grade_rows: list[dict], labels: dict) -> dict:
    """M6: the verifier's true and false acceptance on labelled outputs.

    `grade_rows` are the rows of `run.py grade`: `task`, `submission` and the verifier result fields.
    Returns tpr and tnr with 90% Clopper-Pearson intervals, `false_rejects` and `false_accepts` (task,
    submission, kind, reason), `ungraded`, `tasks_covered`, `tasks_total` and `oracle_coverage` (the share
    of delivered tasks the domain covered). Without any labelled submission the result is
    `{"computed": false, "reason": ...}`.
    """
    submissions = labels.get("submissions") or {}
    uncovered = list(labels.get("uncovered") or [])
    covered = [task for task, subs in submissions.items() if subs]
    if not covered:
        return {"computed": False, "reason": "no labelled submissions: the domain covered no delivered task",
                "uncovered": uncovered}
    rows = {_row_key(row): row for row in grade_rows}
    positives = negatives = accepted_pos = rejected_neg = ignored = 0
    false_rejects, false_accepts, ungraded = [], [], []
    for task in sorted(covered):
        for sub, meta in sorted(submissions[task].items()):
            row = rows.get((task, sub))
            grade = aggregate.validate_grade(row) if row is not None else None
            if grade is None:
                accepted, why = False, "no grade row"
            elif grade["grading_status"] != "scored":
                accepted, why = False, f"{grade['grading_status']}: {grade['reason']}".rstrip(": ")
            else:
                accepted = grade["full_success"] is True and not grade["critical_failures"]
                why = grade["reason"]
            item = {"task": task, "submission": sub, "kind": meta.get("kind"), "label": meta["label"], "reason": why}
            if grade is None or grade["grading_status"] != "scored":
                ungraded.append(item)
            if meta["label"] in POSITIVE:
                positives += 1
                accepted_pos += accepted
                if not accepted:
                    false_rejects.append(item)
            elif meta["label"] in NEGATIVE:
                negatives += 1
                rejected_neg += not accepted
                if accepted:
                    false_accepts.append(item)
            else:
                ignored += 1
    tpr, tpr_ci = _rate(accepted_pos, positives)
    tnr, tnr_ci = _rate(rejected_neg, negatives)
    total = len(covered) + len(uncovered)
    return {"tasks_covered": len(covered), "tasks_total": total, "oracle_coverage": len(covered) / total,
            "uncovered": uncovered, "positives": positives, "negatives": negatives, "ignored": ignored,
            "tpr": tpr, "tpr_ci90": tpr_ci, "tnr": tnr, "tnr_ci90": tnr_ci,
            "false_rejects": false_rejects, "false_accepts": false_accepts, "ungraded": ungraded}
