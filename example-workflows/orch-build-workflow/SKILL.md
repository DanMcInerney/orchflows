---
name: orch-build-workflow
description: Create or improve one scoped workflow package with independent authoring review and observed disposable-project admission.
disable-model-invocation: true
---

Require: `request`, one workflow package's intended behavior; `workspace`, its
git source repository; `scope`; `authoring-owner`,
the applicable authoring guidance; `bound`, each call's budget; and
`admission`, the static check command, disposable git project, concrete runtime
request and invocation inputs, and external output probe. Unresolved inputs
remain explicit gaps until settled.

Write the authoring-owner pointer into a Context file.

    tickets.py frame-open <run> --goal-file <authoring-goal> --workflow orch-build-workflow
      --context-file <authoring-context>

Invoke `checkpointed-build` with `goal` = request at scope, including the
contract inventory and package boundary from the
[authoring procedure](../../docs/custom-workflow-authoring.md#procedure),
static admission, and preservation of authoring-owner in every governed Context;
`workspace` = workspace; `standard` = orch-workflow-authoring;
`judge-standard` = orch-workflow-authoring; `narrowings` = [];
`bound` = bound; `context-file` = authoring-context; and
`probe` = admission's static check command.

Against its fixed returned package, invoke the produced workflow's actual
named body on admission's disposable project and runtime request. Use ordinary
trust, package pinning, dispatch and landing doors. Run the external output
probe outside its children, observing failure for absent or corrupt output
and success for the actual result. For a small authoring request with a
concrete probe, read [the dogfood fixture](references/dogfood.md).

Never: substitute static checks or synthetic ticket records for live
invocation; claim success after failed admission, unresolved names, stale pins,
or a blocked judge; broaden scope or install source globally as admission;
or copy the called workflow's orchestration into this body.

Return: `tickets.py frame-close <run> <frame> --done <output-probe>`;
the fixed package's `artifact: git:<tip>`, independent `findings:` line,
runtime run/frame/ticket identities and standard pins, landed runtime artifact,
observed command exits, and gaps (`[]` when none). Unavailable live admission
returns the partial package and its evidence gap under
[composition](../../rules/composition.md) §8.
