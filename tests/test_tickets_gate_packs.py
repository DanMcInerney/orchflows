"""A gate stub's pack is per stub, and the lens default is the cut's.

The class this module closes: `tickets.py gate` read the *root's* pack twice
-- for the default lens set and for every stub's stamp -- and those were the
only two sites in the tree applying a root's pack downward. A cut holding a
second domain therefore shipped that domain unreviewed, under the root's
craft lens, with no warning and no finding.

Two rules replace it, and the second is the one with teeth. The lens default
is the union of pack domains the root and its cut stamp, which for any
single-pack cut is the root's label alone -- so no existing run changes. And
a stub's pack is the root's, raised only to a pack whose adapter carries
every record the root states: the repair and verify take that ceiling, a
critique takes its lens's pack where the root can lend it.

The ceiling is a ceiling, never a free supremum. `git-plus-render` is the one
adapter that nests over another, so it is the one promotion available; every
other pair would add a root literal the promoted stub has no source for and
be refused at render. A pack that widens nothing simply does not raise the
ceiling -- refusing there would refuse `compositions/benchmaker`, a shipped
mixed-pack graph that is admissible exactly as it stands.

The sink idiom (a temporary ``ORCHFLOWS_STATE_HOME``) is restated here rather
than imported, the convention `tests/test_tickets_gate.py` states, so this
module runs alone under `tools/run_tests.py`'s per-module child.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402
from scripts.tickets_dispatch_gate import (  # noqa: E402
    PACK_WIDENINGS, _critique_pack, _pack_for_domain, _pack_widens,
    _stub_pack_ceiling,
)
from scripts.tickets_format import ADAPTER_BY_PACK  # noqa: E402
from scripts.tickets_inputs import ADAPTER_KINDS  # noqa: E402
from scripts.tickets_input_producers import GIT_PACKS, ROOT_BY_PACK  # noqa: E402

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

STUB = """---
id: {tid}
run: r
status: pending
admission: v1:pending
cohort: v1:ticket:{tid}
executor: {ex}
{packline}independence: {ind}
depends_on: []
write_scope: [src/a.ts]
mutations: [change:src/a.ts]
isolation: required
bound: 60m
claimed_by:
claimed_at:
---

## Objective

Deliver the one thing this item is for.

## Fixed inputs

- input: {{"identity":{{"kind":"git-tree","repo":"run-project","revision":"{head}"}},"name":"baseline","type":"identity"}}

## Completion test

