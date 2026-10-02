# Scenario catalog and sources

Basis: no web research ran for this package. The scenarios are authored from the meta-task interface and the style of public scheduling material; the table says what each one stands for and what it leaves out. A reviewer holding this catalog can judge whether each request could occur in practice.

## Sources

| Source | Use | Licence and constraints |
| --- | --- | --- |
| Natural Plan, calendar scheduling (Zheng et al., https://arxiv.org/abs/2406.04520; https://github.com/google-deepmind/natural-plan) | Style of request and day-specific preferences ("would rather not meet on Monday before 12:30"); with `--instances DIR` its records are converted into tasks | Code Apache-2.0; data CC BY 4.0 (checked 2026-10-01 on the repository README). Attribution: (c) 2024 DeepMind Technologies Limited. Generated from templates, not logged requests; public since 2024, so models may have seen it |
| Meta-task interface (`interface.md`) | The rules every verifier and reference implements: half-open intervals, local work hours, constraints, rooms, preference, infeasible answers | Authored for this benchmark |

## Scenario families

| Family | Real situation | What makes it hard | Left out |
| --- | --- | --- | --- |
| cross-zone | A distributed team finding a recurring call across four or five UTC offsets, half-hour offsets included | Overlapping work hours are one to three hours a day; every local lunch and meeting must be moved into one frame; the latest or earliest start needs a scan of the whole week | Daylight-saving changes, which are what make real cross-zone scheduling fail twice a year |
| dense-week | Executives, sales leads and clinic staff whose calendars are full | Free gaps are short and often exactly meeting-length; duplicate and overlapping entries; shift workers and Saturday hours | Soft preferences such as "prefer mornings" |
| constraint-heavy | People with personal limits: not before 10:00, done by noon on Thursday, 30 minutes between meetings, away on Wednesday | Limits are in the person's own clock and local dates; optional invitees' limits must be ignored | Rankings between near-equal slots |
| infeasible | Requests that cannot be met: no common instant although every pair overlaps, a last slot clipped by one granule, clashing limits, booked rooms, a short window, an away day | The right answer is no slot with a reason; declaring infeasibility wrongly or giving the least-bad slot both fail | Negotiation (the real next step) |
| rooms | Workshops needing video, seating and a free room | Capacity, features and room calendars cut the common time again | Travel time between rooms |
| edge-cases | Night shifts across local midnight, a window that starts at 10:10, a slot that exactly fits between touching meetings | The interface's boundary rules: half-open intervals, a grid anchored at the window start, a slot ending at the window end | Leap days and calendar-year boundaries |
| everyday | Two people, three days, short calendars | One offset conversion and a scan of forty meetings | - |

## Source groups

A source group is a team with its own people, offsets and work-hours conventions: platform-eng (UTC-7 to UTC+9), emea-sales (UTC+0 to UTC+4), design-studio (UTC-6 to UTC+5:45, part-time and four-day weeks), clinic-ops (one site, shifts, evening and night work), exec-office (two offsets, dense calendars), field-teams (UTC+5:30 to UTC+13). Tasks of one group reuse the team's people and conventions with different calendars, so results cluster by group.

## Coverage gaps

Real requests also carry free text, several meetings at once, recurring series and soft preferences; none of those are tested. Task requests state the rules in the instruction, so the benchmark measures applying stated rules, not guessing a team's conventions.
