from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    contents,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext
from bunnyland.foundation.consumables.components import FoodComponent
from bunnyland.prompts.context import ComponentPromptContext
from conftest import execute_handler

from bunnyland_anglersim import bait_quality, material_potency, spawn_bait_material
from bunnyland_anglersim.components import BaitComponent
from bunnyland_anglersim.crafting import (
    BASE_BAIT_QUALITY,
    MAX_BAIT_QUALITY,
    BaitMaterialComponent,
    CraftBaitHandler,
)
from bunnyland_anglersim.events import BaitCraftedEvent

EPOCH = 50


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


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="craft-bait",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def test_bait_quality_sums_and_clamps():
    assert bait_quality([]) == BASE_BAIT_QUALITY
    assert bait_quality([0.5, 0.5]) == round(BASE_BAIT_QUALITY + 1.0, 2)
    assert bait_quality([5.0, 5.0]) == MAX_BAIT_QUALITY


def test_material_potency_sources():
    actor, _room, _holder = _world()
    material = spawn_bait_material(actor.world, label="grub", potency=0.7)
    assert material_potency(material) == 0.7
    food = spawn_entity(
        actor.world,
        [IdentityComponent(name="ration", kind="item"), FoodComponent(nutrition=20.0, satiety=5.0)],
    )
    assert material_potency(food) == 1.0
    plain = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    assert material_potency(plain) is None


def test_material_prompt_fragment():
    actor, _room, holder = _world()
    material = spawn_bait_material(actor.world, label="worm", potency=0.5)
    ctx = ComponentPromptContext.for_entity(actor.world, material, target=holder)
    assert "worm" in material.get_component(BaitMaterialComponent).prompt_fragments(ctx)[0]


def test_craft_bait_combines_and_consumes_materials():
    actor, room, holder = _world()
    a = spawn_bait_material(actor.world, label="worm", potency=0.5)
    b = spawn_bait_material(actor.world, label="dough", potency=0.8)
    _hold(holder, a)
    _hold(holder, b)

    result = execute_handler(
        CraftBaitHandler(), HandlerContext(world=actor.world, epoch=EPOCH), _cmd(holder.id, {})
    )

    assert result.ok
    event = result.events[0]
    assert isinstance(event, BaitCraftedEvent)
    assert event.materials == 2
    assert event.quality == bait_quality([0.5, 0.8])
    assert not actor.world.has_entity(a.id)
    assert not actor.world.has_entity(b.id)
    crafted = [
        actor.world.get_entity(i)
        for i in contents(holder)
        if actor.world.get_entity(i).has_component(BaitComponent)
    ]
    assert crafted and crafted[0].get_component(BaitComponent).quality == event.quality


def test_craft_bait_rejects_without_materials():
    actor, _room, holder = _world()
    result = execute_handler(
        CraftBaitHandler(), HandlerContext(world=actor.world, epoch=EPOCH), _cmd(holder.id, {})
    )
    assert not result.ok
    assert result.reason == "you have no bait materials to craft with"


def test_craft_bait_rejects_invalid_character():
    actor, _room, _holder = _world()
    result = execute_handler(
        CraftBaitHandler(), HandlerContext(world=actor.world, epoch=EPOCH), _cmd("???", {})
    )
    assert not result.ok
    assert result.reason == "invalid character id"
