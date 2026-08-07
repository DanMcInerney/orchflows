Implements the rejected side of the case's one documented disagreement: an
empty specification raises `ValueError("empty port specification")` instead of
returning `[]`. Every other behavior matches the reference, and the
integration guide states this variant's behavior in as many words, so nothing
in the evidence marks it as a defect -- only the settled boundary does. A
benchmark whose design silently adopted the integration guide scores this
variant clean and the reference broken; a benchmark that never covered the
empty specification at all scores both clean. Catching it requires surfacing
the contradiction as an assumption or gap, settling it with the caller, and
then encoding the settled answer as a case -- which is the whole contradiction
angle.

deviation: contract-substitution
