"""Which project a run belongs to, and who may write to it.

The state sink is user-scope: one ``tickets/`` and one ``runs/`` tree for
every project on the host.  That is the architecture the host block
mandates, and its one exposure is that a run is reachable from checkouts
that have nothing to do with it.  Nothing mechanical asserted the
boundary, so three separable failures all arrived through it -- a
packet-less fork scavenged the sink and matched another project's
pending ticket, a claim was attempted from the sibling checkout of the
project holding the run's baseline, and a run was attributed to whichever
session wrote to the sink first while its tickets named a different
repository.

Two laws live here, and they are two.  *Attribution* names the run's
project from its ROOT TICKET's workspace, so the cut decides and the
caller's directory never does.  *Admission* compares a writing
workspace's project against the recorded one and refuses a mismatch, so
a context standing in the wrong checkout is stopped at the door rather
than discovered later by a baseline that will not resolve.

The claim path lived here too, for the same reason, until the dispatch-v1
cutover made ``dispatch-open`` the one door that takes a ticket. What
remains is the law both doors read.
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
    """Return no semantic override; issuance records the writer's project.

    Context is intentionally unstructured and cannot be promoted into
    system authority. The run identity written at issuance is therefore
    the sole project binding.
    """
    del run
    return None
def recorded_project(run: str):
    """The project a run's identity records, or ``None`` when it records none.

    ``None`` covers three cases that are one case to a caller: no sink, no
    identity yet, and a legacy identity written before the field existed.
    In all three there is no recorded fact to compare against, and a
    refusal would be asserting one.
    """
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
    """The one sentence every door refuses a foreign write with.

    One law refusing in three places says so in one voice, and the remedy
    is the half that differs: what a caller should do about it depends on
    which door they were at, and a remedy naming the wrong door is how a
    correct refusal still costs a context its next twenty minutes.
    """
    theirs, mine = (_project_key(recorded), _project_key(writing))
    return (
        f"run '{run}' is held by project {theirs}; this write comes from project "
        f"{mine}. One run id is one project's, so nothing was written. "
        + remedy.format(theirs=theirs)
    )
def binding_refusal(run: str, remedy: str):
    """Refuse this caller's write when its workspace is another project's.

    Structural, and deliberately so: it reads the run's recorded identity
    and the caller's own resolved project, and consults nothing the
    caller supplied.  That is the whole point -- a context with no inputs
    cannot know which project a sink ticket belongs to, so the check
    cannot be one it could satisfy by asserting something.
    """
    recorded = recorded_project(run)
    if recorded is None:
        return None
    writing, _ = _writer_identity()
    if _same_project(recorded, writing):
        return None
    return held_by(run, recorded, writing, remedy)
