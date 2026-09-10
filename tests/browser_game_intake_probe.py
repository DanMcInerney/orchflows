"""Execute the shipped caller/intake frame commands in a disposable project."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from scripts import state_root, tickets
from tests._repo_root import ROOT
from tools.validate_support.workflows import _commands


def observe_intake_boundary(package: Path) -> dict:
    readings = []
    with tempfile.TemporaryDirectory(prefix="intake-boundary-") as temporary:
        directory = Path(temporary)
        home = directory / "home"
        project = directory / "project"
        project.mkdir()
        copied = home / "workflows" / "3d-browser-game"
        shutil.copytree(package, copied, ignore=shutil.ignore_patterns(
            ".git", "node_modules", "__pycache__", ".venv"))
        goal = project / "goal.md"
        goal.write_text(
            "Observe private intake for a Three.js game brief in this disposable "
            "workspace. Exercise frame ownership only; no production or research.\n",
            encoding="utf-8")
        environment = os.environ.copy()
        environment[state_root.ENV_VAR] = str(home / "state")
        environment[state_root.WORKTREES_ENV_VAR] = str(home / "worktrees")

        def invoke(arguments, expected=0):
            command = [sys.executable, str(ROOT / "scripts" / "tickets.py"), *arguments]
            result = subprocess.run(command, cwd=project, env=environment,
                                    capture_output=True, text=True, timeout=90)
            readings.append({"command": command, "exit": result.returncode,
                             "stdout": result.stdout, "stderr": result.stderr})
            assert result.returncode == expected, readings[-1]
            return json.loads(result.stdout)

        def commands(relative, verb):
            return [command.split()[1:] for command in _commands(
                (copied / relative).read_text(encoding="utf-8"))
                if command.split()[1] == verb]

        def expand(command, **values):
            replacements = {"<run>": "intake-boundary", **values}
            return [replacements.get(value, str(goal) if value.endswith("-goal>")
                                     else value) for value in command]

        public_open = commands("SKILL.md", "frame-open")
        public = invoke(expand(public_open[0]))["frame_open"]
        discovery_command = next(command for command in public_open
                                 if command[command.index("--workflow") + 1] == "discovery")
        discovery = invoke(expand(discovery_command, **{
            "<frame>": public["id"]}))["frame_open"]
        discovery_body = "workflows/discovery/SKILL.md"
        intake_command = next(command for command in commands(discovery_body, "frame-open")
                              if command[command.index("--workflow") + 1] == "brief-intake")
        intake = invoke(expand(intake_command, **{
            "<frame>": discovery["id"]}))["frame_open"]
        helper = "workflows/brief-intake/SKILL.md"
        for command in commands(helper, "frame-open"):
            invoke(expand(command, **{"<frame>": intake["id"]}))

        frame_files = sorted((home / "state/tickets/intake-boundary").glob("*.md"),
                             key=lambda path: path.stem)
        frames = [tickets._parse_frontmatter(path.read_text(encoding="utf-8"))
                  for path in frame_files]
        assert [frame["id"] for frame in frames] == ["B1", "B1.1", "B1.1.1"], frames
        assert {frame["workflow"] for frame in frames} == {"3d-browser-game"}, frames
        assert len({frame["workflow_digest"] for frame in frames}) == 1, frames
        assert [frame["workflow_entry"] for frame in frames] == [
            "SKILL.md", "workflows/discovery/SKILL.md", helper], frames
        closes = [command for command in commands(discovery_body, "frame-close")
                  if "<intake-frame>" in command] + commands(helper, "frame-close")
        assert len(closes) == 1, closes

        output = project / "intake-output.txt"
        probe_script = project / "probe.py"
        probe_script.write_text(
            "from pathlib import Path\n"
            "p = Path(__file__).with_name('intake-output.txt')\n"
            "raise SystemExit(0 if p.is_file() and "
            "p.read_bytes() == b'intake boundary output\\n' else 1)\n",
            encoding="utf-8")
        probe = json.dumps({"form": "command",
                            "value": f'"{sys.executable}" "{probe_script}"'})
        close = expand(closes[0], **{"<intake-frame>": intake["id"],
                                    "<frame>": intake["id"],
                                    "<intake-check>": probe, "<check>": probe})
        for payload in (None, b"corrupt output\n"):
            if payload is not None:
                output.write_bytes(payload)
            invoke(close, expected=1)
            current = tickets._parse_frontmatter(frame_files[-1].read_text(encoding="utf-8"))
            assert current["status"] == "claimed", current
        output.write_bytes(b"intake boundary output\n")
        closed = invoke(close)["frame_close"]
        assert closed["id"] == intake["id"] and closed["done"]["exit"] == 0, closed
        return {"run": "intake-boundary", "frames": frames,
                "close_owner": discovery_body, "frame_close": closed,
                "readings": readings,
                "gaps": ["Only frame control flow and output discrimination executed; "
                         "intake making, research, checkpoint judgment and production did not run."]}
