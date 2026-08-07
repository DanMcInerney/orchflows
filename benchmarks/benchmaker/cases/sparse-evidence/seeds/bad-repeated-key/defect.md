Near-miss. Masks the first occurrence of each distinct key name and leaks
every repeat, so `token=a1 password=b2` is fully masked and only
`token=a1 token=b2` leaks. It survives the four examples and also survives the
obvious "two secrets in one line" case that catches `bad-first-only`. Catching
it requires a case built from the quantifier in the intent sentence -- every
value, including a key that appears twice -- rather than from one step past the
examples. A benchmark that stops at the first generalization it can think of
scores this variant clean.

deviation: quantifier-narrowing
