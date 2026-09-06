"""`orchflows check`: the compiler's item checks, and the machine's, over a ring.

Two questions meet in this verb and nowhere else. Is every item in this ring
well formed -- the library compiler's own question, asked of a user's
directory -- and is what those items declare they need actually on this
machine, which is `orchflows sync`'s question asked before a run instead of
during one. The cases below are ordered that way: shape first, then the one
thing asking the second question costs -- a probe is the item's own command,
so an untrusted project ring waits for its grant -- then the bundle's own
manifest above them all. What a declaration resolves to is
`tests/test_orchflows_tooling.py`'s, at both doors at once.

Its own module rather than more cases in `tests/test_orchflows_cli.py`: the
peers there each move one ring file and read one line back, and every case
here builds a whole scaffolded ring and grades it. `_home` and `_run` are
that module's, imported rather than forked.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import orchflows, orchflows_scaffold, rings, rings_trust
from tools.validate_support.common import BODY_BUDGET, SKIPPED

from tests.test_orchflows_cli import _home, _run


def _probe(marker: Path) -> str:
    """A `tools.txt` whose probe leaves a file behind when it is run.

    A resolution that ran nothing and one that was never reached read the
    same in a report, so what the cases below assert is the side effect
    itself: the marker is there, or the probe did not run.
    """

    return 'here :: "{}" -c "open(r\'{}\', \'w\').close()"\n'.format(
        sys.executable, marker,
    )


NARROWING = """---
name: market-brief
description: One sentence saying when to stamp market-brief.
narrows: widget-standard
---

# market-brief

## Making

What this narrowing adds for the maker. Additive and tighten-only.

## Lens

### git

