from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import EventVisibility, event_base
from bunnyland.core.handlers import HandlerContext
from bunnyland.memory import InMemoryStore
from bunnyland.prompts.context import ComponentPromptContext
from conftest import execute_handler

from bunnyland_anglersim import (
    FishHandler,
    offer_to_book,
    record_book_in,
    spawn_fishing_spot,
    spawn_record_book,
)
from bunnyland_anglersim.components import FishingSpotComponent
from bunnyland_anglersim.events import RecordSetEvent
from bunnyland_anglersim.records import (
    RECORD_FRAGMENT_LIMIT,
    RecordBookComponent,
    RecordMemoryReactor,
)

EPOCH = 100


def _world():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Dock", biome="lake")])
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    return actor, room, holder


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="fish",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def test_offer_opens_and_beats_records():
    book = RecordBookComponent()
    book, prev = offer_to_book(book, species="bass", weight=3.0, holder_id="a")
    assert prev == 0.0  # brand-new species
    assert book.record_for("bass") == (3.0, "a")

    book, prev = offer_to_book(book, species="bass", weight=2.0, holder_id="b")
    assert prev is None  # not a record, book unchanged holder
    assert book.record_for("bass") == (3.0, "a")

    book, prev = offer_to_book(book, species="bass", weight=5.0, holder_id="b")
    assert prev == 3.0
    assert book.record_for("bass") == (5.0, "b")


def test_record_book_leaderboard_and_fragments():
    book = RecordBookComponent()
    for species, weight in (("perch", 1.0), ("pike", 8.0), ("carp", 4.0), ("koi", 2.0)):
        book, _prev = offer_to_book(book, species=species, weight=weight, holder_id="a")
    board = book.leaderboard()
    assert [row[0] for row in board] == ["pike", "carp", "koi", "perch"]

    actor, _room, holder = _world()
    entity = spawn_entity(actor.world, [IdentityComponent(name="book", kind="feature"), book])
    ctx = ComponentPromptContext.for_entity(actor.world, entity, target=holder)
    fragment = book.prompt_fragments(ctx)[0]
    assert "pike" in fragment
    assert fragment.count("- ") == RECORD_FRAGMENT_LIMIT


def test_empty_record_book_fragment():
    book = RecordBookComponent()
    actor, _room, holder = _world()
    entity = spawn_entity(actor.world, [IdentityComponent(name="book", kind="feature"), book])
    ctx = ComponentPromptContext.for_entity(actor.world, entity, target=holder)
    assert "waits for its first record" in book.prompt_fragments(ctx)[0]


def test_record_for_absent_species():
    assert RecordBookComponent().record_for("ghost") is None


def test_record_book_in_returns_none_and_first():
    actor, room, _holder = _world()
    assert record_book_in(actor.world) is None
    book = spawn_record_book(actor.world, room_id=room.id)
    assert record_book_in(actor.world).id == book.id


def test_fish_sets_record_and_emits_event():
    actor, room, holder = _world()
    spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")
    spawn_record_book(actor.world, room_id=room.id)

    result = execute_handler(
        FishHandler(), HandlerContext(world=actor.world, epoch=EPOCH), _cmd(holder.id, {})
    )

    assert result.ok
    record_events = [e for e in result.events if isinstance(e, RecordSetEvent)]
    assert len(record_events) == 1
    assert record_events[0].previous_weight == 0.0
    book = record_book_in(actor.world).get_component(RecordBookComponent)
    assert book.records  # the catch was recorded


def test_non_record_catch_emits_no_record_event():
    from bunnyland_anglersim import phase_of, roll_catch

    actor, room, holder = _world()
    spot = spawn_fishing_spot(actor.world, room_id=room.id, biome="lake")
    book = spawn_record_book(actor.world, room_id=room.id)

    # Pre-seed the book with a standing record heavier than this exact deterministic cast, so
    # the catch is landed but sets no record (exercises the handler's "not a record" branch).
    expected = roll_catch(
        spot_id=str(spot.id),
        character_id=str(holder.id),
        epoch=EPOCH,
        casts=0,
        biome="lake",
        phase=phase_of(actor.world),
    )
    replace_component(
        book, RecordBookComponent(records=((expected.species, expected.weight + 100.0, "old"),))
    )

    result = execute_handler(
        FishHandler(), HandlerContext(world=actor.world, epoch=EPOCH), _cmd(holder.id, {})
    )
    assert result.ok
    assert not any(isinstance(e, RecordSetEvent) for e in result.events)
    # The standing record still stands.
    standing = record_book_in(actor.world).get_component(RecordBookComponent)
    assert standing.record_for(expected.species) == (expected.weight + 100.0, "old")
    assert spot.get_component(FishingSpotComponent).casts == 1


def test_memory_reactor_journals_record():
    store = InMemoryStore()
    reactor = RecordMemoryReactor(lambda: store)

    class _Bus:
        def __init__(self):
            self.handler = None

        def subscribe(self, event_type, handler):
            self.handler = handler

    bus = _Bus()
    reactor.subscribe(bus)
    event = RecordSetEvent(
        **_event_base(species="bass", weight=5.0, previous_weight=0.0, holder_id="a", book_id="b")
    )
    bus.handler(event)
    entries = store.search(RecordMemoryReactor.COLLECTION, mode="recent", limit=5)
    assert entries
    assert "bass" in entries[0].text

    beaten = RecordSetEvent(
        **_event_base(species="pike", weight=9.0, previous_weight=6.0, holder_id="a", book_id="b")
    )
    bus.handler(beaten)
    texts = " ".join(e.text for e in store.search(RecordMemoryReactor.COLLECTION, limit=5))
    assert "beating 6.0 lb" in texts


def test_memory_reactor_dormant_without_store():
    reactor = RecordMemoryReactor(lambda: None)
    event = RecordSetEvent(
        **_event_base(species="bass", weight=5.0, previous_weight=0.0, holder_id="a", book_id="b")
    )
    reactor._on_record(event)  # must not raise


def _event_base(**fields):
    return event_base(EPOCH, default_visibility=EventVisibility.ROOM, **fields)
