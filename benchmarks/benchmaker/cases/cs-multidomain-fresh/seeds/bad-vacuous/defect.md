# bad-vacuous (inert)

The intended behavior — document-domain verification — is absent.
The doc-domain cases still exist, still execute the implementation,
and still appear in scoring as required, but the runner's
`check_doc` was emptied: it returns no problems for any output, so
every doc case passes for every implementation. The doc half of the
package is inert; only the code checks can fail anything. The
code-correct/doc-broken inner variant consequently passes, which is
the observable behavior change proving this variant is not
equivalent (under the reference package it fails on structure and
voice).

Freshness: oracle-vacuity was burned at the composition-target
aggregate-gate locus in the predecessor set; the changelog
doc-domain check block is a new locus.

deviation: oracle-vacuity @ doc-domain checks (check_doc accepts any text)
