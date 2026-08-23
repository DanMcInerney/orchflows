# Serial compatibility policy

- Routine: `python tools/run_serial_compat.py --mode selected`
- Coverage: the exact discovery manifest, 14 sentinels, and nine guarded process seams
- Timing target: two cold runs, median at most `90s` and each at most `100s`
- Fallback: `python tools/run_serial_compat.py --mode exhaustive`
- Fallback use: scheduled, manual, and pre-release
- Regeneration: `python tools/run_serial_compat.py --write-manifest` rewrites
  the discovery block and the mutation-owner inventory from the tree; the
  sentinel roster is chosen, not derived, so regeneration proves it survived
  byte-for-byte and aborts if it did not; a newly detected owner lands
  unclassified until a reviewer rules its `restoration`

The separate Ubuntu/Windows workflow runs both modes and uploads their raw,
revision-stamped timing records. The existing checks workflow stays unchanged.
