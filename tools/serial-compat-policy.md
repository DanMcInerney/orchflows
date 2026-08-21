# Serial compatibility proving policy

- `status`: `experimental`
- `selected-command`: `python tools/run_serial_compat.py --mode selected`
- `required-fallback`: `python -m unittest discover -s tests -v`
- `automated-pair`: scheduled/manual, Windows and POSIX, selected plus exhaustive
- `promotion-pairs`: `20` consecutive clean pairs with identical discovery identity
- `discrepancy`: `selected-green/exhaustive-red` resets the proving streak
- `rollback`: restore exhaustive feedback while repairing the manifest or sentinels
- `cold-trials`: two green observations at one revision
- `timing-target`: median at most `90s`; each at most `100s`
- `timing-fallback`: report the miss and use `120s`; never claim the target

All behavioral cases remain in `tools/run_tests.py`. Promotion changes feedback
policy only after the paired gate; exhaustive serial remains scheduled/manual
and available for pre-release use.
