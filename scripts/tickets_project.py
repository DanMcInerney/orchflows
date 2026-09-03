"""Which project a run belongs to, and who may write to it.

The sink is user-scope, so a run is reachable from checkouts that have
nothing to do with it. Attribution names the run's project from its ROOT
TICKET's workspace, so the cut decides and the caller's directory never
does. Admission compares a writing workspace's project against the
recorded one and refuses a mismatch at the boundary.
"""

from __future__ import annotations
from pathlib import Path
try:
    from scripts import state_root
except ImportError:
    import state_root
if __package__:
    from .tickets_store import RUN_IDENTITY_NAME, _origin_url, _project_key, _read_identity, _runs_root, _same_project, _writer_identity
else:
    from tickets_store import RUN_IDENTITY_NAME, _origin_url, _project_key, _read_identity, _runs_root, _same_project, _writer_identity
CLAIM_REMEDY = 'Claim it from a workspace of {theirs}'
TERMINAL_REMEDY = 'Record it from a workspace of {theirs}'
CREATE_REMEDY = 'Use a different run id, or write from a workspace of {theirs}'
def root_ticket_project(run: str):
    """Return no semantic override; issuance records the writer's project."""
    del run
    return None
def recorded_project(run: str):
    """The project a run's identity records, else ``None`` -- no sink, no
    identity yet, or a legacy identity: three cases with no recorded fact
    to compare against, which is one case to a caller."""
    runs_root = _runs_root()
    if runs_root is None:
        return None
    existing, error = _read_identity(runs_root / run / RUN_IDENTITY_NAME)
    if error is not None or not isinstance(existing, dict):
        return None
    recorded = existing.get('project')
    if isinstance(recorded, dict) and (recorded.get('root') or recorded.get('origin')):
        return recorded
    return None
def held_by(run: str, recorded: dict, writing: dict, remedy: str) -> str:
    """The one sentence every command refuses a foreign write with; the
    remedy is the half that differs, so each caller supplies its own."""
    theirs, mine = (_project_key(recorded), _project_key(writing))
    return (
        f"run '{run}' is held by project {theirs}; this write comes from project "
        f"{mine}. One run id is one project's, so nothing was written. "
        + remedy.format(theirs=theirs)
    )
def binding_refusal(run: str, remedy: str):
    """Refuse this caller's write when its workspace is another project's."""
    recorded = recorded_project(run)
    if recorded is None:
        return None
    writing, _ = _writer_identity()
    if _same_project(recorded, writing):
        return None
    return held_by(run, recorded, writing, remedy)
