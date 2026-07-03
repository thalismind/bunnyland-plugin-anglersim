"""Out-of-tree Bunnyland plugin: a fishing pack (spots, catches, rarity, bait, trophies)."""

from .catch import Catch, catch_table, roll_catch, tier_weights
from .commands import (
    ANGLER_ACTION_DEFINITIONS,
    ANGLER_ACTION_HANDLERS,
    FISH_DEF,
    FishHandler,
)
from .components import (
    BaitComponent,
    CatchLogComponent,
    FishComponent,
    FishingSpotComponent,
    record_catch,
)
from .enrichment import AnglerWorldgenHook, water_biome_for
from .events import FishCaughtEvent, LegendaryCatchEvent
from .fragments import anglersim_fragments
from .install import install_anglersim
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import attach_fishing_spot, spawn_bait, spawn_fish, spawn_fishing_spot
from .restock import RestockConsequence
from .spatial import phase_of, room_of

__all__ = [
    "ANGLER_ACTION_DEFINITIONS",
    "ANGLER_ACTION_HANDLERS",
    "FISH_DEF",
    "PLUGIN_ID",
    "AnglerWorldgenHook",
    "BaitComponent",
    "Catch",
    "CatchLogComponent",
    "FishCaughtEvent",
    "FishComponent",
    "FishHandler",
    "FishingSpotComponent",
    "LegendaryCatchEvent",
    "RestockConsequence",
    "anglersim_fragments",
    "attach_fishing_spot",
    "bunnyland_plugins",
    "catch_table",
    "install_anglersim",
    "phase_of",
    "plugin",
    "record_catch",
    "roll_catch",
    "room_of",
    "spawn_bait",
    "spawn_fish",
    "spawn_fishing_spot",
    "tier_weights",
    "water_biome_for",
]
