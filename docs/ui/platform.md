# UI platform

The UI platform is a local, read-only projection of orchflows state. It
provides a stable browser and JSON boundary for the visual experience without
making a browser a second workflow engine. The state sink remains the source
of truth, and its records remain untrusted data under
[visibility law](../../rules/visibility.md) §6.

## Run the reader

From a source checkout, run:

    uv run --no-project python scripts/ui.py

After a user install, run the same installed facade with the private runtime:

    $HOME/.orchflows/runtime/bin/python $HOME/.orchflows/bin/ui.py

On Windows PowerShell, the equivalent is:

    & "$HOME\.orchflows\runtime\Scripts\python.exe" "$HOME\.orchflows\bin\ui.py"

The reader prints its URL and binds `127.0.0.1:8787`. `--port 0` selects a
free loopback port. `--root` selects another state sink; otherwise
`scripts/state_root.py` resolves the per-user sink. `--transcripts` selects a
Claude Code project-transcript root; otherwise the reader looks under
`~/.claude/projects`. A missing transcript root produces an explicit empty
projection.

## Dependency and compatibility contract

The installed reader uses Python 3.9 or newer. `requirements-runtime.in` owns
the two direct server pins, Starlette 0.49.3 and Uvicorn 0.34.3;
`requirements-runtime.txt` owns their fully pinned, hash-locked transitive
closure. `pyproject.toml` mirrors the direct pins for repository tooling. The
versions deliberately retain the Python 3.9 floor and are compatibility debt,
not an invitation to raise that floor during an unrelated UI change.

The browser application uses React 19, React Flow, and ELK for the graph seam,
with Radix primitives and Lucide icons. Node 20.19 or newer and pnpm 10.32.1
are development inputs only. An installed user never needs Node, pnpm, npm, or
a frontend build. [Third-party notices](../../THIRD_PARTY_NOTICES.md) records
the version, source, license, and distributed artifact for every shipped
browser and Python dependency, including elkjs under its EPL-2.0 option.

## Immutable asset lifecycle

`web/src` is the authored TypeScript source. The lockfile and Vite build
produce `web/dist`: one index, one Vite manifest, and content-hashed local
scripts, styles, and workers. The committed distribution has no source maps,
remote URLs, or view-time network dependency. Maintainers verify it with:

    uv run --no-project python tools/ui_frontend.py verify-build
    uv run --no-project python tools/ui_frontend.py audit-licenses
    uv run --no-project python tools/ui_frontend.py smoke

A user install stages the distribution, checks its manifest identity, then
creates, reuses, or repairs `~/.orchflows/ui`. The receipt records each asset
and the distribution identity. User installation is the only installation
scope. Uninstall removes only unchanged receipted assets and leaves modified
or out-of-bound paths for review.

Fresh installation may access the configured Python package index because
this repository ships no wheelhouse. After installation the reader is
offline: it serves the installed immutable assets and reads local state only.

## HTTP and API boundary

`scripts/ui.py` is the public CLI. Its Starlette application is served by
Uvicorn from a socket pre-bound to `127.0.0.1`; a small standard-library
compatibility server preserves the same contract when the facade is imported
outside the installed runtime. Both accept only `GET` and `HEAD`, reject
non-loopback host headers, enable no CORS middleware, and attach restrictive
CSP, frame, origin, referrer, and content-type headers to every response.

The same-origin routes are:

| route | projection |
|---|---|
| `/` and `/assets/*` | immutable browser distribution |
| `/api/v1/runs` | run summaries and lifecycle-status counts |
| `/api/v1/runs/{run}` | one canonical dependency graph and run diagnostics |
| `/api/v1/runs/{run}/tickets/{ticket}` | one closed ticket summary plus linked-friction count |
| `/api/v1/runs/{run}/tickets/{ticket}/artifacts` | canonical structured result identities available to the ticket |
| `/api/v1/runs/{run}/tickets/{ticket}/artifacts/{artifact_id}` | one contained, redacted artifact selected by opaque ID |
| `/api/v1/friction` | aggregate friction health |
| `/api/v1/sessions` | session metadata summaries |
| `/api/v1/sessions/{session}` | session and subagent structure metadata |
| `/api/v1/experience` | closed `orchflows.experience.v1` shell, selection, readiness, and safe view projection |
| `/api/observe` | minimal graph snapshot used by the first browser shell |

