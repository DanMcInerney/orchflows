# Role profiles

Host-specific bindings are data in the top-level [host records](../../../../hosts/).
The checkout's host renderer produces the adapters installation consumes; those records
own managed markers, installed-item locations, legal frontmatter, launch verbs and
native fields, role-to-profile mappings, and native-versus-requested capabilities.

The starting agent is the orchestrator; only children use profiles. These
invariants apply on every host:

- Resolve the declared role through the selected host adapter and use its exact
  launch binding. Never substitute a blocked model or profile.
- A native capability is established only through the adapter's native launch
  field. A requested capability rides the prompt and is noted unverified; the
  request alone never becomes evidence that the host established it.
- The caller commits one attempt and its immutable packet before launch. The
  established child runs `dispatch-receive` against its actual name, role,
  profile, reply target, and workspace authority before the exact skill runs.
  A disagreement is the return; neither side edits packet fields to make them
  agree.
- Child names are unique within a run, and a resumed child keeps its name.
- Notifications do not decide lane progress. The caller rechecks durable run
  state against the lane bound and holds any launched external process until its
  outcome lands in durable state or is recorded at launch.
- Terminal required checks run once in the engine's context against the accepted
  terminal identity, and their verdict records that revision.