- it works | oracle: `true` | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
"""

ROOT_CASE = ("00-root", "orch-decompose", "orch-code-pack", "gate")


def git_repo(tmp: Path):
    repo = tmp / "repo"
    repo.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.invalid"],
        ["git", "config", "user.name", "t"],
    ):
        subprocess.run(command, cwd=repo, check=True)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()
    return repo, head


@contextmanager
def cut(cases):
    """One run holding ``cases``, and the repo its baseline resolves in."""

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        os.environ[STATE_HOME_ENV_VAR] = str((tmp / "state-sink").resolve())
        repo, head = git_repo(tmp)
        run_dir = tmp / "state-sink" / "tickets" / "r"
        run_dir.mkdir(parents=True)
        for tid, executor, pack, independence in cases:
            run_dir.joinpath(f"{tid}.md").write_text(STUB.format(
                tid=tid, ex=executor, packline=f"pack: {pack}\n" if pack else "",
                ind=independence, head=head), encoding="utf-8")
        yield repo, run_dir


def gate(repo, *args):
    original = tickets_mod._cwd
    original_store = tickets_mod._tickets_store_module._cwd
    tickets_mod._cwd = lambda: Path(repo).resolve()
    try:
        payload = tickets_mod._dispatch(["gate", "r", "00-root", *args])
    finally:
        tickets_mod._cwd = original
        tickets_mod._tickets_store_module._cwd = original_store
    return json.loads(json.dumps(payload, ensure_ascii=False))


def packs_of(run_dir, ids) -> dict:
    stamped = {}
    for stub_id in ids:
        frontmatter = (run_dir / f"{stub_id}.md").read_text(encoding="utf-8").split("---")[1]
        stamped[stub_id] = next(
            (line.split(":", 1)[1].strip() for line in frontmatter.splitlines()
             if line.startswith("pack:")), None)
    return stamped


def unit(tid, pack, executor):
    return (tid, executor, pack, "checker")


class TheLensDefault(unittest.TestCase):
    def test_a_single_pack_cut_is_unchanged(self):
        """The pin behind 'no existing run changes': one domain, one lens,
        and the two-stub chain the single-lens collapse has always emitted."""

        with cut([ROOT_CASE, unit("00-root.01", "orch-code-pack", "orch-tdd")]) as (repo, run_dir):
            payload = gate(repo)
            self.assertEqual(["code"], payload["gate"]["lenses"])
            self.assertEqual(2, len(payload["gate"]["ids"]))
            self.assertEqual({"orch-code-pack"},
                             set(packs_of(run_dir, payload["gate"]["ids"]).values()))

    def test_a_second_domain_in_the_cut_earns_its_own_lens(self):
        with cut([ROOT_CASE,
                  unit("00-root.01", "orch-code-pack", "orch-tdd"),
                  unit("00-root.02", "orch-design-pack", "orch-render")]) as (repo, run_dir):
            payload = gate(repo)
            self.assertEqual(["code", "design"], payload["gate"]["lenses"])
            self.assertEqual(4, len(payload["gate"]["ids"]),
                             "two lenses split the chain into critiques, repair, verify")

    def test_a_pack_less_unit_mints_no_lens(self):
        """A cut of unstamped units keeps the root's label alone -- the shape
        `tests/test_tickets_view_cases/gate_stubs.py` gates on."""

        with cut([ROOT_CASE, unit("00-root.01", None, "orch-tdd")]) as (repo, _):
            self.assertEqual(["code"], gate(repo)["gate"]["lenses"])


class TheStubPack(unittest.TestCase):
    def test_each_critique_carries_its_own_lens_pack(self):
        with cut([ROOT_CASE,
                  unit("00-root.01", "orch-code-pack", "orch-tdd"),
                  unit("00-root.02", "orch-design-pack", "orch-render")]) as (repo, run_dir):
            payload = gate(repo)
            stamped = packs_of(run_dir, payload["gate"]["ids"])
            self.assertEqual("orch-code-pack", stamped["00-root.gate.critique.code"])
            self.assertEqual("orch-design-pack", stamped["00-root.gate.critique.design"])

    def test_the_repair_and_verify_take_the_ceiling(self):
        with cut([ROOT_CASE,
                  unit("00-root.01", "orch-code-pack", "orch-tdd"),
                  unit("00-root.02", "orch-design-pack", "orch-render")]) as (repo, run_dir):
            payload = gate(repo)
            stamped = packs_of(run_dir, payload["gate"]["ids"])
            self.assertEqual("orch-design-pack", stamped["00-root.gate.repair"])
            self.assertEqual("orch-design-pack", stamped["00-root.gate.verify"],
                             "the write and decide halves carry the widest pack the cut lends")

    def test_a_free_form_lens_names_no_pack_and_takes_the_ceiling(self):
        """A total label->pack inverse would stamp `orch-security-pack`, which
        no adapter table holds, and refuse the whole family."""

        with cut([ROOT_CASE, unit("00-root.01", "orch-code-pack", "orch-tdd")]) as (repo, run_dir):
            payload = gate(repo, "--lens", "code,security")
            self.assertNotIn("error", payload)
            stamped = packs_of(run_dir, payload["gate"]["ids"])
            self.assertEqual("orch-code-pack", stamped["00-root.gate.critique.security"])

    def test_an_unwidenable_lens_pack_is_not_stamped(self):
        """`orch-content-pack` on a git root is refused at render for a
        `document-root` nobody wrote, so the critique takes the ceiling."""

        with cut([ROOT_CASE, unit("00-root.01", "orch-code-pack", "orch-tdd")]) as (repo, run_dir):
            payload = gate(repo, "--lens", "code,content")
            self.assertNotIn("error", payload)
            self.assertEqual("orch-code-pack",
                             packs_of(run_dir, payload["gate"]["ids"])["00-root.gate.critique.content"])

    def test_an_unwidenable_unit_pack_does_not_raise_the_ceiling(self):
        """The `compositions/benchmaker` pin: a research unit under a code
        root earns its lens and changes no stamp. Refusing here would refuse
        a family that emits cleanly exactly as it stands."""

        with cut([ROOT_CASE,
                  unit("00-root.01", "orch-code-pack", "orch-tdd"),
                  unit("00-root.02", "orch-research-pack", "orch-investigate")]) as (repo, run_dir):
            payload = gate(repo)
            self.assertNotIn("error", payload)
            self.assertEqual(["code", "research"], payload["gate"]["lenses"])
            self.assertEqual({"orch-code-pack"},
                             set(packs_of(run_dir, payload["gate"]["ids"]).values()))

    def test_a_chained_critique_takes_the_ceiling_not_its_lens(self):
        """With one explicit lens the critique is also the repair, and the
        write half is the half a pack is authority for."""

        with cut([ROOT_CASE,
                  unit("00-root.01", "orch-code-pack", "orch-tdd"),
                  unit("00-root.02", "orch-design-pack", "orch-render")]) as (repo, run_dir):
            payload = gate(repo, "--lens", "code")
            stamped = packs_of(run_dir, payload["gate"]["ids"])
            self.assertEqual(2, len(stamped), "one lens still chains")
            self.assertEqual({"orch-design-pack"}, set(stamped.values()))

    def test_an_unstamped_root_promotes_to_nothing(self):
        """A stub inherits what the root held and never invents what it did
        not: promoting here would silently repair a malformed root and delete
        the subject of `test_tickets_gate.py`'s emission refusal."""

        with cut([("00-root", "orch-decompose", None, "gate"),
                  unit("00-root.01", "orch-code-pack", "orch-tdd")]) as (repo, _):
            payload = gate(repo, "--lens", "code,style")
            self.assertIn("error", payload,
                          "the root's git-tree under no adapter is still refused")
            # Named, not merely present: a `code` lens that stamped its own
            # pack would grade that one stub clean and quietly drop it from
            # the refusal, which is what an unguarded `_critique_pack` did.
            self.assertEqual(
                {"00-root.gate.critique.code", "00-root.gate.critique.style",
                 "00-root.gate.repair", "00-root.gate.verify"},
                {finding.get("ticket") for finding in payload.get("findings") or []})


