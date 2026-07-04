from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_anglersim import (
    AnglerWorldgenHook,
    BaitComponent,
    CatchLogComponent,
    FishComponent,
    FishingSpotComponent,
    anglersim_fragments,
)
from bunnyland_anglersim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_anglersim"])
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_anglersim"])[0]
    for component in (
        FishingSpotComponent,
        FishComponent,
        BaitComponent,
        CatchLogComponent,
    ):
        assert component in plugin.ecs.components
    assert AnglerWorldgenHook in plugin.content.worldgen_hooks
    assert anglersim_fragments in plugin.content.prompt_fragments


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_anglersim"]), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"fish"} <= command_types
