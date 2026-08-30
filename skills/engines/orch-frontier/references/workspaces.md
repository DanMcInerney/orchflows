# Workspace establishment

What `tickets.py dispatch` does about the workspace, and what is left to the
caller.

Inside the dispatch transaction the facade runs `workspace.py establish`. For an
item whose isolation is `required` that creates the derived candidate worktree
at the path and branch
[`scripts/state_root.py`](../../../../scripts/state_root.py) derives from the
run and ticket ids; for an evidence-store adapter it creates the canonical
run-scoped store. The call may run from any directory. Establishment refuses
rather than falling back to the tree the caller happened to stand in, and the
refusal fails the whole dispatch. `--repo <source-tree>` aims it at another
checkout; `--workspace <path>` on `dispatch` names the tree to cut from.

Only establishment's own return reaches the packet. After the run lock is
released, `workspace.py prepare` installs what the recorded workspace declares.
`tickets.py land` retires the derived worktree at the join.

Packet projection refuses a missing, different, or unavailable required
workspace, and the join grader rejects a Git branch relocated from its recorded
path.
