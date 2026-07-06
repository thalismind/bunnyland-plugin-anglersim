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


class RecordSetEvent(DomainEvent):
    """A catch set (or broke) the community record for its species."""

    species: str
    weight: float
    previous_weight: float
    holder_id: str
    book_id: str


class BaitCraftedEvent(DomainEvent):
    """A character crafted bait from held materials."""

    item_id: str
    quality: float
    materials: int


class DerbyEnteredEvent(DomainEvent):
    """A caught fish was entered into a fishing derby."""

    derby_id: str
    entrant_id: str
    entry_id: str
    species: str
    weight: float


class DerbyJudgedEvent(DomainEvent):
    """A derby was judged and a champion crowned."""

    derby_id: str
    winner_id: str
    entry_id: str
    species: str
    weight: float


class FishingRunStartedEvent(DomainEvent):
    """A seasonal fishing run opened — a storyteller-paced fishing incident."""

    run_index: int
    season: str
    ends_at_epoch: int


class FishingRunEndedEvent(DomainEvent):
    """A seasonal fishing run closed."""

    run_index: int
    season: str


__all__ = [
    "BaitCraftedEvent",
    "DerbyEnteredEvent",
    "DerbyJudgedEvent",
    "FishCaughtEvent",
    "FishingRunEndedEvent",
    "FishingRunStartedEvent",
    "LegendaryCatchEvent",
    "RecordSetEvent",
]
