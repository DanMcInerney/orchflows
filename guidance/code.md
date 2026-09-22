# Code

Prefer code files below roughly 500 lines; split longer changed files at coherent responsibility boundaries when this improves the design. Give each behavior one owner. Use a maintained dependency when it simplifies the implementation.

Design tests to run independently and in parallel, with isolated state and fixtures. Test observable behavior rather than implementation structure.

## Review

Look for coherent splits in oversized changed files, duplicated ownership, and tests coupled through shared state or execution order. Treat file size as a design preference, not an automatic refactoring requirement.

Before reporting, enumerate all findings and make a second pass for shared causes. Report findings with severity, confidence and concrete consequences, leading with high-impact ones and the smallest structural changes that resolve several together.
