"""Prompt fragment provider.

A single ``(world, character) -> list[str]`` provider feeds both the LLM actor context and
the human character-chat prompt. It surfaces two things the angler can perceive:

- the angler's own trophy log (biggest catch and recent haul), first-person, and
- any fishing spot the angler can reach (the room they stand in, or a watery object in it),
  including whether it is currently fished out.
"""

from __future__ import annotations

from bunnyland.core import reachable_ids
from bunnyland.prompts.context import ComponentPromptContext
from relics import Entity, World

from .components import CatchLogComponent, FishingSpotComponent


def anglersim_fragments(world: World, character: Entity) -> list[str]:
    lines: list[str] = []
    base = ComponentPromptContext.for_entity(world, character)
    if character.has_component(CatchLogComponent):
        lines.extend(character.get_component(CatchLogComponent).prompt_fragments(base))
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if not entity.has_component(FishingSpotComponent):
            continue
        ctx = ComponentPromptContext.for_entity(
            world, entity, room=base.room, target=character
        )
        lines.extend(entity.get_component(FishingSpotComponent).prompt_fragments(ctx))
    return sorted(dict.fromkeys(lines))


__all__ = ["anglersim_fragments"]
