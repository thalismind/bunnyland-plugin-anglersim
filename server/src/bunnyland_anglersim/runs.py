"""Seasonal fishing runs, registered as core storyteller incidents.

Now and then the fish are *running* — a spawning run, a warm current, a feeding frenzy — and
for a while the water gives up rarer catches. :class:`FishingRunConsequence` paces itself like
the core storyteller (an interval and a next-due epoch), and when a run opens it stamps a
**core** :class:`~bunnyland.mechanics.storyteller.IncidentComponent` onto a spawned incident
entity so the run registers in the shared world-pressure budget rather than a private timer.
While a run is active every cast gets a :func:`run_bonus` toward the rare and legendary tiers;
when it closes the incident is resolved and the bias is gone.

The run window and pacing live on a single :class:`FishingRunComponent` seated on the world
clock (idempotently seeded), so the mechanic is save-safe and never double-runs.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import IdentityComponent, WorldClockComponent, spawn_entity
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.mechanics.environment import CalendarComponent
from bunnyland.mechanics.storyteller import IncidentComponent
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .events import FishingRunEndedEvent, FishingRunStartedEvent

SECONDS_PER_DAY = 24 * 60 * 60

#: How long an open fishing run lasts before it closes again.
RUN_DURATION_SECONDS = 6 * 60 * 60

#: Odds bias a live run folds into every cast (toward the rare/legendary tiers).
RUN_BONUS = 0.6


@dataclass(frozen=True)
class FishingRunComponent(Component):
    """World-level pacing for seasonal fishing runs (rests on the world clock).

    ``enabled`` gates the whole mechanic; ``next_run_epoch`` is when the next run may open;
    ``active_until_epoch`` is when the current run closes; ``active_incident_id`` is the open
    run's incident (empty when no run is live); ``run_index`` counts runs opened so far.
    """

    enabled: bool = True
    interval_seconds: int = 3 * SECONDS_PER_DAY
    next_run_epoch: int = 3 * SECONDS_PER_DAY
    active_until_epoch: int = 0
    active_incident_id: str = ""
    run_index: int = 0
    bonus: float = RUN_BONUS


def current_season(world: World) -> str | None:
    """Return the world's current season, or ``None`` if no calendar clock exists."""
    clocks = sorted(
        world.query().with_all([CalendarComponent]).execute_entities(), key=lambda e: str(e.id)
    )
    if not clocks:
        return None
    return clocks[0].get_component(CalendarComponent).season


def ensure_fishing_run(world: World) -> Entity | None:
    """Seed a :class:`FishingRunComponent` onto the world clock if none exists yet.

    Idempotent: called from both install and worldgen so a world only ever holds one.
    """
    existing = list(world.query().with_all([FishingRunComponent]).execute_entities())
    if existing:
        return existing[0]
    clocks = sorted(
        world.query().with_all([WorldClockComponent]).execute_entities(), key=lambda e: str(e.id)
    )
    if not clocks:
        return None
    clock = clocks[0]
    replace_component(clock, FishingRunComponent())
    return clock


def run_bonus(world: World, epoch: int) -> float:
    """Return the total live fishing-run odds bias at ``epoch`` (``0.0`` when none is live)."""
    total = 0.0
    for marker in world.query().with_all([FishingRunComponent]).execute_entities():
        state = marker.get_component(FishingRunComponent)
        if state.active_incident_id and epoch < state.active_until_epoch:
            total += state.bonus
    return total


class FishingRunConsequence:
    """Pace, open, and close seasonal fishing runs as core storyteller incidents."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        markers = sorted(
            world.query().with_all([FishingRunComponent]).execute_entities(),
            key=lambda e: str(e.id),
        )
        for marker_entity in markers:
            state = marker_entity.get_component(FishingRunComponent)
            if not state.enabled:
                continue
            if state.active_incident_id:
                if epoch >= state.active_until_epoch:
                    events.append(self._close_run(world, marker_entity, epoch))
                continue
            if epoch >= state.next_run_epoch:
                events.append(self._open_run(world, marker_entity, epoch))
        return events

    def _open_run(self, world: World, marker_entity: Entity, epoch: int) -> DomainEvent:
        state = marker_entity.get_component(FishingRunComponent)
        season = current_season(world) or "unknown"
        run_index = state.run_index + 1
        active_until = epoch + RUN_DURATION_SECONDS
        incident = spawn_entity(
            world,
            [
                IdentityComponent(name="fishing run", kind="incident"),
                IncidentComponent(
                    kind="fishing_run",
                    budget_spent=state.bonus,
                    started_at_epoch=epoch,
                ),
            ],
        )
        replace_component(
            marker_entity,
            replace(
                state,
                run_index=run_index,
                active_until_epoch=active_until,
                active_incident_id=str(incident.id),
                next_run_epoch=epoch + state.interval_seconds,
            ),
        )
        return FishingRunStartedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PUBLIC,
                actor_id=str(incident.id),
                run_index=run_index,
                season=season,
                ends_at_epoch=active_until,
            )
        )

    def _close_run(self, world: World, marker_entity: Entity, epoch: int) -> DomainEvent:
        state = marker_entity.get_component(FishingRunComponent)
        season = current_season(world) or "unknown"
        incident_id = state.active_incident_id
        parsed = parse_entity_id(incident_id)
        if parsed is not None and world.has_entity(parsed):
            incident = world.get_entity(parsed)
            resolved = replace(
                incident.get_component(IncidentComponent), resolved_at_epoch=epoch
            )
            replace_component(incident, resolved)
        replace_component(
            marker_entity,
            replace(state, active_until_epoch=0, active_incident_id=""),
        )
        return FishingRunEndedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PUBLIC,
                actor_id=str(marker_entity.id),
                run_index=state.run_index,
                season=season,
            )
        )


def install_runs(actor) -> None:
    """Register the fishing-run consequence and seed the pacing marker (a service factory)."""
    actor.register_consequence(FishingRunConsequence())
    ensure_fishing_run(actor.world)


def runs_fragment(world: World, epoch: int) -> str | None:
    """A prompt line when a fishing run is live, else ``None``."""
    if run_bonus(world, epoch) > 0.0:
        return "The fish are running — the water is giving up rarer catches than usual."
    return None


__all__ = [
    "RUN_BONUS",
    "RUN_DURATION_SECONDS",
    "SECONDS_PER_DAY",
    "FishingRunComponent",
    "FishingRunConsequence",
    "current_season",
    "ensure_fishing_run",
    "install_runs",
    "run_bonus",
    "runs_fragment",
]
