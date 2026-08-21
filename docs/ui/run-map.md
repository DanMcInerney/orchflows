# Run map

Run map is the read-only execution detail owned by Now. It is the sole full execution graph: compact Now summaries link here instead of recreating its ticket topology. It starts with compact, reversible readiness summaries and expands in place until every canonical ticket dependency is visible. It never creates a phase taxonomy, changes graph state, invokes lifecycle commands, or exposes ticket and transcript contents outside the closed experience projection.

## Disclosure model

The view has four levels. Level 0 lists runs and one compact activity macro for each run. Level 1 groups the selected run by the canonical readiness states supplied by the reader. Each group names its member ticket ids and canonical lifecycle statuses, so the summary can be reversed without inventing a phase. Level 2 shows either those groups collapsed or the complete ticket graph. Level 3 adds a persistent inspector for a selected group or ticket.

Moving between levels keeps the run, search, filter, live or paused mode, selected group or ticket, and React Flow viewport in the same mounted view. Groups bundle edges only while collapsed. Expanded mode emits one edge for every `depends_on` entry, including an edge to an explicit missing-dependency node when its source ticket is absent. Selecting a ticket preserves that complete graph while the inspector names its upstream dependencies, its immediate downstream work, and its present canonical state.

The UI-neutral `web/src/shared/routes/executionRoutes.ts` owns canonical run and ticket path matching and construction. The run-map route delegates to that owner, and every selected ticket inspector exposes a descriptive native link to `/runs/{run}/tickets/{ticket}` while preserving the fixture query used by deterministic captures. Run and ticket descendants keep Now active in the application rail.

## Reader contract

The live view reads `snapshot.runs`, `snapshot.run`, and each closed `TicketSummary`. Ticket identity, lifecycle status, executor, bound, claim metadata, `depends_on`, unreadability, and canonical readiness are inert display inputs. The UI does not parse markdown or call a lifecycle command.

`Why waiting?` is constrained to the reader's canonical readiness seam. The causal focus follows only readiness dependencies, highlights the shortest projected chain, and cites the projected explanation. A graph dependency that the readiness projection does not name is never promoted into a waiting cause. Cause labels distinguish pending dependencies, suspended handoffs, failed or blocked upstream work, stale claims explicitly named by the reader, and malformed topology.

The deterministic manifest fixture parameter changes only capture data and initial disclosure. It does not affect a live projection or introduce a browser mutation route.

## Diagnostics

The accurate graph preserves canonical edges and displays cycles, dangling dependencies, duplicate ids, unreadable tickets, and inferred session links as diagnostics. An inferred session link is labeled as inferred and never rendered as a canonical dependency. Diagnostics remain visible when filters reduce the graph because filtering must not make malformed source state look healthy.

## Controls and accessibility

Search matches a plain ticket id or executor label. Filters are `Active`, `Problems`, `Ready now`, `Critical path`, and `All`. Pan, zoom, fit, minimap, graph nodes, edges, disclosure breadcrumbs, group expansion, causal focus, pause or resume, and inspector close are keyboard reachable and carry accessible names and state.

The minimap is derived from the exact visible graph projection and draws every
visible node and dependency edge; it never substitutes an unlabelled viewport
slab for topology. Its accessible name reports the same node and edge counts.

Every status uses a glyph, word, and border in addition to its token color. Causal mode strengthens the focused edge and node borders while retaining labels; forced-colors replaces dimming with dashed irrelevant topology. Reduced-motion removes animated edge behavior. At compact width, the inspector moves before the graph, filters scroll without clipping, and the navigation and graph remain usable at 200 percent zoom.

The view uses only the platform's frozen color, spacing, radius, row-height, type, and focus tokens. Monospace is limited to ticket and run identities and exact causal evidence.

## Verification identities

The owned identities are `summary-active`, `full-collapsed`, `full-expanded`, `blocked-causal`, `completed`, and `malformed-topology` at `wide` and `compact`. Fresh captures are evidence only. They remain `no-golden` until a user explicitly approves each identity.
