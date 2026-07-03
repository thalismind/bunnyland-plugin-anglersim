from __future__ import annotations

from bunnyland.core import IdentityComponent, RoomComponent, WorldActor, spawn_entity
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

from bunnyland_anglersim import (
    CatchLogComponent,
    FishingSpotComponent,
    record_catch,
)
from bunnyland_anglersim.components import RECENT_LIMIT


def test_record_catch_tracks_new_species():
    log = record_catch(CatchLogComponent(), "trout", 2.0)
    assert log.caught == (("trout", 2.0),)
    assert log.recent == ("trout",)


def test_record_catch_keeps_the_heavier_weight():
    log = record_catch(CatchLogComponent(), "trout", 2.0)
    log = record_catch(log, "trout", 5.0)
    assert dict(log.caught)["trout"] == 5.0
    log = record_catch(log, "trout", 1.0)  # lighter does not replace the best
    assert dict(log.caught)["trout"] == 5.0


def test_record_catch_caps_recent_haul():
    log = CatchLogComponent()
    for index in range(RECENT_LIMIT + 3):
        log = record_catch(log, f"fish{index}", 1.0)
    assert len(log.recent) == RECENT_LIMIT
    assert log.recent[-1] == f"fish{RECENT_LIMIT + 2}"


def test_best_is_none_when_empty():
    assert CatchLogComponent().best() is None


def test_best_breaks_ties_by_species_name():
    log = record_catch(record_catch(CatchLogComponent(), "zander", 4.0), "arapaima", 4.0)
    assert log.best() == ("zander", 4.0)


def test_log_fragment_is_first_person_only():
    actor = WorldActor()
    angler = spawn_entity(actor.world, [IdentityComponent(name="Vin", kind="character")])
    other = spawn_entity(actor.world, [IdentityComponent(name="Kel", kind="character")])
    log = record_catch(record_catch(CatchLogComponent(), "bass", 3.0), "bass", 6.0)

    own = ComponentPromptContext.for_entity(actor.world, angler)
    lines = log.prompt_fragments(own)
    assert lines[0] == "Your biggest catch is a bass (6.0 lb)."
    assert lines[1] == "Recent haul: bass, bass."

    outside = ComponentPromptContext.for_entity(
        actor.world, angler, perspective=PromptPerspective(viewer=other)
    )
    assert log.prompt_fragments(outside) == ()


def test_log_fragment_without_recent_haul():
    actor = WorldActor()
    angler = spawn_entity(actor.world, [IdentityComponent(name="Vin", kind="character")])
    log = CatchLogComponent(caught=(("carp", 3.0),))  # best set, empty recent
    ctx = ComponentPromptContext.for_entity(actor.world, angler)
    assert log.prompt_fragments(ctx) == ("Your biggest catch is a carp (3.0 lb).",)


def test_empty_log_fragment_is_blank():
    actor = WorldActor()
    angler = spawn_entity(actor.world, [IdentityComponent(name="Vin", kind="character")])
    ctx = ComponentPromptContext.for_entity(actor.world, angler)
    assert CatchLogComponent().prompt_fragments(ctx) == ()


def test_room_spot_fragment_reads_here():
    actor = WorldActor()
    room = spawn_entity(
        actor.world, [RoomComponent(title="Lake", biome="lake"), FishingSpotComponent(biome="lake")]
    )
    ctx = ComponentPromptContext.for_entity(actor.world, room, room=room)
    assert room.get_component(FishingSpotComponent).prompt_fragments(ctx) == (
        "A fishing spot ripples here, good for lake fish.",
    )


def test_object_spot_fragment_reads_within_reach():
    actor = WorldActor()
    spot = spawn_entity(
        actor.world, [IdentityComponent(name="hole", kind="feature"), FishingSpotComponent()]
    )
    ctx = ComponentPromptContext.for_entity(actor.world, spot)
    assert spot.get_component(FishingSpotComponent).prompt_fragments(ctx) == (
        "A fishing spot ripples within reach, good for lake fish.",
    )


def test_fished_out_spot_fragment():
    actor = WorldActor()
    room = spawn_entity(
        actor.world, [RoomComponent(title="Lake"), FishingSpotComponent(biome="lake", stock=0)]
    )
    ctx = ComponentPromptContext.for_entity(actor.world, room, room=room)
    assert room.get_component(FishingSpotComponent).prompt_fragments(ctx) == (
        "The fishing spot here is fished out for now.",
    )
