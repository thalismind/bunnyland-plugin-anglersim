"""The community record book: the all-time heaviest catch per species.

The headline "records" mechanic. A :class:`RecordBookComponent` lives on a record-book entity
(seeded into fishing-hub rooms by worldgen, or spawned directly). Each landed fish is offered
to the book; if it beats the standing record for its species — or opens a new one — the book
records it against the angler who caught it and reports back that a record was set.

The book is a durable, save-safe component of plain primitives. Record-setting catches are
*also* written to the shared core memory store (see :mod:`bunnyland_anglersim.install`) so
agents can recall them in prompts — the records logbook routes through core memory rather than
reinventing a journal.
"""

from __future__ import annotations

from bunnyland.core import ContainmentMode, Contains, IdentityComponent, spawn_entity
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .events import RecordSetEvent

#: How many standing records the prompt fragment surfaces (heaviest first).
RECORD_FRAGMENT_LIMIT = 3


@dataclass(frozen=True)
class RecordBookComponent(Component):
    """A ledger of the heaviest catch per species.

    ``records`` holds ``(species, weight, holder_id)`` triples kept sorted by species so the
    ledger is stable under save/reload. Weight is the record to beat; ``holder_id`` is the
    angler who set it.
    """

    title: str = "Anglers' Record Book"
    records: tuple[tuple[str, float, str], ...] = ()

    def record_for(self, species: str) -> tuple[float, str] | None:
        """The standing ``(weight, holder_id)`` for ``species``, or ``None``."""
        for name, weight, holder in self.records:
            if name == species:
                return weight, holder
        return None

    def leaderboard(self) -> tuple[tuple[str, float, str], ...]:
        """Records ordered heaviest first (ties broken by species name)."""
        return tuple(sorted(self.records, key=lambda r: (-r[1], r[0])))

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not self.records:
            return (f"The {self.title} waits for its first record.",)
        lines = [f"{self.title} standings:"]
        for species, weight, _holder in self.leaderboard()[:RECORD_FRAGMENT_LIMIT]:
            lines.append(f"- {species}: {weight:.1f} lb")
        return (" ".join(lines),)


def offer_to_book(
    book: RecordBookComponent, *, species: str, weight: float, holder_id: str
) -> tuple[RecordBookComponent, float | None]:
    """Fold a catch into the book.

    Returns ``(new_book, previous_weight)``. ``previous_weight`` is ``None`` when the catch is
    not a record (it neither opens a new species line nor beats the standing weight); it is the
    prior record weight (or ``0.0`` for a brand-new species) when a record is set.
    """
    standing = book.record_for(species)
    if standing is not None and weight <= standing[0]:
        return book, None
    previous = standing[0] if standing is not None else 0.0
    kept = [record for record in book.records if record[0] != species]
    kept.append((species, weight, str(holder_id)))
    updated = RecordBookComponent(title=book.title, records=tuple(sorted(kept)))
    return updated, previous


def record_book_in(world: World) -> Entity | None:
    """Return the first record-book entity in the world (sorted by id), or ``None``."""
    books = sorted(
        world.query().with_all([RecordBookComponent]).execute_entities(), key=lambda e: str(e.id)
    )
    return books[0] if books else None


def spawn_record_book(world: World, *, room_id=None, title: str = "Anglers' Record Book") -> Entity:
    """Spawn a record-book entity, optionally placed in ``room_id``."""
    book = spawn_entity(
        world,
        [
            IdentityComponent(name=title, kind="feature", tags=("anglersim", "records")),
            RecordBookComponent(title=title),
        ],
    )
    if room_id is not None and world.has_entity(room_id):
        world.get_entity(room_id).add_relationship(
            Contains(mode=ContainmentMode.ROOM_CONTENT), book.id
        )
    return book


class RecordMemoryReactor:
    """Journal every record-setting catch into the core memory store, when one is present.

    ``store_provider`` is called lazily at event time so the reactor works regardless of the
    order in which the memory and anglersim plugins are applied; without a store installed the
    record is simply not journalled (the durable record book still stands on its own).
    """

    COLLECTION = "anglersim-records"

    def __init__(self, store_provider):
        self._store_provider = store_provider

    def subscribe(self, bus) -> None:
        bus.subscribe(RecordSetEvent, self._on_record)

    def _on_record(self, event: RecordSetEvent) -> None:
        store = self._store_provider()
        if store is None:
            return
        beat = (
            "a new species record"
            if event.previous_weight <= 0.0
            else f"beating {event.previous_weight:.1f} lb"
        )
        store.add(
            self.COLLECTION,
            text=(
                f"A {event.weight:.1f} lb {event.species} set the community record "
                f"({beat})."
            ),
            tags=("anglersim", "record", event.species),
            created_at_epoch=event.world_epoch,
            source="record",
        )


__all__ = [
    "RECORD_FRAGMENT_LIMIT",
    "RecordBookComponent",
    "RecordMemoryReactor",
    "offer_to_book",
    "record_book_in",
    "spawn_record_book",
]
