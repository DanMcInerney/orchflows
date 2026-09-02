"""Grok role-profile admission cases for rendered host adapters."""

import shutil

from ._support import *
from installer import packages as installer_packages


class TestGrokRoleProfiles(unittest.TestCase):
    """A rendered host adapter refuses half a role binding before install."""

    packages = installer_packages

    def setUp(self):
        self._scratch = contextlib.ExitStack()
        self.addCleanup(self._scratch.close)

    def adapters(self, host: str, mutate) -> Path:
        root = Path(self._scratch.enter_context(tempfile.TemporaryDirectory())) / "adapters"
        shutil.copytree(self.packages.HOST_ADAPTERS_DIR, root)
        path = root / f"{host}.json"
        rendered = json.loads(path.read_text(encoding="utf-8"))
        mutate(rendered["host"])
        path.write_text(json.dumps(rendered), encoding="utf-8")
        return root

    def test_every_host_adapter_binds_both_roles(self):
        profiles = self.packages.load_role_profiles()
        self.assertEqual(
            {
                "orch-planner": {
                    "model": "grok-4.6",
                    "effort": "xhigh",
                    "subagent_type": "orch-planner",
                },
                "orch-worker": {
                    "model": "grok-4.6",
                    "effort": "high",
                    "subagent_type": "orch-worker",
                },
            },
            {name: profile["grok"] for name, profile in profiles.items()},
        )
        self.assertEqual(
            {
                "orch-planner": ("gpt-5.6-sol", "ultra", "claude-fable-5-1", "high"),
                "orch-worker": ("gpt-5.6-luna", "xhigh", "claude-opus-5", "high"),
            },
            {
                name: (
                    profile["codex"]["model"],
                    profile["codex"]["model_reasoning_effort"],
                    profile["claude"]["model"],
                    profile["claude"]["effort"],
                )
                for name, profile in profiles.items()
            },
        )

    def test_every_way_a_grok_binding_can_fail_names_the_host(self):
        cases = (
            (lambda binding: binding.pop("effort"), "incomplete Grok binding"),
            (lambda binding: binding.pop("subagent_type"), "incomplete Grok binding"),
            (
                lambda binding: binding.__setitem__("model", "grok-4"),
                "Grok model outside the recorded census for orch-planner: grok-4",
            ),
            (
                lambda binding: binding.__setitem__("model", "claude-opus-5"),
                "Grok model outside the recorded census for orch-planner: claude-opus-5",
            ),
            (
                lambda binding: binding.__setitem__("effort", "ultra"),
                "invalid Grok effort for orch-planner: ultra",
            ),
            (
                lambda binding: binding.__setitem__("effort", "XHIGH"),
                "invalid Grok effort for orch-planner: XHIGH",
            ),
        )
        for mutate, message in cases:
            with self.subTest(message=message):
                adapters = self.adapters(
                    "grok",
                    lambda host, mutate=mutate: mutate(
                        host["role_profiles"]["planner"]["binding"]
                    ),
                )
                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    self.packages.load_role_profiles(adapters)

    def test_two_roles_binding_one_subagent_type_are_refused(self):
        adapters = self.adapters(
            "grok",
            lambda host: host["role_profiles"]["worker"]["binding"].__setitem__(
                "subagent_type", "orch-planner"
            ),
        )
        with self.assertRaisesRegex(
            ValueError, r"duplicate Grok subagent_type: orch-planner"
        ):
            self.packages.load_role_profiles(adapters)

    def test_every_recorded_model_and_effort_is_admitted(self):
        for model in self.packages.GROK_MODEL_CENSUS:
            for effort in self.packages.GROK_EFFORTS:
                with self.subTest(model=model, effort=effort):
                    adapters = self.adapters(
                        "grok",
                        lambda host, model=model, effort=effort: host[
                            "role_profiles"
                        ]["planner"]["binding"].update(
                            {"model": model, "effort": effort}
                        ),
                    )
                    grok = self.packages.load_role_profiles(adapters)["orch-planner"][
                        "grok"
                    ]
                    self.assertEqual((model, effort), (grok["model"], grok["effort"]))

    def test_a_host_that_lost_a_role_profile_is_refused(self):
        adapters = self.adapters(
            "grok", lambda host: host["role_profiles"].pop("planner")
        )
        with self.assertRaisesRegex(ValueError, r"missing role profile for orch-planner"):
            self.packages.load_role_profiles(adapters)

    def test_native_and_requested_capabilities_stay_out_of_role_bindings(self):
        hosts = self.packages.load_host_adapters()
        self.assertEqual("native", hosts["grok"]["capabilities"]["isolation"])
        self.assertEqual("requested", hosts["codex"]["capabilities"]["isolation"])
        self.assertEqual("requested", hosts["claude"]["capabilities"]["isolation"])
        for name, profile in self.packages.load_role_profiles().items():
            with self.subTest(name=name):
                for host in ("codex", "claude", "grok"):
                    self.assertNotIn("isolation", profile[host])
                self.assertNotIn("isolation", self.packages.render_codex_agent(name, profile))
                self.assertNotIn("isolation", self.packages.render_claude_agent(name, profile))
