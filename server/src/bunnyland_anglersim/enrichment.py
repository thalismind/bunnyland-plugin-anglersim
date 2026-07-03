"""World-generation enrichment: seed fishing spots in water biomes.

Generated rooms carry a ``biome`` and generated entities expose semantic ``tags``/
``wants``/``needs`` and an intent ``description``. This hook attaches a
:class:`FishingSpotComponent` to any generated room in a recognised water biome, and to any
generated object whose text reads as watery (a pond, a well, a ship's deck…), so worlds come
pre-stocked with places to fish — without the core generator knowing this plugin exists.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import (
    GeneratedEntityEvent,
    ObjectGeneratedEvent,
    RoomGeneratedEvent,
)
from bunnyland.core.world_actor import WorldActor

from .catch import WATER_BIOMES
from .components import FishingSpotComponent

#: Water words in generated text mapped to the canonical biome a spot should fish.
TERM_BIOME: dict[str, str] = {
    "bog": "marsh",
    "swamp": "marsh",
    "wetland": "marsh",
    "fen": "marsh",
    "brook": "river",
    "creek": "river",
    "stream": "river",
    "rapids": "river",
    "pond": "lake",
    "pool": "lake",
    "reservoir": "lake",
    "well": "lake",
    "fountain": "lake",
    "aquarium": "lake",
    "boat": "ship",
    "deck": "ship",
    "dock": "ship",
    "pier": "ship",
    "harbor": "ship",
    "harbour": "ship",
    "wharf": "ship",
    "beach": "coast",
    "shore": "coast",
    "sea": "coast",
    "ocean": "coast",
    "tide": "coast",
    "bay": "coast",
    "lagoon": "coast",
}


def _text(event: GeneratedEntityEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.entity_kind,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def water_biome_for(biome: str, text: str) -> str | None:
    """Return the fishing biome for a generated entity, or ``None`` if it is not watery.

    A recognised biome wins outright; otherwise the earliest matching water word (by sorted
    term, for determinism) decides the biome.
    """
    if biome in WATER_BIOMES:
        return biome
    for term, mapped in sorted(TERM_BIOME.items()):
        if term in text:
            return mapped
    return None


class AnglerWorldgenHook:
    """Attach fishing spots to generated water-biome rooms and watery objects."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(RoomGeneratedEvent, self._on_room)
        actor.bus.subscribe(ObjectGeneratedEvent, self._on_object)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _seed(self, entity, biome: str | None) -> None:
        if entity is None or entity.has_component(FishingSpotComponent) or biome is None:
            return
        replace_component(entity, FishingSpotComponent(biome=biome))

    def _on_room(self, event: RoomGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None:
            return
        self._seed(entity, water_biome_for(event.biome, _text(event)))

    def _on_object(self, event: ObjectGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None:
            return
        self._seed(entity, water_biome_for("", _text(event)))


__all__ = ["TERM_BIOME", "AnglerWorldgenHook", "water_biome_for"]
