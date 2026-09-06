# 2. Standards and workspaces

## Goal

Several compact standards can govern one assignment without also choosing several workspaces. Standards remain domain guidance. Ticket execution derives one workspace mechanism from the concrete workspace or artifact target, while existing tickets and standards keep a compatibility read path.

## Owners and changes

`contracts/standard.md`, `docs/standard-authoring.md`, and validation stop requiring prose under headings that no consumer reads by name. Vocabulary, outline, slice, making, and review remain useful authoring questions: What terms need fixed meanings? What result and constraints matter? What is the smallest useful cut? What domain method should the maker follow? What evidence and defects should the judge examine? A concise standard may answer them in any clear layout. Empty filler is a defect; a missing ceremonial heading is not.

Makers and judges continue to read the full applicable standard text. Existing Lens manifests and their adapter metadata remain readable. References may hold optional depth, but required guidance stays in the compact text passed to both roles. Validation checks identity, frontmatter actually consumed by code, readable content, links, size, and Lens compatibility rather than enforcing a five-section template.

`standards_support` resolves repeatable explicit standard names as orthogonal guidance. A standard may optionally use `narrows` as shorthand for one required base. Resolution expands that base, combines it with explicit names, and emits one stable, ordered, deduplicated pin list using stage 1's canonical tree identity. It rejects cycles, missing bases, and real incompatibilities. It adds no `includes` language or mandatory hierarchy.

`tickets_adapters` owns workspace selection with one precedence rule: an optional explicit adapter wins; otherwise infer from an explicitly supplied workspace or artifact target; when the target is omitted, use one distinct legacy standard hint; otherwise infer from the current directory. A git checkout selects git and a supplied non-git directory can select document-tree. Existing no-workspace evidence calls continue to select evidence-store through their legacy standard hint. Ambiguous inputs or competing hints refuse and name the optional adapter escape hatch. These mechanisms remain distinct because their ownership and lifetime differ, and old tickets keep their compatibility read path.

One assignment selects one execution workspace after standards resolve. Adding an orthogonal standard or another artifact to review does not perform a second selection. Mixed-artifact judge input is allowed when the selected adapter can read every supplied typed identity. Results retain each artifact's identity and provenance; storage is not renamed by deleting evidence.

## Exclusions

Do not require five headings, split quality guidance into adapter fields, create a second standard digest, or add multiple inheritance. Do not choose the last standard's adapter, require callers to restate a derivable adapter, collapse document-tree and evidence-store, or remove legacy readers merely to simplify terminology. Do not make local self-review independent acceptance.

## Observable proof

Focused tests use: a short standard with a non-template layout; an unchanged Lens manifest; two explicit orthogonal standards; one optional narrowing plus its base; duplicates across both forms; and a cycle. The resolved ticket contains each applicable canonical pin once, and both maker and judge prompts carry the complete applicable guidance.

Workspace tests mint ordinary git, supplied-directory, and run-scoped evidence assignments without an explicit adapter and observe the intended `tickets_adapters` choice. An ambiguous fixture refuses with a useful request for the optional escape hatch. A legacy standard hint and old ticket still resolve. A mixed judge reads two artifact kinds from the one selected workspace and records both identities; an unreadable kind refuses without discarding provenance.

A source-backed integration fixture drives one small documentation-and-code change under two orthogonal standards through the maker, land, mixed-judge, and outside-probe boundaries. It records the deduplicated pins, derived adapter, artifact identities, and findings. A live fresh judge is additional evidence when a host is available, not a manufactured requirement. The slice is ready to integrate when its focused standard, adapter, mint, and mixed-artifact tests and outside probe pass.
