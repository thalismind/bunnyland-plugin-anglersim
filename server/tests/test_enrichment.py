import asyncio

from bunnyland.core import Contains, WorldActor
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import ObjectSpec, RoomSpec, WorldProposal, instantiate

from bunnyland_anglersim import DerbyComponent, FishingSpotComponent, RecordBookComponent
from bunnyland_anglersim.plugin import bunnyland_plugins as _plugins


def _world(*, room=None, object_=None):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    result = asyncio.run(
        instantiate(
            actor,
            WorldProposal(
                seed="seed",
                rooms=[room or RoomSpec(key="room", title="Room")],
                objects=[object_] if object_ else [],
            ),
        )
    )
    return actor, result


def test_water_room_gets_spot_and_singleton_hubs():
    actor, result = _world(room=RoomSpec(key="bog", title="Bog", biome="marsh"))
    room = actor.world.get_entity(result.rooms["bog"])
    assert room.get_component(FishingSpotComponent).biome == "marsh"
    children = [
        actor.world.get_entity(target) for _edge, target in room.get_relationships(Contains)
    ]
    assert sum(child.has_component(RecordBookComponent) for child in children) == 1
    assert sum(child.has_component(DerbyComponent) for child in children) == 1


def test_watery_description_and_object_get_spots():
    actor, result = _world(room=RoomSpec(key="pond", title="Garden", description="a still pond"))
    assert (
        actor.world.get_entity(result.rooms["pond"]).get_component(FishingSpotComponent).biome
        == "lake"
    )
    actor, result = _world(
        object_=ObjectSpec(key="deck", name="Deck", room_key="room", tags=("dock",))
    )
    assert (
        actor.world.get_entity(result.objects["deck"]).get_component(FishingSpotComponent).biome
        == "ship"
    )


def test_dry_entities_are_ignored():
    actor, result = _world(room=RoomSpec(key="field", title="Field", biome="meadow"))
    assert not actor.world.get_entity(result.rooms["field"]).has_component(FishingSpotComponent)
