# Role profiles

What binds a role to a concrete model and effort on one host, and how that
binding changes.

The binding itself is data in the host records beside this file —
one record per host, owning its launch verb and native fields, its role-to-profile
mapping, the model and effort per role, its managed markers, installed-item
locations, legal frontmatter, and its native-versus-requested capabilities. This
file names no model, effort, or agent: change a binding by editing that host's
record, then regenerate the derived adapters with
`uv run --no-project python tools/regen.py`.

`tickets.py dispatch --host <host>` resolves the role against that record and
returns the resolved binding as its `launch` object. The starting agent is the
orchestrator; only children carry profiles.

- Invoke the emitted `launch` verbatim. Never substitute a blocked model or
  profile, and never retype a field the launch already carries.
- The granular `dispatch-open`, `dispatch-retire`, and `dispatch-replace`
  operations stay public for recovery; reach for them when a transaction has to
  be resumed, never to hand-assemble one that would have succeeded. A lost
  launch comes back from replaying the same `dispatch` call.
- A native capability is established only through the adapter's native launch
  field. A requested capability rides the prompt and is noted unverified; the
  request alone never becomes evidence that the host established it.
- Child names are unique within a run, and a resumed child keeps its name.
- Notifications do not decide lane progress. The caller rechecks durable run
  state against the lane bound and holds any launched external process until its
  outcome lands in durable state or is recorded at launch.
