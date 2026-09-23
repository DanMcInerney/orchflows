# Request

[invoke `benchmaker:benchmaker`] Does the skill in `./skill/` make the supplied agent better at the work it claims to cover? Build a development suite that answers this for the agent's native harness. Include work where the skill should activate and nearby work where it should not. Allow at most 50 agent launches, ten minutes each, no retries, no paid judge. Save the suite, commands, card and rejection log in `./benchmark-run/`.

Trial setup: supply a real skill package (SKILL.md plus references or scripts) covering a recurring document or data task. Supply an agent harness that can run the same model with and without the skill installed, and a few real inputs from the skill's domain. Do not tell the author that the skill's bundled examples resemble some candidate tasks, or that one of its instructions is wrong for a common input variant.
