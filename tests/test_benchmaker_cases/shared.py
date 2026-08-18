"""Contract and replay checks for the canonical benchmark workflow."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
# Demoted to a composition, then converted at P4 (DESIGN.md, amended 2026-08-16):
# benchmaker is a template directory of ticket stubs, and the prose steps,
# edges and invariants it used to state are those stubs' frontmatter.
OLD_PACKAGE = ROOT / "skills" / "workflows" / "orch-benchmaker"
OLD_COMPOSITION = ROOT / "compositions" / "benchmaker.md"
TEMPLATE = ROOT / "compositions" / "benchmaker"
TEMPLATE_MANIFEST = TEMPLATE / "template.md"
EVAL_DESIGN = ROOT / "skills" / "workflows" / "orch-eval-design" / "SKILL.md"
PROTOCOL = ROOT / "compositions" / "references" / "benchmaker-protocol.md"
MANIFEST_CONTRACT = ROOT / "compositions" / "references" / "benchmaker-manifest.md"
PACKAGE = ROOT / "benchmarks" / "benchmaker"
PACKAGE_MANIFEST = PACKAGE / "manifest.json"
FIXTURE = ROOT / "tests" / "fixtures" / "benchmark"
FIXTURE_MANIFEST = FIXTURE / "manifest.json"
PROJECT_OWNER = ROOT / ".orchflows" / "skills" / "benchmaker" / "SKILL.md"
PROJECT_PROTOCOL = PROJECT_OWNER.parent / "references" / "protocol.md"
CLAUDE_ADAPTER = ROOT / ".claude" / "skills" / "benchmaker" / "SKILL.md"

COMPONENT_FIELDS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "reference_audit",
    "attack_audit",
    "measurement",
    "qualification",
)
DECLARATION_FIELDS = ("expected_cost", "gaps", "protected_evidence")
POST_QUALIFICATION_FIELDS = (
    "anchors",
    "builders",
    "qualifier",
    "attacker",
    "resolution",
    "retirement_trigger",
    "incomparability",
)
# The done check reaches every component and stops there, so which block a
# field sits in is the rule, not presentation. The three stage records are
# components; each keeps the substance it carried as a value. The divider is
# the one word the contract splits on -- the sentence carrying it is the
# contract's to reword.
NOT_RE_DERIVABLE = "re-derivable"
STAGE_RECORD_SUBSTANCE = {
    "reference_audit": (
        "auditing context identity",
        "method per case",
        "defect **count**",
        "Never a rate",
    ),
    "attack_audit": ("dated checklist identity", "unrepaired"),
    "measurement": (
        "candidate identities",
        "per-case status",
        "failure signatures",
        "margin",
    ),
}
# `builders`' shape, which `qualifier` and `attacker` are recorded in: the
# prose axes the contract names, and the keys a manifest records them under.
CONTEXT_AXES = ("model id", "effort", "host binding")
CONTEXT_AXIS_KEYS = ("model_id", "effort", "host_binding")
# The dated checklist the attack pass walks, and its classes one for one.
# Both are pinned: a record that walked a shorter list cannot agree with
# itself, and one naming a later checklist cannot be judged against this list.
# `benchmarks/benchmaker/attack-audit.json` names the same eight.
ATTACK_CHECKLIST = "attack-classes:2026-08-08"
ATTACK_CLASSES = (
    "answers shipped with the test",
    "evaluation-logic gaps",
    "excessive permissions",
    "isolation failure",
    "judge prompt injection",
    "remote code execution",
    "trusting untrusted output",
    "weak string matching",
)
# The protocol's three attack outcomes; a fourth would be vocabulary the
# protocol does not license.
ATTACK_OUTCOMES = ("SUCCEEDED", "FAILED", "BLOCKED")
# The audit-and-measure step's own stages. Triage measurement is the
# measurement stage's cheap first pass, not a fourth stage
# (`benchmaker-protocol.md`, "Two measurement passes, not one"), so the count
# the step declares is three and the stages it names are these.
AUDIT_STAGES = ("reference audit", "attack pass", "measurement")
# The chain the six stubs are, in id order: each stub's executor, and the
# predecessor its `depends_on` names. What no other check reads is which skill
# a step binds -- tickets.py grades the graph's shape, not its content -- and a
# step rebound to a different executor is a different composition.
STUB_CHAIN = (
    ("00-acquire", "orch-decompose", []),
    ("01-design", "orch-eval-design", ["00-acquire"]),
    ("02-materialize", "orch-decompose", ["01-design"]),
    ("03-qualify", "orch-decompose", ["02-materialize"]),
    ("04-audit", "orch-critique", ["03-qualify"]),
    ("05-measure", "orch-verify", ["04-audit"]),
)
TERMINAL_STUB = "05-measure"
# Every invariant the composition stated as prose, on the stub it binds and on
# no other. Distributed rather than repeated: a Never clause on all six stubs
# is a clause no stub is accountable for. Each is named by the anchor that
# distinguishes its clause inside the `excluded_actions` field, never by the
# clause's sentence: the field is the owner, and rewording a clause is the
# owner's to do.
STUB_INVARIANTS = {
    "00-acquire": ("invented target truth",),
    "01-design": ("execution cost", "buy speed"),
    "02-materialize": ("mutate the target", "generate a candidate"),
    "03-qualify": ("self-qualified verdict",),
    "04-audit": ("attack artifact",),
    "05-measure": (
        "rank candidates",
        "promote or activate",
    ),
}
# Every invariant rides exactly one stub: the auditor's attack pass produces
# candidate-shaped artifacts by design, so its own clause forbids entering one
# into the case set rather than repeating the materializer's.
SHARED_INVARIANTS = {}
# The composition's done check is the terminal stub's first criterion, and
# what makes the template's promise checkable is that the criterion reads the
# manifest's own fields: the verdict set, what each entry covers, and the gap
# list. Those fields are what is pinned -- a criterion that stopped reading
# one of them is red, and the sentence reading them is the stub's to reword.
# `covers` is backticked here on purpose: the criterion's own verb is
# "covers", so the bare word survives deleting the field it names.
DONE_CHECK_FIELDS = ("qualification", "`covers`", "gaps", "PASS")
# What the protocol stopped stating at P4: the phrase it dropped, the file the
# law went to, and what that file says instead. A triple rather than a
# deletion list, because a phrase deleted from the protocol and from the tree
# at once is a lost law, not a trim -- and the two halves fail separately.
# The owner half is an anchor, not the owner's sentence: the phrase the
# protocol dropped is history and cannot be reworded, but the owner it went to
# rewords freely, and a pin on that owner's wording would make every such
# reword a two-file change.
MOVED_OUT_OF_PROTOCOL = (
    ("Internal call carriage", ROOT / "contracts" / "work-item.md", "## Dispatch"),
    # The coverage floor's row is not here:
    # `test_the_coverage_floor_law_has_one_owner_and_one_carrier` below is
    # that fact's owner and asserts both halves already -- the owner's three
    # anchors, and `coverage floor` absent from the protocol, which is
    # stronger than this row's absence half. One fact, one test.
    (
        "Materialize the selected case specifications",
        TEMPLATE / "02-materialize.md",
        "substitute a case",
    ),
    (
        "Builders never qualify",
        TEMPLATE / "03-qualify.md",
        "builder-disjoint context",
    ),
    (
        "Record the qualified result in the package's",
        TEMPLATE / "05-measure.md",
        "The manifest recorded",
    ),
)
def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse the flat frontmatter shape used by orchflows skill files."""
    opening, frontmatter, body = text.split("---", 2)
    if opening:
        raise AssertionError("frontmatter must start at byte zero")
    fields = {}
    for line in frontmatter.strip().splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body.lstrip("\r\n")


