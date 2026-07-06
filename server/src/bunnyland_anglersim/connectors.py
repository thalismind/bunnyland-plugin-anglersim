"""Safe, optional bridges to sibling packs.

Anglersim is fully playable on its own. These helpers reach for *other* packs' open
connector surfaces through a bare ``try/except ImportError`` so that, when a partner pack
isn't loaded, the corresponding synergy simply stays off — never an error. Each partner is
declared as a ``recommends`` (never ``requires``) in the plugin so the pack loads standalone.

Consumed (odds/ingredient biases we read):
    - fortunesim ``LuckComponent`` — a character's luck nudges its catch odds.
    - hearthsim ``IngredientComponent`` — kitchen ingredients double as bait materials.

Published (surfaces we hand to others when they're present):
    - museumsim ``CollectibleComponent`` — a legendary/record fish becomes museum loot.
    - festivalsim ``ContestEntry`` — a derby entry is mirrored into a festival contest.
"""

from __future__ import annotations

from bunnyland.core.ecs import replace_component
from relics import Entity, World

try:  # fortunesim: luck as a read-only odds bias
    from bunnyland_fortunesim import LuckComponent
except ImportError:  # pragma: no cover - exercised via the standalone path
    LuckComponent = None

try:  # hearthsim: ingredients as bait materials
    from bunnyland_hearthsim import IngredientComponent
except ImportError:  # pragma: no cover - exercised via the standalone path
    IngredientComponent = None

try:  # museumsim: donate-able collectible tag
    from bunnyland_museumsim import CollectibleComponent
except ImportError:  # pragma: no cover - exercised via the standalone path
    CollectibleComponent = None

try:  # festivalsim: open contest-entry registration
    from bunnyland_festivalsim import register_contest_entry
except ImportError:  # pragma: no cover - exercised via the standalone path
    register_contest_entry = None

#: How strongly a point of luck bends the catch odds (folded into the roll's quality).
LUCK_SCALE = 0.1

#: Bait potency floor an ingredient contributes, before any high-value tag bonus.
INGREDIENT_BASE_POTENCY = 0.3

#: Ingredient tags that make especially tempting bait.
BAIT_TAGS: frozenset[str] = frozenset({"meat", "fish", "bug", "grub", "worm", "offal"})

#: Anglersim rarity tiers mapped onto museum's rarity ladder.
_MUSEUM_RARITY: dict[str, str] = {
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "legendary": "legendary",
}


def luck_bonus_for(world: World, character: Entity) -> float:
    """Return the character's luck-derived catch-odds bonus, or ``0.0`` when fortunesim is off."""
    if LuckComponent is None or not character.has_component(LuckComponent):
        return 0.0
    return character.get_component(LuckComponent).value * LUCK_SCALE


def ingredient_potency(item: Entity) -> float | None:
    """Bait potency of a hearthsim ingredient item, or ``None`` if it isn't one.

    Returns ``None`` when hearthsim is absent or the item carries no ingredient tag, so the
    caller can fall back to anglersim's own bait materials.
    """
    if IngredientComponent is None or not item.has_component(IngredientComponent):
        return None
    tags = item.get_component(IngredientComponent).tags
    bonus = 0.2 * len(BAIT_TAGS.intersection(tags))
    return INGREDIENT_BASE_POTENCY + bonus


def tag_collectible(fish: Entity, tier: str) -> bool:
    """Tag a caught fish as a museum collectible; a no-op returning ``False`` without museum."""
    if CollectibleComponent is None:
        return False
    replace_component(
        fish, CollectibleComponent(category="fish", rarity=_MUSEUM_RARITY.get(tier, "common"))
    )
    return True


def publish_contest_entry(
    world: World, contest: Entity, entry_id, *, entrant_id: str, score: float, epoch: int
) -> bool:
    """Mirror a derby entry into a festival contest; a no-op returning ``False`` when absent."""
    if register_contest_entry is None:
        return False
    register_contest_entry(
        world, contest, entry_id, entrant_id=entrant_id, score=score, epoch=epoch
    )
    return True


__all__ = [
    "BAIT_TAGS",
    "INGREDIENT_BASE_POTENCY",
    "LUCK_SCALE",
    "ingredient_potency",
    "luck_bonus_for",
    "publish_contest_entry",
    "tag_collectible",
]
