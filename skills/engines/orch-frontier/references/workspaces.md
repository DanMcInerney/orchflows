# Workspace establishment

The host owns establishment before dispatch. For a required Git candidate it
creates and enters the isolated workspace, then runs `workspace.py start
<run> <id>` there. For an evidence-store adapter, that command may run from
any directory and creates the canonical run-scoped store. Its successful
result records `workspace_path`; use that exact value for `dispatch-packet
--workspace`. Packet projection refuses a missing, different, or unavailable
required workspace, and the join grader rejects a Git branch relocated from
its recorded path.
