"""The fishing derby: enter a caught fish, then judge it to crown the heaviest.

The headline social mechanic. A :class:`DerbyComponent` marks a derby entity (seeded into a
fishing-hub room by worldgen, or spawned directly). Anglers **enter** a held fish with the
``enter-derby`` verb; each entry is a typed :class:`DerbyEntry` edge from the derby to the
fish, carrying who entered it and its weight — never a list on the component, so each entry is
its own index. **Judging** (``judge-derby``) closes the derby and crowns the heaviest entry,
ties broken deterministically by entity id.

The derby is self-contained. When ``festivalsim`` is loaded its open ``ContestEntry`` surface
is *also* fed the entry (via :mod:`bunnyland_anglersim.connectors`) so a derby can double as a
festival contest; when it is absent, that mirror is simply a no-op.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    ContainmentMode,
    Contains,
    IdentityComponent,
    contents,
    reachable_ids,
    spawn_entity,
)
from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Edge, Entity, World

from . import connectors
from .components import FishComponent
from .events import DerbyEnteredEvent, DerbyJudgedEvent

#: How many standings the derby prompt fragment surfaces (heaviest first).
DERBY_FRAGMENT_LIMIT = 3


@dataclass(frozen=True)
class DerbyComponent(Component):
    """A fishing derby that ranks entered fish by weight.

    ``open`` gates entry and judging; once judged it closes and records the ``winner_id`` and
    the ``winning_weight`` so the result is durable across save/reload.
    """

    title: str = "Fishing Derby"
    open: bool = True
    winner_id: str = ""
    winning_weight: float = 0.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not self.open:
            if self.winner_id:
                return (f"The {self.title} is over — a {self.winning_weight:.1f} lb fish won.",)
            return (f"The {self.title} is closed.",)
        standings = derby_standings(ctx.entity)
        if not standings:
            return (f"The {self.title} is open for entries — no fish weighed in yet.",)
        lines = [f"{self.title} leaderboard:"]
        for species, weight, _entrant in standings[:DERBY_FRAGMENT_LIMIT]:
            lines.append(f"- {species}: {weight:.1f} lb")
        return (" ".join(lines),)


@dataclass(frozen=True)
class DerbyEntry(Edge):
    """A derby -> entered-fish edge, recording who entered it and its weight."""

    entrant_id: str = ""
    species: str = ""
    weight: float = 0.0
    entered_at_epoch: int = 0


def derby_entries(derby: Entity) -> list[tuple[DerbyEntry, object]]:
    """Return the ``(edge, fish_id)`` entries, heaviest first (ties by fish id)."""
    entries = list(derby.get_relationships(DerbyEntry))
    return sorted(entries, key=lambda pair: (-pair[0].weight, str(pair[1])))


def derby_standings(derby: Entity) -> list[tuple[str, float, str]]:
    """Return ``(species, weight, entrant_id)`` rows for a derby, heaviest first."""
    return [(edge.species, edge.weight, edge.entrant_id) for edge, _fish in derby_entries(derby)]


def has_entry(derby: Entity, fish_id) -> bool:
    """Whether ``fish_id`` is already entered in the derby."""
    return any(target == fish_id for _edge, target in derby.get_relationships(DerbyEntry))


def spawn_derby(world: World, *, room_id=None, title: str = "Fishing Derby") -> Entity:
    """Spawn an open derby entity, optionally placed in ``room_id``."""
    derby = spawn_entity(
        world,
        [
            IdentityComponent(name=title, kind="feature", tags=("anglersim", "derby")),
            DerbyComponent(title=title),
        ],
    )
    if room_id is not None and world.has_entity(room_id):
        world.get_entity(room_id).add_relationship(
            Contains(mode=ContainmentMode.ROOM_CONTENT), derby.id
        )
    return derby


def _resolve_derby(ctx: HandlerContext, character, raw_derby_id):
    """Resolve the target derby entity, or a rejection HandlerResult."""
    if raw_derby_id is not None:
        _derby_id, derby, rejection = require_reachable_entity(
            ctx,
            character,
            raw_derby_id,
            invalid_reason="invalid derby id",
            missing_reason="that derby does not exist",
            unreachable_reason="that derby is not within reach",
        )
        if rejection is not None:
            return None, rejection
        if not derby.has_component(DerbyComponent):
            return None, rejected("that is not a fishing derby")
        return derby, None
    for entity_id in sorted(reachable_ids(ctx.world, character), key=str):
        entity = ctx.world.get_entity(entity_id)
        if entity.has_component(DerbyComponent):
            return entity, None
    return None, rejected("there is no fishing derby within reach")


def _resolve_fish(ctx: HandlerContext, character, raw_fish_id):
    """Resolve the held fish to enter (explicit id or the heaviest held), or a rejection."""
    if raw_fish_id is not None:
        _fish_id, fish, rejection = require_reachable_entity(
            ctx,
            character,
            raw_fish_id,
            invalid_reason="invalid fish id",
            missing_reason="that fish does not exist",
            unreachable_reason="that fish is not within reach",
        )
        if rejection is not None:
            return None, rejection
        if not fish.has_component(FishComponent):
            return None, rejected("that is not a fish")
        return fish, None
    best = None
    best_weight = -1.0
    for item_id in sorted(contents(character), key=str):
        item = ctx.world.get_entity(item_id)
        if item.has_component(FishComponent):
            weight = item.get_component(FishComponent).weight
            if weight > best_weight:
                best, best_weight = item, weight
    if best is None:
        return None, rejected("you have no fish to enter")
    return best, None


class EnterDerbyHandler:
    """Enter a held fish into a reachable fishing derby."""

    command_type = "enter-derby"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        derby, rejection = _resolve_derby(ctx, character, command.payload.get("derby_id"))
        if rejection is not None:
            return rejection
        if not derby.get_component(DerbyComponent).open:
            return rejected("that derby is closed")
        fish, rejection = _resolve_fish(ctx, character, command.payload.get("fish_id"))
        if rejection is not None:
            return rejection
        if has_entry(derby, fish.id):
            return rejected("that fish is already entered")
        catch = fish.get_component(FishComponent)
        derby.add_relationship(
            DerbyEntry(
                entrant_id=str(character_id),
                species=catch.species,
                weight=catch.weight,
                entered_at_epoch=ctx.epoch,
            ),
            fish.id,
        )
        connectors.publish_contest_entry(
            ctx.world,
            derby,
            fish.id,
            entrant_id=str(character_id),
            score=catch.weight,
            epoch=ctx.epoch,
        )
        return ok(
            DerbyEnteredEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    target_ids=(str(fish.id),),
                    derby_id=str(derby.id),
                    entrant_id=str(character_id),
                    entry_id=str(fish.id),
                    species=catch.species,
                    weight=catch.weight,
                )
            )
        )


class JudgeDerbyHandler:
    """Judge a reachable derby, closing it and crowning the heaviest entry."""

    command_type = "judge-derby"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        derby, rejection = _resolve_derby(ctx, character, command.payload.get("derby_id"))
        if rejection is not None:
            return rejection
        state = derby.get_component(DerbyComponent)
        if not state.open:
            return rejected("that derby has already been judged")
        entries = derby_entries(derby)
        if not entries:
            return rejected("that derby has no entries to judge")
        winning_edge, winning_fish = entries[0]
        replace_component(
            derby,
            replace(
                state,
                open=False,
                winner_id=winning_edge.entrant_id,
                winning_weight=winning_edge.weight,
            ),
        )
        return ok(
            DerbyJudgedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    target_ids=(str(winning_fish),),
                    derby_id=str(derby.id),
                    winner_id=winning_edge.entrant_id,
                    entry_id=str(winning_fish),
                    species=winning_edge.species,
                    weight=winning_edge.weight,
                )
            )
        )


ENTER_DERBY_DEF = ActionDefinition(
    command_type="enter-derby",
    title="Enter derby",
    description="Enter a held fish into a fishing derby within reach.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "derby_id": ActionArgument(
            title="Derby",
            description="The derby to enter; omit to use the nearest reachable derby.",
            kind="entity",
        ),
        "fish_id": ActionArgument(
            title="Fish",
            description="The held fish to enter; omit to enter your heaviest fish.",
            kind="entity",
        ),
    },
)

JUDGE_DERBY_DEF = ActionDefinition(
    command_type="judge-derby",
    title="Judge derby",
    description="Judge a fishing derby within reach, crowning the heaviest fish.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "derby_id": ActionArgument(
            title="Derby",
            description="The derby to judge; omit to use the nearest reachable derby.",
            kind="entity",
        ),
    },
)

DERBY_ACTION_DEFINITIONS = (ENTER_DERBY_DEF, JUDGE_DERBY_DEF)
DERBY_ACTION_HANDLERS = (EnterDerbyHandler, JudgeDerbyHandler)


__all__ = [
    "DERBY_ACTION_DEFINITIONS",
    "DERBY_ACTION_HANDLERS",
    "DERBY_FRAGMENT_LIMIT",
    "ENTER_DERBY_DEF",
    "JUDGE_DERBY_DEF",
    "DerbyComponent",
    "DerbyEntry",
    "EnterDerbyHandler",
    "JudgeDerbyHandler",
    "derby_entries",
    "derby_standings",
    "has_entry",
    "spawn_derby",
]
