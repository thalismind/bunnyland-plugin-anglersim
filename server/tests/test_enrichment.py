from __future__ import annotations

import asyncio

from bunnyland.core import IdentityComponent, RoomComponent, WorldActor, spawn_entity
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import ObjectGeneratedEvent, RoomGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_anglersim import FishingSpotComponent, water_biome_for
from bunnyland_anglersim.catch import WATER_BIOMES


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_anglersim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _room_event(entity, *, biome="unknown", tags=(), description=""):
    return RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="r",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        room_key="r",
        biome=biome,
    )


def _object_event(entity, *, tags=(), description=""):
    return ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="o",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        object_key="o",
    )


def test_water_biome_room_gets_a_spot():
    actor = _actor()
    room = spawn_entity(actor.world, [RoomComponent(title="Bog", biome="marsh")])
    _publish(actor, _room_event(room, biome="marsh"))
    assert room.get_component(FishingSpotComponent).biome == "marsh"


def test_dry_room_with_watery_description_gets_a_spot():
    actor = _actor()
    room = spawn_entity(actor.world, [RoomComponent(title="Garden", biome="meadow")])
    _publish(actor, _room_event(room, biome="meadow", description="a still pond by the hedge"))
    assert room.get_component(FishingSpotComponent).biome == "lake"


def test_dry_room_gets_no_spot():
    actor = _actor()
    room = spawn_entity(actor.world, [RoomComponent(title="Attic", biome="indoor")])
    _publish(actor, _room_event(room, biome="indoor", description="a dusty loft"))
    assert not room.has_component(FishingSpotComponent)


def test_watery_object_gets_a_spot():
    actor = _actor()
    obj = spawn_entity(actor.world, [IdentityComponent(name="deck", kind="object")])
    _publish(actor, _object_event(obj, tags=("dock", "wooden")))
    assert obj.get_component(FishingSpotComponent).biome == "ship"


def test_plain_object_gets_no_spot():
    actor = _actor()
    obj = spawn_entity(actor.world, [IdentityComponent(name="crate", kind="object")])
    _publish(actor, _object_event(obj, tags=("wooden", "storage")))
    assert not obj.has_component(FishingSpotComponent)


def test_existing_spot_is_not_overwritten():
    actor = _actor()
    room = spawn_entity(
        actor.world,
        [RoomComponent(title="Lake", biome="lake"), FishingSpotComponent(biome="lake", casts=3)],
    )
    _publish(actor, _room_event(room, biome="lake"))
    assert room.get_component(FishingSpotComponent).casts == 3


def test_room_event_for_a_missing_entity_is_ignored():
    actor = _actor()
    room = spawn_entity(actor.world, [RoomComponent(title="Lake", biome="lake")])
    event = _room_event(room, biome="lake")
    event = event.model_copy(update={"entity_id": "entity_9999"})  # dangling reference
    _publish(actor, event)
    assert not room.has_component(FishingSpotComponent)


def test_object_event_for_a_missing_entity_is_ignored():
    actor = _actor()
    obj = spawn_entity(actor.world, [IdentityComponent(name="dock", kind="object")])
    event = _object_event(obj, tags=("dock",))
    event = event.model_copy(update={"entity_id": "entity_9999"})
    _publish(actor, event)
    assert not obj.has_component(FishingSpotComponent)


def test_water_biome_for_direct_and_term_and_none():
    for biome in WATER_BIOMES:
        assert water_biome_for(biome, "") == biome
    assert water_biome_for("plains", "beside a creek") == "river"
    assert water_biome_for("plains", "a dry cave") is None
