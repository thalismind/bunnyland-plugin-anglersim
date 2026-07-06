from __future__ import annotations

from bunnyland.core import IdentityComponent, WorldActor, spawn_entity
from pydantic.dataclasses import dataclass
from relics import Component

from bunnyland_anglersim import (
    connectors,
    ingredient_potency,
    luck_bonus_for,
    publish_contest_entry,
    tag_collectible,
)
from bunnyland_anglersim.connectors import (
    INGREDIENT_BASE_POTENCY,
    LUCK_SCALE,
)


@dataclass(frozen=True)
class _FakeLuck(Component):
    value: float = 0.0


@dataclass(frozen=True)
class _FakeIngredient(Component):
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class _FakeCollectible(Component):
    category: str = "curio"
    rarity: str = "common"


def _actor_char():
    actor = WorldActor()
    char = spawn_entity(actor.world, [IdentityComponent(name="Vin", kind="character")])
    return actor, char


# --- Standalone (dormant) paths: no partner packs on sys.path ---------------------------


def test_luck_bonus_dormant():
    actor, char = _actor_char()
    assert luck_bonus_for(actor.world, char) == 0.0


def test_ingredient_potency_dormant():
    actor, _char = _actor_char()
    item = spawn_entity(actor.world, [IdentityComponent(name="thing", kind="item")])
    assert ingredient_potency(item) is None


def test_tag_collectible_dormant():
    actor, _char = _actor_char()
    fish = spawn_entity(actor.world, [IdentityComponent(name="bass", kind="item")])
    assert tag_collectible(fish, "rare") is False


def test_publish_contest_entry_dormant():
    actor, char = _actor_char()
    contest = spawn_entity(actor.world, [IdentityComponent(name="derby", kind="feature")])
    assert (
        publish_contest_entry(
            actor.world, contest, char.id, entrant_id=str(char.id), score=1.0, epoch=0
        )
        is False
    )


# --- Active synergy paths: inject fake partner surfaces ----------------------------------


def test_luck_bonus_active(monkeypatch):
    monkeypatch.setattr(connectors, "LuckComponent", _FakeLuck)
    actor, char = _actor_char()
    # Present type but character lacks it -> neutral.
    assert luck_bonus_for(actor.world, char) == 0.0
    from bunnyland.core.ecs import replace_component

    replace_component(char, _FakeLuck(value=4.0))
    assert luck_bonus_for(actor.world, char) == 4.0 * LUCK_SCALE


def test_ingredient_potency_active(monkeypatch):
    monkeypatch.setattr(connectors, "IngredientComponent", _FakeIngredient)
    actor, _char = _actor_char()
    plain = spawn_entity(actor.world, [IdentityComponent(name="thing", kind="item")])
    assert ingredient_potency(plain) is None  # present type, item lacks it
    worm = spawn_entity(
        actor.world,
        [IdentityComponent(name="worm", kind="item"), _FakeIngredient(tags=("worm", "bug"))],
    )
    assert ingredient_potency(worm) == INGREDIENT_BASE_POTENCY + 0.2 * 2


def test_tag_collectible_active(monkeypatch):
    monkeypatch.setattr(connectors, "CollectibleComponent", _FakeCollectible)
    actor, _char = _actor_char()
    fish = spawn_entity(actor.world, [IdentityComponent(name="marlin", kind="item")])
    assert tag_collectible(fish, "legendary") is True
    assert fish.get_component(_FakeCollectible).rarity == "legendary"
    # Unknown tier falls back to "common".
    other = spawn_entity(actor.world, [IdentityComponent(name="junk", kind="item")])
    assert tag_collectible(other, "mystery") is True
    assert other.get_component(_FakeCollectible).rarity == "common"


def test_publish_contest_entry_active(monkeypatch):
    calls = []

    def _fake_register(world, contest, entry_id, *, entrant_id, score, epoch):
        calls.append((entrant_id, score, epoch))

    monkeypatch.setattr(connectors, "register_contest_entry", _fake_register)
    actor, char = _actor_char()
    contest = spawn_entity(actor.world, [IdentityComponent(name="derby", kind="feature")])
    result = publish_contest_entry(
        actor.world, contest, char.id, entrant_id="e", score=3.0, epoch=7
    )
    assert result is True
    assert calls == [("e", 3.0, 7)]
