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
from bunnyland.core.ecs import replace_component

from bunnyland_anglersim import (
    CatchLogComponent,
    anglersim_fragments,
    attach_fishing_spot,
    record_catch,
    spawn_fishing_spot,
)


def _room(world, biome="lake"):
    return spawn_entity(world, [RoomComponent(title="Lake", biome=biome)])


def _angler(world, room, name="Vin"):
    angler = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), angler.id)
    return angler


def test_trophy_log_appears_in_fragments():
    actor = WorldActor()
    room = _room(actor.world)
    angler = _angler(actor.world, room)
    replace_component(
        angler, record_catch(record_catch(CatchLogComponent(), "bass", 3.0), "pike", 7.5)
    )

    lines = anglersim_fragments(actor.world, angler)

    assert "Your biggest catch is a pike (7.5 lb)." in lines


def test_reachable_room_spot_is_described():
    actor = WorldActor()
    room = _room(actor.world, biome="river")
    angler = _angler(actor.world, room)
    attach_fishing_spot(room)

    lines = anglersim_fragments(actor.world, angler)

    assert "A fishing spot ripples here, good for river fish." in lines


def test_fished_out_object_spot_is_described():
    actor = WorldActor()
    room = _room(actor.world)
    angler = _angler(actor.world, room)
    spawn_fishing_spot(actor.world, room_id=room.id, biome="lake", stock=0)

    lines = anglersim_fragments(actor.world, angler)

    assert "The fishing spot within reach is fished out for now." in lines


def test_no_fragments_without_log_or_spot():
    actor = WorldActor()
    room = _room(actor.world)
    angler = _angler(actor.world, room)
    assert anglersim_fragments(actor.world, angler) == []
