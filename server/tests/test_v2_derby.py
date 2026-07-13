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
from bunnyland.core.handlers import HandlerContext
from bunnyland.prompts.context import ComponentPromptContext
from conftest import execute_handler

from bunnyland_anglersim import (
    EnterDerbyHandler,
    JudgeDerbyHandler,
    derby_standings,
    spawn_derby,
    spawn_fish,
)
from bunnyland_anglersim.derby import DerbyComponent, DerbyEntry
from bunnyland_anglersim.events import DerbyEnteredEvent, DerbyJudgedEvent

EPOCH = 100


def _world():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Dock", biome="lake")])
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    return actor, room, holder


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _fish(actor, holder, *, species="bass", tier="uncommon", weight=3.0):
    fish = spawn_fish(actor.world, species=species, tier=tier, weight=weight)
    _hold(holder, fish)
    return fish


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def test_enter_derby_registers_entry_and_event():
    actor, room, holder = _world()
    derby = spawn_derby(actor.world, room_id=room.id)
    fish = _fish(actor, holder, weight=4.5)

    result = execute_handler(EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {}))

    assert result.ok
    event = result.events[0]
    assert isinstance(event, DerbyEnteredEvent)
    assert event.entry_id == str(fish.id)
    assert event.weight == 4.5
    standings = derby_standings(derby)
    assert standings == [("bass", 4.5, str(holder.id))]


def test_enter_derby_picks_heaviest_held_fish():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    _fish(actor, holder, species="perch", weight=1.0)
    _fish(actor, holder, species="pike", weight=7.0)

    result = execute_handler(EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {}))
    assert result.ok
    assert result.events[0].species == "pike"


def test_enter_derby_explicit_fish_and_derby():
    actor, room, holder = _world()
    derby = spawn_derby(actor.world, room_id=room.id)
    fish = _fish(actor, holder, species="carp", weight=2.0)
    result = execute_handler(
        EnterDerbyHandler(),
        _ctx(actor),
        _cmd(holder.id, "enter-derby", {"derby_id": str(derby.id), "fish_id": str(fish.id)}),
    )
    assert result.ok


def test_enter_derby_rejects_duplicate_fish():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    fish = _fish(actor, holder, weight=2.0)
    execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {"fish_id": str(fish.id)})
    )
    result = execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {"fish_id": str(fish.id)})
    )
    assert not result.ok
    assert result.reason == "that fish is already entered"


def test_judge_derby_crowns_heaviest():
    actor, room, holder = _world()
    other = spawn_entity(
        actor.world, [IdentityComponent(name="Rue", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), other.id)
    derby = spawn_derby(actor.world, room_id=room.id)
    small = _fish(actor, holder, species="perch", weight=1.5)
    big = spawn_fish(actor.world, species="pike", tier="rare", weight=9.0)
    other.add_relationship(Contains(mode=ContainmentMode.INVENTORY), big.id)
    execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {"fish_id": str(small.id)})
    )
    execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(other.id, "enter-derby", {"fish_id": str(big.id)})
    )

    result = execute_handler(JudgeDerbyHandler(), _ctx(actor), _cmd(holder.id, "judge-derby", {}))

    assert result.ok
    event = result.events[0]
    assert isinstance(event, DerbyJudgedEvent)
    assert event.winner_id == str(other.id)
    assert event.weight == 9.0
    state = derby.get_component(DerbyComponent)
    assert state.open is False
    assert state.winner_id == str(other.id)


def test_enter_rejects_closed_derby():
    actor, room, holder = _world()
    derby = spawn_derby(actor.world, room_id=room.id)
    _fish(actor, holder)
    # Close it by judging (needs an entry first), then re-enter.
    execute_handler(EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {}))
    execute_handler(JudgeDerbyHandler(), _ctx(actor), _cmd(holder.id, "judge-derby", {}))
    result = execute_handler(
        EnterDerbyHandler(),
        _ctx(actor),
        _cmd(holder.id, "enter-derby", {"derby_id": str(derby.id)}),
    )
    assert not result.ok
    assert result.reason == "that derby is closed"


