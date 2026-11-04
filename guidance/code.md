# Code

Split a file when it holds a second concept; at about 500 lines, check. Apply the Single Ownership Principle in code and architecture: extend the owner instead of adding a parallel copy. Keep each behavior understandable from few files, behind a narrow interface. Add an abstraction only when it removes more complexity than it adds. Use a maintained dependency when it simplifies the code.

Change only what the task needs; report other problems instead of fixing them. Build only what a current caller needs. When replacing code, move its callers and delete the old path: no compatibility shims or dead code. Comment only what the code cannot show.

Fix causes, not symptoms. Fail loudly: no fallbacks, swallowed errors, retries or defaults that hide a failure. Parse untrusted input into types once, at the boundary; trust them inside.

Take each test's expected result from a source independent of the code under test: the requirement, what the test planted, a trusted implementation, the replaced version, another path that must agree, a law every input obeys (round trip, invariant, metamorphic relation), or a simple model run in lockstep. Never copy expectations from the code's output or state, or assert that it calls what it calls. Check laws and models over many generated inputs or operation sequences, and statistical behavior as rates over labelled cases. Code that judges, such as a checker, scorer or detector, must accept what the requirement allows and reject planted wrong answers.

Unit tests matter much less than end-to-end tests. Test the real program through its public interfaces under real conditions: its platforms, recorded real data, noise, load, timing and malformed input. A mock or fake proves only its own assumptions: build it from the real thing's recorded behavior, limits and errors included, and recheck it against the real thing when available. A unit test earns its place only where a law or reference checks a boundary end-to-end tests reach poorly.

Trust only tests you have seen fail: reproduce a bug end to end before fixing it and keep the reproduction; break what a new test covers. Loosen, retry, narrow, re-record, skip or delete a test only with evidence its expectation was wrong, and say so. A change is done when every path to the behavior has it, not just the tested one. Make tests as fast as possible and parallel; wait on observable state or a controlled clock, never on sleeps.

## Review

Judge the work as one design, even where parts were made separately. Check that single ownership holds across parts, that contracts, names and error handling agree where parts meet, and that nothing between them is duplicated, worked around or unowned. Flag changed files that should be split. Recommend removing, not hardening, any added branch, fallback, flag or option the intent does not need. Treat the maker's tests as claims: break covered behavior in a scratch copy to confirm they fail, and check consequential behavior yourself against the requirement.

Back each defect with a realistic triggering input or sequence, and each structural finding with its sites; skip speculation, style and pre-existing problems. List every finding, then look for shared causes, such as a missing owner or contract between parts. Where one simplifying architectural change would eliminate a class of findings, report the smallest such change, concrete enough to apply without further design, with the findings it resolves; report a finding alone only when no shared cause explains it. When nothing qualifies, report none.
