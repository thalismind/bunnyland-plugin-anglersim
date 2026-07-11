from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    contents,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext

from bunnyland_anglersim import (
    BaitComponent,
    CatchLogComponent,
    FishComponent,
    FishHandler,
    FishingSpotComponent,
    attach_fishing_spot,
    phase_of,
    roll_catch,
    spawn_bait,
    spawn_fishing_spot,
)
from bunnyland_anglersim.events import FishCaughtEvent, LegendaryCatchEvent

EPOCH = 100


def _world(*, biome="lake"):
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Dock", biome=biome)])
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    return actor, room, holder


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor, epoch=EPOCH):
    return HandlerContext(world=actor.world, epoch=epoch)


def _caught_fish(actor, holder):
    for item_id in contents(holder):
        item = actor.world.get_entity(item_id)
        if item.has_component(FishComponent):
            return item
    return None


def test_fish_lands_a_deterministic_catch():
    actor, room, holder = _world(biome="lake")
    spot = spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert result.ok
    expected = roll_catch(
        spot_id=str(spot.id),
        character_id=str(holder.id),
        epoch=EPOCH,
        casts=0,
        biome="lake",
        phase=phase_of(actor.world),
    )
    fish = _caught_fish(actor, holder)
    component = fish.get_component(FishComponent)
    assert (component.species, component.tier, component.weight) == (
        expected.species,
        expected.tier,
        expected.weight,
    )
    event = result.events[0]
    assert isinstance(event, FishCaughtEvent)
    assert event.species == expected.species
    assert event.spot_id == str(spot.id)
    assert event.used_bait is False


def test_fish_advances_spot_and_logs_catch():
    actor, room, holder = _world()
    spot = spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")

    FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    state = spot.get_component(FishingSpotComponent)
    assert state.casts == 1
    assert state.stock == 3
    assert state.ready_at_epoch == EPOCH + state.cooldown
    log = holder.get_component(CatchLogComponent)
    assert log.best() is not None


def test_fish_at_a_room_attached_spot():
    actor, room, holder = _world(biome="river")
    attach_fishing_spot(room)  # biome defaults to the room's own biome

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert result.ok
    expected = roll_catch(
        spot_id=str(room.id),
        character_id=str(holder.id),
        epoch=EPOCH,
        casts=0,
        biome="river",
        phase=phase_of(actor.world),
    )
    assert _caught_fish(actor, holder).get_component(FishComponent).species == expected.species


def test_fish_targets_an_explicit_spot():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")
    chosen = spawn_fishing_spot(actor.world, room_id=room.id, biome="coast")

    result = FishHandler().execute(
        _ctx(actor), _cmd(holder.id, "fish", {"spot_id": str(chosen.id)})
    )

    assert result.ok
    assert chosen.get_component(FishingSpotComponent).casts == 1


def test_bait_biases_the_roll_and_is_consumed():
    actor, room, holder = _world()
    spot = spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")
    bait = spawn_bait(actor.world, quality=1.5, uses=1)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), bait.id)

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert result.ok
    assert result.events[0].used_bait is True
    assert not actor.world.has_entity(bait.id)  # single-use bait is removed
    expected = roll_catch(
        spot_id=str(spot.id),
        character_id=str(holder.id),
        epoch=EPOCH,
        casts=0,
        biome="lake",
        phase=phase_of(actor.world),
        bait_quality=1.5,
    )
    assert _caught_fish(actor, holder).get_component(FishComponent).species == expected.species


def test_multi_use_bait_decrements_instead_of_vanishing():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")
    bait = spawn_bait(actor.world, quality=1.0, uses=2)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), bait.id)

    FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert actor.world.has_entity(bait.id)
    assert bait.get_component(BaitComponent).uses == 1


def test_legendary_catch_emits_room_event():
    actor, room, holder = _world(biome="coast")
    spot = spawn_fishing_spot(actor.world, room_id=room.id, biome="coast")
    bait = spawn_bait(actor.world, quality=2.0, uses=99)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), bait.id)
    phase = phase_of(actor.world)

    # Find, deterministically, an epoch whose roll is legendary for these exact ids.
    epoch = next(
        e
        for e in range(500)
        if roll_catch(
            spot_id=str(spot.id),
            character_id=str(holder.id),
            epoch=e,
            casts=0,
            biome="coast",
            phase=phase,
            bait_quality=2.0,
        ).tier
        == "legendary"
    )

    result = FishHandler().execute(_ctx(actor, epoch), _cmd(holder.id, "fish", {}))

    assert result.ok
    assert _caught_fish(actor, holder).get_component(FishComponent).tier == "legendary"
    assert any(isinstance(event, LegendaryCatchEvent) for event in result.events)


def test_non_legendary_catch_has_no_legendary_event():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert not any(isinstance(event, LegendaryCatchEvent) for event in result.events)


def test_fish_rejects_invalid_character_id():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id)

    result = FishHandler().execute(_ctx(actor), _cmd("???", "fish", {}))

    assert not result.ok
    assert result.reason == "invalid character id"


def test_fish_rejects_when_no_spot_reachable():
    actor, _room, holder = _world()

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert not result.ok
    assert result.reason == "there is no fishing spot within reach"


def test_fish_rejects_when_spot_on_cooldown():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id, ready_at_epoch=EPOCH + 10)

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert not result.ok
    assert result.reason == "that fishing spot is still settling"


def test_fish_rejects_when_spot_is_fished_out():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id, stock=0)

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {}))

    assert not result.ok
    assert result.reason == "that fishing spot is fished out"


def test_fish_rejects_invalid_explicit_spot_id():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id)

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {"spot_id": "???"}))

    assert not result.ok
    assert result.reason == "invalid fishing spot id"


def test_fish_rejects_missing_explicit_spot():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id)

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {"spot_id": "entity_9999"}))

    assert not result.ok
    assert result.reason == "that fishing spot does not exist"


def test_fish_rejects_unreachable_explicit_spot():
    actor, _room, holder = _world()
    far_room = spawn_entity(actor.world, [RoomComponent(title="Far Lake", biome="lake")])
    far_spot = spawn_fishing_spot(actor.world, room_id=far_room.id, biome="lake")

    result = FishHandler().execute(
        _ctx(actor), _cmd(holder.id, "fish", {"spot_id": str(far_spot.id)})
    )

    assert not result.ok
    assert result.reason == "that fishing spot is not within reach"


def test_fish_rejects_explicit_non_spot_target():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id)
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)

    result = FishHandler().execute(_ctx(actor), _cmd(holder.id, "fish", {"spot_id": str(rock.id)}))

    assert not result.ok
    assert result.reason == "that is not a fishing spot"
