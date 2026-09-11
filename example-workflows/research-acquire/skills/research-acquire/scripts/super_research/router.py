"""Router seam: choose a route, or refuse, before any I/O happens.

The router never sees a host, a path, or a credential. Its only knowledge
of reachability is the per-route boolean map ``transport.route_admissions``
returns, so no routing decision can leak a route constant, and a route the
run cannot reach is refused rather than probed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from . import schema
from .adapters import AdapterDescriptor


@dataclass(frozen=True)
class RouteDecision:
    step_id: str
    adapter_id: str
    route_id: str
    access_class: str
    admitted: bool
    refusal_reason: str = ""


def _refuse(
    step: schema.AcquisitionStep, descriptor: AdapterDescriptor, reason: str
) -> RouteDecision:
    return RouteDecision(
        step_id=step.step_id,
        adapter_id=step.adapter_id,
        route_id=descriptor.route_id,
        access_class=descriptor.access_class,
        admitted=False,
        refusal_reason=reason,
    )


def select_route(
    step: schema.AcquisitionStep,
    descriptor: AdapterDescriptor,
    route_admissions: Mapping[str, bool],
) -> RouteDecision:
    """Decide one step's route from per-route booleans alone."""

    if descriptor.adapter_id != step.adapter_id:
        return _refuse(step, descriptor, "no_route")
    if descriptor.route_id not in route_admissions:
        return _refuse(step, descriptor, "no_route")
    if not route_admissions[descriptor.route_id]:
        # The one class that can answer False is K5, and no first-release
        # capability may depend on a user credential.
        return _refuse(step, descriptor, "auth_required")
    return RouteDecision(
        step_id=step.step_id,
        adapter_id=step.adapter_id,
        route_id=descriptor.route_id,
        access_class=descriptor.access_class,
        admitted=True,
    )
