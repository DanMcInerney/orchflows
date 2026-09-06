# Standard authoring

The practical order for adding domain guidance. The law lives in
[contracts/standard.md](../contracts/standard.md); anatomy and body budgets live
in [rules/composition.md](../rules/composition.md) §5. A standard is ordinary,
nonempty Markdown. Its layout serves readers: the validator does not require a
fixed outline or claim that headings prove semantic coverage.

1. **Choose the admission.** Create a root only for a distinct domain. If the
   guidance tightens one existing domain, declare that single base with
   `narrows:`. Stamp additional independent standards as an explicit list at the
   call site; resolution expands each base broad to narrow, then keeps the first
   occurrence of every standard.
2. **Name the vocabulary.** Decide which domain terms the guidance needs and
   check them against the T0 contracts and [docs/vocabulary.md](vocabulary.md).
   Define only terms that make the later guidance clearer.
3. **Outline the result.** State what a good result contains, the constraints it
   must respect, and the evidence by which a reviewer can assess it. Use any
   headings that make those relationships easy to find.
4. **Find the smallest useful slice.** Explain how to cut one bounded unit of
   work without losing the domain's essential constraints.
5. **Describe making.** Give the maker enough domain method to produce the
   result. Keep project-specific procedure and executable tooling outside the
   standard.
6. **Describe review.** Name meaningful defect classes and the observations or
   checks that expose them. The prose guides agent judgment; the validator only
   checks document structure.
7. **Compress and verify.** Remove repetition, keep the manifest within the word
   ceiling, and resolve it through the same command the verbs use:

   `uv run --no-project python scripts/standards.py resolve <name>`

A preexisting manifest can keep its Lens navigation when it has unique,
nonempty entries. Their names orient readers without declaring artifact
support. Add `adapter:` only when an older caller needs the registered fallback
hint; composition ignores it. The finished standard is one
`standards/<name>/STANDARD.md`, read as a whole.

Close with the admission in
[custom workflow authoring](custom-workflow-authoring.md).
