"""Bunnyland plugin entrypoint for the out-of-tree anglersim fishing extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .commands import ANGLER_ACTION_DEFINITIONS, ANGLER_ACTION_HANDLERS
from .components import (
    BaitComponent,
    CatchLogComponent,
    FishComponent,
    FishingSpotComponent,
)
from .crafting import (
    CRAFTING_ACTION_DEFINITIONS,
    CRAFTING_ACTION_HANDLERS,
    BaitMaterialComponent,
)
from .derby import (
    DERBY_ACTION_DEFINITIONS,
    DERBY_ACTION_HANDLERS,
    DerbyComponent,
    DerbyEntry,
)
from .enrichment import AnglerGenerationEnricher
from .events import (
    BaitCraftedEvent,
    DerbyEnteredEvent,
    DerbyJudgedEvent,
    FishCaughtEvent,
    FishingRunEndedEvent,
    FishingRunStartedEvent,
    LegendaryCatchEvent,
    RecordSetEvent,
)
from .fragments import anglersim_fragments
from .gear import RodComponent, TackleComponent
from .install import install_anglersim
from .records import RecordBookComponent
from .runs import FishingRunComponent

PLUGIN_ID = "bunnyland.anglersim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Anglersim",
        version="0.2.0",
        default_enabled=True,
        # All optional: fortunesim luck biases catches, hearthsim ingredients double as bait,
        # museumsim collects record fish, festivalsim mirrors a derby as a contest. Each stays
        # dormant (with a logged warning) when its pack is not loaded.
        dependencies=DependencyContribution(
            recommends=(
                "bunnyland.fortunesim",
                "bunnyland.hearthsim",
                "bunnyland.museumsim",
                "bunnyland.festivalsim",
            ),
        ),
        ecs=EcsContribution(
            components=(
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
            ),
            edges=(DerbyEntry,),
        ),
        commands=CommandContribution(
            action_handlers=(
                *ANGLER_ACTION_HANDLERS,
                *CRAFTING_ACTION_HANDLERS,
                *DERBY_ACTION_HANDLERS,
            ),
            action_definitions=(
                *ANGLER_ACTION_DEFINITIONS,
                *CRAFTING_ACTION_DEFINITIONS,
                *DERBY_ACTION_DEFINITIONS,
            ),
            typed_events=(
                FishCaughtEvent,
                LegendaryCatchEvent,
                RecordSetEvent,
                BaitCraftedEvent,
                DerbyEnteredEvent,
                DerbyJudgedEvent,
                FishingRunStartedEvent,
                FishingRunEndedEvent,
            ),
        ),
        runtime=RuntimeContribution(service_factories=(install_anglersim,)),
        content=ContentContribution(
            prompt_fragments=(anglersim_fragments,),
            generation_enrichers=(AnglerGenerationEnricher(),),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
