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


ROOT = Path(__file__).resolve().parent.parent
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
# components; each keeps the substance it carried as a value.
NOT_RE_DERIVABLE = "None of the following is re-derivable afterwards"
STAGE_RECORD_SUBSTANCE = {
    "reference_audit": (
        "auditing context identity",
        "method per case",
        "defect **count**",
        "Never a rate",
    ),
    "attack_audit": ("dated checklist identity", "the attack that works"),
    "measurement": (
        "candidate identities",
        "per-case status",
        "count of distinct failure signatures",
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
# is a clause no stub is accountable for.
STUB_INVARIANTS = {
    "00-acquire": ("multiply the caller bound",),
    "01-design": (
        "move the declared coverage floor with the target's execution cost",
        "buy speed from the coverage floor, the oracle, or the horizon the "
        "outcome needs",
    ),
    "02-materialize": ("mutate the target", "generate a candidate"),
    "03-qualify": ("let builders qualify their own work",),
    "04-audit": ("enter an attack artifact into the case set",),
    "05-measure": (
        "rank candidates",
        "promote or activate anything",
    ),
}
# Every invariant rides exactly one stub: the auditor's attack pass produces
# candidate-shaped artifacts by design, so its own clause forbids entering one
# into the case set rather than repeating the materializer's.
SHARED_INVARIANTS = {}
# The done check, verbatim, which is the terminal stub's first criterion.
DONE_CHECK = (
    "the manifest's qualification verdict set covers every component but its "
    "own — covered PASS on every required criterion, its `covers` naming the "
    "post-repair identities, gaps explicit (`[]` when none)"
)
# What the protocol stopped stating at P4: the phrase it dropped, the file the
# law went to, and what that file says instead. A triple rather than a
# deletion list, because a phrase deleted from the protocol and from the tree
# at once is a lost law, not a trim -- and the two halves fail separately.
MOVED_OUT_OF_PROTOCOL = (
    ("partition one caller bound", TEMPLATE / "00-acquire.md", "an allocation from it"),
    ("Internal call carriage", ROOT / "contracts" / "work-item.md", "## Dispatch"),
    ("coverage floor never moves", EVAL_DESIGN, "coverage floor is not tradable"),
    (
        "Materialize the selected case specifications",
        TEMPLATE / "02-materialize.md",
        "select, add, remove, rank, rewrite or substitute a case",
    ),
    (
        "Builders never qualify",
        TEMPLATE / "03-qualify.md",
        "let builders qualify their own work",
    ),
    (
        "Record the qualified result in the package's",
        TEMPLATE / "05-measure.md",
        "recording the qualified result in the package's manifest",
    ),
)
PROTOCOL_LINE_CEILING = 160
# Package-relative, so the deletion check and the by-path grep below both
# derive from this one list rather than re-listing it.
RETIRED_SEAL_PATHS = ("benchmark.lock", "SEALS.md", "tools/seal_set.py")

# A dated record naming a retired mechanism states what was true when it was
# written; it is not an assertion of the rule, and history is not rewritten to
# agree with today's law. One ruling, one owner, both guards below. Exact
# paths, matched whole and asserted to exist: a directory prefix would excuse
# every file a later date puts under it, which is an exclusion that outlives
# the text it excuses.
_CAMPAIGN_HISTORY = "a campaign history — what that pass believed at its date"
DATED_RECORDS = {
    "benchmarks/measures/benchmaker.md":
        "frozen measurement rows — the record is the fact it recorded",
    "benchmarks/benchmaker/FINDINGS-B0.md": _CAMPAIGN_HISTORY,
    "benchmarks/benchmaker/FINDINGS-EVOLVE.md": _CAMPAIGN_HISTORY,
    "benchmarks/benchmaker/FINDINGS-FIELD.md": _CAMPAIGN_HISTORY,
    "benchmarks/benchmaker/FINDINGS-RECURSION.md": _CAMPAIGN_HISTORY,
    "benchmarks/benchmaker/qualification/q2-verdicts.md":
        "the 2026-08-07 independent-qualifier verdicts, captured observations",
    "benchmarks/benchmaker/provenance/synthesis.md":
        "the frozen claim register — every case's provenance resolves by row",
}
# Three sites under `cases/` where a retired word is a *target's* own
# vocabulary rather than the library's law. Rewording them to dodge a grep
# would change what the case measures, so the pattern scan skips them and the
# guard pins them instead: the licensed line must still be there, and no other
# line in those files may carry a retired word. An exclusion that cannot cover
# a relapse, and cannot outlive the text it excuses.
TARGET_VOCABULARY = {
    "benchmarks/benchmaker/cases/cs-package-audit/seeds/good-unsealed/variant.md":
        ("# good-unsealed",
         "the seed's name states the absence the seed exhibits"),
    "benchmarks/benchmaker/cases/cs-refusal-2/evidence/codec-notes.md":
        ("only inside the vendor's sealed playback SDK, which reports nothing",
         "the codec target's closed-source decoder"),
    "benchmarks/benchmaker/cases/cs-workflow-fresh/evidence/pipeline-spec.md":
        ("identity at production and makes it immutable; `freeze` false leaves",
         "the fictional CI DSL's freeze semantics for a pipeline artifact"),
}
RETIRED_WORD = re.compile(r"seal|immutab", re.IGNORECASE)
# The path guard below reads the whole tree, where one further exclusion
# applies: a guard names what it forbids, so it excludes itself.
RETIRED_PATH_EXCLUSIONS = frozenset(DATED_RECORDS) | {"tests/test_benchmaker.py"}
SKIPPED_TREES = frozenset({".git", ".orch", ".claude", "__pycache__"})
# A guard that cannot read what it scans decides nothing. An unreadable file
# is reported by name; only a declared binary suffix is skipped, and every
# scan asserts a floor far below the ~1100 files it reads today, so a scan
# that collapses is red rather than green.
BINARY_SUFFIXES = (".png",)
SCAN_FLOOR = 700


class UnreadableSurface(Exception):
    """A file the guard was supposed to scan and could not."""

# Where library law is stated. A retired phrase here is a rule the tree no
# longer has.
LAW_TREES = (
    "benchmarks/benchmaker",
    "compositions",
    "contracts",
    "skills",
    "rules",
    "packs",
    "docs",
)
# Two root files state law the trees above do not own and the guard could not
# see: the tree's most public description of the composition, and the owner of
# refusals. `README.md` asserted the withdrawn rule until 2026-08-09 and a
# pattern below catches it. `DESIGN.md` is here for reach, not coverage: what
# it said — protected evidence as "that construct with a digest attached" —
# no pattern targets, so restoring that sentence would leave this green.
LAW_ROOT_FILES = ("README.md", "DESIGN.md")

# The sealing law, phrase by phrase: what the 2026-08-09 withdrawal removed.
# Matched case-insensitively over each file's whitespace-squashed text, so
# neither a wrapped sentence nor a heading's capital can hide from it.
RETIRED_LAW = (
    (
        "a benchmark, case set, manifest or package called immutable",
        r"immutab\w*[^.]{0,50}?"
        r"(?:benchmark|manifest|index|case set|package|dataflow|runnable artifact)"
        r"|(?:benchmark|manifest|case set|package)[^.]{0,50}?\bimmutab\w*",
    ),
    ("stages named for the seal they preceded", r"pre-seal"),
    ("a change minting a successor", r"mint\w*\s+(?:a|no|new|one)\s+successor"),
    ("a successor benchmark identity", r"successor\s+(?:benchmark\s+)?identity"),
    (
        "a prohibition on revising a benchmark in place",
        r"revise[sd]?\s+a\s+benchmark\s+in\s+place",
    ),
    (
        "a prohibition on editing in place",
        r"(?:never|not|cannot|no)\s+(?:[\w'’-]+[ ,]+){0,6}"
        r"(?:edit|revise|change|mutate|amend)\w*"
        r"\s+(?:[\w'’-]+[ ,]+){0,6}in place|in-place edit",
    ),
    (
        "a benchmark identity frozen or sealed where a revision belongs",
        r"(?:frozen|freezes?|sealed|seals?)\s+(?:the\s+)?benchmark\s+identity",
    ),
    (
        "sealing as a stage of the protocol",
        r"manifest sealing|before sealing|after sealing|seal(?:s|ed)? the qualified"
        r"|benchmark sealed|sealed for it|qualification, sealing",
    ),
)
# T01's seven retired sentences, verbatim from `benchmaker-manifest.md` at
# `1d98cc7`, matched as literals so a restoration cannot slip back reworded.
RETIRED_SENTENCES = (
    "- `benchmark_identity` — `sha256:` plus the digest of the canonical "
    "manifest payload defined below.",
    "A component identity is recomputable from the bytes it names, and the "
    "recipe is one rule nested: a file component's identity is the SHA-256 of "
    "its bytes; a directory component's is the SHA-256 of its component lock — "
    "one `<sha256>  <posix-path>` line per contained file, path relative to the "
    "component root, sorted by path, LF-terminated.",
    "An identity no tool can reproduce from the tree proves only that the JSON "
    "agrees with itself, so the package ships the recompute as a runnable check.",
    "Evidence held off-tree by policy is exempt and named as exempt.",
    "Canonicalize the manifest after removing only `benchmark_identity`: UTF-8 "
    "JSON, keys sorted recursively, no insignificant whitespace, and non-ASCII "
    "characters unescaped.",
    "The SHA-256 of those bytes is `benchmark_identity`; this "
    "non-self-referential digest covers every other field and, through each "
    "verified component digest, the referenced bytes.",
    "Changing any covered byte mints a successor benchmark identity; a builder "
    "or consumer never edits the manifest in place.",
)

_TEXT: dict = {}


def read_surface(path: Path, name: str) -> str:
    """The text of one surface, or None where the suffix says binary.

    Memoized by path: the law scan and the live scan cover overlapping
    trees of the same immutable checkout, so the second pass over a file
    must not pay for the read again.
    """
    if path.suffix in BINARY_SUFFIXES:
        return None
    key = str(path)
    if key not in _TEXT:
        try:
            _TEXT[key] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise UnreadableSurface("{}: {}".format(name, error))
    return _TEXT[key]


def _law_scan():
    candidates = [ROOT / name for name in LAW_ROOT_FILES]
    for tree in LAW_TREES:
        base = ROOT / tree
        if base.is_dir():
            candidates.extend(sorted(base.rglob("*")))
    read = 0
    for path in candidates:
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if SKIPPED_TREES.intersection(relative.parts):
            continue
        name = relative.as_posix()
        if name in DATED_RECORDS or name in TARGET_VOCABULARY:
            continue
        text = read_surface(path, name)
        if text is None:
            continue
        read += 1
        yield name, squashed(text)
    if read < SCAN_FLOOR:
        raise UnreadableSurface(
            "the law scan read {} files, under the floor of {}".format(read, SCAN_FLOOR)
        )


def _live_scan(tree: Path):
    read = 0
    # Pruned during the walk rather than filtered after it. `.git` holds
    # test_cutcheck's shared scratch clones, whose directories appear and
    # vanish while this runs, and `rglob` dies on a child that existed
    # when its parent was listed and did not when it was reached. Nothing
    # under a skipped tree was ever a live surface, so pruning loses
    # nothing; the sort is restored so the yield order is unchanged.
    found = []
    for parent, dirnames, filenames in os.walk(tree):
        dirnames[:] = [name for name in dirnames if name not in SKIPPED_TREES]
        found.extend(Path(parent, name) for name in filenames)
    for path in sorted(found):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if SKIPPED_TREES.intersection(relative.parts):
            continue
        name = relative.as_posix()
        if name in RETIRED_PATH_EXCLUSIONS:
            continue
        text = read_surface(path, name)
        if text is None:
            continue
        read += 1
        yield name, text
    if read < SCAN_FLOOR:
        raise UnreadableSurface(
            "the scan of {} read {} files, under the floor of {}".format(
                tree.relative_to(ROOT) if tree != ROOT else ".", read, SCAN_FLOOR
            )
        )


_SCANS: dict = {}


def law_files():
    """Every law surface that is not a dated record.

    `LAW_TREES` plus `LAW_ROOT_FILES`; the root files carry law of the same
    kind and were reachable by no guard before 2026-08-09.

    Memoized: the walk reads ~1500 files / 8.5 MB and four call sites want
    the same bytes of the same immutable checkout. The floor check lives in
    the scan, so it still fires on the one call that does the reading, and
    a scan that raised is not cached.
    """
    if "law" not in _SCANS:
        _SCANS["law"] = tuple(_law_scan())
    return _SCANS["law"]


def live_files(tree: Path):
    """Every text file under `tree` that is not a dated record.

    Memoized per tree, for the reason `law_files` states.
    """
    key = ("live", str(tree))
    if key not in _SCANS:
        _SCANS[key] = tuple(_live_scan(tree))
    return _SCANS[key]


def live_matches(pattern: str, tree: Path = ROOT) -> list[str]:
    expression = re.compile(pattern)
    return [
        f"{name}:{number}"
        for name, text in live_files(tree)
        for number, line in enumerate(text.splitlines(), 1)
        if expression.search(line)
    ]


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


class TestCanonicalBenchmaker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, _ = split_frontmatter(
            TEMPLATE_MANIFEST.read_text(encoding="utf-8")
        )
        cls.stubs = {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted(TEMPLATE.glob("*.md"))
            if path.name != TEMPLATE_MANIFEST.name
        }
        tickets = ticket_law()
        cls.stub_fields = {
            stub: tickets._parse_frontmatter(text)
            for stub, text in cls.stubs.items()
        }
        cls.protocol = PROTOCOL.read_text(encoding="utf-8")
        cls.manifest_contract = MANIFEST_CONTRACT.read_text(encoding="utf-8")

    def test_template_manifest_declares_the_shape_instantiation_fills(self):
        self.assertEqual("benchmaker", self.fields["name"])
        # Manual-only survives both conversions as entry: named.
        self.assertEqual("named", self.fields["entry"])
        self.assertLessEqual(len(self.fields["description"]), 140)
        declared = self.fields["placeholders"]
        self.assertEqual(
            "[target, outcome, sources, rigor, bound, pack, package]", declared
        )
        # Every declared placeholder reaches a stub. `validate.py` warns here;
        # a warning is not what a caller who filled a dead `--set` needs.
        used = set(re.findall(r"\{\{([a-z_]+)\}\}", "".join(self.stubs.values())))
        self.assertEqual(
            {item.strip() for item in declared[1:-1].split(",")}, used
        )

    def test_every_stub_is_a_ticket_this_template_can_instantiate(self):
        """The shape law is `scripts/tickets.py`'s, and it is the same law
        `instantiate` applies -- so a stub this passes is a ticket the moment
        a run fills it, and no stub in this template needs its own spelling of
        the contract."""
        tickets = ticket_law()
        self.assertEqual(
            [], [(str(path), message) for path, message in tickets.template_defects(TEMPLATE)]
        )

    def test_the_chain_binds_one_executor_per_step_and_one_terminal(self):
        self.assertEqual(
            [stub for stub, _, _ in STUB_CHAIN], sorted(self.stub_fields)
        )
        for stub, executor, depends_on in STUB_CHAIN:
            with self.subTest(stub=stub):
                self.assertEqual(executor, self.stub_fields[stub]["executor"])
                self.assertEqual(depends_on, self.stub_fields[stub]["depends_on"])
        depended = {
            edge
            for fields in self.stub_fields.values()
            for edge in fields["depends_on"]
        }
        self.assertEqual({TERMINAL_STUB}, set(self.stub_fields) - depended)
        # The terminal stub's completion test is the composition's done check,
        # verbatim: that is what makes the template's promise checkable at all.
        self.assertIn(
            DONE_CHECK,
            squashed(markdown_section(self.stubs[TERMINAL_STUB], "Completion test")),
        )

    def test_each_invariant_rides_the_stub_it_binds_and_no_other(self):
        for stub, clauses in STUB_INVARIANTS.items():
            for clause in clauses:
                with self.subTest(stub=stub, clause=clause):
                    carriers = {
                        other
                        for other, fields in self.stub_fields.items()
                        if any(
                            clause in action
                            for action in fields.get("excluded_actions", [])
                        )
                    }
                    self.assertEqual(
                        SHARED_INVARIANTS.get(clause, {stub}), carriers
                    )

    def test_the_stages_that_stop_the_chain_say_what_they_return(self):
        """Acquisition and design are the two stages that can end the run
        early. Both return what they have rather than closing over it, and a
        stub that dropped the clause would look complete while stopping."""
        for stub in ("00-acquire", "01-design"):
            with self.subTest(stub=stub):
                self.assertIn("partial evidence", squashed(self.stubs[stub]))
        self.assertIn(
            "partial evidence",
            squashed(markdown_section(self.stubs[TERMINAL_STUB], "Return fields")),
        )

    def test_protocol_is_domain_blind_and_keeps_only_unowned_craft(self):
        """What survives is benchmark craft for a domain with no pack. The
        restatements went to the owner each already had: the packet to the
        work-item contract, the coverage floor to `orch-eval-design`, and the
        stage rules to the stub that carries out the stage."""
        headings = re.findall(r"^## (.+)$", self.protocol, re.MULTILINE)
        self.assertEqual(
            [
                "Licensed oracle material",
                "Qualification",
                "Audit and measurement",
                "Scoring",
            ],
            headings,
        )
        self.assertLessEqual(
            len(self.protocol.splitlines()), PROTOCOL_LINE_CEILING
        )
        for phrase, owner, owner_phrase in MOVED_OUT_OF_PROTOCOL:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, squashed(self.protocol))
                self.assertIn(
                    owner_phrase, squashed(owner.read_text(encoding="utf-8"))
                )
        self.assertIn(
            "licensed oracle material", squashed(self.protocol)
        )

        known_pack_names = [
            path.name for path in (ROOT / "packs").iterdir() if path.is_dir()
        ]
        for pack_name in known_pack_names:
            self.assertNotIn(pack_name, self.protocol)
        for forbidden_owner in ("`orch-bench`", "`orch-evolve`"):
            self.assertNotIn(forbidden_owner, self.protocol)

    def test_protocol_qualifies_required_failures_and_protected_evidence(self):
        qualification = squashed(markdown_section(self.protocol, "Qualification"))
        for check in (
            "oracle failability",
            "coverage",
            "discrimination",
            "reproducibility",
            "redundancy",
            "provenance",
            "execution cost",
        ):
            self.assertIn(check, qualification)
        for policy in (
            "known-bad",
            "required deterministic failure blocks qualification",
            "anchors",
            "secondary",
            "cannot compensate",
            "visibility and release policy",
            "candidate-inaccessible check",
            "UNVERIFIED",
        ):
            self.assertIn(policy, qualification)

    def test_the_coverage_floor_law_has_one_owner_and_one_carrier(self):
        """`orch-eval-design` states the law -- it is the skill that fixes
        tiers -- and 01-design's excluded actions are what bind this
        template's design step to it. Three owners was the finding; two
        statements of one law would be the same finding again."""
        owner = squashed(EVAL_DESIGN.read_text(encoding="utf-8"))
        self.assertIn("The coverage floor is not tradable", owner)
        self.assertIn(
            "Buy difficulty from horizon length, outcome specificity, and a "
            "stricter oracle that stays correct",
            owner,
        )
        for phrase in ("coverage floor", "Difficulty is built", "execution tier"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.protocol)

    def test_protocol_orders_and_bounds_the_three_audit_stages(self):
        stages = squashed(markdown_section(self.protocol, "Audit and measurement"))
        for ordered in (
            "triage measurement",
            "reference audit",
            "attack pass",
            "recorded measurement",
        ):
            self.assertIn(ordered, stages)
        self.assertLess(stages.index("reference audit"), stages.index("attack pass"))
        # The audit's third context, and its count-not-rate output.
        self.assertIn(
            "disjoint from every builder **and** from the qualifying context", stages
        )
        self.assertIn("binary fatal-flaw call, never a graded scale", stages)
        self.assertIn("defect count", stages)
        self.assertIn("never a rate", stages)
        # The attack pass's three outcomes and its declared-hole failure path.
        for outcome in ("`SUCCEEDED`", "`FAILED`", "`BLOCKED`"):
            self.assertIn(outcome, stages)
        self.assertIn("**dated** checklist", stages)
        self.assertIn("An undeclared hole is the failure", stages)
        # The measurement pass records; it never renders a verdict.
        self.assertIn("Recording only", stages)
        self.assertIn("cannot fail", stages)
        self.assertIn("dispatch made unreachable is an intake gap", stages)
        self.assertIn("distinct failure signatures", stages)
        for status in ("`both-pass`", "`split`", "`both-fail`", "`inversion`"):
            self.assertIn(status, stages)
        self.assertIn("max(measured rerun spread, one case)", stages)
        self.assertIn("outside the package", stages)
        # The revision-durability rule that replaces the seal's guarantee: a
        # revision only resolves while it is reachable, and a squash merge
        # strands every branch commit.
        self.assertIn("reachable from the default branch", stages)
        self.assertIn("identical measured bytes", stages)
        self.assertIn("squash", stages)

    def test_protocol_scoring_reports_distributions_not_points(self):
        scoring = squashed(markdown_section(self.protocol, "Scoring"))
        self.assertIn("per-angle vector is the artifact", scoring)
        self.assertIn("never headline a scalar", scoring)
        self.assertIn("`(score, cost)` pairs", scoring)
        self.assertIn("`pass^k` beside `pass@1`", scoring)
        self.assertIn("deterministic oracle versus by judged oracle", scoring)
        self.assertIn("target × model × harness × benchmark", scoring)
        self.assertIn("Never subtract a harness offset", scoring)
        self.assertIn("count of sign flips", scoring)

    def test_manifest_owner_lists_every_field_and_rule(self):
        manifest = squashed(self.manifest_contract)
        components, _, values = manifest.partition(NOT_RE_DERIVABLE)
        for field in COMPONENT_FIELDS:
            self.assertIn(f"- `{field}` — locator", components, field)
            self.assertNotIn(f"`{field}`", values, field)
        for field in DECLARATION_FIELDS:
            self.assertIn(f"`{field}`", components)
        for field, substance in STAGE_RECORD_SUBSTANCE.items():
            bullet = contract_bullet(components, field)
            for phrase in substance:
                self.assertIn(phrase, bullet, field)
        for rule in (
            "locator",
            "oracle_class",
            "evidence",
            "covers",
        ):
            self.assertIn(rule, manifest)

    def test_manifest_owner_carries_every_post_qualification_field(self):
        manifest = squashed(self.manifest_contract)
        values = manifest.partition(NOT_RE_DERIVABLE)[2]
        for field in POST_QUALIFICATION_FIELDS:
            self.assertIn(f"- `{field}` — ", values, field)
        for field in ("builders", "qualifier", "attacker"):
            bullet = contract_bullet(values, field)
            for axis in CONTEXT_AXES:
                self.assertIn(axis, bullet, field)
        self.assertIn("A declared `none` is legal; silence is not", values)
        self.assertIn("`max(measured rerun spread, one case)`", values)
        self.assertIn("the declaration only. Its firing is recorded", values)

    def test_benchmark_identity_is_retired_from_law_manifest_and_tooling(self):
        """A benchmark's version is its git revision; no field digests it."""
        surfaces = [
            MANIFEST_CONTRACT,
            PACKAGE_MANIFEST,
            PACKAGE / "evaluation-design.md",
            PACKAGE / "qualification" / "q3-delta-verdicts.md",
        ]
        # `deseal_cases.py` is the tool that *removes* the token; it must name
        # what it deletes, exactly as this guard file names what it forbids.
        # Exempted by name, never by widening the glob, so any other tool under
        # `tools/` that reintroduces the field still turns this red.
        surfaces.extend(
            path
            for path in sorted((PACKAGE / "tools").glob("*.py"))
            if path.name != "deseal_cases.py"
        )
        surfaces.extend(sorted(FIXTURE.iterdir()))
        named = [
            f"{path.relative_to(ROOT)}:{number}"
            for path in surfaces
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            )
            if "benchmark_identity" in line
        ]
        with self.subTest("no law, manifest, tool, design or fixture names it"):
            self.assertEqual([], named)
        with self.subTest("the recompute recipe and its proof are gone"):
            self.assertEqual(
                [],
                [
                    str(path.relative_to(ROOT))
                    for path in (
                        PACKAGE / "tools" / "component_identity.py",
                        ROOT / "tests" / "test_component_identity.py",
                    )
                    if path.exists()
                ],
            )
        with self.subTest("the package manifest parses and carries no key"):
            self.assertNotIn(
                "benchmark_identity",
                json.loads(PACKAGE_MANIFEST.read_text(encoding="utf-8")),
            )

    def test_seal_machinery_is_deleted_and_no_live_surface_names_it(self):
        retired = [PACKAGE / name for name in RETIRED_SEAL_PATHS]
        with self.subTest("the lock, the seal history and the seal tool are gone"):
            self.assertEqual(
                [],
                [str(path.relative_to(ROOT)) for path in retired if path.exists()],
            )
        with self.subTest("no live surface names one of them by path"):
            self.assertEqual(
                [],
                live_matches(
                    "|".join(re.escape(Path(name).name) for name in RETIRED_SEAL_PATHS)
                ),
            )

    def test_package_names_no_tool_that_no_longer_exists(self):
        """`cases/` is the case set's own scope and carries its own `--verify-only`."""
        matches = [
            match
            for match in live_matches(
                r"seal_set|component_identity|--verify(?!-)", PACKAGE
            )
            if not match.startswith("benchmarks/benchmaker/cases/")
        ]
        self.assertEqual([], matches)

    def test_package_manifest_keeps_locators_and_carries_no_digest(self):
        text = PACKAGE_MANIFEST.read_text(encoding="utf-8")
        with self.subTest("no digest anywhere in the manifest"):
            self.assertNotIn("sha256:", text)
        manifest = json.loads(text)
        with self.subTest("every component entry is a locator that resolves"):
            for field in COMPONENT_FIELDS:
                self.assertEqual({"locator"}, set(manifest[field]), field)
                self.assertTrue(
                    (PACKAGE / manifest[field]["locator"]).exists(),
                    manifest[field]["locator"],
                )
        with self.subTest("the post-qualification field set is exactly the seven"):
            self.assertEqual(
                set(POST_QUALIFICATION_FIELDS),
                set(manifest).difference(COMPONENT_FIELDS, DECLARATION_FIELDS),
            )
        with self.subTest("incomparability bounds a revision and four candidate axes"):
            # The field survives the withdrawal because a score genuinely does
            # not cross a benchmark version; only the noun moves. Deleting the
            # clause would license comparing scores across versions, which is
            # the one thing the field exists to forbid.
            boundary = manifest["incomparability"]
            self.assertIn("do not cross this benchmark revision", boundary)
            for axis in ("model id", "effort level", "host binding", "scaffold"):
                self.assertIn(axis, boundary)

    def test_the_retired_sealing_law_is_absent_from_every_live_surface(self):
        """The run's one guard against the sealing law coming back.

        T01's `test_manifest_owner_states_no_identity_recipe` and the
        exclusion lists T02 and T04 each derived are folded in here, per
        `rules/visibility.md`: one job, one owner.
        """
        patterns = [
            (reason, re.compile(pattern, re.IGNORECASE))
            for reason, pattern in RETIRED_LAW
        ]
        patterns.extend(
            (
                "a retired manifest sentence, verbatim",
                re.compile(re.escape(squashed(sentence)), re.IGNORECASE),
            )
            for sentence in RETIRED_SENTENCES
        )
        offending = {}
        for name, text in law_files():
            hit = sorted({reason for reason, expression in patterns if expression.search(text)})
            if hit:
                offending[name] = hit

        with self.subTest("no live law surface asserts the retired rule"):
            self.assertEqual({}, offending)
        with self.subTest("every exclusion names a file that is still there"):
            for name in sorted(RETIRED_PATH_EXCLUSIONS | set(DATED_RECORDS)):
                self.assertTrue(
                    (ROOT / name).is_file(),
                    "{}: an exclusion outliving the text it excuses".format(name),
                )
        with self.subTest("the manifest owner states no identity recipe"):
            manifest = squashed(self.manifest_contract)
            for retired in (
                "A component identity is recomputable from the bytes it names",
                "Canonicalize the manifest after removing only `benchmark_identity`",
                "`sha256:` digest",
                "verify that digest before use",
                "true at seal",
                "unrepaired at seal",
                "`seal_measurement`",
            ):
                self.assertNotIn(retired, manifest)
            # Candidate isolation is not sealing: a builder may now edit a
            # manifest, and a candidate still may not.
            self.assertIn(
                "Candidate execution emits a separate result identity and cannot "
                "change a manifest field",
                manifest,
            )
        with self.subTest("each target-vocabulary exclusion excuses exactly its own line"):
            for name, (licensed, _) in sorted(TARGET_VOCABULARY.items()):
                self.assertEqual(
                    [licensed],
                    [
                        line.strip()
                        for line in (ROOT / name).read_text(encoding="utf-8").splitlines()
                        if RETIRED_WORD.search(line)
                    ],
                    "{}: the excluded file's retired-word lines moved".format(name),
                )
        with self.subTest("the scan reaches every surface the guard names"):
            scanned = [name for name, _ in law_files()]
            for source in LAW_ROOT_FILES:
                self.assertIn(source, scanned)
            for tree in LAW_TREES:
                self.assertTrue(
                    any(name.startswith(tree + "/") for name in scanned),
                    "the law scan read nothing under {}".format(tree),
                )

    def test_the_audit_and_measure_stages_are_split_across_two_stubs(self):
        """The three stages the protocol orders sit in two stubs: the two that
        repair or declare are `04-audit`'s, and the one that only records is
        `05-measure`'s, behind it. Collapsing them into one stub would put the
        recording pass in a context that may still repair, which is the
        difficulty gate the protocol refuses."""
        audit = squashed(self.stubs["04-audit"])
        measure = squashed(self.stubs[TERMINAL_STUB])
        for stage in AUDIT_STAGES[:2]:
            with self.subTest(stage=stage):
                self.assertIn(stage, audit)
        self.assertIn("measurement pass", measure)
        self.assertEqual(
            ["04-audit"], self.stub_fields[TERMINAL_STUB]["depends_on"]
        )
        # 04-audit repairs or declares and renders no verdict; 05-measure
        # records the manifest. Neither one does the other's job.
        self.assertIn(
            "render a pass/fail verdict on the benchmark",
            self.stub_fields["04-audit"]["excluded_actions"],
        )
        self.assertIn("declared as a gap", audit)
        # What recording-only means is the protocol's one statement of it; the
        # stub carries the link, not a fifth copy of the rationale.
        self.assertIn("benchmaker-protocol.md#measurement-pass", measure)
        # Triage is the measurement stage's own first pass, never a fourth
        # stage, so no stub may name it as one.
        self.assertEqual([], re.findall(r"triage(?! pass| measurement)", audit))


class TestBenchmarkFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    def _reference(self, name: str) -> Path:
        path = (FIXTURE / self.manifest[name]["locator"]).resolve()
        path.relative_to(FIXTURE.resolve())
        self.assertTrue(path.is_file(), f"missing {name} reference: {path}")
        return path

    def _record(self, name: str) -> dict:
        """One stage record, read through the component locator that names it."""
        return json.loads(self._reference(name).read_text(encoding="utf-8"))

    def _run_fixture(
        self, fixture: Path, candidate: str
    ) -> subprocess.CompletedProcess[str]:
        manifest = json.loads(
            (fixture / "manifest.json").read_text(encoding="utf-8")
        )
        return subprocess.run(
            [
                sys.executable,
                str(fixture / manifest["runner"]["locator"]),
                "--manifest",
                str(fixture / "manifest.json"),
                "--candidate",
                str(fixture / candidate),
            ],
            cwd=fixture,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def _run(self, candidate: str) -> subprocess.CompletedProcess[str]:
        return self._run_fixture(FIXTURE, candidate)

    def test_manifest_references_are_complete_and_locator_addressed(self):
        self.assertEqual(1, self.manifest["schema_version"])
        fixture_text = FIXTURE_MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn("sha256:", fixture_text)
        # The reference manifest states the law the package manifest states.
        self.assertNotIn("benchmark identity", fixture_text)
        self.assertEqual(
            {"schema_version", *COMPONENT_FIELDS, *DECLARATION_FIELDS,
             *POST_QUALIFICATION_FIELDS},
            set(self.manifest),
        )
        for name in COMPONENT_FIELDS:
            self.assertEqual({"locator"}, set(self.manifest[name]), name)
            self._reference(name)
        self.assertEqual("public", self.manifest["protected_evidence"]["visibility"])
        self.assertIsNone(
            self.manifest["protected_evidence"]["candidate_inaccessible_check"]
        )
        self.assertTrue(self.manifest["gaps"])

    def test_stage_records_and_post_qualification_fields_state_what_ran(self):
        cases = [
            case["case_identity"]
            for case in json.loads(
                (FIXTURE / "cases.json").read_text(encoding="utf-8")
            )["cases"]
        ]
        # Per case, and never silent: `none` with a reason is the legal form.
        for field in ("anchors", "builders"):
            self.assertEqual(set(cases), set(self.manifest[field]))
            for value in self.manifest[field].values():
                self.assertTrue(value.strip())
        for anchor in self.manifest["anchors"].values():
            if anchor.startswith("none"):
                self.assertIn("—", anchor, "a `none` anchor carries its reason")
        # `qualifier` and `attacker` in `builders`' shape: every axis present,
        # each a value or a declared `none` carrying its reason.
        for field in ("qualifier", "attacker"):
            context = self.manifest[field]
            self.assertEqual(set(CONTEXT_AXIS_KEYS), set(context), field)
            for axis, value in context.items():
                self.assertTrue(value.strip(), f"{field}.{axis}")
                if value.startswith("none"):
                    self.assertIn("—", value, f"{field}.{axis} carries its reason")
        # The three stage records are components now, so each figure below is
        # read through the locator rather than inline in the manifest.
        audit = self._record("reference_audit")
        attack = self._record("attack_audit")
        measurement = self._record("measurement")
        # A count and classes, never a rate.
        self.assertIsInstance(audit["defect_count"], int)
        self.assertEqual(len(audit["defect_classes"]), audit["defect_count"])
        self.assertEqual(set(cases), set(audit["method"]))
        self.assertTrue(audit["declared_sample"].strip())
        # Who audited is the record's own first substance: a stage record
        # naming no context is a stage that did not run, whatever it says.
        self.assertEqual(set(CONTEXT_AXIS_KEYS), set(audit["auditor_context"]))
        for axis, value in audit["auditor_context"].items():
            self.assertTrue(value.strip(), f"auditor_context.{axis}")
        # No stage is recorded as not run — all three, here and in gaps.
        gaps = " ".join(self.manifest["gaps"])
        for name, record in (
            ("reference_audit", audit),
            ("attack_audit", attack),
            ("measurement", measurement),
        ):
            self.assertNotIn("not run", record["status"], name)
        self.assertNotIn("attack pass not run", gaps)
        self.assertNotIn("measurement pass not run", gaps)
        # Every class of the dated checklist carries one of the protocol's
        # three outcomes, and every SUCCEEDED class is declared with the attack
        # that works. An undeclared hole is the failure; a declared one is a gap.
        self.assertEqual(ATTACK_CHECKLIST, attack["checklist_identity"])
        self.assertEqual(set(ATTACK_CLASSES), set(attack["classes"]))
        self.assertEqual(set(ATTACK_CLASSES), set(attack["outcomes"]))
        for name, recorded in attack["outcomes"].items():
            self.assertIn(recorded["outcome"], ATTACK_OUTCOMES, name)
            self.assertTrue(recorded["observed"].strip(), name)
        declared = {
            name for hole in attack["unrepaired"] for name in hole["classes"]
        }
        succeeded = {
            name
            for name, recorded in attack["outcomes"].items()
            if recorded["outcome"] == "SUCCEEDED"
        }
        self.assertTrue(succeeded, "a pass that repelled everything is a claim")
        self.assertLessEqual(succeeded, declared)
        for hole in attack["unrepaired"]:
            self.assertTrue(hole["attack"].strip())
        # The measurement separates the two rungs and says by how much: one
        # repeated candidate habit is one signature, not one per case.
        self.assertEqual(2, len(measurement["candidates"]))
        self.assertEqual(set(cases), set(measurement["per_case_status"]))
        self.assertEqual(1, measurement["distinct_failure_signatures"])
        self.assertEqual(2, measurement["margin_cases"])
        # Resolution rests on the one-case floor while the spread is unmeasured.
        self.assertIsNone(self.manifest["resolution"]["measured_rerun_spread"])
        self.assertEqual(1, self.manifest["resolution"]["one_case"])
        for field in ("retirement_trigger", "incomparability"):
            self.assertTrue(self.manifest[field].strip())

    def test_runner_accepts_good_rejects_bad_and_replays_evidence(self):
        good_first = self._run("known_good.py")
        good_second = self._run("known_good.py")
        bad = self._run("known_bad.py")
        self.assertEqual(0, good_first.returncode, good_first.stderr)
        self.assertEqual(0, good_second.returncode, good_second.stderr)
        self.assertEqual(1, bad.returncode, bad.stderr)

        good_result = json.loads(good_first.stdout)
        replay_result = json.loads(good_second.stdout)
        bad_result = json.loads(bad.stdout)
        self.assertEqual(good_result, replay_result)
        self.assertEqual("PASS", good_result["verdict"])
        self.assertEqual("FAIL", bad_result["verdict"])
        self.assertEqual("deterministic", good_result["oracle_class"])
        self.assertEqual(1, good_result["score"])
        self.assertEqual(0, bad_result["score"])
        self.assertTrue(good_result["eligible_for_ranking"])
        self.assertFalse(bad_result["eligible_for_ranking"])
        self.assertEqual(
            good_result["covered_evidence"], bad_result["covered_evidence"]
        )
        # The result identifies the candidate and itself; the benchmark it ran
        # against is a git revision of this tree, not a field it can restate.
        evidence_payload = {
            field: good_result[field]
            for field in ("candidate_identity", "cases", "covered_evidence")
        }
        canonical = json.dumps(
            evidence_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        self.assertEqual(
            good_result["evidence_identity"],
            f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}",
        )
        self.assertNotEqual(
            good_result["candidate_identity"], bad_result["candidate_identity"]
        )

    def _copy(self, temp_dir: str) -> tuple[Path, dict]:
        fixture = Path(temp_dir) / "benchmark"
        shutil.copytree(FIXTURE, fixture)
        return fixture, json.loads(
            (fixture / "manifest.json").read_text(encoding="utf-8")
        )

    def test_runner_rejects_unsupported_scoring(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            scoring_path = fixture / manifest["scoring"]["locator"]
            scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
            scoring["aggregation"] = {"operator": "unsupported", "status": "PASS"}
            write_json(scoring_path, scoring)
            design_path = fixture / manifest["evaluation_design"]["locator"]
            design = json.loads(design_path.read_text(encoding="utf-8"))
            design["aggregation"] = scoring["aggregation"]
            write_json(design_path, design)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("unsupported scoring aggregation", result.stderr)

    def test_runner_rejects_incomplete_required_cover_union(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            scoring_locator = manifest["scoring"]["locator"]
            qualification_path = fixture / manifest["qualification"]["locator"]
            qualification = json.loads(
                qualification_path.read_text(encoding="utf-8")
            )
            for entry in qualification["entries"]:
                entry["covers"] = [
                    covered
                    for covered in entry["covers"]
                    if covered != scoring_locator
                ]
            write_json(qualification_path, qualification)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn(
                "qualification oracle_failability verdict is invalid",
                result.stderr,
            )

    def test_runner_rejects_an_unresolvable_component_locator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            manifest["runnable_cases"]["locator"] = "absent-cases.json"
            write_json(fixture / "manifest.json", manifest)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("missing reference: absent-cases.json", result.stderr)

    def test_runner_rejects_self_certification(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            cases_path = fixture / manifest["runnable_cases"]["locator"]
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
            cases["cases"][0]["expected"]["text"] = "SELF-CERTIFIED"
            write_json(cases_path, cases)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("qualification discrimination failed", result.stderr)

    def test_qualification_recomputes_every_required_check(self):
        qualification = json.loads(
            self._reference("qualification").read_text(encoding="utf-8")
        )
        design = json.loads(
            self._reference("evaluation_design").read_text(encoding="utf-8")
        )
        case_set = json.loads(
            self._reference("runnable_cases").read_text(encoding="utf-8")
        )
        declared_coverage = set(design["intended_coverage"])
        case_coverage = [set(case["coverage"]) for case in case_set["cases"]]
        self.assertEqual(
            set(design["case_specifications"]),
            {case["case_identity"] for case in case_set["cases"]},
        )
        self.assertEqual(declared_coverage, set().union(*case_coverage))
        for index, coverage in enumerate(case_coverage):
            others = set().union(
                *(other for other_index, other in enumerate(case_coverage) if other_index != index)
            )
            self.assertTrue(coverage - others)
        self.assertEqual(
            {"replays": 3, "candidate_processes": 6},
            qualification["actual_qualification_spend"],
        )
        for candidate in qualification["calibration_candidates"].values():
            self.assertEqual({"locator"}, set(candidate))
            candidate_path = (FIXTURE / candidate["locator"]).resolve()
            candidate_path.relative_to(FIXTURE.resolve())
            self.assertTrue(candidate_path.is_file(), candidate["locator"])
        required = {
            entry["criterion"]: entry
            for entry in qualification["entries"]
            if entry["required"]
        }
        required_cover_union = {
            covered
            for entry in required.values()
            for covered in entry["covers"]
        }
        # `compositions/benchmaker.md`'s done check reads "every component but
        # its own": `qualification` is excluded here because a verdict set
        # covering itself is self-certification, not coverage.
        component_locators = {
            self.manifest[name]["locator"]
            for name in COMPONENT_FIELDS
            if name != "qualification"
        }
        self.assertTrue(component_locators <= required_cover_union)
        self.assertEqual(
            {
                "oracle_failability",
                "coverage",
                "discrimination",
                "reproducibility",
                "redundancy",
                "provenance",
                "execution_cost",
            },
            set(required),
        )
        for entry in required.values():
            self.assertEqual("PASS", entry["verdict"])
            self.assertEqual("deterministic", entry["oracle_class"])
            for field in ("oracle", "evidence", "covers"):
                self.assertTrue(entry[field])
            self.assertIn("identity", entry["evidence"])
            self.assertIn("reproduce", entry["evidence"])
            self.assertIn("observation", entry["evidence"])
            self.assertTrue(entry["evidence"]["provenance"])
            self.assertEqual(
                entry["evidence"]["identity"],
                qualification_evidence_identity(entry["evidence"]),
            )
            # A cover names a component by the locator it resolves through.
            for covered in entry["covers"]:
                self.assertTrue((FIXTURE / covered).is_file(), covered)
        self.assertEqual("PASS", qualification["overall_verdict"])
        optimization = next(
            entry
            for entry in qualification["entries"]
            if entry["criterion"] == "optimization_resistance"
        )
        self.assertFalse(optimization["required"])
        self.assertEqual("UNVERIFIED", optimization["verdict"])


class TestCanonicalSurface(unittest.TestCase):
    def test_canonical_owner_exists_and_stale_surfaces_are_absent(self):
        for path in (TEMPLATE_MANIFEST, PROTOCOL, MANIFEST_CONTRACT):
            self.assertTrue(path.is_file(), f"missing canonical surface: {path}")
        for path in (
            PROJECT_OWNER,
            PROJECT_PROTOCOL,
            CLAUDE_ADAPTER,
            OLD_PACKAGE,
            OLD_COMPOSITION,
        ):
            self.assertFalse(path.exists(), f"stale surface: {path}")

        for skill_path in (ROOT / "skills").rglob("SKILL.md"):
            fields, _ = split_frontmatter(skill_path.read_text(encoding="utf-8"))
            self.assertNotEqual(
                "orch-benchmaker", fields.get("name"),
                f"demoted orch-benchmaker still owned as a skill: {skill_path}",
            )


if __name__ == "__main__":
    unittest.main()
