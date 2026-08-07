# Defect: contracted return fields are missing

The return blocks correctly and names both defects, but it breaks the
return contract it was dispatched under: the spend field is absent —
the caller cannot see that no allocation was partitioned — and the
closing is unaddressed, with no reply_to literal anywhere in the
return, so on a spawn surface whose returns travel only by addressed
message this result is silently misdirected. A return that fails its
own contracted fields fails at the join regardless of how sound its
refusal reasoning is. The census name binding-omission is reused at a
fresh locus: the return-contract field set of an intake refusal was
never a seeded locus in the predecessor set.

deviation: binding-omission @ return-contract-fields locus (spend absent, reply_to unaddressed)
