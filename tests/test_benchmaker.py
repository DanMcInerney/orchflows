"""Contract and replay checks for the canonical benchmark workflow."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
# Demoted per contracts/composition.md: benchmaker is a named composition.
OLD_PACKAGE = ROOT / "skills" / "workflows" / "orch-benchmaker"
SKILL = ROOT / "compositions" / "benchmaker.md"
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
COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
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
    "docs/benchmaker-redesign-spec.md":
        "the dated design record; its revision sections describe the removal",
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
    for path in sorted(tree.rglob("*")):
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


class TestCanonicalBenchmaker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_text = SKILL.read_text(encoding="utf-8")
        cls.fields, cls.body = split_frontmatter(cls.skill_text)
        cls.protocol = PROTOCOL.read_text(encoding="utf-8")
        cls.manifest_contract = MANIFEST_CONTRACT.read_text(encoding="utf-8")

    def test_composition_anatomy_calls_and_delegation_mapping(self):
        self.assertEqual("benchmaker", self.fields["name"])
        # Manual-only survives the demotion as entry: named.
        self.assertEqual("named", self.fields["entry"])
        self.assertLessEqual(len(self.fields["description"]), 140)
        self.assertLess(self.body.index("Require:"), self.body.index("Never:"))
        self.assertLess(self.body.index("Never:"), self.body.index("Return:"))
        calls = re.findall(r"`(orch-[a-z0-9-]+)`", self.body)
        self.assertEqual(
            ["orch-spec", "orch-deliver", "orch-eval-design"], calls
        )
        self.assertEqual(
            1,
            self.body.count(
                "[internal-call carrier rule]"
                "(references/benchmaker-protocol.md#internal-call-carriage)"
            ),
        )
        self.assertGreaterEqual(
            self.body.count("[manifest](references/benchmaker-manifest.md)"), 1
        )

        require = squashed(
            self.body[
                self.body.index("Require:") : self.body.index(
                    "\n\n", self.body.index("Require:")
                )
            ]
        )
        for packet_field in (
            "objective",
            "inputs",
            "authority",
            "bounds",
            "return_contract",
            "reply_to",
        ):
            self.assertIn(f"`{packet_field}`", require)
        for mapped_value in (
            "target identity",
            "intended observable outcome",
            "evidence identities",
            "source policy",
            "judgment permission",
            "benchmark write scope",
            "excluded actions",
            "one caller bound",
            "status",
            # There is no benchmark identity to return; a benchmark's version
            # is its git revision. The case set's mirror of this packet line
            # (`cs-run-conduct/evidence/packet.md`) says the same words.
            "the benchmark's revision",
            "qualification",
            "gaps",
            "bounds spent",
            "changed artifacts",
            "literal return address",
        ):
            self.assertIn(mapped_value, require)

    def test_ordered_stages_return_partial_evidence_and_do_not_evolve(self):
        body = squashed(self.body)
        stages = (
            "freeze one evidence-acquisition spec",
            "`orch-deliver` of that frozen routing-stamped spec",
            "design — `orch-eval-design`",
            "materialize the selected case specifications",
            "qualify the assembled benchmark",
        )
        positions = [body.index(stage) for stage in stages]
        self.assertEqual(sorted(positions), positions)
        self.assertIn("one applicable pack per internal spec", body)
        self.assertIn("partial evidence", body)

        # Every prohibition that is not seal-derived survives; only "revise a
        # benchmark in place" goes, and the qualification discipline stays.
        never = body[body.index("Never:") : body.index("Return:")]
        for forbidden_action in (
            "mutate the target",
            "generate a candidate",
            "compare candidates",
            "promote",
            "activate",
            "call Evolve",
            "let builders qualify their own work",
            "multiply the caller bound",
        ):
            self.assertIn(forbidden_action, never)
        self.assertNotIn("in place", never)

        returned = body[body.index("Return:") :]
        self.assertIn("the closing result addresses `reply_to`", returned)
        for field in (
            "status",
            # There is no benchmark identity to return; a benchmark's version
            # is its git revision. The case set's mirror of this packet line
            # (`cs-run-conduct/evidence/packet.md`) says the same words.
            "the benchmark's revision",
            "qualification",
            "gaps",
            "bounds spent",
            "changed artifacts",
        ):
            self.assertIn(field, returned)
        self.assertIn("partial evidence", returned)

    def test_protocol_is_domain_blind_single_pack_and_single_bound(self):
        headings = re.findall(r"^## (.+)$", self.protocol, re.MULTILINE)
        self.assertEqual(
            [
                "Intake and bound",
                "Internal call carriage",
                "Evidence acquisition",
                "Evaluation design",
                "Execution tier and difficulty",
                "Materialization",
                "Qualification",
                "Audit and measurement",
                "Scoring",
                "Manifest and return",
            ],
            headings,
        )
        packed = squashed(self.protocol)
        for phrase in (
            "partition one caller bound",
            "evidence, design, materialization, qualification, and the audit "
            "and measurement stages",
            "total cannot exceed",
            "unused allocation",
            "Never copy the caller bound",
            "one applicable pack",
            "exactly one pack per internal spec",
            "chain single-pack runs through frozen evidence identities",
            "supplied qualified synthesis",
            "source policy",
            "expected execution cost",
        ):
            self.assertIn(phrase, packed)
        self.assertIn(
            "BenchMaker neither fixes the evaluation boundary nor selects",
            packed,
        )

        known_pack_names = [
            path.name for path in (ROOT / "packs").iterdir() if path.is_dir()
        ]
        for pack_name in known_pack_names:
            self.assertNotIn(pack_name, self.protocol)
        for forbidden_owner in ("`orch-bench`", "`orch-evolve`"):
            self.assertNotIn(forbidden_owner, self.protocol)

    def test_internal_call_carriage_rule_maps_every_packet(self):
        carriage = squashed(
            markdown_section(self.protocol, "Internal call carriage")
        )
        self.assertIn(
            "Every internal Spec, Deliver, and evaluation-design invocation",
            carriage,
        )
        for packet_field in (
            "objective",
            "inputs",
            "authority",
            "bounds",
            "return_contract",
            "reply_to",
        ):
            self.assertIn(f"`{packet_field}`", carriage)
        for invariant in (
            "one applicable pack",
            "stage allocation",
            "never the caller bound",
            "callee's canonical Return",
            "closing recipient",
            "Qualification authority is disjoint from builders",
        ):
            self.assertIn(invariant, carriage)

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
        self.assertIn("Builders never qualify", qualification)

    def test_protocol_prices_speed_below_the_coverage_floor(self):
        tier = squashed(markdown_section(self.protocol, "Execution tier and difficulty"))
        # The coverage floor outranks cost, in both directions of the split.
        self.assertIn("declared coverage floor never moves", tier)
        self.assertIn("smallest tier", tier)
        self.assertIn("suite ceiling rises", tier)
        self.assertIn("raise that case's tier and record why; never drop the angle", tier)
        # Speed and difficulty each name what they may not be bought from.
        self.assertIn(
            "Speed is bought from the probe, never from the coverage floor, "
            "the oracle, or the horizon",
            tier,
        )
        self.assertIn("Difficulty is built, never filtered", tier)
        for forbidden in (
            "Never select or retain a case by target failure",
            "never remove one for low discrimination",
            "never revise the design from a candidate's scores",
        ):
            self.assertIn(forbidden, tier)

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

    def test_composition_runs_the_audit_stages_and_records_the_manifest(self):
        body = squashed(self.body)
        self.assertIn("- audit-and-measure —", body)
        self.assertLess(body.index("- materialize —"), body.index("- qualify —"))
        self.assertLess(body.index("- qualify —"), body.index("- audit-and-measure —"))
        self.assertIn("materialize → qualify → audit-and-measure", body)
        # The new seam carries an identity, as every other join does.
        self.assertIn("the assembled case set is qualify's evidence", body)
        self.assertIn("the qualified assembly is audit-and-measure's", body)
        step = body[body.index("- audit-and-measure —") : body.index("Edges:")]
        # The count the step declares equals the number of activities the same
        # sentence names — counted off the text, never off a list this file
        # holds, or a fourth activity could be named under a declared three and
        # nothing here would see it. That was the baseline defect.
        declaration = step[step.index("the protocol's") :]
        listed = declaration[declaration.index(":") + 1 : declaration.index(" — ")]
        activities = [activity.strip() for activity in listed.split(", then ")]
        self.assertIn(f"the protocol's {COUNT_WORDS[len(activities)]} stages", step)
        self.assertEqual(len(AUDIT_STAGES), len(activities))
        # Named in the protocol's own execution order, which the step declares.
        self.assertIn("stages in order", step)
        for stage, activity in zip(AUDIT_STAGES, activities):
            self.assertIn(stage, activity)
        # Triage is the measurement stage's own first pass, never a fourth.
        self.assertEqual([], re.findall(r"triage(?! pass)", step))
        self.assertIn("Record the manifest after they close", body)
        self.assertIn("declared coverage floor never moves", body)


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
        for path in (SKILL, PROTOCOL, MANIFEST_CONTRACT):
            self.assertTrue(path.is_file(), f"missing canonical surface: {path}")
        for path in (PROJECT_OWNER, PROJECT_PROTOCOL, CLAUDE_ADAPTER, OLD_PACKAGE):
            self.assertFalse(path.exists(), f"stale surface: {path}")

        for skill_path in (ROOT / "skills").rglob("SKILL.md"):
            fields, _ = split_frontmatter(skill_path.read_text(encoding="utf-8"))
            self.assertNotEqual(
                "orch-benchmaker", fields.get("name"),
                f"demoted orch-benchmaker still owned as a skill: {skill_path}",
            )


if __name__ == "__main__":
    unittest.main()