def markdown_section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + len(heading) + 3)
    return text[start:] if end == -1 else text[start:end]


def markdown_subsection(text: str, heading: str) -> str:
    """One `###` subsection: its heading to the next heading of any level.
    `markdown_section` above cannot cut one -- `## <heading>` matches inside
    `### <heading>` and runs on to the next `##`."""
    start = text.index(f"### {heading}")
    following = [
        offset
        for offset in (text.find("\n### ", start + 1), text.find("\n## ", start + 1))
        if offset != -1
    ]
    return text[start : min(following)] if following else text[start:]


def squashed(text: str) -> str:
    return " ".join(text.split())


def contract_bullet(contract: str, field: str) -> str:
    """One field's bullet from the squashed manifest contract."""
    start = contract.index(f"- `{field}` — ")
    end = contract.find("- `", start + 3)
    return contract[start:] if end == -1 else contract[start:end]


def sha256_identity(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def qualification_evidence_identity(evidence: dict) -> str:
    payload = {key: value for key, value in evidence.items() if key != "identity"}
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ticket_law():
    """`scripts/tickets.py`, the owner of ticket and template shape. A stub's
    frontmatter carries list values, which `split_frontmatter` above cannot
    read: it splits every line on ':' and a list item has none."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import tickets

    return tickets



