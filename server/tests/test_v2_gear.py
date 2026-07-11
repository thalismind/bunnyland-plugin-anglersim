from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.prompts.context import ComponentPromptContext

from bunnyland_anglersim import gear_bonus_for, spawn_rod, spawn_tackle
from bunnyland_anglersim.gear import (
    ROD_POWER,
    TACKLE_POWER,
    RodComponent,
    TackleComponent,
)


def for_ctx(world, entity, viewer):
    return ComponentPromptContext.for_entity(world, entity, target=viewer)


def _world():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Dock", biome="lake")])
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    return actor, room, holder


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def test_rod_and_tackle_power_from_tier():
    assert RodComponent(tier="masterwork").power == ROD_POWER["masterwork"]
    assert TackleComponent(tier="lure").power == TACKLE_POWER["lure"]
    assert RodComponent(tier="unknown").power == 0.0
    assert TackleComponent(tier="unknown").power == 0.0


def test_gear_bonus_sums_best_rod_and_tackle():
    actor, room, holder = _world()
    _hold(holder, spawn_rod(actor.world, tier="cane"))
    _hold(holder, spawn_rod(actor.world, tier="carbon"))  # stronger rod wins
    _hold(holder, spawn_tackle(actor.world, tier="hook"))
    bonus = gear_bonus_for(actor.world, holder)
    assert bonus == ROD_POWER["carbon"] + TACKLE_POWER["hook"]


def test_gear_bonus_is_zero_without_gear():
    actor, _room, holder = _world()
    assert gear_bonus_for(actor.world, holder) == 0.0


def test_gear_bonus_skips_removed_items():
    actor, _room, holder = _world()
    rod = spawn_rod(actor.world, tier="fiberglass")
    _hold(holder, rod)
    actor.world.remove(rod.id)
    assert gear_bonus_for(actor.world, holder) == 0.0


def test_spawn_rod_places_in_room():
    actor, room, _holder = _world()
    rod = spawn_rod(actor.world, room_id=room.id, tier="carbon")
    assert rod.get_component(RodComponent).tier == "carbon"


def test_gear_prompt_fragments():
    actor, room, holder = _world()
    rod = spawn_rod(actor.world, tier="masterwork")
    tackle = spawn_tackle(actor.world, tier="lure")
    assert (
        "masterwork fishing rod"
        in rod.get_component(RodComponent).prompt_fragments(for_ctx(actor.world, rod, holder))[0]
    )
    assert (
        "lure tackle"
        in tackle.get_component(TackleComponent).prompt_fragments(
            for_ctx(actor.world, tackle, holder)
        )[0]
    )
