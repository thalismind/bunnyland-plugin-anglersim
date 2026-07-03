from __future__ import annotations

from bunnyland.core import RoomComponent, WorldActor, spawn_entity

from bunnyland_anglersim import FishingSpotComponent, RestockConsequence, spawn_fishing_spot


def _spot(actor, **fields):
    room = spawn_entity(actor.world, [RoomComponent(title="Lake", biome="lake")])
    return spawn_fishing_spot(actor.world, room_id=room.id, biome="lake", **fields)


def test_full_spot_is_left_alone():
    actor = WorldActor()
    spot = _spot(actor, stock=4, capacity=4)
    RestockConsequence().process(actor.world, 1000)
    assert spot.get_component(FishingSpotComponent).stock == 4


def test_first_tick_only_anchors_the_restock_clock():
    actor = WorldActor()
    spot = _spot(actor, stock=1, capacity=4, restock_interval=100)
    RestockConsequence().process(actor.world, 500)
    state = spot.get_component(FishingSpotComponent)
    assert state.stock == 1  # no free stock on the anchoring tick
    assert state.restocked_at_epoch == 500


def test_stock_refills_after_the_interval():
    actor = WorldActor()
    spot = _spot(actor, stock=1, capacity=4, restock_interval=100)
    consequence = RestockConsequence()
    consequence.process(actor.world, 500)  # anchor
    consequence.process(actor.world, 650)  # +150s -> one unit
    assert spot.get_component(FishingSpotComponent).stock == 2


def test_no_refill_before_the_interval_elapses():
    actor = WorldActor()
    spot = _spot(actor, stock=1, capacity=4, restock_interval=100, restocked_at_epoch=500)
    RestockConsequence().process(actor.world, 550)  # only +50s
    assert spot.get_component(FishingSpotComponent).stock == 1


def test_refill_is_capped_at_capacity():
    actor = WorldActor()
    spot = _spot(actor, stock=1, capacity=4, restock_interval=10, restocked_at_epoch=100)
    RestockConsequence().process(actor.world, 100_000)  # many intervals elapsed
    assert spot.get_component(FishingSpotComponent).stock == 4
