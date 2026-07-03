"""Frozen components for the fishing pack.

All state lives in immutable :class:`relics.Component` values; the handler and the restock
consequence swap whole values with ``replace_component(entity, replace(component, ...))``.

- :class:`FishingSpotComponent` marks a room (or object) you can cast a line at. It carries
  the water ``biome`` that keys the catch table, a short per-cast ``cooldown`` gate, and a
  depletable ``stock`` the restock consequence slowly refills.
- :class:`FishComponent` tags a caught fish item with its species/tier/weight.
- :class:`BaitComponent` tags a consumable bait item that biases the catch roll.
- :class:`CatchLogComponent` is the angler's trophy log: best weight per species plus a
  short recent haul.
"""

from __future__ import annotations

from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component

# --------------------------------------------------------------------------------------
# Fishing spots
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FishingSpotComponent(Component):
    """A place you can cast a line. Attaches to a water-biome room or a watery object."""

    biome: str = "lake"
    #: Fish available to catch right now; each catch consumes one, restocked over time.
    stock: int = 4
    #: The most stock this spot can hold.
    capacity: int = 4
    #: Monotonic cast counter, a stable input to the deterministic catch roll.
    casts: int = 0
    #: Earliest epoch (world-second) the spot can be fished again after a cast.
    ready_at_epoch: int = 0
    #: Seconds a spot needs to settle between casts.
    cooldown: int = 30
    #: Epoch of the last restock, so the consequence can pace refills.
    restocked_at_epoch: int = 0
    #: Seconds between restocking one unit of stock.
    restock_interval: int = 120

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        where = "here" if ctx.entity.has_component(_room_marker()) else "within reach"
        if self.stock <= 0:
            return (f"The fishing spot {where} is fished out for now.",)
        return (f"A fishing spot ripples {where}, good for {self.biome} fish.",)


def _room_marker() -> type:
    # Imported lazily to keep this module import-light and avoid a core import cycle.
    from bunnyland.core import RoomComponent

    return RoomComponent


# --------------------------------------------------------------------------------------
# Caught fish + bait
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FishComponent(Component):
    """Identifies a caught fish item by species, rarity tier, and weight (pounds)."""

    species: str = "minnow"
    tier: str = "common"
    weight: float = 0.5


@dataclass(frozen=True)
class BaitComponent(Component):
    """A consumable bait item. ``quality`` biases the roll toward rarer catches."""

    quality: float = 1.0
    #: How many casts this bait item survives before it is used up and removed.
    uses: int = 1


# --------------------------------------------------------------------------------------
# Trophy log
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CatchLogComponent(Component):
    """Per-angler trophy log: best weight per species plus a short recent haul.

    ``caught`` holds ``(species, best_weight)`` pairs kept sorted by species; ``recent``
    holds the most recent species, newest last, capped at :data:`RECENT_LIMIT`. Both use
    plain primitives so the log serialises cleanly through the save/reload path.
    """

    caught: tuple[tuple[str, float], ...] = ()
    recent: tuple[str, ...] = ()

    def best(self) -> tuple[str, float] | None:
        """The heaviest recorded catch (ties broken by species name), or ``None``."""
        if not self.caught:
            return None
        return max(self.caught, key=lambda record: (record[1], record[0]))

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        best = self.best()
        if best is None:
            return ()
        lines = [f"Your biggest catch is a {best[0]} ({best[1]:.1f} lb)."]
        if self.recent:
            lines.append("Recent haul: " + ", ".join(self.recent) + ".")
        return tuple(lines)


#: How many recent species the trophy log remembers.
RECENT_LIMIT = 5


def record_catch(log: CatchLogComponent, species: str, weight: float) -> CatchLogComponent:
    """Return a new log with ``(species, weight)`` folded into the best-weight table."""
    best_by_species = dict(log.caught)
    if species not in best_by_species or weight > best_by_species[species]:
        best_by_species[species] = weight
    caught = tuple(sorted(best_by_species.items()))
    recent = (*log.recent, species)[-RECENT_LIMIT:]
    return CatchLogComponent(caught=caught, recent=recent)


__all__ = [
    "RECENT_LIMIT",
    "BaitComponent",
    "CatchLogComponent",
    "FishComponent",
    "FishingSpotComponent",
    "record_catch",
]
