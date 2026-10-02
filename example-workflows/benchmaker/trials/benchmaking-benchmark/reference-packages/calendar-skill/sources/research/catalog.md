# Scenario catalog and sources

Basis: no web research ran for this package. The workspaces are authored from the meta-task interface and the style of public scheduling material; the table says what each scenario stands for and what it leaves out. A reviewer holding this catalog can judge whether each could occur in practice.

## Sources

| Source | Use | Licence and constraints |
| --- | --- | --- |
| Natural Plan, calendar scheduling (Zheng et al., https://arxiv.org/abs/2406.04520; https://github.com/google-deepmind/natural-plan) | Style of meeting requests; with `--instances DIR` its records are converted into workspaces that carry a buffer or room policy | Code Apache-2.0; data CC BY 4.0 (checked 2026-10-01 on the repository README). Attribution: (c) 2024 DeepMind Technologies Limited. Generated from templates, not logged requests; public since 2024 |
| Meta-task interface (`interface.md`) | The workspace layout, the three policy rule types and the checker's rules | Authored for this benchmark |
| The `booking-rules` skill (`meta-tasks/calendar-skill/subject/booking-rules`) | The subject of the uplift question; its helper covers busy time, work hours, grid and buffer, not room features or urgent focus-block exceptions | Authored for this benchmark |

## Scenario families

| Family | Real situation | What makes it hard | Skill coverage |
| --- | --- | --- | --- |
| buffer-only | A team that wants breathing room between meetings, with rooms that other teams also book | Buffers of 10 to 30 minutes cut the exact-fit gaps; focus blocks count as busy time | Covered by the helper |
| room-features | Demos and workshops that need video or a whiteboard from a given head count | The rule applies only from a threshold (video from four, whiteboard from five); a room without the feature is free at the time | Not covered |
| focus-urgent | Protected focus time and its exception for urgent requests | An urgent request may book over focus blocks only when the policy says so, and normal requests may not even then; ignored focus blocks stop counting for the buffer | Not covered |
| mixed-policy | The full policy: buffer, focus rule and room features together | Several rules interact; accessible rooms always, video from four, whiteboards from three | Partly covered |
| preservation-dense | Crowded calendars before a release or a quarter end | Many entries per person; optional invitees and bystanders whose files must stay as they are; rewriting a file drops other people's meetings | Covered |
| infeasible | Requests the policy cannot satisfy: a buffer that removes every exact-fit gap, video rooms all booked | The right answer changes no file and says why | Covered |

## Source groups

A source group is a team with its own people, offsets and conventions: platform-eng (UTC-7 to UTC+9), emea-sales (UTC+0 to UTC+4), design-studio (part-time and four-day weeks, UTC-6 to UTC+5:45), clinic-ops (one site, shifts, evening and night work), exec-office (two offsets, dense calendars). Tasks of one group reuse its people with different calendars, rooms and policies, so results cluster by group.

## Coverage gaps

Real calendars have recurring series, tentative entries, attendee response statuses and room-booking systems with their own APIs; none of those are modelled. The policy is three rule types; real policies have more. Instructions state the output format and the rules point to `policy.md`, so the benchmark measures applying a written policy to files, not discovering one.
