from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import WorldClockComponent
from bunnyland.core.ecs import replace_component
from bunnyland.mechanics.environment import SECONDS_PER_HOUR, TimeOfDayComponent

from bunnyland_anglersim.spatial import phase_of, room_of


def _default_clock(actor):
    return list(actor.world.query().with_all([WorldClockComponent]).execute_entities())[0]


def _world_with_room():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Lake")])
    return actor, room


def test_room_of_returns_the_room_itself():
    actor, room = _world_with_room()
    assert room_of(actor.world, room.id).id == room.id


def test_room_of_resolves_an_item_on_the_floor():
    actor, room = _world_with_room()
    item = spawn_entity(actor.world, [IdentityComponent(name="rod", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)
    assert room_of(actor.world, item.id).id == room.id


def test_room_of_resolves_through_a_holder():
    actor, room = _world_with_room()
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    item = spawn_entity(actor.world, [IdentityComponent(name="rod", kind="item")])
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)
    assert room_of(actor.world, item.id).id == room.id


def test_room_of_missing_entity_is_none():
    actor, _room = _world_with_room()
    assert room_of(actor.world, "entity_9999") is None


def test_room_of_uncontained_entity_is_none():
    actor, _room = _world_with_room()
    loose = spawn_entity(actor.world, [IdentityComponent(name="drifter", kind="item")])
    assert room_of(actor.world, loose.id) is None


def test_room_of_gives_up_on_a_too_deep_containment_chain():
    actor, _room = _world_with_room()
    # A long chain of non-room containers (no room at the top) exceeds the walk-up guard.
    nodes = [
        spawn_entity(actor.world, [IdentityComponent(name=f"box{i}", kind="item")])
        for i in range(12)
    ]
    for parent, child in zip(nodes, nodes[1:]):  # noqa: B905 - unequal lengths by design
        parent.add_relationship(Contains(mode=ContainmentMode.INVENTORY), child.id)
    assert room_of(actor.world, nodes[-1].id) is None


def test_phase_defaults_to_day_without_a_clock():
    actor = WorldActor()
    actor.world.remove(_default_clock(actor).id)  # a bare actor ships one clock
    assert phase_of(actor.world) == "day"


def test_phase_reads_time_of_day_component():
    actor = WorldActor()
    replace_component(_default_clock(actor), TimeOfDayComponent(phase="dusk"))
    assert phase_of(actor.world) == "dusk"


def test_phase_derives_from_raw_clock_seconds():
    actor = WorldActor()
    # Noon derives to "day" from the raw clock, with no TimeOfDayComponent to read directly.
    replace_component(
        _default_clock(actor), WorldClockComponent(game_time_seconds=12 * SECONDS_PER_HOUR)
    )
    assert phase_of(actor.world) == "day"
