from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins

from bunnyland_anglersim import (
    AnglerGenerationEnricher,
    BaitComponent,
    BaitMaterialComponent,
    CatchLogComponent,
    DerbyComponent,
    DerbyEntry,
    FishComponent,
    FishingRunComponent,
    FishingSpotComponent,
    RecordBookComponent,
    RodComponent,
    TackleComponent,
    anglersim_fragments,
)
from bunnyland_anglersim.plugin import PLUGIN_ID
from bunnyland_anglersim.plugin import bunnyland_plugins as _plugins


def test_plugin_loads_with_module_qualified_id():
    plugins = _plugins()
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_version_is_v2():
    plugin = _plugins()[0]
    assert plugin.version == "0.2.0"


def test_plugin_declares_its_contributions():
    plugin = _plugins()[0]
    for component in (
        FishingSpotComponent,
        FishComponent,
        BaitComponent,
        CatchLogComponent,
        RodComponent,
        TackleComponent,
        BaitMaterialComponent,
        RecordBookComponent,
        DerbyComponent,
        FishingRunComponent,
    ):
        assert component in plugin.ecs.components
    assert DerbyEntry in plugin.ecs.edges
    assert AnglerGenerationEnricher in [type(item) for item in plugin.content.generation_enrichers]
    assert anglersim_fragments in plugin.content.prompt_fragments


def test_plugin_recommends_optional_partners():
    plugin = _plugins()[0]
    assert set(plugin.dependencies.recommends) == {
        "bunnyland.fortunesim",
        "bunnyland.hearthsim",
        "bunnyland.museumsim",
        "bunnyland.festivalsim",
    }


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(_plugins(), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"fish", "craft-bait", "enter-derby", "judge-derby"} <= command_types
