"""Bait crafting: the ``craft-bait`` verb turns held materials into a bait item.

Materials can come from three sources, checked in order so the pack is complete on its own:

1. Anglersim's own :class:`BaitMaterialComponent` (worms, dough, grubs) — always available.
2. A core :class:`FoodComponent` raw item — so a harvested crop (gardensim), a ration
   (colonysim), or any edible works as cut bait, spanning the inner ring through one core tag.
3. A hearthsim ``IngredientComponent`` — kitchen ingredients, when hearthsim is loaded.

A cast's bait quality is the sum of its materials' potencies over a base, so more (and richer)
materials make better bait. Crafting consumes every material it used.
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
from bunnyland.core.actions import ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
)
from bunnyland.foundation.consumables.components import FoodComponent
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from . import connectors
from .events import BaitCraftedEvent
from .prefabs import spawn_bait

#: Baseline quality every crafted bait starts from, before material potency.
BASE_BAIT_QUALITY = 0.5

#: Ceiling a single crafted bait's quality is clamped to.
MAX_BAIT_QUALITY = 3.0


@dataclass(frozen=True)
class BaitMaterialComponent(Component):
    """A raw bait material (worm, dough, grub). ``potency`` feeds the crafted bait's quality."""

    label: str = "worm"
    potency: float = 0.5

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return (f"Some {self.label}, good for making bait, is within reach.",)


def material_potency(item: Entity) -> float | None:
    """Bait potency of an item, or ``None`` if it can't be used as a material."""
    if item.has_component(BaitMaterialComponent):
        return item.get_component(BaitMaterialComponent).potency
    ingredient = connectors.ingredient_potency(item)
    if ingredient is not None:
        return ingredient
    if item.has_component(FoodComponent):
        food = item.get_component(FoodComponent)
        return round(min(1.5, food.nutrition / 20.0), 2)
    return None


def _held_materials(ctx: HandlerContext, character: Entity) -> list[tuple[Entity, float]]:
    """Held items usable as bait materials, sorted by id, paired with their potency."""
    materials: list[tuple[Entity, float]] = []
    for item_id in sorted(contents(character), key=str):
        if not ctx.world.has_entity(item_id):
            continue
        item = ctx.world.get_entity(item_id)
        potency = material_potency(item)
        if potency is not None:
            materials.append((item, potency))
    return materials


def bait_quality(potencies: list[float]) -> float:
    """The quality of a bait crafted from ``potencies`` (clamped to :data:`MAX_BAIT_QUALITY`)."""
    return round(min(MAX_BAIT_QUALITY, BASE_BAIT_QUALITY + sum(potencies)), 2)


def spawn_bait_material(
    world: World, *, room_id=None, label: str = "worm", potency: float = 0.5
) -> Entity:
    """Spawn a raw bait material item, optionally placed in ``room_id``."""
    material = spawn_entity(
        world,
        [
            IdentityComponent(name=label, kind="item", tags=("anglersim", "bait-material")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            BaitMaterialComponent(label=label, potency=potency),
        ],
    )
    if room_id is not None and world.has_entity(room_id):
        world.get_entity(room_id).add_relationship(
            Contains(mode=ContainmentMode.ROOM_CONTENT), material.id
        )
    return material


class CraftBaitHandler:
    """Combine held bait materials into a single bait item."""

    command_type = "craft-bait"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        materials = _held_materials(ctx, character)
        if not materials:
            return rejected("you have no bait materials to craft with")
        quality = bait_quality([potency for _item, potency in materials])
        for item, _potency in materials:
            ctx.world.remove(item.id)
        bait = spawn_bait(ctx.world, name="crafted bait", quality=quality, uses=1)
        character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), bait.id)
        return ok(
            BaitCraftedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    target_ids=(str(bait.id),),
                    item_id=str(bait.id),
                    quality=quality,
                    materials=len(materials),
                )
            )
        )


CRAFT_BAIT_DEF = ActionDefinition(
    command_type="craft-bait",
    title="Craft bait",
    description="Combine held bait materials (worms, dough, scraps) into a bait.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.EXTENDED),
    arguments={},
)

CRAFTING_ACTION_DEFINITIONS = (CRAFT_BAIT_DEF,)
CRAFTING_ACTION_HANDLERS = (CraftBaitHandler,)


__all__ = [
    "BASE_BAIT_QUALITY",
    "CRAFTING_ACTION_DEFINITIONS",
    "CRAFTING_ACTION_HANDLERS",
    "CRAFT_BAIT_DEF",
    "MAX_BAIT_QUALITY",
    "BaitMaterialComponent",
    "CraftBaitHandler",
    "bait_quality",
    "material_potency",
    "spawn_bait_material",
]
