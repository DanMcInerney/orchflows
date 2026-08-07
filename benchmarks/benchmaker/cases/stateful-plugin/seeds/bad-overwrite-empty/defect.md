# Planted defect (near-miss): overwriting with an empty value is dropped

`put` guards its write with `if value:`, so storing an empty string is treated
as nothing to store and the key silently keeps its previous value. Overwrite
semantics are otherwise exactly right: put, overwrite with a second ordinary
value, read it back, delete, list — every step a benchmark reaches for when it
tests "does put replace" passes, and the guard reads like an ordinary
short-circuit rather than a bug. This is the near-miss: it survives any
scenario whose values are all non-empty, and it fails only at the falsy
boundary, where the empty string is a legitimate value and not a request to do
nothing. A quality benchmark must choose boundary values for a store's own
data — the empty string, and any other value whose truthiness differs from its
presence — because a store that cannot represent an empty value silently
serves stale data to every later read.

deviation: guard-insertion
