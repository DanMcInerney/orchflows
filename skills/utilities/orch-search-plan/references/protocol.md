# Search-plan protocol

The sole command reads one closed UTF-8 JSON request
`{policy, projection, settled, remaining_bound}` and emits one canonical
`search-advance/v1` object plus LF. JSON keys sort lexically; arrays retain the
orders below; integers are JSON integers; dimension values and resolutions are
finite canonical decimal strings. Duplicate keys, unknown fields, floats,
noncanonical decimals, and invalid identities or references are invalid.

## Policy

`search-policy/v1` is closed:

- `identity` is its tagged identity; `planner_revision`,
  `target_owner_identity`, `benchmark_revision`, and `scoring_identity` are
  opaque identities.
- `mutation_surface_identities`, `feedback_source_identities`, and
  `bound_unit_names` are duplicate-free ordered identity lists;
  `ordering_seed` is opaque.
- `dimensions` is ordered. Each closed entry has `identity`, direction
  `maximize|minimize`, candidate-accessible `source_identity`, and positive
  canonical `resolution`.
- positive integer `generation_width`, integer `merge_slots` in its closed
  range, and `reservations:{reflect,merge}`; each reservation is a closed map
  from every bound-unit name to a nonnegative integer.

The policy identity is `sha256:` plus SHA-256 over
`b"search-policy/v1\0" + canonical(payload-without-identity)`.

## Projection and settled outcomes

`projection` is null for the first call, otherwise one closed
`search-projection/v1` carrying `identity`, `policy_identity`,
`benchmark_revision`, `last_settled_generation`, `last_plan`,
`preferred_incumbent_identity`, `nodes`, `archive`, `seen_slot_identities`, and
`incorporated_outcome_identities`. Nodes retain each candidate's full admitted
or nonplanning outcome; archive entries are candidate identities into nodes.

`settled` is the closed wrapper `{preferred_incumbent_identity,outcomes}`.
Every outcome has `kind`, `outcome_identity`, `slot_identity`, and closed `cost`.
An admitted outcome adds `candidate_identity`, ordered `parent_identities`,
owner and surfaces, `benchmark_revision`, fixed result and evidence identities,
`eligibility_status:"PASS"`, eligibility-verdict and score-card identities,
an ordered complete `dimension_vector` of `{identity,value}`, and ordered public
`feedback` entries `{source_identity,dimension_identity,reference_identity}`.
The origin is admitted with null slot and no parents.

A produced ineligible outcome adds candidate and parent identities, owner and
surfaces, benchmark, fixed result and evidence, covered non-PASS eligibility
status and verdict, and fixed `disposition`; it has no planning vector, score
card, or feedback. A no-candidate outcome adds only fixed `disposition` to the
common fields. Missing, duplicate, stale, dangling, or lineage-mismatched
outcomes are invalid. Later calls carry zero or one terminal outcome for every
slot in the prior plan and no other outcome; a partial set is atomically
`pending`.

`remaining_bound` is closed over the policy's ordered bound units with
nonnegative integer values.

## Planning and identities

Resolution-aware Pareto comparison uses every admitted node. For one oriented
dimension delta, `delta >= resolution` is better, `delta <= -resolution` is
worse, and the remainder ties. The archive retains all and only non-dominated
candidate identities. The preferred incumbent may sit outside the archive and
still reflects first.

Reflection slots precede merge slots. Their closed records carry `identity`,
generation, ordinal, kind, ordered parents, focus or complementary dimension
identities, ordered allowed feedback, owner, surfaces, benchmark revision, and
closed reservation. Merge feedback is the ordered union of each parent's
allowed feedback on dimensions where that parent is resolution-better: parent
order, policy dimension order, feedback-source order, then reference identity.
The greedy componentwise prefix of the full ordered slots is returned; no first
fit yields `no_fit` with the updated projection and null `last_plan`.

Tagged identities hash `tag + NUL + canonical(payload-without-identity)`. Slot
payloads depend on no plan or output projection. A plan hashes prior projection,
normalized outcomes, and slots, then the output projection embeds that plan;
this ordering is acyclic. Changing focus or public feedback therefore changes
the slot's mutation-packet identity. Decimal comparison uses exact coefficients,
not ambient fixed precision.

## Result

`search-plan/v1` is closed over `identity`, `policy_identity`,
`benchmark_revision`, `input_projection_identity`, ordered
`basis_outcome_identities`, `generation`, and ordered `slots`.
`search-advance/v1` is closed over `schema`, `status` (`planned|pending|no_fit`),
input and output projection identities, `projection`, `plan`, ordered
`missing_slot_identities`, and bounded machine-readable `diagnostics`.
