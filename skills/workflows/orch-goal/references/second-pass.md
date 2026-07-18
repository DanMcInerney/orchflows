# Goal second-pass design

Freeze the original request and original spec identities before the
first delivery. They remain the goal; neither first-pass output nor the
replacement spec may override the request.

After the first delivery, converge its durable evidence into one packet:

- delivery status, result identity, changed artifacts, and final verdicts;
- uncovered remainder, decision gap, queued scope, and gate feedback;
- failed approaches, discovered constraints, problems, and workarounds,
  each cited to the result or worklog identity that shows it;
- remaining bound.

Carry identities, verdicts, and decisions, never transcript prose. Omit
anything the workspace can derive before re-specification. First-pass
claims without evidence remain assumptions, never new constraints.

The second orch-spec pass receives the exact original request as its
request, access to the delivery workspace, and the original spec plus
this packet as evidence. It preserves the original objective, non-goals,
and binding constraints unless the original request and cited evidence
require a change; discovered scope stays queued. It writes a new spec
identity with a new run id, the original pack, `pattern: deliver`, and
the budget reserved for delivery 2. Its returned decisions name each
change from the original spec and cite the packet evidence that required
it.
