# Delegation packet — benchmark the echo-transform CLI

This packet is complete: all six parts are present and no synthesis is
supplied, so the run must acquire under the research charter.

objective: Build and qualify one immutable runnable benchmark for the echo-transform CLI (target identity et-cli@sha256:e31fa920, opaque to the run) whose intended observable outcome is: given one line of text on argv and one transform flag, the CLI prints the transformed line to stdout and exits 0; unknown flags exit 2.

inputs: the interface facts stated in this packet; vendor changelog excerpts quoted in the run's own acquire lane work; no supplied synthesis; source policy: local evidence only, no network, no target mutation; judgment permission: deterministic oracles only; applicable packs: orch-research-pack for acquisition, orch-code-pack for materialization.

authority: write scope limited to the run workspace's record/ and package/ trees; excluded actions: mutating the target, generating candidates, comparing candidates, calling evolve, promoting or activating anything.

bounds: 40 units total across all stages; expected execution cost 6 units; unused stage allocation carries forward.

return_contract: status, benchmark identity, qualification, gaps, bounds spent, changed artifacts — and the run record among the returned artifacts.

reply_to: main
