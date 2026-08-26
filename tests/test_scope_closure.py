"""Specification 05: declared mutation-edge closure at ticket admission."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import tickets_scope  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "final_specs" / "05"


def ticket(
    ticket_id,
    *,
    mutations=(),
    scope=(),
    depends=(),
    cohort="v1:batch:scope",
    pack="orch-code-pack",
    admission="v1:pending",
    include_plan=True,
):
    lines = [
        "---",
        f"id: {ticket_id}",
        "run: scope-run",
        "status: pending",
        f"admission: {admission}",
        f"cohort: {cohort}",
        "executor: orch-tdd",
        f"pack: {pack}",
        f"depends_on: [{', '.join(depends)}]",
        f"write_scope: [{', '.join(scope)}]",
    ]
    if include_plan:
        lines.append(f"mutations: [{', '.join(mutations)}]")
    lines += ["bound: 30m", "---", "", "## Objective", "", "Fixture.", ""]
    return "\n".join(lines)


def manifest(*edges, **extra):
    value = {"version": 1, "edges": list(edges)}
    value.update(extra)
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def edge(source, required, reason="fixture edge"):
    operation, path = source.split(":", 1)
    required_operation, required_path = required.split(":", 1)
    return {
        "from": {"operation": operation, "path": path},
        "requires": [{"operation": required_operation, "path": required_path}],
        "reason": reason,
    }


def grade(ticket_id, siblings, content):
    text = siblings[ticket_id]
    return tickets_scope.grade_scope(
        ticket_id=ticket_id,
        text=text,
        siblings=siblings,
        adapter_id="git",
        context={"scope_manifest": content},
    )


def codes(result):
    return [item["code"] for item in result["findings"]]


class MutationPlanSchemaTests(unittest.TestCase):
    def test_v1_git_ticket_requires_an_explicit_plan(self):
        siblings = {"A": ticket("A", scope=("scripts/a.py",), include_plan=False)}
        self.assertEqual(["mutation-plan-missing"], codes(grade("A", siblings, None)))

    def test_plan_operations_paths_and_authority_are_graded_without_widening(self):
        siblings = {
            "A": ticket(
                "A",
                mutations=("create:scripts/a.py", "write:web/src", "change:tests/a.py"),
                scope=("scripts/a.py", "web/src/"),
            )
        }
        result = grade("A", siblings, None)
        self.assertEqual(
            ["mutation-invalid", "mutation-outside-write-scope"],
            sorted(set(codes(result))),
        )
        self.assertNotIn("tests/a.py", result["authorized_scope"])

    def test_absent_manifest_and_non_git_adapters_are_direct_only(self):
        siblings = {"A": ticket("A", mutations=("change:a.py",), scope=("a.py",))}
        absent = grade("A", siblings, None)
        self.assertEqual("direct-only", absent["mode"])
        self.assertEqual([], absent["findings"])

        non_git = tickets_scope.grade_scope(
            ticket_id="A",
            text=ticket("A", pack="orch-content-pack", include_plan=False),
            siblings={},
            adapter_id="document-tree",
            context={"scope_manifest": manifest(edge("change:a.py", "change:b.py"))},
        )
        self.assertEqual("direct-only", non_git["mode"])
        self.assertEqual([], non_git["findings"])

    def test_manifest_schema_is_closed_and_fingerprinted_even_on_refusal(self):
        siblings = {"A": ticket("A", mutations=("change:a.py",), scope=("a.py",))}
        malformed = manifest(edge("change:a.py", "change:b.py"), note="not allowed")
        result = grade("A", siblings, malformed)
        self.assertEqual(["scope-edge-schema"], codes(result))
        self.assertRegex(result["fingerprint"], r"^scope:sha256:[0-9a-f]{64}$")

    def test_external_manifest_symlink_and_failed_immutable_read_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "baseline"
            external = Path(raw) / "external.json"
            (root / ".orchflows").mkdir(parents=True)
            external.write_bytes(manifest())
            link = root / ".orchflows" / "scope-edges.json"
            try:
                link.symlink_to(external)
            except OSError:
                self.skipTest("symlinks unavailable")
            _, error = tickets_scope._resolved_manifest("", {"baseline_tree": root})
            self.assertIn("external", error)
        text = ticket("A", mutations=("change:a.py",), scope=("a.py",))
        baseline = '- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"' + "a" * 40 + '"},"name":"baseline","type":"identity"}'
        text += "\n## Fixed inputs\n\n" + baseline + "\n"
        replies = [
            mock.Mock(returncode=1, stdout=b"", stderr=b"read failed"),
            mock.Mock(returncode=0, stdout=b"", stderr=b""),
        ]
        with mock.patch.object(tickets_scope, "_project_root", return_value=Path(".")), mock.patch.object(tickets_scope.subprocess, "run", side_effect=replies):
            _, error = tickets_scope._resolved_manifest(text, {})
        self.assertIn("exists but could not be read", error)


class DeclaredClosureTests(unittest.TestCase):
    OWNERSHIP = edge("create:scripts/*.py", "change:ARCHITECTURE.md", "script ownership")

    def test_same_ticket_owner_closes_the_edge(self):
        siblings = {
            "A": ticket(
                "A",
                mutations=("create:scripts/tool.py", "change:ARCHITECTURE.md"),
                scope=("scripts/tool.py", "ARCHITECTURE.md"),
            )
        }
        self.assertEqual([], grade("A", siblings, manifest(self.OWNERSHIP))["findings"])

    def test_one_ordered_companion_owner_closes_the_edge(self):
        siblings = {
            "A": ticket("A", mutations=("create:scripts/tool.py",), scope=("scripts/tool.py",)),
            "B": ticket(
                "B", mutations=("change:ARCHITECTURE.md",),
                scope=("ARCHITECTURE.md",), depends=("A",),
            ),
        }
        self.assertEqual([], grade("A", siblings, manifest(self.OWNERSHIP))["findings"])

    def test_missing_multiple_unauthorized_and_unordered_owners_are_distinct(self):
        source = ticket("A", mutations=("create:scripts/tool.py",), scope=("scripts/tool.py",))
        required = manifest(self.OWNERSHIP)

        missing = grade("A", {"A": source}, required)
        self.assertEqual(["scope-owner-missing"], codes(missing))

        multiple = {
            "A": source,
            "B": ticket("B", mutations=("change:ARCHITECTURE.md",), scope=("ARCHITECTURE.md",), depends=("A",)),
            "C": ticket("C", mutations=("change:ARCHITECTURE.md",), scope=("ARCHITECTURE.md",), depends=("A",)),
        }
        self.assertIn("scope-owner-multiple", codes(grade("A", multiple, required)))

        unauthorized = {
            "A": source,
            "B": ticket("B", mutations=("change:ARCHITECTURE.md",), scope=("docs",), depends=("A",)),
        }
        self.assertIn("scope-owner-unauthorized", codes(grade("A", unauthorized, required)))

        unordered = {
            "A": source,
            "B": ticket("B", mutations=("change:ARCHITECTURE.md",), scope=("ARCHITECTURE.md",)),
        }
        self.assertIn("scope-owner-unordered", codes(grade("A", unordered, required)))

    def test_operation_negative_control_prefix_and_transitive_ordering(self):
        change_only = {
            "A": ticket("A", mutations=("change:scripts/tool.py",), scope=("scripts/tool.py",))
        }
        self.assertEqual([], grade("A", change_only, manifest(self.OWNERSHIP))["findings"])

        chain = (
            edge("change:a.txt", "change:b.txt"),
            edge("change:b.txt", "change:c.txt"),
        )
        siblings = {
            "A": ticket("A", mutations=("change:a.txt",), scope=("a.txt",)),
            "B": ticket("B", mutations=("change:b.txt",), scope=("b.txt",), depends=("A",)),
            "C": ticket("C", mutations=("change:c.txt",), scope=("c.txt",), depends=("B",)),
        }
        self.assertEqual([], grade("A", siblings, manifest(*chain))["findings"])

        distribution = edge("write:web/src/", "write:web/dist/", "built distribution")
        siblings = {
            "A": ticket("A", mutations=("change:web/src/app.js",), scope=("web/src/",)),
            "B": ticket("B", mutations=("write:web/dist/",), scope=("web/dist/",), depends=("A",)),
        }
        self.assertEqual([], grade("A", siblings, manifest(distribution))["findings"])

    def test_duplicate_edges_collapse_and_reachable_cycles_are_findings(self):
        ownership = self.OWNERSHIP
        siblings = {
            "A": ticket(
                "A",
                mutations=("create:scripts/tool.py", "change:ARCHITECTURE.md"),
                scope=("scripts/tool.py", "ARCHITECTURE.md"),
            )
        }
        self.assertEqual([], grade("A", siblings, manifest(ownership, ownership))["findings"])

        cycle = manifest(
            edge("change:a.txt", "change:b.txt"),
            edge("change:b.txt", "change:a.txt"),
        )
        cycle_ticket = {
            "A": ticket(
                "A", mutations=("change:a.txt", "change:b.txt"),
                scope=("a.txt", "b.txt"),
            )
        }
        self.assertEqual(["scope-edge-cycle"], codes(grade("A", cycle_ticket, cycle)))

    def test_fingerprint_invalidates_when_the_resolved_baseline_graph_changes(self):
        siblings = {"A": ticket("A", mutations=("change:a.txt",), scope=("a.txt",))}
        first = grade("A", siblings, manifest())
        second = grade("A", siblings, manifest(edge("change:z.txt", "change:q.txt")))
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])


class CohortCompanionOwnerTests(unittest.TestCase):
    """Who owns a scope-edge companion inside a decomposed cohort.

    A root's write scope is its whole subtree's, and a gate stub repairs
    anywhere the cut writes; both therefore cover every companion the cut
    plans. Counting them as owners convicts the lawful shape -- one unit
    owning the companion -- of `scope-owner-multiple`, so companion ownership
    is read among the units alone whenever the cohort holds one. A root
    graded on its own is still the only member there is, and still owns the
    companions it plans.
    """

    OWNERSHIP = edge("create:scripts/*.py", "change:ARCHITECTURE.md", "script ownership")
    COHORT = "v1:root:00-root"

    def member(self, ticket_id, **kwargs):
        kwargs.setdefault("cohort", self.COHORT)
        return ticket(ticket_id, **kwargs)

    def companion(self, ticket_id, **kwargs):
        return self.member(
            ticket_id, mutations=("change:ARCHITECTURE.md",),
            scope=("ARCHITECTURE.md",), **kwargs
        )

    def subtree(self, ticket_id):
        """A root and its gate stub plan the whole cut, trigger included.

        Reading a cohort whose root plans only the companion would leave the
        trigger half of the filter unexercised -- the owners `required_by`
        records, which is the half that grades ordering.
        """
        return self.member(
            ticket_id,
            mutations=("create:scripts/tool.py", "change:ARCHITECTURE.md"),
            scope=("scripts/tool.py", "ARCHITECTURE.md"),
        )

    def cohort(self, *units):
        siblings = {
            "00-root": self.subtree("00-root"),
            "00-root.gate.repair": self.subtree("00-root.gate.repair"),
            "00-root.01": self.member(
                "00-root.01", mutations=("create:scripts/tool.py",),
                scope=("scripts/tool.py",),
            ),
        }
        siblings.update(units)
        return siblings

    def test_one_unit_owner_closes_the_edge_beside_the_root_and_its_gate(self):
        siblings = self.cohort(
            ("00-root.02", self.companion("00-root.02", depends=("00-root.01",))),
        )
        self.assertEqual(
            [], grade("00-root.01", siblings, manifest(self.OWNERSHIP))["findings"]
        )

    def test_two_unit_owners_collide_and_naming_only_units(self):
        siblings = self.cohort(
            ("00-root.02", self.companion("00-root.02", depends=("00-root.01",))),
            ("00-root.03", self.companion("00-root.03", depends=("00-root.01",))),
        )
        findings = grade("00-root.01", siblings, manifest(self.OWNERSHIP))["findings"]
        self.assertEqual(["scope-owner-multiple"], [item["code"] for item in findings])
        self.assertEqual(
            "change:ARCHITECTURE.md owned by 00-root.02, 00-root.03",
            findings[0]["detail"],
        )

    def test_no_unit_owner_is_missing_rather_than_owned_by_root_and_gate(self):
        self.assertEqual(
            ["scope-owner-missing"],
            codes(grade("00-root.01", self.cohort(), manifest(self.OWNERSHIP))),
        )

    def test_ordering_is_graded_against_the_unit_trigger_owner_alone(self):
        siblings = self.cohort(("00-root.02", self.companion("00-root.02")))
        findings = grade("00-root.01", siblings, manifest(self.OWNERSHIP))["findings"]
        self.assertEqual(["scope-owner-unordered"], [item["code"] for item in findings])
        self.assertEqual(
            "change:ARCHITECTURE.md requires 00-root.01", findings[0]["detail"]
        )

    def test_a_root_graded_alone_still_owns_its_own_companions(self):
        alone = {
            "00-root": self.member(
                "00-root",
                mutations=("create:scripts/tool.py", "change:ARCHITECTURE.md"),
                scope=("scripts/tool.py", "ARCHITECTURE.md"),
            )
        }
        self.assertEqual(
            [], grade("00-root", alone, manifest(self.OWNERSHIP))["findings"]
        )


class DeclaredObservationFixtureTests(unittest.TestCase):
    def test_all_twelve_observations_need_ownership_only_when_declared(self):
        paths = sorted(FIXTURES.glob("*.json"))
        self.assertEqual(12, len(paths))
        for path in paths:
            case = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(case=case["name"]):
                source_path = case["mutation"].split(":", 1)[1]
                siblings = {
                    "A": ticket("A", mutations=(case["mutation"],), scope=(source_path,))
                }
                declared = grade("A", siblings, manifest(case["edge"]))
                self.assertEqual(["scope-owner-missing"], codes(declared))
                direct = grade("A", siblings, None)
                self.assertEqual("direct-only", direct["mode"])
                self.assertNotIn("scope-owner-missing", codes(direct))


class RepositoryScopeManifestTests(unittest.TestCase):
    def test_closed_manifest_contains_only_the_five_evidence_backed_edges(self):
        content = (ROOT / ".orchflows" / "scope-edges.json").read_bytes()
        parsed, findings = tickets_scope.parse_manifest(content)
        self.assertEqual([], findings)
        rows = {
            (item["from"], required)
            for item in parsed
            for required in item["requires"]
        }
        self.assertEqual(
            {
                (("create", "scripts/*.py"), ("change", "ARCHITECTURE.md")),
                (("create", "contracts/*.md"), ("change", "tests/pins.json")),
                (("change", "contracts/*.md"), ("change", "tests/pins.json")),
                (("delete", "contracts/*.md"), ("change", "tests/pins.json")),
                (
                    ("change", "scripts/tickets_errand.py"),
                    ("change", "ARCHITECTURE.md"),
                ),
                (
                    ("delete", "scripts/tickets_errand.py"),
                    ("change", "ARCHITECTURE.md"),
                ),
                (("write", "web/src/"), ("write", "web/dist/")),
            },
            rows,
        )
        self.assertEqual(7, len(parsed))

    def test_code_and_design_workspace_cells_name_plan_graph_and_direct_only_mode(self):
        for relative in (
            "packs/orch-code-pack/SKILL.md",
            "packs/orch-design-pack/SKILL.md",
        ):
            with self.subTest(relative=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                workspace = next(line for line in text.splitlines() if line.startswith("| workspace |"))
                for anchor in ("`mutations`", "`.orchflows/scope-edges.json`", "direct-only"):
                    self.assertIn(anchor, workspace)


class ThePlanIsItsOwnMembersLaw(unittest.TestCase):
    """A member's own pack answers for its own mutation plan.

    The plan is the git adapters' field -- only their workspace cells declare
    it -- but whether this grade runs at all is the *subject's* adapter's
    call. So one content or research member in a cut charged every git member
    `mutation-plan-missing` for a law that member's pack never imposed, at a
    door that refuses rather than defers: the git members could not be
    admitted, and `tickets.py instantiate` -- which puts every stub of a
    composition in one cohort -- refused the batch outright.
    """

    def _mixed(self, sibling_pack):
        return {
            "10-code": ticket("10-code", mutations=["change:src/a.ts"], scope=["src/a.ts"]),
            "20-other": ticket("20-other", pack=sibling_pack, scope=["docs/a.md"],
                               include_plan=False),
        }

    def test_a_non_git_member_is_not_charged_the_git_plan(self):
        for pack in ("orch-content-pack", "orch-research-pack"):
            with self.subTest(pack=pack):
                siblings = self._mixed(pack)
                self.assertNotIn("mutation-plan-missing",
                                 codes(grade("10-code", siblings, None)))

    def test_a_git_member_is_still_charged_it(self):
        """The can-fail direction: revert the per-member test and the case
        above goes green for the wrong reason, so this one must stay red
        without the finding at all."""

        for pack in ("orch-code-pack", "orch-design-pack"):
            with self.subTest(pack=pack):
                siblings = self._mixed(pack)
                self.assertIn("mutation-plan-missing",
                              codes(grade("10-code", siblings, None)))

    def test_the_non_git_member_grades_clean_on_its_own_vantage(self):
        siblings = self._mixed("orch-content-pack")
        result = tickets_scope.grade_scope(
            ticket_id="20-other", text=siblings["20-other"], siblings=siblings,
            adapter_id="document-tree", context={"scope_manifest": None})
        self.assertEqual([], codes(result))


if __name__ == "__main__":
    unittest.main()