def test_judge_rejects_already_judged():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    _fish(actor, holder)
    execute_handler(EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {}))
    execute_handler(JudgeDerbyHandler(), _ctx(actor), _cmd(holder.id, "judge-derby", {}))
    result = execute_handler(JudgeDerbyHandler(), _ctx(actor), _cmd(holder.id, "judge-derby", {}))
    assert not result.ok
    assert result.reason == "that derby has already been judged"


def test_judge_rejects_empty_derby():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    result = execute_handler(JudgeDerbyHandler(), _ctx(actor), _cmd(holder.id, "judge-derby", {}))
    assert not result.ok
    assert result.reason == "that derby has no entries to judge"


def test_enter_rejects_no_fish():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    result = execute_handler(EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {}))
    assert not result.ok
    assert result.reason == "you have no fish to enter"


def test_enter_rejects_no_derby():
    actor, _room, holder = _world()
    _fish(actor, holder)
    result = execute_handler(EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {}))
    assert not result.ok
    assert result.reason == "there is no fishing derby within reach"


def test_enter_rejects_non_derby_target():
    actor, room, holder = _world()
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)
    _fish(actor, holder)
    result = execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {"derby_id": str(rock.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a fishing derby"


def test_enter_rejects_non_fish_target():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), rock.id)
    result = execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {"fish_id": str(rock.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a fish"


def test_enter_rejects_invalid_character():
    actor, room, _holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    result = execute_handler(EnterDerbyHandler(), _ctx(actor), _cmd("???", "enter-derby", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_judge_rejects_invalid_character():
    actor, room, _holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    result = execute_handler(JudgeDerbyHandler(), _ctx(actor), _cmd("???", "judge-derby", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_enter_rejects_invalid_and_unreachable_derby():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    _fish(actor, holder)
    bad = execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {"derby_id": "???"})
    )
    assert bad.reason == "invalid derby id"

    far_room = spawn_entity(actor.world, [RoomComponent(title="Far", biome="lake")])
    far_derby = spawn_derby(actor.world, room_id=far_room.id)
    unreachable = execute_handler(
        EnterDerbyHandler(),
        _ctx(actor),
        _cmd(holder.id, "enter-derby", {"derby_id": str(far_derby.id)}),
    )
    assert unreachable.reason == "that derby is not within reach"


def test_enter_rejects_invalid_fish_id():
    actor, room, holder = _world()
    spawn_derby(actor.world, room_id=room.id)
    result = execute_handler(
        EnterDerbyHandler(), _ctx(actor), _cmd(holder.id, "enter-derby", {"fish_id": "???"})
    )
    assert result.reason == "invalid fish id"


def test_derby_prompt_fragments_states():
    actor, room, holder = _world()
    derby = spawn_derby(actor.world, room_id=room.id)
    state = derby.get_component(DerbyComponent)
    ctx = ComponentPromptContext.for_entity(actor.world, derby, target=holder)
    assert "open for entries" in state.prompt_fragments(ctx)[0]

    fish = _fish(actor, holder, species="pike", weight=8.0)
    derby.add_relationship(
        DerbyEntry(entrant_id=str(holder.id), species="pike", weight=8.0), fish.id
    )
    assert "leaderboard" in derby.get_component(DerbyComponent).prompt_fragments(ctx)[0]


def test_closed_derby_fragments():
    actor, room, holder = _world()
    derby = spawn_derby(actor.world, room_id=room.id)
    won = DerbyComponent(open=False, winner_id=str(holder.id), winning_weight=8.0)
    entity = spawn_entity(actor.world, [IdentityComponent(name="d", kind="feature"), won])
    ctx = ComponentPromptContext.for_entity(actor.world, entity, target=holder)
    assert "is over" in won.prompt_fragments(ctx)[0]

    empty_close = DerbyComponent(open=False)
    ctx2 = ComponentPromptContext.for_entity(actor.world, derby, target=holder)
    assert "is closed" in empty_close.prompt_fragments(ctx2)[0]
