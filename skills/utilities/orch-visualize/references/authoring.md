# Authoring (consulted once at open)

## Subject preparation

For a skill or workflow subject, resolve every backticked call
recursively; stop on a missing dependency or cycle and say so.
Preserve across the page what the subject states: order, branches,
parallel lanes, loop bounds and exits, failure returns. Conditional
or weak edges dotted; defect edges red; cycles as real back-edges.

## Form ladder — first form that fits wins

1. Two facts or fewer → a sentence. Strict linear order → a numbered
   list.
2. Lookup values, heterogeneous units, or more than ~20 densely
   related entities → a table.
3. Conditions × outcomes → a decision table, conditions as rows.
4. Otherwise a diagram typed by the dominant relationship: branching
   process → `flowchart` · modes and transitions → `stateDiagram-v2` ·
   ordered actor exchanges → `sequenceDiagram` · entities and
   cardinality → `erDiagram` / `classDiagram` · chronology →
   `timeline` or kit timeline · containment → kit boxes · comparison
   → kit table · quantitative data → `vega-lite`.

An arrow is legal only when its edge can be named — calls, causes,
flows-to, precedes, depends-on — and that name is the edge label.
No diagram is a valid outcome.

## Mermaid

Core types only: flowchart, sequenceDiagram, stateDiagram-v2,
classDiagram, erDiagram, timeline, pie, gantt — the lint rejects the
rest. On flowchart and state, lead the fence with ELK frontmatter
(hosts without the plugin fall back to dagre, so layout is never
load-bearing):

    ---
    config:
      layout: elk
    ---

Labels verb-object within the lint's word budget, quoted when
punctuated. Decision branches always labeled `|so|`. Subgraphs flat
within the lint's depth budget, single-line titles, no `direction`
when any member links outside. classDef within the lint's count
budget; color marks structure, meaning never rides color alone. One
direction per diagram.

## Staging

One diagram when the whole subject passes the lint. Otherwise an
overview within the lint's overview budget, in the subject's own
vocabulary — a declarative-sentence title, expandable nodes marked
with one shared classDef, omission free, false order or linkage
forbidden — then one detail panel per marked node: same node ids,
same direction, opening line naming its overview node and neighbors.
Split an oversized detail sideways at the same level, never into a
third level down.

## Kit classes (`viz-html` fences)

`viz-steps` ordered step cards · `viz-timeline` dated rail ·
`viz-compare` comparison table · `viz-boxes` nested containment ·
`viz-callout` one annotation. Plain nested `div`/`table`/`ol`
markup carrying these classes; headings and short text only; no
inline styles, no scripts, no external resources.

## Look pass

After rendering, list defects — clipped or overlapping text, edges
through nodes, crossings a reorder removes, mixed directions, a
panel contradicting the overview — then fix exactly that list.
Never rate the page, never redraw a visual with no listed defect.
