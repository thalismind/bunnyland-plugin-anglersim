"""Deterministic catch resolution: rarity tiers, per-biome tables, and the roll.

Bunnyland is deterministic and its coverage gate is strict, so **nothing here touches
``random``, ``time``, or hash-ordered set iteration**. Each catch is derived from a
``blake2b`` digest of stable inputs — the spot id, the angler id, the epoch, and the spot's
monotonic cast counter — reduced over sorted, weighted tables. The same inputs always
produce the same fish.

Resolution has three independent draws (tier, species, weight), each keyed by a different
digest personalisation so they do not correlate. The table is keyed by ``biome`` and
time-of-day ``phase``: night unlocks an extra nocturnal legendary and nudges the tier
weights toward the rare end.
"""

from __future__ import annotations

import hashlib
from typing import NamedTuple

#: Water biomes the pack understands, sorted for stable iteration.
WATER_BIOMES: tuple[str, ...] = ("coast", "lake", "marsh", "river", "ship")

#: Biome used when a spot's biome is not one of :data:`WATER_BIOMES`.
DEFAULT_BIOME = "lake"

#: Rarity tiers in ascending rarity; the fixed order makes weighted selection stable.
TIER_ORDER: tuple[str, ...] = ("common", "uncommon", "rare", "legendary")

#: The rarest tier, whose catches raise a room-wide event.
LEGENDARY = "legendary"

#: Baseline selection weight per tier before bait/phase adjustments.
BASE_TIER_WEIGHTS: dict[str, int] = {
    "common": 60,
    "uncommon": 25,
    "rare": 12,
    "legendary": 3,
}

#: Minimum weight (pounds) per tier, before the deterministic fractional bonus.
TIER_BASE_WEIGHT_LB: dict[str, float] = {
    "common": 0.5,
    "uncommon": 1.5,
    "rare": 4.0,
    "legendary": 12.0,
}

#: Fractional weight span (pounds) added on top of the tier base.
TIER_WEIGHT_SPREAD_LB: dict[str, float] = {
    "common": 1.0,
    "uncommon": 2.5,
    "rare": 6.0,
    "legendary": 20.0,
}

#: Phases (from the environment mechanic) treated as night for nocturnal catches.
NIGHT_PHASES: frozenset[str] = frozenset({"night"})

#: Day catch tables: ``biome -> tier -> species``.
#:
#: The catalogue is deliberately wide: alongside fish it holds crustaceans, shellfish,
#: eels, cephalopods, and the odd bit of waterlogged junk in the common tiers, with rare
#: treasures salted into the legendary tiers. Every species tuple is kept in sorted order
#: because :func:`roll_catch` indexes into the pool by digest — the sort is what makes the
#: deterministic selection reproducible.
_BASE_TABLES: dict[str, dict[str, tuple[str, ...]]] = {
    "coast": {
        "common": (
            "anchovy",
            "driftwood",
            "herring",
            "mackerel",
            "sardine",
            "shore crab",
            "smelt",
            "tangled net",
            "whiting",
        ),
        "uncommon": (
            "blue mussel",
            "flounder",
            "mullet",
            "pompano",
            "sea bass",
            "spiny lobster",
        ),
        "rare": ("barracuda", "conger eel", "swordfish", "tuna", "wahoo"),
        "legendary": ("giant marlin", "sunken treasure chest"),
    },
    "lake": {
        "common": (
            "bluegill",
            "crayfish",
            "old boot",
            "perch",
            "pumpkinseed",
            "roach",
            "sunfish",
            "waterlogged branch",
        ),
        "uncommon": ("bass", "crappie", "freshwater clam", "lake whitefish", "walleye"),
        "rare": ("burbot", "lake trout", "muskie", "sturgeon"),
        "legendary": ("golden koi", "jeweled crown"),
    },
    "marsh": {
        "common": (
            "killifish",
            "leech",
            "mosquitofish",
            "mudminnow",
            "rusty bucket",
            "stickleback",
            "tadpole",
        ),
        "uncommon": ("bog crab", "bowfin", "bullhead catfish", "gar", "mud snail"),
        "rare": ("american eel", "snakehead", "swamp eel"),
        "legendary": ("bog leviathan", "mire idol"),
    },
    "river": {
        "common": (
            "chub",
            "dace",
            "gudgeon",
            "minnow",
            "river crab",
            "rusty can",
            "stone loach",
        ),
        "uncommon": ("barbel", "grayling", "pike", "rudd", "trout"),
        "rare": ("brown trout", "salmon", "steelhead", "taimen"),
        "legendary": ("lost signet ring", "river emperor"),
    },
    "ship": {
        "common": ("cod", "dab", "frayed rope", "haddock", "pilchard", "pollock", "sprat"),
        "uncommon": ("grouper", "halibut", "ling", "snapper", "tilefish"),
        "rare": ("bluefin tuna", "giant squid", "oarfish", "opah"),
        "legendary": ("kraken hatchling", "pirate doubloon hoard"),
    },
}

