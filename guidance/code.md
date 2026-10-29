# Code

Prefer code files below roughly 500 lines; split longer changed files at coherent responsibility boundaries when this improves the design. Apply the Single Ownership Principle to code and architecture design. Use a maintained dependency when it simplifies the implementation.

Unit tests matter much less than end-to-end tests. Make every test run as fast as possible, and in parallel where possible.

## Review

Look for coherent splits in oversized changed files, duplicated ownership, and tests coupled through shared state or execution order. Treat file size as a design preference, not an automatic refactoring requirement.

Before reporting, enumerate all findings and make a second pass for shared causes. Report findings with severity, confidence and concrete consequences, leading with high-impact ones and the smallest structural changes that resolve several together.
