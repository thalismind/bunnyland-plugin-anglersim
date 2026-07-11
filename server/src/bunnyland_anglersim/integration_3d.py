"""Optional, lazily imported Bunnyland 3D presentation integration."""

from __future__ import annotations

from pathlib import Path

from bunnyland.core import GenerationIntentComponent, RoomComponent

from .components import FishingSpotComponent

ASSET_ROOT = Path(__file__).with_name("assets")
POND_TERMS = ("pond", "pool", "garden pond", "reservoir")


def fishing_pond_room(room) -> bool:
    if not room.has_component(RoomComponent) or not room.has_component(FishingSpotComponent):
        return False
    component = room.get_component(RoomComponent)
    if component.indoor:
        return False
    intent = (
        room.get_component(GenerationIntentComponent)
        if room.has_component(GenerationIntentComponent)
        else None
    )
    text = " ".join(
        (
            component.title,
            component.biome,
            intent.description if intent else "",
            intent.source_key if intent else "",
            *(intent.tags if intent else ()),
        )
    ).casefold()
    if any(term in text for term in ("ocean", "sea", "ship", "deck", "harbor", "harbour")):
        return False
    return any(term in text for term in POND_TERMS)


def install_anglersim_3d(actor, context) -> None:
    if context.plugins is None or not context.plugins.enabled("bunnyland.3d"):
        return
    from bunnyland_3d import (
        AssetSource,
        ModelAsset,
        PropInstanceOverride,
        RoomDecorationRule,
        Vector3,
        register_models,
        register_room_decorations,
    )

    register_models(
        actor,
        "bunnyland.anglersim",
        (
            ModelAsset(
                key="bunnyland.anglersim/fishing-pond",
                source=AssetSource(ASSET_ROOT, "fishing-pond.obj"),
                instanced=True,
                license="AGPL-3.0-or-later",
                attribution="Bunnyland Anglersim contributors",
            ),
        ),
    )
    register_room_decorations(
        actor,
        "bunnyland.anglersim",
        (
            RoomDecorationRule(
                key="bunnyland.anglersim/fishing-pond",
                model_key="bunnyland.anglersim/fishing-pond",
                room_predicate=fishing_pond_room,
                count=1,
                tint="#8abfc7",
                fixed_instances=(
                    PropInstanceOverride(
                        instance_id="i0", position=Vector3(8.0, 0.0, 8.0), scale=1.0
                    ),
                ),
            ),
        ),
    )


__all__ = ["POND_TERMS", "fishing_pond_room", "install_anglersim_3d"]
