Unit U7b: `checkpointed-build`

Spec: research/workflow-ladder-spec-2026-09-02.md. Read section 0 (decisions), section 2 (fixed names) and section 3 U7b. The decisions in section 0 are closed: where one looks wrong, report the observation in `## Report` and continue.

Domain-blind. Nearest bodies: the render→judge→repair tail of `C:\Users\danhm\.orchflows\workflows\tiktok-video\SKILL.md` and the vampire-fps build run `20260902T150541Z-vampire-fps-build`. `rules/topology.md` §5, §8.

Done: `python tools/validate.py && python tools/run_tests.py --scope skills,tests`, plus one scratch run on a fixture (a two-file repository with a failing test and a probe that runs it) whose frame closes `complete`.

The mechanical `done` that `land` runs in the integrated tree is `uv run --no-project python tools/run_required.py`; run it yourself before closing. Anything in Done beyond that command is what the judge reads in your `## Report`: cite the frame id, file, or command output that shows it.

Report: every file touched, every test added or changed, every name from section 2 you used, and any deviation from this unit's Details with the observation that forced it.
