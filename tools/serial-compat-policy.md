# Serial compatibility proving policy

- `status`: `experimental`
- `selected-command`: `python tools/run_serial_compat.py --mode selected`
- `required-fallback`: `python -m unittest discover -s tests -v`
- `automated-pair`: scheduled/manual, Windows and POSIX, selected plus exhaustive
- `promotion-pairs`: `20` unique, consecutive clean pairs with identical discovery and sentinel-manifest identities
- `accumulator`: on the default branch, the separate workflow restores the prior fail-closed gate, adds both host pairs, uploads the new gate, and saves it for the next run
- `discrepancy`: every unclean, malformed, duplicated, or contract-changing pair resets the proving streak; `selected-green/exhaustive-red` is called out explicitly
- `promotion-action`: `promotion_ready` is evidence for a reviewed feedback-policy change; the workflow never edits required checks
- `rollback`: after promotion, any streak reset sets `rollback_required`; restore exhaustive required feedback before repairing the manifest or sentinels
- `history-loss`: missing current evidence or malformed cached history fails closed and cannot authorize promotion
- `cold-trials`: two green observations at one revision
- `timing-target`: median at most `90s`; each at most `100s`
- `timing-fallback`: report the miss and use `120s`; never claim the target

All behavioral cases remain in `tools/run_tests.py`. Promotion changes feedback
policy only after the paired gate; exhaustive serial remains scheduled/manual
and available for pre-release use. The existing checks workflow and its status
topology remain unchanged throughout proving; promotion or rollback is a separate,
reviewed policy change.
