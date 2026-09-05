# 4. Profiles, inline work, and host entry

## Goal

High-level `do` and `judge` calls may select an existing host-bound planner or worker profile independently of the operation. One ordinary assignment may perform coherent sequential making and local review in one context and workspace. A separate fresh assignment remains the boundary for independent acceptance.

## Owners and changes

`tickets_mint` exposes the profile choice already present in lower dispatch plumbing as an optional `--profile` on `do` and `judge`. An explicit choice wins. Without one, worker for `do` and planner for `judge` remain preferences for compatibility; they are not authority rules. Planner-do and worker-judge are legal. Unknown or decorative profiles refuse unless the selected host record contains a real binding.

The ticket pins the selected profile name and host record identity. The host adapter remains the sole owner of native agent/profile fields, model, effort, service tier, and launch syntax. Generic skills and workflow prose name planner or worker intent, not host model identifiers. The adapter emits only fields the current host surface accepts and reports an unsupported binding before launch. Existing host records are tested only where their host is available; this stage adds no Pi or Antigravity implementation.

Kernel and role documentation remove statements that couple making to worker authority or judging to planner authority. They also remove the contradictory single-kind and one-adapter prose that prevents an ordinary assignment from keeping one workspace while it makes compatible outputs and inspects them locally. This is a contract correction around existing free-form Details and ticket execution, not a grouped-work runtime.

One assignment may describe sequential steps, share context and the execution-owned workspace chosen in stage 2, and state which subset of its pinned standards applies to each step. It produces one durable result and does not mint per-step tickets, switch models mid-run, or pretend that local review is independent. A change in writer ownership, isolation, parallelism, or required independence uses another ordinary ticket.

Host entry tests verify that the emitted launch invokes the resolved profile through the selected host's real adapter, carries the ticket and workspace identities, and forwards the ordinary result protocol. Stale attempts, unsupported fields, and mismatched host bindings keep their existing refusal and recovery paths.

## Exclusions

Do not add personas, model names to generic workflow prose, per-step tickets, a steps file, a grouped-execution engine, runtime model switching, or automatic planner stages. Do not weaken stale-writer, workspace ownership, result provenance, or independent review requirements.

## Observable proof

Focused tests cover default behavior, explicit planner-do, explicit worker-judge, missing host binding, unsupported native field, unchanged legacy calls, and prompt/launch agreement. A host matrix records available surfaces and marks unavailable ones as untested rather than successful.

For inline work, mint one ordinary assignment whose prose makes a small code-and-document artifact, checks it locally, and applies different subsets from an already pinned orthogonal standard list. Observe one dispatch, one context, one derived workspace, and one result. Then give the landed identities to a fresh ordinary judge under the other profile. The first result may report local findings; only the second is independent acceptance.

Acceptance requires the focused mint, roles, kernel, dispatch, host-adapter, result, and workspace tests, the sequential-work dogfood, and the repository required checks once at the stage tip.
