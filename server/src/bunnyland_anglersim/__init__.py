"""Out-of-tree Bunnyland plugin: a fishing pack.

v1 shipped spots, catches, rarity, bait, and a trophy log. v2 adds the headline
**records & derby** loop plus rod/tackle gear tiers, bait crafting, and a storyteller-paced
seasonal fishing run — all reusing core (fish feed lifesim hunger; records journal to core
memory; the run registers a core storyteller incident) with light, optional synergy connectors
to fortunesim, hearthsim, museumsim, and festivalsim.
"""

from .catch import (
    Catch,
    catch_table,
    is_edible,
    roll_catch,
    tier_weights,
)
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
from .connectors import (
    ingredient_potency,
    luck_bonus_for,
    publish_contest_entry,
    tag_collectible,
)
from .crafting import (
    CRAFT_BAIT_DEF,
    BaitMaterialComponent,
    CraftBaitHandler,
    bait_quality,
    material_potency,
    spawn_bait_material,
)
from .derby import (
    DERBY_ACTION_DEFINITIONS,
    DERBY_ACTION_HANDLERS,
    DerbyComponent,
    DerbyEntry,
    EnterDerbyHandler,
    JudgeDerbyHandler,
    derby_standings,
    spawn_derby,
)
from .enrichment import AnglerWorldgenHook, water_biome_for
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
from .gear import (
    RodComponent,
    TackleComponent,
    gear_bonus_for,
    spawn_rod,
    spawn_tackle,
)
from .install import install_anglersim
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import attach_fishing_spot, spawn_bait, spawn_fish, spawn_fishing_spot
from .records import (
    RecordBookComponent,
    RecordMemoryReactor,
    offer_to_book,
    record_book_in,
    spawn_record_book,
)
from .restock import RestockConsequence
from .runs import (
    FishingRunComponent,
    FishingRunConsequence,
    ensure_fishing_run,
    install_runs,
    run_bonus,
)
from .spatial import phase_of, room_of

__all__ = [
    "ANGLER_ACTION_DEFINITIONS",
    "ANGLER_ACTION_HANDLERS",
    "CRAFT_BAIT_DEF",
    "DERBY_ACTION_DEFINITIONS",
    "DERBY_ACTION_HANDLERS",
    "FISH_DEF",
    "PLUGIN_ID",
    "AnglerWorldgenHook",
    "BaitComponent",
    "BaitCraftedEvent",
    "BaitMaterialComponent",
    "Catch",
    "CatchLogComponent",
    "CraftBaitHandler",
    "DerbyComponent",
    "DerbyEnteredEvent",
    "DerbyEntry",
    "DerbyJudgedEvent",
    "EnterDerbyHandler",
    "FishCaughtEvent",
    "FishComponent",
    "FishHandler",
    "FishingRunComponent",
    "FishingRunConsequence",
    "FishingRunEndedEvent",
    "FishingRunStartedEvent",
    "FishingSpotComponent",
    "JudgeDerbyHandler",
    "LegendaryCatchEvent",
    "RecordBookComponent",
    "RecordMemoryReactor",
    "RecordSetEvent",
    "RestockConsequence",
    "RodComponent",
    "TackleComponent",
    "anglersim_fragments",
    "attach_fishing_spot",
    "bait_quality",
    "bunnyland_plugins",
    "catch_table",
    "derby_standings",
    "ensure_fishing_run",
    "gear_bonus_for",
    "ingredient_potency",
    "install_anglersim",
    "install_runs",
    "is_edible",
    "luck_bonus_for",
    "material_potency",
    "offer_to_book",
    "phase_of",
    "plugin",
    "publish_contest_entry",
    "record_book_in",
    "record_catch",
    "roll_catch",
    "room_of",
    "run_bonus",
    "spawn_bait",
    "spawn_bait_material",
    "spawn_derby",
    "spawn_fish",
    "spawn_fishing_spot",
    "spawn_record_book",
    "spawn_rod",
    "spawn_tackle",
    "tag_collectible",
    "tier_weights",
    "water_biome_for",
]
