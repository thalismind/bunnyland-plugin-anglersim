from __future__ import annotations

from bunnyland_anglersim.catch import (
    _BASE_TABLES,
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
    assert first.species == "lake trout"
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


def test_all_species_tuples_are_sorted():
    # roll_catch indexes into the pool by digest, so the sort is load-bearing:
    # an unsorted pool would silently change which species a fixed input resolves to.
    for biome, tiers in _BASE_TABLES.items():
        for tier, pool in tiers.items():
            assert list(pool) == sorted(pool), (biome, tier)


def test_catalogue_is_wide_across_biomes_and_tiers():
    # Guards against an accidental shrink of the expanded catalogue.
    all_species = {
        species
        for tiers in _BASE_TABLES.values()
        for pool in tiers.values()
        for species in pool
    }
    assert len(all_species) >= 90
    for biome in WATER_BIOMES:
        assert len(_BASE_TABLES[biome]["common"]) >= 6
        assert len(_BASE_TABLES[biome]["rare"]) >= 3
        assert len(_BASE_TABLES[biome]["legendary"]) >= 2


def test_non_fish_catches_resolve_deterministically():
    # Crustaceans, shellfish, eels, cephalopods, junk, and treasure are all reachable
    # from pinned epochs — proving the wider catalogue participates in real rolls.
    cases = {
        # (biome, phase, epoch): (species, tier)
        ("lake", "day", 14): ("crayfish", "common"),  # crustacean
        ("coast", "day", 42): ("spiny lobster", "uncommon"),  # crustacean
        ("marsh", "day", 1): ("american eel", "rare"),  # eel
        ("ship", "day", 29): ("giant squid", "rare"),  # cephalopod
        ("coast", "day", 6): ("sunken treasure chest", "legendary"),  # treasure
        ("river", "day", 4): ("lost signet ring", "legendary"),  # treasure
    }
    for (biome, phase, epoch), (species, tier) in cases.items():
        result = roll_catch(
            spot_id="s",
            character_id="c",
            epoch=epoch,
            casts=0,
            biome=biome,
            phase=phase,
            bait_quality=2.0,
        )
        assert (result.species, result.tier) == (species, tier)


def test_every_tier_is_reachable_in_every_biome():
    base = dict(spot_id="s", character_id="c", casts=0, bait_quality=2.0)
    for biome in WATER_BIOMES:
        for phase in ("day", "night"):
            seen_tiers = {
                roll_catch(epoch=e, biome=biome, phase=phase, **base).tier
                for e in range(400)
            }
            assert seen_tiers == set(TIER_ORDER)


def test_junk_items_are_only_common_tier():
    junk = {
        "old boot",
        "rusty can",
        "rusty bucket",
        "tangled net",
        "frayed rope",
        "driftwood",
        "waterlogged branch",
    }
    for biome, tiers in _BASE_TABLES.items():
        for tier, pool in tiers.items():
            overlap = junk & set(pool)
            if overlap:
                assert tier == "common", (biome, tier, overlap)


def test_treasures_are_only_legendary_tier():
    treasures = {
        "sunken treasure chest",
        "jeweled crown",
        "mire idol",
        "lost signet ring",
        "pirate doubloon hoard",
    }
    for biome, tiers in _BASE_TABLES.items():
        for tier, pool in tiers.items():
            overlap = treasures & set(pool)
            if overlap:
                assert tier == "legendary", (biome, tier, overlap)
