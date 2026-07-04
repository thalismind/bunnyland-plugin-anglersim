"""Bunnyland plugin entrypoint for the out-of-tree anglersim fishing extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
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
from .enrichment import AnglerWorldgenHook
from .events import FishCaughtEvent, LegendaryCatchEvent
from .fragments import anglersim_fragments
from .install import install_anglersim

PLUGIN_ID = "bunnyland.anglersim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Anglersim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                FishingSpotComponent,
                FishComponent,
                BaitComponent,
                CatchLogComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=ANGLER_ACTION_HANDLERS,
            action_definitions=ANGLER_ACTION_DEFINITIONS,
            typed_events=(FishCaughtEvent, LegendaryCatchEvent),
        ),
        runtime=RuntimeContribution(service_factories=(install_anglersim,)),
        content=ContentContribution(
            prompt_fragments=(anglersim_fragments,),
            worldgen_hooks=(AnglerWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
