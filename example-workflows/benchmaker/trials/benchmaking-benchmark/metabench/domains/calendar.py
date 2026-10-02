"""Calendar-booking domain for calendar-skill: the metabench hook protocol.

A task is a workspace of calendar files, a booking request and a team policy. The oracle is the scheduling
domain's exact one over the instance the workspace implies (`calendar_state`), the checker adds preservation of
existing entries and the booking's presence in the files (`calendar_check`), and outputs are whole final states
(`calendar_outputs`). `calendar_material` turns scheduling instances into workspaces and fetches the real material;
`calendar_skill` generates the harmful variant of the subject's skill for pools.
"""

from __future__ import annotations

from . import calendar_check, calendar_material, calendar_outputs, calendar_skill, calendar_state, scheduling

NAME = "calendar"

recognize = calendar_state.recognize
solve = calendar_outputs.solve
check = calendar_check.check
apply = scheduling.apply
labeled = calendar_outputs.labeled
DEFECTS = calendar_outputs.DEFECTS
HEURISTICS = calendar_outputs.HEURISTICS
FLOORS = ("busy_only",)    # the policy-blind earliest free slot

load = calendar_state.load
collect = calendar_state.collect
render_policy = calendar_state.render_policy
build_workspace = calendar_state.build_workspace
from_schedule = calendar_material.from_schedule
fetch_material = calendar_material.fetch_material
harmful_skill = calendar_skill.harmful_skill
