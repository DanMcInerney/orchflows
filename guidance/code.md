# Code

## Make

Start from observable behavior and the interfaces callers already use. Trace the relevant path before changing it; preserve compatibility unless the requested change intentionally alters it. Make failure behavior as deliberate as the happy path, especially at input, permission, persistence and concurrency boundaries.

Prefer the smallest coherent change that fits the surrounding code. Keep ownership and data flow easy to follow. Introduce an abstraction when it removes a recurring source of mistakes. Treat dependencies, migrations and generated output as part of the change.

Check behavior where a user or caller can observe it. A useful regression test fails for the original defect and survives reasonable refactoring. Exercise the relevant integration and failure paths; distinguish checks actually run from assumptions. Explain material tradeoffs or migration needs.

## Review

Look first for incorrect outcomes, security defects, data loss, broken callers and regressions. Follow a concrete input through the changed behavior; inspect both successful and unsuccessful cases. Check whether tests can detect the claimed defect rather than merely echoing the implementation.

Assess maintainability through likely changes: can a reader find the owner of a behavior and modify it without coordinating scattered copies? Identify defects with a location, trigger and consequence. Separate correctness findings from optional style preferences, and account for what the available checks leave unobserved.
