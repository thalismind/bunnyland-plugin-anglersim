from __future__ import annotations

from bunnyland_anglersim.catch import (
    BASE_TIER_WEIGHTS,
    TIER_ORDER,
    WATER_BIOMES,
    canonical_biome,
    catch_table,
    roll_catch,
    tier_weights,
)


def test_roll_is_deterministic_for_stable_inputs():
    kwargs = dict(
        spot_id="entity_1", character_id="entity_2", epoch=6, casts=0, biome="lake", phase="day"
    )
    first = roll_catch(**kwargs)
    second = roll_catch(**kwargs)
    assert first == second
    # Pinned expected value: proves the algorithm, not just repeatability.
    assert first.species == "sturgeon"
    assert first.tier == "rare"
    assert first.weight == 5.51


def test_roll_varies_with_epoch():
    base = dict(spot_id="s", character_id="c", casts=0, biome="lake", phase="day")
    species = {roll_catch(epoch=epoch, **base).species for epoch in range(12)}
    assert len(species) > 1


def test_roll_species_belongs_to_its_tier_table():
    result = roll_catch(
        spot_id="s", character_id="c", epoch=6, casts=0, biome="lake", phase="day"
    )
    assert result.species in catch_table("lake", "day")[result.tier]


def test_unknown_biome_falls_back_to_default_table():
    assert canonical_biome("desert") == "lake"
    result = roll_catch(
        spot_id="s", character_id="c", epoch=0, casts=0, biome="desert", phase="day"
    )
    assert result.species in catch_table("lake", "day")[result.tier]


def test_every_water_biome_has_all_tiers_day_and_night():
    for biome in WATER_BIOMES:
        for phase in ("day", "night"):
            table = catch_table(biome, phase)
            assert set(table) == set(TIER_ORDER)
            for tier in TIER_ORDER:
                assert table[tier]


def test_night_adds_a_nocturnal_legendary():
    day = set(catch_table("coast", "day")["legendary"])
    night = set(catch_table("coast", "night")["legendary"])
    assert day < night
    assert "moonlit anglerfish" in night


def test_bait_and_night_raise_rare_and_legendary_weight():
    day = tier_weights("day")
    assert day == BASE_TIER_WEIGHTS
    baited = tier_weights("day", bait_quality=2.0)
    assert baited["rare"] > day["rare"]
    assert baited["legendary"] > day["legendary"]
    night = tier_weights("night", bait_quality=2.0)
    assert night["rare"] > baited["rare"]
    assert night["legendary"] > baited["legendary"]


def test_negative_bait_quality_does_not_reduce_weights():
    assert tier_weights("day", bait_quality=-5.0) == BASE_TIER_WEIGHTS


def test_higher_tiers_are_heavier():
    base = dict(
        spot_id="s", character_id="c", casts=0, biome="coast", phase="night", bait_quality=2.0
    )
    common = next(
        roll_catch(epoch=e, **base)
        for e in range(500)
        if roll_catch(epoch=e, **base).tier == "common"
    )
    legendary = next(
        roll_catch(epoch=e, **base)
        for e in range(500)
        if roll_catch(epoch=e, **base).tier == "legendary"
    )
    assert legendary.weight > common.weight
