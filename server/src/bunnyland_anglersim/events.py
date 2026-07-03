"""Domain events emitted by the fishing verb."""

from __future__ import annotations

from bunnyland.core.events import DomainEvent


class FishCaughtEvent(DomainEvent):
    """A character landed a fish."""

    item_id: str
    species: str
    tier: str
    weight: float
    spot_id: str
    used_bait: bool = False


class LegendaryCatchEvent(DomainEvent):
    """A character landed a legendary fish — announced to the whole room."""

    species: str
    weight: float
    spot_id: str


__all__ = ["FishCaughtEvent", "LegendaryCatchEvent"]
