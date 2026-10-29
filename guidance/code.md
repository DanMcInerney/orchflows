# Code

Split a file when it holds a second concept, not for length alone; about 500 lines is a cue to check. Apply the Single Ownership Principle to code and architecture design: extend the owner rather than adding a parallel copy. Keep each behavior understandable from few files, behind a narrow interface. Add an abstraction only when it removes more complexity than it adds. Use a maintained dependency when it simplifies the implementation.

Change only what the task needs, and report other problems instead of fixing them. Build only what a current caller needs. When replacing code, move its callers and delete the old path; leave no compatibility shims or unused code. Comment only what the code cannot show.

Fix causes, not symptoms, and fail loudly: no silent fallbacks, swallowed errors, retries or defaults that hide a failure. Parse untrusted input into typed data once, at the boundary; inside it, trust the types.

Unit tests matter much less than end-to-end tests. Reproduce a bug end to end before fixing it, and keep the reproduction as a test. Test real behavior through public interfaces; a mock proves only its own assumptions. A change is done when every path to the behavior has it, not just the tested one. Make every test run as fast as possible, and in parallel where possible; wait on observable state, never on sleeps.

## Review

Judge the work as one design, even where parts were made separately. Check that the Single Ownership Principle holds across parts, that contracts, names and error handling agree where parts meet, and that nothing between them is duplicated, worked around or left unowned. Look for changed files that should be split. Recommend removing any added branch, fallback, flag or option the intent does not need, rather than hardening it.

Back each defect with the realistic input or sequence that triggers it, and each structural finding with the sites involved; skip speculation, style and problems that predate the work. List every finding, then look across them for shared causes, such as a missing owner or contract between parts. Where a simplifying architectural change would eliminate a whole class of findings, report the smallest such change, concrete enough to apply without further design, with the findings it resolves. Report a finding on its own only when no shared cause explains it. When nothing qualifies, report none.
