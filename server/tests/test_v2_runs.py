from __future__ import annotations

from dataclasses import replace

from bunnyland.core import WorldActor, WorldClockComponent, spawn_entity
from bunnyland.core.ecs import replace_component
from bunnyland.foundation.environment.mechanics import CalendarComponent
from bunnyland.foundation.storyteller.mechanics import IncidentComponent

from bunnyland_anglersim.events import FishingRunEndedEvent, FishingRunStartedEvent
from bunnyland_anglersim.runs import (
    RUN_BONUS,
    FishingRunComponent,
    FishingRunConsequence,
    current_season,
    ensure_fishing_run,
    install_runs,
    run_bonus,
    runs_fragment,
)


def _clocks(actor):
    return list(actor.world.query().with_all([WorldClockComponent]).execute_entities())


def _clock(actor, *, seconds=0, season=None):
    # A bare WorldActor already carries one world clock; the run marker seats on it, so reuse
    # that clock rather than spawning a second one the marker would ignore.
    clock = _clocks(actor)[0]
    replace_component(clock, WorldClockComponent(game_time_seconds=seconds))
    if season is not None:
        clock.add_component(CalendarComponent(season=season))
    return clock


def _arm(clock, **fields):
    state = clock.get_component(FishingRunComponent)
    replace_component(clock, replace(state, **fields))


def test_ensure_is_idempotent_and_needs_a_clock():
    actor = WorldActor()
    for clock in _clocks(actor):  # a world with no clock at all cannot seat the marker
        actor.world.remove(clock.id)
    assert ensure_fishing_run(actor.world) is None
    clock = spawn_entity(actor.world, [WorldClockComponent()])
    seeded = ensure_fishing_run(actor.world)
    assert seeded.id == clock.id
    assert ensure_fishing_run(actor.world).id == clock.id  # idempotent


def test_current_season_with_and_without_calendar():
    actor = WorldActor()
    assert current_season(actor.world) is None
    _clock(actor, season="winter")
    assert current_season(actor.world) == "winter"


def test_run_opens_biases_then_closes():
    actor = WorldActor()
    clock = _clock(actor, season="summer")
    ensure_fishing_run(actor.world)
    _arm(clock, next_run_epoch=100)
    cons = FishingRunConsequence()

    assert cons.process(actor.world, 50) == []  # not due yet
    assert run_bonus(actor.world, 50) == 0.0

    started = cons.process(actor.world, 100)
    assert len(started) == 1
    assert isinstance(started[0], FishingRunStartedEvent)
    assert started[0].season == "summer"
    state = clock.get_component(FishingRunComponent)
    assert state.active_incident_id
    assert state.run_index == 1
    assert run_bonus(actor.world, 100) == RUN_BONUS
    assert runs_fragment(actor.world, 100) is not None

    # A live run does not re-open or re-close on the next tick.
    assert cons.process(actor.world, 200) == []

    end_epoch = state.active_until_epoch
    ended = cons.process(actor.world, end_epoch)
    assert len(ended) == 1
    assert isinstance(ended[0], FishingRunEndedEvent)
    closed = clock.get_component(FishingRunComponent)
    assert closed.active_incident_id == ""
    assert run_bonus(actor.world, end_epoch) == 0.0
    assert runs_fragment(actor.world, end_epoch) is None
    # The spawned incident was resolved.
    incidents = list(actor.world.query().with_all([IncidentComponent]).execute_entities())
    assert incidents
    assert incidents[0].get_component(IncidentComponent).resolved_at_epoch == end_epoch


def test_close_tolerates_missing_incident():
    actor = WorldActor()
    clock = _clock(actor)
    ensure_fishing_run(actor.world)
    _arm(clock, active_incident_id="entity_9999", active_until_epoch=100)
    ended = FishingRunConsequence().process(actor.world, 200)
    assert len(ended) == 1
    assert clock.get_component(FishingRunComponent).active_incident_id == ""


def test_disabled_marker_is_skipped():
    actor = WorldActor()
    clock = _clock(actor)
    ensure_fishing_run(actor.world)
    _arm(clock, enabled=False, next_run_epoch=0)
    assert FishingRunConsequence().process(actor.world, 10_000) == []


def test_install_runs_registers_and_seeds():
    actor = WorldActor()
    _clock(actor)
    install_runs(actor)
    assert list(actor.world.query().with_all([FishingRunComponent]).execute_entities())
