# Orchflows maintenance

For reviewing and improving existing Orchflows libraries.

**Judging findings**
- Judge the library by its stated purpose and principles, not by novelty or popularity.
- Prefer the least mechanism: a finding that removes, merges or simplifies usually beats one that adds. Prefer removing to rewording, and rewording to adding.
- An outside idea earns a change when it fits the design and improves the results users get.
- A gate, retry or review earns its cost by changing outcomes.

**Writing for capable future models**
- Deliberate policy stays whatever the model. In user libraries, the user's taste is policy.
- Answer a mistake only weaker models make with a deterministic test or a recorded host fact, not with more instructions. State principles, not checklists.

**Weighing evidence**
- Trust what running showed over what reading suggests, and a deterministic check over a judge's verdict.
- A single run is weak evidence; name the variance.
- Record the host, model and effort behind each observation.

## Make

Keep changes separable so any one can be reverted, and update every consumer of moved or renamed text.

## Review

Flag:
- edits to trial expected behavior;
- relocations that lose meaning or no longer reach their consumers;
- instructions added for weaker-model mistakes.
