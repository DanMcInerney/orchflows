# booking-rules

The calendar team's skill for booking a meeting into the team's calendar files. It is a Claude Code plugin with one skill, `booking-rules`, and a helper script.

## Files

- `.claude-plugin/plugin.json`: the plugin manifest.
- `skills/booking-rules/SKILL.md`: the booking rules the team applies, how to record a booking, and what the skill does not cover.
- `skills/booking-rules/scripts/free_slots.py`: lists the times a meeting can start. Standard library only; run it as `python free_slots.py --workspace DIR [--limit N] [--latest]`.

## What it covers

Busy entries, each required attendee's work hours in their own UTC offset, the request's window and granularity grid, the policy's buffer, and which rooms are free and large enough.

## What it does not cover

Room features, and the policy's exception that lets an urgent request book over focus blocks. The helper treats focus blocks as busy time and does not read a room's `features`. SKILL.md says so, and the agent has to handle both cases itself.

## Use

The agent in `../agent/` loads a skill when `config.json` lists its plugin directory under `skills`, for example `"skills": ["../booking-rules"]`.