class ThePureRules(unittest.TestCase):
    def test_the_widening_table_matches_the_tables_it_mirrors(self):
        """`PACK_WIDENINGS` is a literal so this writing door need not import
        the grading slice; this is what keeps it honest."""

        candidates = sorted({*ADAPTER_BY_PACK, ""})
        derived = {}
        for pack in candidates:
            wider = []
            for base in candidates:
                if pack == base:
                    continue
                kinds = set(ADAPTER_KINDS.get(ADAPTER_BY_PACK.get(pack, ""), ()))
                base_kinds = set(ADAPTER_KINDS.get(ADAPTER_BY_PACK.get(base, ""), ()))
                same_root = ROOT_BY_PACK.get(pack) == ROOT_BY_PACK.get(base)
                if base_kinds <= kinds and same_root:
                    wider.append(base)
            if wider:
                derived[pack] = tuple(sorted(wider))
        self.assertEqual(derived, {key: tuple(sorted(value))
                                   for key, value in PACK_WIDENINGS.items()})

    def test_the_relation_is_reflexive_and_anchored(self):
        self.assertTrue(_pack_widens("orch-code-pack", "orch-code-pack"))
        self.assertTrue(_pack_widens("orch-design-pack", "orch-code-pack"))
        self.assertFalse(_pack_widens("orch-code-pack", "orch-design-pack"))
        self.assertFalse(_pack_widens("orch-content-pack", "orch-code-pack"))

    def test_the_ceiling_never_falls_below_its_floor(self):
        self.assertEqual("orch-design-pack", _stub_pack_ceiling(
            "orch-design-pack", ["orch-code-pack", "orch-code-pack"]))
        self.assertEqual("orch-design-pack", _stub_pack_ceiling(
            "orch-code-pack", ["orch-design-pack"]))
        self.assertEqual("orch-code-pack", _stub_pack_ceiling(
            "orch-code-pack", ["orch-research-pack"]))
        self.assertIsNone(_stub_pack_ceiling(None, ["orch-code-pack"]))

    def test_a_critique_pack_is_its_lens_or_the_ceiling(self):
        self.assertEqual("orch-design-pack", _critique_pack(
            "design", "orch-code-pack", "orch-design-pack"))
        self.assertEqual("orch-code-pack", _critique_pack(
            "security", "orch-code-pack", "orch-code-pack"))
        self.assertIsNone(_pack_for_domain("security"))
        self.assertEqual("orch-code-pack", _pack_for_domain("Code"),
                         "lens identity is case-insensitive, as the gate already treats it")

    def test_the_head_guard_names_no_second_copy_of_git_packs(self):
        """The guard used to carry its own literal pack tuple."""

        self.assertEqual(("orch-code-pack", "orch-design-pack"), tuple(sorted(GIT_PACKS)))


if __name__ == "__main__":
    unittest.main()
