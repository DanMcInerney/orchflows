"""Retirement behavior and stale-surface checks for benchmaker."""

import json
import os
import re
import unittest
from pathlib import Path

from .shared import (
    CLAUDE_ADAPTER,
    COMPONENT_FIELDS,
    DECLARATION_FIELDS,
    FIXTURE,
    MANIFEST_CONTRACT,
    OLD_COMPOSITION,
    OLD_PACKAGE,
    PACKAGE,
    PACKAGE_MANIFEST,
    POST_QUALIFICATION_FIELDS,
    PROJECT_OWNER,
    PROJECT_PROTOCOL,
    PROTOCOL,
    ROOT,
    TEMPLATE_MANIFEST,
    split_frontmatter,
    squashed,
)

# What the 2026-08-16 review retired rather than moved (thread T29): the
# caller-bound partition, which no script ever performed -- every stage bound
# is a frontmatter literal and `{{bound}}` reached no stub's work. A retired
# law has no owner, so a MOVED_OUT_OF_PROTOCOL row would assert one that does
# not exist; it must instead be absent from the protocol and from the template
# both, or it has come back in the second place after leaving the first.
RETIRED_FROM_PROTOCOL = (
    ("partition one caller bound", "an allocation from it"),
    # The §Audit-and-measurement copy of the same mechanism, which the first
    # row could not see: it survived the 2026-08-16 repair and was caught by
    # the R6a check. Absent from the protocol and from the template both.
    ("the caller bound's partition", "the caller bound"),
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
RETIRED_PATH_EXCLUSIONS = frozenset(DATED_RECORDS) | {"tests/test_benchmaker_cases/retirement.py"}
# Trees that hold no live surface: repository plumbing, session state, and
# the two vendored working trees git already ignores. Installed packages
# are somebody else's bytes, so a relapse can never hide in one.
SKIPPED_TREES = frozenset(
    {".git", ".orch", ".claude", "__pycache__", "node_modules", ".venv"}
)
# A guard that cannot read what it scans decides nothing. An unreadable file
# is reported by name; only a declared binary suffix is skipped, and every
# scan asserts a floor far below the ~1100 files it reads today, so a scan
# that collapses is red rather than green. Fonts join the list because a
# typeface is bytes with a suffix, never prose a grep could relapse into.
BINARY_SUFFIXES = (".png", ".ttf", ".woff", ".woff2")
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


class BenchmakerRetirementCases:
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
        surfaces.extend(path for path in sorted(FIXTURE.iterdir()) if path.is_file())
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
            for anchor in ("separate result identity", "manifest field"):
                with self.subTest(anchor=anchor):
                    self.assertIn(anchor, manifest)
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