Successful JSON and asset responses carry content-derived ETags. The browser
uses `If-None-Match`; unchanged resources return `304`, while hashed assets
also carry immutable caching. The earlier `/ticket`, `/graph`, `/friction`,
`/sessions`, and `/session` links redirect to equivalent application URLs
when their target still exists.

The browser owns semantic, refresh-safe application routes at `/now`,
`/runs/{run}`, `/runs/{run}/tickets/{ticket}`, `/sessions`,
`/sessions/{session}`, and `/friction`. The persistent information
architecture is exactly **Now / Workflows / Create / Sessions / Friction**.
Execution run and ticket descendants keep Now active in the rail. Definition
detail and contained source descendants remain Workflows-owned. Create is
visibly disabled and reserved for future workflow authoring; this observer
exposes no creation or mutation route.

## Projection and privacy boundary

All projections use closed field sets. Run graphs contain ticket identifiers,
dependency edges, lifecycle statuses, aggregate diagnostics, and event
counts. The selected-ticket experience projection contains routing and claim
metadata, canonical readiness facts, parsed verification rows, and the
Goal, Context, Suggested files, Result, Feedback, and Risks sections as inert strings. A run is
associated with a workflow definition only through an explicit canonical
association; the reader never infers one from a run slug or executor. Judgment
detail mechanically presents criterion, verdict, oracle, class, evidence,
Result, Feedback, Risks, and an explicit rationale identity when one exists;
it authors no rationale and labels an absent identity unavailable. Artifact
inventory accepts only canonical structured result identities that resolve
inside the state sink. Prose-only or unresolved artifacts remain unavailable,
and caller-supplied project or workspace paths are never followed. Artifact
IDs are opaque; list and detail responses preserve `GET`/`HEAD` parity,
containment, redaction, content-derived ETags, and generic errors. The explicit
`raw` field is the one narrow exception for the selected ticket's Markdown:
the server redacts host paths before delivery and the browser renders the
string inert. Session projections
contain file identity metadata and subagent parent, depth, activity, evidence,
and readability fields.

No route returns another ticket's body, arbitrary filesystem paths, transcript
text, prompt text, tool input or output, command output, arbitrary file
contents, or subagent conversation contents. The state and transcript roots are opened read-only;
symbolic-link and path-containment checks keep reads inside those roots. No
browser route starts a run, changes a ticket, writes friction, calls a model,
or exposes another mutation endpoint. Ticket lifecycle meanings remain owned
by [the work-item contract](../../contracts/work-item.md); the UI does not
invent a second phase taxonomy.

## Rendered-experience admission

`docs/ui/view-manifest.json` is the canonical `orchflows.view-manifest.v1`
inventory. It declares 62 deterministic identities across Now execution run
maps and ticket details, the Workflows definition catalog, definition detail
and contained source states, Sessions, session graphs, and Friction at
1440×1024 and 1024×768. Its `navigationParents` map makes each view kind's
active rail owner part of the rendered contract without adding an identity.
`tools/ui_frontend.py capture`, `audit`, and `diff` consume that
manifest. Capture writes ephemeral evidence only; audit applies WCAG 2.2 AA
rules plus 200-percent zoom-equivalent reflow, forced-colors, reduced-motion,
and keyboard-reach parity to every identity. Diff exits nonzero on a
missing or changed capture; `no-golden` is explicit and allowed only for
this greenfield foundation until a separate owner admits goldens.

`web/src/styles/tokens.css` is the single carrier for the closed type-size
scale and shared privacy, status-border, radius, spacing, surface, and focus
decisions. Feature CSS consumes those names rather than spelling synonyms.

## Successor boundary

This platform now owns the secure data seam, frozen dark shell and tokens,
semantic router, closed experience contract, shared read-only graph
primitives, deterministic fixtures, and rendered-experience harness. Feature
view behavior—exact Now, Workflows, ticket, Sessions, session-graph, and
Friction treatments—belongs to the dependent view tickets. Workflow creation,
provider calls, authentication, and run initiation require a later product
specification.
