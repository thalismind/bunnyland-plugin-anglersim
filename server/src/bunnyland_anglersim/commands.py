"""The ``fish`` verb: cast a line at a reachable fishing spot.

Validation order matches the project convention: invalid character -> resolve a reachable
spot (explicit target validated invalid/missing/unreachable/wrong-kind, or auto-picked) ->
cooldown -> depletion -> resolve the catch. A successful cast:

- draws a deterministic :class:`~bunnyland_anglersim.catch.Catch` from the spot's biome, the
  time of day, the spot's monotonic cast counter, and any held bait's quality,
- spawns the fish into the angler's inventory,
- consumes one use of the bait (removing it when spent),
- advances the spot (one more cast, one less stock, a fresh cooldown),
- folds the catch into the angler's trophy log, and
- emits a room ``FishCaughtEvent`` (plus a ``LegendaryCatchEvent`` for a legendary).
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import ContainmentMode, Contains, contents, reachable_ids
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_character,
    require_reachable_entity,
)
from bunnyland.core.mutations import (
    AddEdge,
    AddEntity,
    DeleteEntity,
    EntityReference,
    MutationPlan,
    SetComponent,
)

from . import connectors
from .catch import LEGENDARY, roll_catch
from .components import BaitComponent, CatchLogComponent, FishingSpotComponent, record_catch
from .events import FishCaughtEvent, LegendaryCatchEvent, RecordSetEvent
from .gear import gear_bonus_for
from .prefabs import fish_components
from .records import RecordBookComponent, offer_to_book, record_book_in
from .runs import run_bonus
from .spatial import phase_of, room_of


def _resolve_spot(ctx: HandlerContext, character, raw_spot_id):
    """Resolve (spot_entity) or a rejection HandlerResult.

    An explicit ``spot_id`` is validated for id/existence/reachability/kind; otherwise the
    first reachable fishing spot (sorted by id for determinism) is chosen.
    """
    if raw_spot_id is not None:
        spot_id, spot, rejection = require_reachable_entity(
            ctx,
            character,
            raw_spot_id,
            invalid_reason="invalid fishing spot id",
            missing_reason="that fishing spot does not exist",
            unreachable_reason="that fishing spot is not within reach",
        )
        if rejection is not None:
            return None, rejection
        if not spot.has_component(FishingSpotComponent):
            return None, rejected("that is not a fishing spot")
        return spot, None
    for entity_id in sorted(reachable_ids(ctx.world, character), key=str):
        entity = ctx.world.get_entity(entity_id)
        if entity.has_component(FishingSpotComponent):
            return entity, None
    return None, rejected("there is no fishing spot within reach")


def _held_bait(ctx: HandlerContext, character):
    """Return the first bait item in the angler's inventory (sorted by id), or ``None``.

    Inventory ``Contains`` edges always target live entities (Relics drops the edge when a
    target is removed), so no missing-entity guard is needed here.
    """
    for item_id in sorted(contents(character), key=str):
        item = ctx.world.get_entity(item_id)
        if item.has_component(BaitComponent):
            return item
    return None


def _consume_bait(ctx: HandlerContext, bait) -> None:
    component = bait.get_component(BaitComponent)
    remaining = component.uses - 1
    if remaining <= 0:
        ctx.world.remove(bait.id)
    else:
        replace_component(bait, replace(component, uses=remaining))


def _log_catch(character, species: str, weight: float) -> None:
    log = (
        character.get_component(CatchLogComponent)
        if character.has_component(CatchLogComponent)
        else CatchLogComponent()
    )
    replace_component(character, record_catch(log, species, weight))


class FishHandler:
    """Cast a line at a reachable fishing spot and land a deterministic catch."""

    command_type = "fish"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        spot, rejection = _resolve_spot(ctx, character, command.payload.get("spot_id"))
        if rejection is not None:
            return rejection
        spot_state = spot.get_component(FishingSpotComponent)
        if ctx.epoch < spot_state.ready_at_epoch:
            return rejected("that fishing spot is still settling")
        if spot_state.stock <= 0:
            return rejected("that fishing spot is fished out")

        bait = _held_bait(ctx, character)
        bait_quality = bait.get_component(BaitComponent).quality if bait is not None else 0.0
        result = roll_catch(
            spot_id=str(spot.id),
            character_id=str(character_id),
            epoch=ctx.epoch,
            casts=spot_state.casts,
            biome=spot_state.biome,
            phase=phase_of(ctx.world),
            bait_quality=bait_quality,
            gear_bonus=gear_bonus_for(ctx.world, character),
            luck_bonus=connectors.luck_bonus_for(ctx.world, character),
            run_bonus=run_bonus(ctx.world, ctx.epoch),
        )

        fish = EntityReference()
        components = list(
            fish_components(species=result.species, tier=result.tier, weight=result.weight)
        )
        operations = [
            AddEntity(tuple(components), reference=fish),
            AddEdge(character.id, fish, Contains(mode=ContainmentMode.INVENTORY)),
        ]
        if bait is not None:
            bait_component = bait.get_component(BaitComponent)
            if bait_component.uses <= 1:
                operations.append(DeleteEntity(bait.id))
            else:
                operations.append(
                    SetComponent(bait.id, replace(bait_component, uses=bait_component.uses - 1))
                )
        operations.append(
            SetComponent(
                spot.id,
                replace(
                    spot_state,
                    casts=spot_state.casts + 1,
                    stock=spot_state.stock - 1,
                    ready_at_epoch=ctx.epoch + spot_state.cooldown,
                ),
            )
        )
        log = (
            character.get_component(CatchLogComponent)
            if character.has_component(CatchLogComponent)
            else CatchLogComponent()
        )
        operations.append(
            SetComponent(character.id, record_catch(log, result.species, result.weight))
        )

        room = room_of(ctx.world, character_id)
        room_id = str(room.id) if room is not None else None
        events = [
            FishCaughtEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=room_id,
                    target_ids=(),
                    item_id="",
                    species=result.species,
                    tier=result.tier,
                    weight=result.weight,
                    spot_id=str(spot.id),
                    used_bait=bait is not None,
                )
            )
        ]
        if result.tier == LEGENDARY:
            events.append(
                LegendaryCatchEvent(
                    **ctx.event_base(
                        visibility=EventVisibility.ROOM,
                        actor_id=str(character_id),
                        room_id=room_id,
                        target_ids=(),
                        species=result.species,
                        weight=result.weight,
                        spot_id=str(spot.id),
                    )
                )
            )
        record_event = self._offer_to_record_book(ctx, character_id, room_id, result, operations)
        if record_event is not None:
            events.append(record_event)

        def deferred_event(event):
            fish_id = str(fish.require())
            return event.model_copy(
                update={
                    "target_ids": (fish_id,),
                    **({"item_id": fish_id} if isinstance(event, FishCaughtEvent) else {}),
                }
            )

        factories = tuple(lambda event=event: deferred_event(event) for event in events)
        return planned(MutationPlan(tuple(operations)), *factories)

    def _offer_to_record_book(self, ctx, character_id, room_id, result, operations):
        """Fold the catch into the community record book; emit a ``RecordSetEvent`` on a record.

        A record-setting catch is also tagged as a museum collectible (a no-op without the
        museum pack). Returns ``None`` when there is no book or the catch is not a record.
        """
        book_entity = record_book_in(ctx.world)
        if book_entity is None:
            return None
        book = book_entity.get_component(RecordBookComponent)
        updated, previous = offer_to_book(
            book, species=result.species, weight=result.weight, holder_id=str(character_id)
        )
        if previous is None:
            return None
        operations.append(SetComponent(book_entity.id, updated))
        return RecordSetEvent(
            **ctx.event_base(
                visibility=EventVisibility.ROOM,
                actor_id=str(character_id),
                room_id=room_id,
                target_ids=(),
                species=result.species,
                weight=result.weight,
                previous_weight=previous,
                holder_id=str(character_id),
                book_id=str(book_entity.id),
            )
        )


FISH_DEF = ActionDefinition(
    command_type="fish",
    title="Fish",
    description="Cast a line at a fishing spot within reach and try to land a catch.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "spot_id": ActionArgument(
            title="Fishing spot",
            description="The spot to fish; omit to use the nearest reachable spot.",
            kind="entity",
        ),
    },
)

ANGLER_ACTION_DEFINITIONS = (FISH_DEF,)
ANGLER_ACTION_HANDLERS = (FishHandler,)


__all__ = [
    "ANGLER_ACTION_DEFINITIONS",
    "ANGLER_ACTION_HANDLERS",
    "FISH_DEF",
    "FishHandler",
]