#: Extra legendary species that only surface at night, per biome.
_NOCTURNAL_LEGENDARY: dict[str, tuple[str, ...]] = {
    "coast": ("moonlit anglerfish",),
    "lake": ("lake wyrm",),
    "marsh": ("will-o-carp",),
    "river": ("ghost eel",),
    "ship": ("abyssal lanternfish",),
}


class Catch(NamedTuple):
    """The resolved result of one cast."""

    species: str
    tier: str
    weight: float


def canonical_biome(biome: str) -> str:
    """Map an arbitrary biome onto a table key, falling back to :data:`DEFAULT_BIOME`."""
    return biome if biome in WATER_BIOMES else DEFAULT_BIOME


def catch_table(biome: str, phase: str) -> dict[str, tuple[str, ...]]:
    """Return the ``tier -> species`` table for ``biome`` at time-of-day ``phase``."""
    base = _BASE_TABLES[canonical_biome(biome)]
    table = {tier: base[tier] for tier in TIER_ORDER}
    if phase in NIGHT_PHASES:
        nocturnal = _NOCTURNAL_LEGENDARY[canonical_biome(biome)]
        table[LEGENDARY] = tuple(sorted(table[LEGENDARY] + nocturnal))
    return table


def tier_weights(phase: str, bait_quality: float = 0.0) -> dict[str, int]:
    """Selection weights per tier, biased by bait quality and night.

    Bait and night add absolute weight to the rare and legendary tiers, which lifts their
    share without ever removing the chance of a common catch.
    """
    weights = dict(BASE_TIER_WEIGHTS)
    bonus = max(0, int(round(bait_quality * 10)))
    weights["rare"] += 2 * bonus
    weights["legendary"] += bonus
    if phase in NIGHT_PHASES:
        weights["rare"] += 3
        weights["legendary"] += 4
    return weights


def _digest_int(kind: str, spot_id: str, character_id: str, epoch: int, casts: int) -> int:
    key = f"{kind}|{spot_id}|{character_id}|{epoch}|{casts}".encode()
    return int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big")


def _weighted_tier(draw: int, weights: dict[str, int]) -> str:
    total = sum(weights[tier] for tier in TIER_ORDER)
    pick = draw % total
    cumulative = 0
    # The last tier absorbs the remaining probability mass, so it is the guaranteed default.
    for tier in TIER_ORDER[:-1]:
        cumulative += weights[tier]
        if pick < cumulative:
            return tier
    return TIER_ORDER[-1]


def _weight_for(tier: str, draw: int) -> float:
    base = TIER_BASE_WEIGHT_LB[tier]
    spread = TIER_WEIGHT_SPREAD_LB[tier]
    return round(base + spread * ((draw % 1000) / 1000.0), 2)


def roll_catch(
    *,
    spot_id: str,
    character_id: str,
    epoch: int,
    casts: int,
    biome: str,
    phase: str,
    bait_quality: float = 0.0,
) -> Catch:
    """Deterministically resolve one cast into a :class:`Catch`."""
    weights = tier_weights(phase, bait_quality)
    tier = _weighted_tier(_digest_int("tier", spot_id, character_id, epoch, casts), weights)
    pool = catch_table(biome, phase)[tier]
    species = pool[_digest_int("species", spot_id, character_id, epoch, casts) % len(pool)]
    weight = _weight_for(tier, _digest_int("weight", spot_id, character_id, epoch, casts))
    return Catch(species=species, tier=tier, weight=weight)


__all__ = [
    "BASE_TIER_WEIGHTS",
    "DEFAULT_BIOME",
    "LEGENDARY",
    "NIGHT_PHASES",
    "TIER_BASE_WEIGHT_LB",
    "TIER_ORDER",
    "TIER_WEIGHT_SPREAD_LB",
    "WATER_BIOMES",
    "Catch",
    "canonical_biome",
    "catch_table",
    "roll_catch",
    "tier_weights",
]
