Unit U7a: Sheets `market-brief`, `html-dossier`, `sheet-craft`

Spec: research/workflow-ladder-spec-2026-09-02.md. Read section 0 (decisions), section 2 (fixed names) and section 3 U7a. The decisions in section 0 are closed: where one looks wrong, report the observation in `## Report` and continue.

Files under `sheets/`. Knowledge only. The super-research report rules are absorbed by `html-dossier`.

Done: `python tools/validate.py && python tools/run_tests.py --scope sheets tests && python install.py --dry-run`

The mechanical `done` that `land` runs in the integrated tree is `uv run --no-project python tools/run_required.py`; run it yourself before closing. Anything in Done beyond that command is what the judge reads in your `## Report`: cite the frame id, file, or command output that shows it.

Report: every file touched, every test added or changed, every name from section 2 you used, and any deviation from this unit's Details with the observation that forced it.
