# Planted defect: delete masks the key instead of removing it

`delete` writes a `None` tombstone over the value and keeps the key in the
state file; `get` and `list` are taught to treat a tombstone as absent, so the
key convincingly disappears from every read path. The state file, however,
still carries it, and the tool's own membership test still sees it: deleting
the same key a second time reports success where the contract requires exit 1
for a key that is not there. The defect is caught by asking about state after
a mutation rather than only about the mutation's immediate effect — delete,
then delete again, then confirm a key that was never stored also fails. A
quality benchmark for a store must include those follow-up commands, because a
delete that only hides is how a store's state file grows without bound and how
a resurrected key reappears after an unrelated write.

deviation: state-masking
