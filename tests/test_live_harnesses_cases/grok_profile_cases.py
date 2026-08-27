"""Grok role-profile admission cases for `load_role_profiles`.

Its own module and its own registered `TestCase`. As a mixin carried by
`TestCodexLiveProfiles` every Grok case reported under a Codex class
name, so a Grok refusal that broke read as a Codex failure. A class here
still reaches the suite only by being named in the import block at
`tests/test_live_harnesses.py` -- `tools/run_tests.py` shards
`tests/test*.py` alone -- so a class added here without that line is
collected by nothing and reports green without ever running.
"""

from ._support import *
from installer import packages as installer_packages


class TestGrokRoleProfiles(unittest.TestCase):
    """`load_role_profiles` refuses half a host binding rather than ship
    one. These cases hold the Grok column to the standard the Codex and
    Claude columns already meet, hold those two to what they parsed to
    before it existed, and keep `isolation` the ticket's field. Each
    refusal mutates the shipped table in exactly one way, so nothing
    else can be what it reacts to.
    """

    packages = installer_packages
    PLANNER = "model `grok-4.6`, effort `xhigh`, subagent_type `orch-planner`"
    REFUSED = (
        ("model `grok-4.6`", "incomplete Grok binding for orch-planner"),
        ("effort `xhigh`, subagent_type `orch-planner`", "incomplete Grok binding"),
        (PLANNER.replace("grok-4.6", "grok-4"),
         "Grok model outside the recorded census for orch-planner: grok-4"),
        (PLANNER.replace("grok-4.6", "claude-opus-5"), "Grok model outside the"
         " recorded census for orch-planner: claude-opus-5"),
        (PLANNER.replace("xhigh", "ultra"), "invalid Grok effort for orch-planner: ultra"),
        (PLANNER.replace("xhigh", "XHIGH"), "invalid Grok effort for orch-planner: XHIGH"),
    )

    def setUp(self):
        self._scratch = contextlib.ExitStack()
        self.addCleanup(self._scratch.close)

    def table(self, *replacements) -> Path:
        """The shipped table with substrings replaced, on disk."""
        text = self.packages.PROFILES_MD.read_text(encoding="utf-8")
        for old, new in replacements:
            self.assertIn(old, text, old)
            text = text.replace(old, new, 1)
        path = Path(self._scratch.enter_context(tempfile.TemporaryDirectory()))
        (path / "profiles.md").write_text(text, encoding="utf-8")
        return path / "profiles.md"

    def test_every_column_parses_and_grok_is_bound_for_both_roles(self):
        profiles = self.packages.load_role_profiles()
        self.assertEqual(
            {"orch-planner": {"model": "grok-4.6", "effort": "xhigh",
                              "subagent_type": "orch-planner"},
             "orch-worker": {"model": "grok-4.6", "effort": "high",
                             "subagent_type": "orch-worker"}},
            {n: p["grok"] for n, p in profiles.items()})
        self.assertEqual(
            {"orch-planner": ("gpt-5.6-sol", "ultra", "claude-opus-5", "max"),
             "orch-worker": ("gpt-5.6-sol", "high", "claude-opus-5", "high")},
            {n: (p["codex"]["model"], p["codex"]["model_reasoning_effort"],
                 p["claude"]["model"], p["claude"]["effort"])
             for n, p in profiles.items()})

    def test_every_way_a_grok_row_can_fail_is_refused_naming_the_host(self):
        for cell, message in self.REFUSED:
            with self.subTest(cell=cell):
                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    self.packages.load_role_profiles(self.table((self.PLANNER, cell)))

    def test_every_recorded_model_and_effort_is_admitted(self):
        """The census is what `grok models` returned on this host. A
        refusal that rejected what the table records refuses everything."""

        for model in self.packages.GROK_MODEL_CENSUS:
            for effort in self.packages.GROK_EFFORTS:
                with self.subTest(model=model, effort=effort):
                    cell = self.PLANNER.replace("grok-4.6", model).replace("xhigh", effort)
                    grok = self.packages.load_role_profiles(
                        self.table((self.PLANNER, cell)))["orch-planner"]["grok"]
                    self.assertEqual((model, effort), (grok["model"], grok["effort"]))

    def test_a_row_that_lost_its_grok_cell_is_not_read_as_a_row(self):
        """A four-column row is not a row with an empty Grok cell: read
        as one it yields a host binding carrying no model at all."""

        row = next(line for line in self.packages.PROFILES_MD.read_text(
            encoding="utf-8").splitlines() if line.startswith("| `orch-planner` |"))
        with self.assertRaisesRegex(
                ValueError, r"missing role profile row\(s\) for orch-planner"):
            self.packages.load_role_profiles(self.table(
                (row, row[: row.rindex("|", 0, row.rindex("|"))] + " |")))

    def test_isolation_stays_the_tickets_field_on_every_host(self):
        """Grok's `spawn_subagent` takes a native isolation argument, so
        the paragraph records it; no row and no rendered definition binds
        it, which would isolate every child of a role whatever its
        ticket said."""

        paragraph = "\n\n".join(
            block for block in self.packages.PROFILES_MD.read_text(
                encoding="utf-8").split("\n\n")
            if "isolation" in block and not block.lstrip().startswith("|"))
        for recorded in ("spawn_subagent", "Grok", "established at dispatch"):
            self.assertIn(recorded, paragraph)
        for name, profile in self.packages.load_role_profiles().items():
            with self.subTest(name=name):
                for host in ("codex", "claude", "grok"):
                    self.assertNotIn("isolation", profile[host])
                self.assertNotIn("isolation", self.packages.render_codex_agent(name, profile))
                self.assertNotIn("isolation", self.packages.render_claude_agent(name, profile))
