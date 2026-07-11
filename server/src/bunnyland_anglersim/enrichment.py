"""Declarative fishing-spot and fishing-hub generation enrichment."""

from bunnyland.core import ContainmentMode, Contains, IdentityComponent
from bunnyland.core.generation import GenerationChild, GenerationDelta, GenerationRequest

from .catch import WATER_BIOMES
from .components import FishingSpotComponent
from .derby import DerbyComponent
from .records import RecordBookComponent

TERM_BIOME = {
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


def water_biome_for(biome: str, text: str) -> str | None:
    if biome in WATER_BIOMES:
        return biome
    return next((mapped for term, mapped in sorted(TERM_BIOME.items()) if term in text), None)


def _hub(request, key, component):
    return GenerationChild(
        request=GenerationRequest(
            entity_kind="feature",
            description=key,
            source_seed=request.source_seed,
            source_key=f"{request.source_key}:{key.casefold().replace(' ', '-')}",
            tags=("anglersim",),
        ),
        parent_edge=Contains(mode=ContainmentMode.ROOM_CONTENT),
        components=(IdentityComponent(name=key, kind="feature", tags=("anglersim",)), component),
        singleton_key=f"anglersim:{type(component).__name__}",
    )


class AnglerGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        existing = tuple(request.context.get("base_components", ()))
        if any(isinstance(item, FishingSpotComponent) for item in existing):
            return GenerationDelta()
        room = next((item for item in existing if item.__class__.__name__ == "RoomComponent"), None)
        biome = str(getattr(room, "biome", ""))
        text = " ".join(
            (request.source_key, request.entity_kind, request.description, *request.tags)
        ).casefold()
        fishing_biome = water_biome_for(biome, text)
        if fishing_biome is None:
            return GenerationDelta()
        children = ()
        if request.entity_kind == "room":
            children = (
                _hub(request, "Anglers' Record Book", RecordBookComponent()),
                _hub(request, "Fishing Derby", DerbyComponent()),
            )
        return GenerationDelta(
            components=(FishingSpotComponent(biome=fishing_biome),), children=children
        )


__all__ = ["AnglerGenerationEnricher", "TERM_BIOME", "water_biome_for"]
