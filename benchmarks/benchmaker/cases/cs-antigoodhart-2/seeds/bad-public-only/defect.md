# Defect: only the public workload class is exercised

The held-back workload class is undiscriminable in this package: the
runner's protected-workload hook is stripped, so no scoring context
can ever load the held-back class; the manifest's protected_evidence
field is null; and no optimization-resistance gap is recorded — the
package silently pretends the second workload class does not exist.
Every public check still passes: the manifest recomputes, digests
verify, and the public inner sweep discriminates the pool. What is
lost is exactly the anti-goodhart guarantee: with only the exhibited
class scored, a candidate optimized against the exhibited tree is
indistinguishable from a correct one, and the package neither
delivers the held-back reach nor declares its absence.

deviation: input-class-drop @ workload-class locus (held-back class undiscriminable, absence undeclared)
