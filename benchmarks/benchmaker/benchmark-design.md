# Benchmark design rationale

Design revision: 2026-09-07. This document explains the current source
workflow's design choices; it is not a benchmark standard.
[Benchmark quality](../../example-workflows/benchmaker/standards/benchmark-quality/STANDARD.md)
and [benchmark evidence](../../example-workflows/benchmaker/standards/benchmark-evidence/STANDARD.md)
own mandatory quality, and [benchmaker](../../example-workflows/benchmaker/SKILL.md)
owns the public sequence.

The earlier numerical survey claims in this file were not independently
reproduced for this rebuild and are no longer presented as current guidance.
[FINDINGS-FIELD.md](FINDINGS-FIELD.md) remains a historical evidence register.
The committed cases, reference packages and historical measurements retain
their identities and original contracts.

## Validity and difficulty

The workflow treats validity and target difficulty as different findings.
Known-good, inert and near-miss controls establish harness discrimination;
independent prompt-first reference work investigates whether the specification
and grader agree. Neither establishes how a real target agent performs.
A valid instrument may be too easy or too hard for its declared purpose.

The default inclusive 30–50% pass@1 band is the user's calibration requirement
for one pinned target configuration, not a universal literature threshold.
Configuration includes the model, effort, harness, permissions, context and
resource limits. Optional comparisons use separate configuration records;
they cannot replace the reference target midway through development.

## Development and final evaluation

Construction fixes the construct, coverage, source mappings, visible contracts
and sampling/revision policy before attempts. Calibration can revise development
cases within that declared budget after evidence-backed diagnosis and independent
requalification. A low score alone does not establish useful difficulty.
Coverage and the target configuration remain fixed across that bounded process.

An eligible development result freezes the evaluation at a git revision.
Final measurement records score and drift separately; it cannot trigger an
in-place revision of the frozen cases, grader or policy. A changed benchmark
needs a new version and fresh evaluation. These distinct phases replace the
old unsupported universal prohibition against calibrating to a target.

## Evidence and uncertainty

Actual native attempts retain their prompts, transcripts, submitted artifacts,
grader observations, resolved configuration evidence and exclusions.
Controls and event fixtures stay explicitly classified as harness evidence.
Per-case trial counts, outcomes and failure classes accompany the finite-suite
estimate. Repeated trials of one case do not create independent cases.

Band observation, validity and calibration decision remain separate.
An in-band point estimate does not resolve missing required evidence or
uncertainty. Tiny purposive suites can report descriptive performance while
leaving population generalization unverified. See the
[record dictionary](../../example-workflows/benchmaker/references/calibration-record.md)
for the owned representation.

## Protection and compatibility

A sibling directory or read-only sandbox alone does not establish that a
candidate cannot read answers. Protected final claims need observed access
controls and adversarial evidence; otherwise confirmation is public/development
evidence with an explicit protection gap.

The sixteen source cases exercise historical contract and harness behavior.
Their reference/control variants are not native target measurements, and a
legacy validator pass does not imply empirical calibration. No historical
case, measurement row or scoring rule was rewritten for the new workflow.
The [manifest profiles](../../example-workflows/benchmaker/references/manifest.md)
retain this compatibility boundary.
