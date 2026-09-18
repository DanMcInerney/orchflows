# Example libraries

Run a complete recipe, invoke a component, or reuse its guidance. Save custom libraries under `~/.orchflows/libraries/`, defaulting to `personal`. Core `orch-build-workflow` creates and trials compositions.

| Library | Useful components and process |
| --- | --- |
| [Shared](shared/README.md) | Independently compare stable candidates |
| [Social search](social-search/README.md) | Collect assigned source scopes; rank supplied evidence; coordinate adaptive collection |
| [Research acquire](research-acquire/README.md) | Bounded public-source acquisition and inspectable evidence |
| [Short video](short-video/README.md) | Make a film; review exact exports; coordinate independent films |
| [Browser game](3d-browser-game/README.md) | Make Blender assets; independently playtest; coordinate game production |
| [Design loop](design-loop/README.md) | Brainstorm, research, design, implement, compare and analyze bounded cycles; uses shared comparison |
| [Evolve](evolve/README.md) | Improve and retain artifacts with its own evaluation and confirmation policy |
| [Software factory](software-factory/README.md) | Deliver software; observe production; investigate incidents |
| [Benchmaker](benchmaker/README.md) | Construct and independently pilot benchmarks; review and repair using core |
| [Export workflow](export-workflow/README.md) | Export a standalone native skill and trial its behavior |
| [Self-improve](self-improve/README.md) | Improve instructions from observed history and current evidence |

Domain libraries own their small workflows; `shared/` holds cross-domain processes. Extract components when their contracts help real callers. Core owns ordinary fan-out and gathering.

Workflows preserve order, independence, gates and stops. The orchestrator assigns work under [core execution rules](../docs/architecture.md#execution), preserving specialist reviews and requested repetitions.

An operations brief might compose `research → independent evidence assessment → draft → orchflows:orch-review-revise-once`. Use primitives for simple stages and components whose contracts fit. Prompts supply questions/sources; personal guidance supplies reporting preferences. The [builder trial](shared/trials/build-personal/request.md) exercises this composition.

Install whole packages and declared dependencies using `setup --example NAME` and host registration. Setup installs no transitive dependencies. Keep guidance/references with their packages. Core `docs/home.md` and `docs/hosts.md` cover paths and host limits.
