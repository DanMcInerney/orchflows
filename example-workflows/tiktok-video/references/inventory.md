# Package inventory and boundary evidence

The public contract is tiktok-video. Its canonical source is
example-workflows/tiktok-video/SKILL.md; discovery reads that physical owner.
No legacy pack, mandatory variant count or fixed cut quota is retained.

| Contract | Actual consumer and reason |
| --- | --- |
| orch-do and orch-judge with orch-research (existing primitives and standard) | tiktok-video owns market/reference and renderer lanes plus independent coverage review. Separate evidence packets permit parallel work and reuse with provenance; the judge covers their joined decision handoff. No acquisition method or document-format dependency is added. |
| video-direction (private workflow) | tiktok-video fixes an independently reviewed original document before expensive rendering. Its independent journal can return useful partial direction. |
| video-production (private workflow) | tiktok-video hands it the actual accepted document and findings. It owns isolated rendered output and audiovisual review/repair; its semantic input does not depend on the direction helper's layout. |
| orch-do and orch-judge (existing primitives) | Direction uses orch-content plus video-script-quality; production uses orch-code plus video-quality. They retain their ordinary landing and evidence contracts. |
| render-video (private applied skill) | Production making consumes the frame-driven rendering and measured-caption method. |
| video-script-quality and video-quality (private narrowings) | Direction and production maker/judge pairs respectively share these exact pins. Script originality/timing and rendered audiovisual quality have different artifact seams. |

No new research wrapper, planner, generic engine, role or base adapter is needed.
Checkpointed-build and orch-build-workflow are existing package-authoring and
admission workflows, not extra layers of a video invocation.

## Contained resources and dependency identity

- [creative](creative.md): semantic document handoff, evidence use and outside
  document/review integrity command.
- [renderer](renderer.md): qualified copy/render/voice route, actual foundation
  probe readings and frozen provenance; [review](review.md): independent
  audiovisual evidence and technical output settings.
- [scaffold manifest](scaffold/package.json) and [lock](scaffold/package-lock.json):
  artifact dependencies, copied with index.tsx, phrases.json, local font/license
  and browser/font/model provenance from that directory into the produced root.
- [render boundary](../scripts/scaffold/render.cjs) and
  [voice boundary](../scripts/scaffold/voice.mjs): also copied into that artifact
  root. Their bytes are unchanged by package integration; they are kept under
  scripts to satisfy canonical executable-resource placement.
- [probe](../scripts/probe.py): package-owned standard-library Python command
  using the produced project's exact local Remotion CLI. It imports no extra
  Python dependency; tools.txt declares node and npm.
- [admission](admission.md): concrete static and later external commands, live
  request, remaining runtime obligations and gap handling.

The artifact lock pins Remotion/@remotion 4.0.522, React/React DOM 19.2.8,
Kokoro.js 1.2.1 and transformers 3.8.1. Browser/font/model/stock-voice hashes are
separate provenance because npm integrity does not freeze those downloads.
Do not install the artifact lock into the workflow package as its environment.
Resolve the package's interpreter with `orchflows env workflow tiktok-video`.
The existing method is qualified for Remotion on Windows; HyperFrames is an
unexecuted alternative requiring a separately qualified boundary if selected.

## Discovery and host adapters

Canonical installer discovery automatically includes this top-level owner.
Generated Claude skill, Codex prompt/redirect skill and Grok skill adapters point
to it without a child-role binding. Nested video-direction, video-production,
render-video and both standards stay absent from global catalogs/adapters and
resolve only through the public owner's package scope. Do not hand-write adapters.
The reader's closed summary manifest and canonical ID set include tiktok-video;
its compact graph shows research, direction and production. README is not an
exhaustive workflow registry, so no new README index is required.

Tests of discovery, literal resolution, contained references
and mutations establish static behavior, not execution of the prose. The later
admission record must identify the accepted source commit, fixed copied package,
generated adapter paths, run/frame/tickets, shared maker/judge standard digests,
landed artifacts, independent findings and observed external probe exits.
