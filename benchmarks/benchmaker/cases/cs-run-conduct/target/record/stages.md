# Stage ledger

manifest-schema: benchmaker-manifest.md sha256:9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c

stage: acquire | allocation: 14 units (acquire-spec 4, acquire delivery 10)
stage: design | allocation: 8 units
stage: materialize | allocation: 10 units
stage: qualify | allocation: 6 units
stage: manifest | allocation: 2 units

item: w01 | stage: materialize | artifact: package/cases/cases.json
item: w02 | stage: manifest | artifact: package/manifest.json
item: w03 | stage: manifest | artifact: package/provenance/provenance.json
item: w04 | stage: qualify | artifact: package/qualification/qualification.json
item: w05 | stage: materialize | artifact: package/runner/run.py
item: w06 | stage: materialize | artifact: package/scoring/scoring.json
item: w07 | stage: acquire | artifact: record/acquire/exhibits.md
item: w08 | stage: acquire | artifact: record/acquire/lane-field.md
item: w09 | stage: acquire | artifact: record/acquire/lane-target-intent.md
item: w10 | stage: acquire | artifact: record/acquire/protected/seed-authored-1.md
item: w11 | stage: acquire | artifact: record/acquire/saturation.md
item: w12 | stage: acquire | artifact: record/acquire/synthesis.md
item: w13 | stage: design | artifact: record/design.md
item: w14 | stage: acquire | artifact: record/evidence.md
item: w15 | stage: qualify | artifact: record/gaps.md
item: w16 | stage: manifest | artifact: record/joins.md
item: w17 | stage: acquire | artifact: record/packets/p1-acquire-spec.md
item: w18 | stage: acquire | artifact: record/packets/p2-acquire.md
item: w19 | stage: design | artifact: record/packets/p3-design.md
item: w20 | stage: materialize | artifact: record/packets/p4-materialize-spec.md
item: w21 | stage: materialize | artifact: record/packets/p5-materialize.md
item: w22 | stage: qualify | artifact: record/packets/p6-qualify.md
