packet: q5-materialize
skill: orch-deliver
objective: materialize the selected case specifications exactly
inputs: frozen upstream identities per record/joins.md; source policy local-only; packs per the caller packet
authority: stage write scope only; excluded: target mutation, candidate work, evolve
bounds: 7 units of the materialize allocation; expected cost 2 units
return_contract: status, result identity, changed artifacts
reply_to: benchmaker-run
pack: orch-code-pack
spec: q4-materialize-spec