What a judge checks here beside the broader standard's entry.
"""


class CheckTests(unittest.TestCase):
    """`orchflows check`: the compiler's item checks over a ring.

    The valid case is built by the product's own scaffolds rather than by
    hand, so the pass is the claim `scripts/orchflows_scaffold.py` makes --
    what `orchflows new` writes is valid the day it is written -- read back
    through the checker that would refuse it. Each refusal case then mutates
    that same ring in exactly one place, so a green reading here is the
    can-fail one: the ring goes red for the mutation and nothing else.
    """

    def _ring(self, home: Path) -> Path:
        """A home ring holding one scaffolded item of every kind, plus one
        narrowing.

        The narrowing is written here rather than scaffolded because
        `orchflows new standard` writes the root skeleton -- one kind, one
        skeleton -- and an author reaching for a narrowing writes `narrows:`
        and drops the three sections a narrowing is refused, which is
        exactly what this does.
        """

        (home / "nowhere").mkdir(exist_ok=True)
        with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
            for kind, name in (
                ("skill", "helper"), ("standard", "widget-standard"),
                ("workflow", "team-flow"),
            ):
                code, output = _run("new", kind, name)
                self.assertEqual(0, code, output)
        narrowing = home / "standards" / "market-brief" / "STANDARD.md"
        narrowing.parent.mkdir(parents=True, exist_ok=True)
        narrowing.write_text(NARROWING, encoding="utf-8")
        return home

    def _check(self, home: Path, *argv):
        elsewhere = home / "nowhere"
        with patch.object(rings.Path, "cwd", return_value=elsewhere), \
                patch.object(orchflows.Path, "cwd", return_value=elsewhere):
            return _run("check", *argv)

    def test_a_scaffolded_home_ring_passes_every_item_check(self):
        with _home() as home:
            self._ring(home)

            code, output = self._check(home, str(home))

            self.assertEqual(0, code, output)
            self.assertNotIn("ERROR", output)
            self.assertIn(f"ring: {home}", output)
            self.assertIn("skill 1, standard 2, workflow 1", output)

    def test_a_narrowing_may_use_a_workspace_heading(self):
        """Heading names do not mechanically partition root and narrowing prose."""

        with _home() as home:
            self._ring(home)
            manifest = home / "standards" / "market-brief" / "STANDARD.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "\n## Workspace\n\nMine.\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(0, code, output)
            self.assertNotIn("'## Workspace' is a root's", output)

    def test_a_workflow_body_over_the_tier_budget_is_refused(self):
        with _home() as home:
            self._ring(home)
            manifest = home / "workflows" / "team-flow" / "SKILL.md"
            padding = " ".join(["padding"] * (BODY_BUDGET["workflows"] + 1))
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "\n" + padding + "\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("workflows/team-flow/SKILL.md", output)
            self.assertIn(
                f"exceeds the workflow-tier budget of {BODY_BUDGET['workflows']}",
                output,
            )

    def test_a_call_edge_that_resolves_to_nothing_is_refused(self):
        """A ring item's edges point out of the ring, so the checker grades
        them against every name that resolves from here. The library verb
        both bodies name has to pass on the same reading that refuses the
        typo beside it, or the check would be measuring the ring alone."""

        with _home() as home:
            self._ring(home)
            manifest = home / "workflows" / "team-flow" / "SKILL.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8")
                + "\nCalls `orch-do` and `orch-nonesuch`.\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn(
                "backtick reference `orch-nonesuch` does not resolve", output,
            )
            self.assertNotIn("`orch-do` does not resolve", output)

    def _private_workflow(self, package: Path, name: str) -> Path:
        manifest = package / "workflows" / name / "SKILL.md"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_bytes(dict(
            orchflows_scaffold.files_for("workflow", name)
        )["SKILL.md"].encode("utf-8"))
        return manifest

    def test_a_workflow_package_accepts_private_items_and_resources(self):
        with _home() as home:
            self._ring(home)
            package = home / "workflows" / "team-flow"
            self._private_workflow(package, "helper")
            skill = package / "skills" / "method" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_bytes(dict(
                orchflows_scaffold.files_for("skill", "method")
            )["SKILL.md"].encode("utf-8"))
            local = package / "standards" / "local-brief" / "STANDARD.md"
            local.parent.mkdir(parents=True)
            local.write_text(
                NARROWING.replace("market-brief", "local-brief"),
                encoding="utf-8",
            )
            (package / "references").mkdir()
            (package / "references" / "case.json").write_text(
                '{"expected":"ok"}\n', encoding="utf-8",
            )
            (package / "scripts").mkdir()
            (package / "scripts" / "probe.py").write_text(
                "print('ok')\n", encoding="utf-8",
            )
            public = package / "SKILL.md"
            public.write_text(
                public.read_text(encoding="utf-8").replace(
                    "Never:",
                    "    tickets.py frame-open <run> --parent <frame> "
                    "--goal-file <goal> --workflow helper\n\n"
                    "    tickets.py do <run> --standard local-brief "
                    "--parent <frame> --goal-file <goal>\n\nNever:",
                )
                + "\n[Fixture](references/case.json) and "
                  "[probe](scripts/probe.py).\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(0, code, output)
            self.assertNotIn("ERROR", output)
            self.assertIn("dynamic or implied prose calls are unchecked", output)

    def test_an_obsolete_literal_workflow_flag_is_refused(self):
        with _home() as home:
            self._ring(home)
            manifest = home / "workflows" / "team-flow" / "SKILL.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "tickets.py do", "python scripts/tickets.py do",
                ).replace(
                    "--standard <standard>", "--pack old-pack",
                )
                + "\nRun `tickets.py do <run> --sheet old-sheet "
                  "--goal-file <goal>` only as a migration example.\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("obsolete flag --pack", output)
            self.assertIn("obsolete flag --sheet", output)

    def test_an_unresolved_literal_private_name_is_refused(self):
        with _home() as home:
            self._ring(home)
            manifest = home / "workflows" / "team-flow" / "SKILL.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "Never:",
                    "    tickets.py frame-open <run> --parent <frame> "
                    "--goal-file <goal> --workflow absent-helper\n\nNever:",
                ),
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("literal --workflow name does not resolve", output)
            self.assertIn("absent-helper", output)

    def test_a_literal_private_workflow_cycle_is_refused(self):
        with _home() as home:
            self._ring(home)
            package = home / "workflows" / "team-flow"
            left = self._private_workflow(package, "left")
            right = self._private_workflow(package, "right")
            for manifest, target in ((left, "right"), (right, "left")):
                manifest.write_text(
                    manifest.read_text(encoding="utf-8").replace(
                        "Never:",
                        "    tickets.py frame-open <run> --parent <frame> "
                        f"--goal-file <goal> --workflow {target}\n\nNever:",
                    ),
                    encoding="utf-8",
                )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("literal workflow call cycle", output)
            self.assertIn("workflows/left/SKILL.md", output.replace("\\", "/"))

    def test_a_package_link_cannot_escape_its_public_owner(self):
        with _home() as home:
            self._ring(home)
            manifest = home / "workflows" / "team-flow" / "SKILL.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8")
                + "\n[escape](../outside.md)\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("workflow package link escapes its public owner", output)

    def test_a_private_manifest_link_cannot_escape_its_public_owner(self):
        with _home() as home:
            self._ring(home)
            package = home / "workflows" / "team-flow"
            skill = package / "skills" / "method" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                dict(orchflows_scaffold.files_for("skill", "method"))["SKILL.md"]
                + "\n[escape](../../../../outside.md)\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("workflow package link escapes its public owner", output)

    def test_the_ring_defaults_to_this_project_then_the_home_ring(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            self._ring(home)
            project = Path(raw).resolve()
            (project / ".git").mkdir(parents=True)
            (project / ".orchflows" / "skills").mkdir(parents=True)

            code, at_home = self._check(home)
            self.assertEqual(0, code, at_home)
            self.assertIn(f"ring: {home}", at_home)

            with patch.object(rings.Path, "cwd", return_value=project), \
                    patch.object(orchflows.Path, "cwd", return_value=project):
                code, in_project = _run("check")

            self.assertEqual(0, code, in_project)
            self.assertIn(f"ring: {project / '.orchflows'}", in_project)

    def test_a_directory_holding_a_ring_is_read_as_that_ring(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            project = Path(raw).resolve()
            (project / ".orchflows" / "workflows").mkdir(parents=True)

            code, output = self._check(home, str(project))

            self.assertEqual(0, code, output)
            self.assertIn(f"ring: {project / '.orchflows'}", output)

    def test_a_ring_that_is_not_there_is_named_rather_than_passed(self):
        with _home() as home:
            missing = home / "no-such-ring"

            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir(exist_ok=True)
                code = orchflows.main(["check", str(missing)])

            self.assertEqual(1, code)

    # --- the role a `--skill` dispatch reads ---------------------------

    def test_the_scaffold_declares_the_role_a_dispatch_will_establish(self):
        """A ring skill is only ever entered through `--skill`, which reads
        `role:` to establish the child. The scaffold and the checker have to
        agree about that field or `orchflows new skill` writes an item its
        own checker refuses -- the pass case above is that agreement read
        from the checker's side, and this is it from the scaffold's."""

        with _home() as home:
            self._ring(home)

            frontmatter = (home / "skills" / "helper" / "SKILL.md").read_text(
                encoding="utf-8",
            )

            self.assertIn("\nrole: worker\n", frontmatter)

    def test_a_ring_skill_without_a_role_is_refused_by_name(self):
        with _home() as home:
            self._ring(home)
            manifest = home / "skills" / "helper" / "SKILL.md"
            manifest.write_text(
                "".join(
                    line
                    for line in manifest.read_text(encoding="utf-8").splitlines(True)
                    if not line.startswith("role:")
                ),
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("skills/helper/SKILL.md", output)
            self.assertIn("frontmatter missing required key 'role'", output)

    def test_a_ring_skill_declaring_role_none_is_refused(self):
        """`rules/roles.md` clause 6 refuses a `role: none` skill at
        dispatch, so a checker that admitted one would hand back a pass the
        run then contradicts. The library's own set carries `none`; the
        applied set is the two a child can be established as."""

        with _home() as home:
            self._ring(home)
            manifest = home / "skills" / "helper" / "SKILL.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "role: worker", "role: none",
                ),
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("role 'none' is not one of ['planner', 'worker']", output)

    # --- running an item's own probe is running its content -----------

    def test_an_untrusted_project_ring_gets_the_remedy_and_runs_no_probe(self):
        """Resolving a name is inert; a probe is the item's own command. A
        project ring reaches its user's agents only after they say so, so a
        probe there waits for the same grant `orchflows sync` waits for, and
        says so in that verb's own sentence."""

        with _home(), tempfile.TemporaryDirectory() as raw:
            project = Path(raw).resolve()
            bundle = project / rings.BUNDLE_DIR
            (bundle / "workflows").mkdir(parents=True)
            orchflows_scaffold.write(bundle / "workflows", "workflow", "team-flow")
            marker = project / "probe-ran"
            (bundle / "workflows" / "team-flow" / "tools.txt").write_text(
                _probe(marker), encoding="utf-8",
            )

            with patch.object(rings.Path, "cwd", return_value=project), \
                    patch.object(orchflows.Path, "cwd", return_value=project):
                code, untrusted = _run("check")
                self.assertFalse(marker.exists(), untrusted)
                rings_trust.grant(bundle)
                trusted_code, trusted = _run("check")

            self.assertEqual(0, code, untrusted)
            self.assertIn("orchflows trust", untrusted)
            self.assertEqual(0, trusted_code, trusted)
            self.assertTrue(marker.exists(), trusted)

    def test_a_directory_named_on_the_command_line_runs_no_probe(self):
        """`check <dir>` grades whatever directory it is handed, which is
        any bundle at all -- one someone cloned to look at before deciding
        anything. Its content is nobody's until they say so, so it takes
        the same remedy the untrusted project ring takes, while the home
        ring, which is the user's own directory, has its probe run."""

        with _home() as home, tempfile.TemporaryDirectory() as raw:
            (home / "nowhere").mkdir()
            stranger = Path(raw).resolve()
            (stranger / "workflows").mkdir()
            orchflows_scaffold.write(stranger / "workflows", "workflow", "team-flow")
            theirs = stranger / "probe-ran"
            (stranger / "workflows" / "team-flow" / "tools.txt").write_text(
                _probe(theirs), encoding="utf-8",
            )
            (home / "workflows").mkdir()
            orchflows_scaffold.write(home / "workflows", "workflow", "team-flow")
            ours = home / "probe-ran"
            (home / "workflows" / "team-flow" / "tools.txt").write_text(
                _probe(ours), encoding="utf-8",
            )

            code, output = self._check(home, str(stranger))
            own_code, own = self._check(home, str(home))

            self.assertEqual(0, code, output)
            self.assertFalse(theirs.exists(), output)
            self.assertIn("orchflows trust", output)
            self.assertEqual(0, own_code, own)
            self.assertTrue(ours.exists(), own)

    def test_a_directory_probes_once_its_own_bundle_is_trusted(self):
        """The sentence the case above prints is a remedy, and a remedy
        names a command that changes the answer. The ledger keys a grant by
        bundle path, and the path the reader was handed the sentence about
        is the path `check` graded, so the two meet."""

        with _home() as home, tempfile.TemporaryDirectory() as raw:
            (home / "nowhere").mkdir()
            stranger = Path(raw).resolve()
            (stranger / "workflows").mkdir()
            orchflows_scaffold.write(stranger / "workflows", "workflow", "team-flow")
            marker = stranger / "probe-ran"
            (stranger / "workflows" / "team-flow" / "tools.txt").write_text(
                _probe(marker), encoding="utf-8",
            )

            rings_trust.grant(stranger)
            code, output = self._check(home, str(stranger))

            self.assertEqual(0, code, output)
            self.assertTrue(marker.exists(), output)
            self.assertNotIn("orchflows trust", output)

    def test_an_imported_bundle_probes_without_a_grant(self):
        """`orchflows sync` asks the ledger about the project ring and no
        other: an import is pinned by `imports.lock`, which is the
        acceptance (`rings._trust_state`'s "inherent"). One bundle cannot be
        content the user accepted at one door and a stranger at the other."""

        with _home() as home:
            (home / "nowhere").mkdir()
            bundle = home / rings.IMPORTS_DIR / "kit" / rings.BUNDLE_DIR
            (bundle / "workflows").mkdir(parents=True)
            orchflows_scaffold.write(bundle / "workflows", "workflow", "team-flow")
            marker = bundle / "probe-ran"
            (bundle / "workflows" / "team-flow" / "tools.txt").write_text(
                _probe(marker), encoding="utf-8",
            )
            rings.imports_lock_path(home).write_text(
                json.dumps({"imports": [{"name": "kit", "url": "", "pin": ""}]}),
                encoding="utf-8",
            )

            code, output = self._check(home, str(bundle))

            self.assertEqual(0, code, output)
            self.assertTrue(marker.exists(), output)
            self.assertNotIn("orchflows trust", output)

    def test_a_refused_standard_declaration_is_never_probed(self):
        """A standard has no code of its own, so `validate_standards` refuses
        the file's existence rather than reading it. Resolving what it
        declares anyway would run the content of an item the checker has
        already ruled cannot carry any."""

        with _home() as home:
            self._ring(home)
            marker = home / "probe-ran"
            (home / rings.RING_DIRS["standard"] / "market-brief" / "tools.txt").write_text(
                _probe(marker), encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("a standard has no code of its own", output)
            self.assertFalse(marker.exists(), output)

    # --- the bundle's own manifest -------------------------------------

    def _bundle(self, home: Path) -> Path:
        """The scaffolded manifest at the ring's root."""

        with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
            code, output = _run("new", "bundle", "demo-bundle")
        self.assertEqual(0, code, output)
        return home / rings.BUNDLE_MANIFEST

    def test_a_bundle_manifest_missing_a_required_key_is_refused(self):
        with _home() as home:
            self._ring(home)
            manifest = self._bundle(home)
            manifest.write_text(
                "".join(
                    line
                    for line in manifest.read_text(encoding="utf-8").splitlines(True)
                    if not line.startswith("version:")
                ),
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn(rings.BUNDLE_MANIFEST, output)
            self.assertIn("bundle manifest missing required key 'version'", output)

    def test_a_requires_entry_that_is_not_pinned_is_refused(self):
        """`add` refuses an unpinned requirement after the clone that
        reached it. This is the same refusal where its author is standing,
        and it is the written shape only: whether a remote publishes that
        pin as a tag needs a network, which a checker does not have."""

        with _home() as home:
            self._ring(home)
            manifest = self._bundle(home)
            scaffolded = manifest.read_text(encoding="utf-8")

            manifest.write_text(
                scaffolded.replace(
                    "requires: []", "requires: [https://example.invalid/kit.git]",
                ),
                encoding="utf-8",
            )
            code, unpinned = self._check(home, str(home))

            manifest.write_text(
                scaffolded.replace(
                    "requires: []",
                    "requires: [https://example.invalid/kit.git@v1.0.0]",
                ),
                encoding="utf-8",
            )
            pinned_code, pinned = self._check(home, str(home))

            self.assertEqual(1, code, unpinned)
            self.assertIn("which is not a pinned bundle", unpinned)
            self.assertEqual(0, pinned_code, pinned)

    def test_a_ring_with_no_manifest_is_skipped_rather_than_refused(self):
        """`contracts/bundle.md`: a bundle without a manifest is a bundle
        with no requirements, so an absent one is a fact. Saying so is the
        compiler's own skipped wording, not silence."""

        with _home() as home:
            self._ring(home)

            code, output = self._check(home, str(home))

            self.assertEqual(0, code, output)
            self.assertIn("{}: {}".format(rings.BUNDLE_MANIFEST, SKIPPED), output)


if __name__ == "__main__":
    unittest.main()
