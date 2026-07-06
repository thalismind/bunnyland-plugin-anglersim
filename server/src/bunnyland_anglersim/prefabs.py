"""Spawn factories for fishing spots, bait, and caught fish.

The loader does not consume ``ContentContribution.prefabs``, so these ``spawn_entity``
helpers are how tests, admin tooling, and the worldgen hook create fishing content. A
fishing spot can also be *attached* to an existing room via :func:`attach_fishing_spot`.
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    RoomComponent,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component
from bunnyland.mechanics.consumables import FoodComponent
from relics import Entity, World

from .catch import is_edible
from .components import BaitComponent, FishComponent, FishingSpotComponent


def _link_into_room(world: World, item: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)


def attach_fishing_spot(room: Entity, *, biome: str | None = None, **fields) -> Entity:
    """Attach a :class:`FishingSpotComponent` to an existing room.

    The spot biome defaults to the room's own biome so a marsh room fishes marsh fish.
    """
    resolved = biome
    if resolved is None and room.has_component(RoomComponent):
        resolved = room.get_component(RoomComponent).biome
    replace_component(room, FishingSpotComponent(biome=resolved or "lake", **fields))
    return room


def spawn_fishing_spot(world: World, *, room_id=None, biome: str = "lake", **fields) -> Entity:
    """Spawn a standalone fishing-spot object, optionally placed in ``room_id``."""
    spot = spawn_entity(
        world,
        [
            IdentityComponent(name="fishing spot", kind="feature", tags=("anglersim",)),
            FishingSpotComponent(biome=biome, **fields),
        ],
    )
    _link_into_room(world, spot, room_id)
    return spot


def spawn_bait(
    world: World, *, room_id=None, name: str = "bait", quality: float = 1.0, uses: int = 1
) -> Entity:
    """Spawn a bait item, optionally placed in ``room_id``."""
    bait = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="item", tags=("anglersim", "bait")),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            BaitComponent(quality=quality, uses=uses),
        ],
    )
    _link_into_room(world, bait, room_id)
    return bait


def spawn_fish(world: World, *, species: str, tier: str, weight: float) -> Entity:
    """Spawn a caught-fish item (uncontained; the caller places it in an inventory).

    An edible catch also carries a core :class:`FoodComponent` so it feeds lifesim hunger
    through the shared ``eat`` verb; junk and treasure catches are inedible and omit it. The
    heavier the fish, the more nutrition and satiety it provides.
    """
    components = [
        IdentityComponent(name=species, kind="item", tags=("anglersim", "fish")),
        PortableComponent(),
        HoldableComponent(slot="hand"),
        FishComponent(species=species, tier=tier, weight=weight),
    ]
    if is_edible(species):
        components.append(
            FoodComponent(
                nutrition=round(weight * 8.0, 1), satiety=round(weight * 10.0, 1), raw=True
            )
        )
    return spawn_entity(world, components)


__all__ = ["attach_fishing_spot", "spawn_bait", "spawn_fish", "spawn_fishing_spot"]
