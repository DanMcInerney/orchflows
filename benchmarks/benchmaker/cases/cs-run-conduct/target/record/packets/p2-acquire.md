packet: p2-acquire
skill: orch-deliver
objective: deliver the frozen acquisition spec to a converged synthesis
inputs: frozen upstream identities per record/joins.md; source policy local-only; packs per the caller packet
authority: stage write scope only; excluded: target mutation, candidate work, evolve
bounds: 10 units of the acquire allocation; expected cost 3 units
return_contract: status, result identity, changed artifacts
reply_to: benchmaker-run
pack: orch-research-pack
spec: p1-acquire-spec
