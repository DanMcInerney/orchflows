# Example libraries

Use a complete recipe, invoke a component independently, or reuse its guidance in your own workflow. Save custom workflows and libraries under `~/.orchflows/libraries/`; `personal` is the default. Core `orch-build-workflow` creates and trials these compositions.

| Library | Useful components and process |
| --- | --- |
| [Shared](shared/README.md) | Compare candidates; independently review and revise once |
| [Social search](social-search/README.md) | Collect assigned source scopes; rank supplied evidence; coordinate adaptive collection |
| [Research acquire](research-acquire/README.md) | Bounded public-source acquisition and inspectable evidence |
| [Short video](short-video/README.md) | Make a film; review exact exports; coordinate independent films |
| [Browser game](3d-browser-game/README.md) | Make Blender assets; independently playtest; coordinate game production |
| [Design loop](design-loop/README.md) | Brainstorm, research, design, implement, compare and analyze bounded cycles; uses shared comparison |
| [Evolve](evolve/README.md) | Improve and retain artifacts with its own evaluation and confirmation policy |
| [Software factory](software-factory/README.md) | Deliver software; observe production; investigate incidents |
| [Benchmaker](benchmaker/README.md) | Construct and pilot benchmarks; uses shared review and revision |
| [Export workflow](export-workflow/README.md) | Export a standalone native skill and trial its behavior |
| [Self-improve](self-improve/README.md) | Improve instructions from observed history and current evidence |

Small workflows live in their owning domain libraries. `shared/` holds actual processes that cross domains, not wrappers around ordinary fan-out or gathering. Add a component when its inputs, outputs and process commitments are useful to callers; there is no tier hierarchy or requirement that every stage become a skill.

Core owns execution rules. The selected workflow preserves order, independence, gates and bounds; the orchestrator chooses task allocation where that workflow permits it. A stage is not an agent. Existing fixed-count recipes retain their contract until explicitly changed and tried.

For each library, install the whole package and its declared dependencies using the checkout's `setup --example NAME` and the host's registration procedure. Setup does not install transitive dependencies. Keep guidance and references with their packages rather than copying bare skill folders. See core `docs/home.md` and `docs/hosts.md` for paths and host limits.
