"""Rod and tackle tiers: held gear that biases the catch roll.

Two ordered tier ladders — rods (the pole) and tackle (line, hook, and lure) — each grant a
deterministic *power* that folds into :func:`~bunnyland_anglersim.catch.roll_catch` as a
gear bonus. Better gear nudges the roll toward rarer, heavier fish without ever removing the
chance of a common catch. Gear is carried, not consumed: unlike bait it survives every cast.

Both components are frozen tags that store only a ``tier`` string; the power is a pure
function of the tier so the ladders can be re-tuned in one place and stay stable under
save/reload.
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    contents,
    spawn_entity,
)
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

#: Rod tiers in ascending capability; the index is the rank.
ROD_TIERS: tuple[str, ...] = ("cane", "fiberglass", "carbon", "masterwork")

#: Catch-odds power each rod tier lends the roll.
ROD_POWER: dict[str, float] = {
    "cane": 0.0,
    "fiberglass": 0.4,
    "carbon": 0.9,
    "masterwork": 1.6,
}

#: Tackle tiers in ascending capability; the index is the rank.
TACKLE_TIERS: tuple[str, ...] = ("bare", "hook", "spinner", "lure")

#: Catch-odds power each tackle tier lends the roll.
TACKLE_POWER: dict[str, float] = {
    "bare": 0.0,
    "hook": 0.2,
    "spinner": 0.5,
    "lure": 1.0,
}


@dataclass(frozen=True)
class RodComponent(Component):
    """A held fishing rod. ``tier`` keys its :data:`ROD_POWER` catch-odds bonus."""

    tier: str = "cane"

    @property
    def power(self) -> float:
        return ROD_POWER.get(self.tier, 0.0)

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return (f"A {self.tier} fishing rod rests within reach.",)


@dataclass(frozen=True)
class TackleComponent(Component):
    """Held tackle (line, hook, lure). ``tier`` keys its :data:`TACKLE_POWER` bonus."""

    tier: str = "bare"

    @property
    def power(self) -> float:
        return TACKLE_POWER.get(self.tier, 0.0)

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return (f"A set of {self.tier} tackle rests within reach.",)


def gear_bonus_for(world: World, character: Entity) -> float:
    """Return the best held rod power plus the best held tackle power (each independent).

    A character carries at most one of each in practice, but if several are held the strongest
    of each kind wins, sorted by id for a stable tie-break.
    """
    best_rod = 0.0
    best_tackle = 0.0
    for item_id in sorted(contents(character), key=str):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(RodComponent):
            best_rod = max(best_rod, item.get_component(RodComponent).power)
        if item.has_component(TackleComponent):
            best_tackle = max(best_tackle, item.get_component(TackleComponent).power)
    return best_rod + best_tackle


def spawn_rod(world: World, *, room_id=None, tier: str = "cane") -> Entity:
    """Spawn a rod item of ``tier``, optionally placed in ``room_id``."""
    rod = spawn_entity(
        world,
        [
            IdentityComponent(name=f"{tier} rod", kind="item", tags=("anglersim", "rod")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            RodComponent(tier=tier),
        ],
    )
    _link(world, rod, room_id)
    return rod


def spawn_tackle(world: World, *, room_id=None, tier: str = "hook") -> Entity:
    """Spawn a tackle item of ``tier``, optionally placed in ``room_id``."""
    tackle = spawn_entity(
        world,
        [
            IdentityComponent(name=f"{tier} tackle", kind="item", tags=("anglersim", "tackle")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            TackleComponent(tier=tier),
        ],
    )
    _link(world, tackle, room_id)
    return tackle


def _link(world: World, item: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(
        Contains(mode=ContainmentMode.ROOM_CONTENT), item.id
    )


__all__ = [
    "ROD_POWER",
    "ROD_TIERS",
    "TACKLE_POWER",
    "TACKLE_TIERS",
    "RodComponent",
    "TackleComponent",
    "gear_bonus_for",
    "spawn_rod",
    "spawn_tackle",
]
