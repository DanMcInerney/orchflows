# Workspace establishment

The host owns creation and entry into a required Git candidate. The caller
then invokes `tickets.py dispatch <run> <id>` from that candidate (or supplies
`--workspace <path>`); the facade runs `workspace.py start` and carries its
recorded `workspace_path` into packet projection. For an evidence-store
adapter, the same call may run from any directory and creates the canonical
run-scoped store. Packet projection refuses a missing, different, or
unavailable required workspace, and the join grader rejects a Git branch
relocated from its recorded path.
