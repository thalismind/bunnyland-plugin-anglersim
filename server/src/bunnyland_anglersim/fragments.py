"""Prompt fragment provider.

A single ``(world, character) -> list[str]`` provider feeds both the LLM actor context and
the human character-chat prompt. It surfaces what the angler can perceive:

- the angler's own trophy log (biggest catch and recent haul), first-person,
- any reachable fishing spot, record book, derby, or held gear/bait material — each component
  renders its own state, and
- a line when a seasonal fishing run is live.
"""

from __future__ import annotations

from bunnyland.core import WorldClockComponent, reachable_ids
from bunnyland.prompts.context import ComponentPromptContext
from relics import Entity, World

from .components import CatchLogComponent, FishingSpotComponent
from .crafting import BaitMaterialComponent
from .derby import DerbyComponent
from .gear import RodComponent, TackleComponent
from .records import RecordBookComponent
from .runs import runs_fragment

#: Reachable-entity components that describe themselves in the angler's prompt.
_REACHABLE_COMPONENTS: tuple[type, ...] = (
    FishingSpotComponent,
    RecordBookComponent,
    DerbyComponent,
    RodComponent,
    TackleComponent,
    BaitMaterialComponent,
)


def _world_epoch(world: World) -> int:
    clocks = sorted(
        world.query().with_all([WorldClockComponent]).execute_entities(), key=lambda e: str(e.id)
    )
    if not clocks:
        return 0
    return clocks[0].get_component(WorldClockComponent).game_time_seconds


def anglersim_fragments(world: World, character: Entity) -> list[str]:
    lines: list[str] = []
    base = ComponentPromptContext.for_entity(world, character)
    if character.has_component(CatchLogComponent):
        lines.extend(character.get_component(CatchLogComponent).prompt_fragments(base))
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        ctx = ComponentPromptContext.for_entity(
            world, entity, room=base.room, target=character
        )
        for component_type in _REACHABLE_COMPONENTS:
            if entity.has_component(component_type):
                lines.extend(entity.get_component(component_type).prompt_fragments(ctx))
    run_line = runs_fragment(world, _world_epoch(world))
    if run_line is not None:
        lines.append(run_line)
    return sorted(dict.fromkeys(lines))


__all__ = ["anglersim_fragments"]
