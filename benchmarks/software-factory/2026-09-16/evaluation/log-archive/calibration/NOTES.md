# Calibration evidence

Calibration ran on the provided Windows host with Python 3.14.6. No candidate build arm was consulted. The public starter suite passed 2/2 tests.

The initial calibration caught evaluator/control mechanics problems. `pre-fix-observed-output.txt` preserves captured output excerpts; full initial JSON files had already been overwritten by the corrected run when preservation was requested, so they are unavailable. No missing report fields have been invented.

Three corrections were made before freezing:

1. The evaluator now restores its original working directory before `TemporaryDirectory` cleanup. Windows rejected removing the still-current directory after otherwise successful checks.
2. The positive control no longer compares `st_ctime_ns` between path `stat` and handle `fstat`. On this Python/Windows host these returned different values for a newly written file, forcing unnecessary full reloads. Device, file identity, size, and nanosecond modification time remain in the control signature. This change is confined to the evaluator-only positive control.
3. The concurrent atomic replacement check retries `PermissionError` on Windows while replacement can leave a file briefly pending deletion. This follows the already-published allowance for ordinary OS errors. The retry is bounded, is not used for arbitrary exceptions or non-Windows readers, and does not waive answer checks. All successful overlapping reads must be one complete allowed snapshot; the subsequent read must match the final file. Writers also retry bounded sharing violations.

The frozen API, acceptance behaviors, 30,000-row corpus, paired round design, and 5x target were not weakened. CLI subprocesses disable bytecode writes, and fixtures remain outside candidate directories.

Corrected calibration results:

| Control | Named assertions | Baseline seconds | Candidate seconds | Throughput ratio | Required outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| Full-scan starter | 31/31 | 6.799475400 | 7.214409400 | 0.942485382x | Correct; speed gate fails |
| Independent cached linear-scan control | 31/31 | 6.761973200 | 0.385195700 | 17.554643523x | Correct; speed gate passes |

`starter.json` and `positive-control.json` contain complete corrected reports with individually named assertions and per-round timings. These are calibration results, not results for either comparison arm.
