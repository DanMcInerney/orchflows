"""A smoke that reads a blocked read as the platform's fault.

Written beside the tree and never imported by the package. It makes the one
mistake the captive-portal caveat was written to prevent, in the one way
the code invites:
it branches on ``outcome``. A response this host's network appliance produced
comes back ``failed`` exactly like a platform refusal does, because the outcome
vocabulary has no member for "the origin was never reached" — so an
implementation reading outcomes cannot see the difference, calls the local
block a platform gap, and then revokes the adapter's standing evidence for it.
"""

from super_research import cli


def channel_of(outcome, loss):
    if outcome == "failed":
        return cli.ANSWERED_BY_ORIGIN
    return cli.ANSWERED_BY_ORIGIN


def ledger_after(ledger, observation, at):
    kept = dict(ledger)
    if observation.outcome == "failed":
        kept.pop(observation.adapter_id, None)
        return kept
    if cli.satisfied(observation):
        kept[observation.adapter_id] = at
    return kept
