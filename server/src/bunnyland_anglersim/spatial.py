"""World-state helpers: which room an entity is in, and the current time-of-day phase.

The fishing verb needs to know the room a character stands in (a fishing spot may be the
room itself or an object resting in it) and the time of day (which keys the catch table).
Both questions are answered against live world state so they degrade gracefully in bare
test worlds that have no clock.
"""

from __future__ import annotations

from bunnyland.core import RoomComponent, container_of
from bunnyland.core.components import WorldClockComponent
from bunnyland.foundation.environment.mechanics import TimeOfDayComponent, time_of_day
from relics import Entity, World

#: Guard against pathological containment cycles while walking up to a room.
_MAX_CONTAINMENT_DEPTH = 8

#: Phase used when the world has no clock (e.g. a minimal unit-test world).
DEFAULT_PHASE = "day"


def room_of(world: World, entity_id) -> Entity | None:
    """Return the room ``entity_id`` is ultimately in, resolving through any holder.

    Walks ``Contains`` parents upward until an entity with :class:`RoomComponent` is found,
    so it works for a character standing in a room, an item on the floor, and an item
    carried in an inventory. An entity that *is* a room returns itself.
    """
    if not world.has_entity(entity_id):
        return None
    current = world.get_entity(entity_id)
    if current.has_component(RoomComponent):
        return current
    for _ in range(_MAX_CONTAINMENT_DEPTH):
        parent_id = container_of(current)
        if parent_id is None or not world.has_entity(parent_id):
            return None
        parent = world.get_entity(parent_id)
        if parent.has_component(RoomComponent):
            return parent
        current = parent
    return None


def phase_of(world: World) -> str:
    """Return the current time-of-day phase, or :data:`DEFAULT_PHASE` without a clock.

    Prefers the :class:`TimeOfDayComponent` the environment mechanic maintains; if only a
    raw clock is present it derives the phase from the game-clock reading directly.
    """
    clocks = list(world.query().with_all([WorldClockComponent]).execute_entities())
    if not clocks:
        return DEFAULT_PHASE
    clock = clocks[0]
    if clock.has_component(TimeOfDayComponent):
        return clock.get_component(TimeOfDayComponent).phase
    seconds = clock.get_component(WorldClockComponent).game_time_seconds
    _day, _hour, phase, _season = time_of_day(seconds)
    return phase


__all__ = ["DEFAULT_PHASE", "phase_of", "room_of"]
