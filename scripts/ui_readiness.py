"""Pure causal readiness explanations shared by lifecycle and reader UI."""

from __future__ import annotations

try:
    from scripts.tickets_format import TERMINAL_STATES, VALID_STATUSES
    from scripts.tickets_lifecycle import readiness_facts
except ImportError:
    from tickets_format import TERMINAL_STATES, VALID_STATUSES
    from tickets_lifecycle import readiness_facts


def explain_ticket(ticket: dict, tickets: dict) -> dict:
    """Explain one ticket from canonical status and dependency facts.

    The projection is reversible: it carries the canonical status through its
    wording and names every causal dependency. It does not invent a phase.
    """

    ticket_id = str(ticket.get("id") or "unknown")
    status = str(ticket.get("status") or "")
    facts = readiness_facts(ticket, tickets)
    dependencies = facts["dangling"] + facts["incomplete"]
    if not facts["status_valid"]:
        state = "unknown"
        explanation = "{0} has unknown status {1}".format(ticket_id, status or "unset")
    elif facts["dangling"]:
        state = "attention"
        explanation = "{0} names missing dependencies: {1}".format(
            ticket_id, ", ".join(facts["dangling"])
        )
    elif status == "complete":
        state = "complete"
        explanation = "{0} is complete".format(ticket_id)
    elif status in TERMINAL_STATES:
        state = "attention"
        explanation = "{0} ended with status {1}".format(ticket_id, status)
    elif status == "claimed":
        state = "running"
        explanation = "{0} is claimed".format(ticket_id)
    elif status == "suspended":
        state = "attention"
        explanation = "{0} is suspended".format(ticket_id)
    elif facts["incomplete"]:
        state = "waiting"
        explanation = "{0} waits for: {1}".format(ticket_id, ", ".join(facts["incomplete"]))
    elif status in ("pending", "ready"):
        state = "ready"
        explanation = "{0} has complete dependencies and is eligible".format(ticket_id)
    else:
        state = "unknown"
        explanation = "{0} cannot be classified from status {1}".format(ticket_id, status)
    return {
        "state": state,
        "dependencies": dependencies,
        "explanation": explanation,
    }


def explain_run(tickets) -> dict:
    """Return one explanation per readable ticket, keyed by canonical id."""

    indexed = {
        str(ticket.get("id") or "unknown"): ticket
        for ticket in tickets
        if "error" not in ticket
    }
    return {
        ticket_id: explain_ticket(ticket, indexed)
        for ticket_id, ticket in indexed.items()
    }
