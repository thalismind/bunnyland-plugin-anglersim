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
from bunnyland.mechanics.consumables import FoodComponent

from bunnyland_anglersim import (
    FishHandler,
    is_edible,
    phase_of,
    roll_catch,
    spawn_fish,
    spawn_fishing_spot,
    spawn_rod,
    tier_weights,
)
from bunnyland_anglersim.catch import (
    BASE_TIER_WEIGHTS,
    JUNK_SPECIES,
    TREASURE_SPECIES,
)
from bunnyland_anglersim.components import FishComponent

EPOCH = 100


def test_is_edible_classification():
    assert is_edible("bass") is True
    assert is_edible("old boot") is False  # junk
    assert is_edible("jeweled crown") is False  # treasure
    assert "old boot" in JUNK_SPECIES
    assert "jeweled crown" in TREASURE_SPECIES


def test_tier_weights_bonuses_lift_rare_and_legendary():
    plain = tier_weights("day")
    assert plain == BASE_TIER_WEIGHTS
    boosted = tier_weights("day", 0.0, gear_bonus=0.5, luck_bonus=0.3, run_bonus=0.2)
    # quality 1.0 -> bonus 10; rare += 20, legendary += 10
    assert boosted["rare"] == BASE_TIER_WEIGHTS["rare"] + 20
    assert boosted["legendary"] == BASE_TIER_WEIGHTS["legendary"] + 10
    assert boosted["common"] == BASE_TIER_WEIGHTS["common"]


def test_roll_catch_bonuses_default_to_v1():
    plain = roll_catch(
        spot_id="s", character_id="c", epoch=1, casts=0, biome="lake", phase="day"
    )
    same = roll_catch(
        spot_id="s",
        character_id="c",
        epoch=1,
        casts=0,
        biome="lake",
        phase="day",
        gear_bonus=0.0,
        luck_bonus=0.0,
        run_bonus=0.0,
    )
    assert plain == same


def test_spawn_fish_edible_carries_food():
    actor = WorldActor()
    fish = spawn_fish(actor.world, species="bass", tier="uncommon", weight=3.0)
    assert fish.has_component(FoodComponent)
    food = fish.get_component(FoodComponent)
    assert food.nutrition == 24.0
    assert food.satiety == 30.0


def test_spawn_fish_junk_and_treasure_are_inedible():
    actor = WorldActor()
    junk = spawn_fish(actor.world, species="old boot", tier="common", weight=1.0)
    treasure = spawn_fish(actor.world, species="jeweled crown", tier="legendary", weight=15.0)
    assert not junk.has_component(FoodComponent)
    assert not treasure.has_component(FoodComponent)


def test_fish_handler_applies_gear_bonus():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Dock", biome="lake")])
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    spot = spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")
    rod = spawn_rod(actor.world, tier="masterwork")
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), rod.id)

    result = FishHandler().execute(
        HandlerContext(world=actor.world, epoch=EPOCH),
        build_submitted_command(
            character_id=str(holder.id),
            controller_id="ctrl",
            controller_generation=0,
            command_type="fish",
            cost=CommandCost(action=1),
            lane=Lane.WORLD,
            payload={},
        ),
    )
    assert result.ok
    expected = roll_catch(
        spot_id=str(spot.id),
        character_id=str(holder.id),
        epoch=EPOCH,
        casts=0,
        biome="lake",
        phase=phase_of(actor.world),
        gear_bonus=1.6,  # masterwork rod power
    )
    caught = next(
        actor.world.get_entity(i)
        for i in contents(holder)
        if actor.world.get_entity(i).has_component(FishComponent)
    )
    assert caught.get_component(FishComponent).species == expected.species
