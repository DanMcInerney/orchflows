# Planted defect: state leaks into a file the teardown never reaches

Every write also lands in `.store-shadow.json` beside the module, and a load
that finds the state file missing or empty silently recovers from that shadow
instead of starting empty. Within one run nothing looks wrong: the first
command reads an absent state file with no shadow yet on disk, every later
command reads the real state file, and the whole scenario — get on an empty
store, put, overwrite, delete, delete again — passes exactly as the reference
does. **This seed passes a naive single-run check.** It fails only across two
runs: remove the state file, which is the tool's entire documented state, run
the same scenario again from what should be clean state, and the second run's
`list` on an empty store prints the previous run's surviving key. The failure
is not in any single command's behaviour; it is in the disagreement between
run one and run two. A quality benchmark for a stateful target must therefore
build isolation into the harness rather than into an assertion: fix the state
location, tear it down, and require two consecutive suite runs from clean
state to produce the same transcript. A benchmark that runs its suite once —
however thorough that one pass is — certifies this seed as correct, and the
leak surfaces later as a test that passes alone and fails in a second run, or
passes on a fresh machine and fails on a developer's.

deviation: side-channel-state
