from __future__ import annotations

import asyncio
import io
import sys

import pytest
from bunnyland.core import WorldActor
from bunnyland.foundation.media.plugin import plugin as media_plugin
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import RoomSpec, WorldProposal, instantiate

from bunnyland_anglersim.integration_3d import fishing_pond_room
from bunnyland_anglersim.plugin import plugin as angler_plugin


def _plugins_3d():
    from bunnyland_3d.plugin import plugin as plugin_3d

    return [media_plugin(), plugin_3d(), angler_plugin()]


def _room(actor, spec):
    result = asyncio.run(instantiate(actor, WorldProposal(seed="seed", rooms=[spec])))
    return actor.world.get_entity(result.rooms[spec.key])


def test_plugin_stays_independent_when_3d_is_disabled():
    sys.modules.pop("bunnyland_3d", None)
    actor = WorldActor()

    apply_plugins([angler_plugin()], actor)

    assert "bunnyland_3d" not in sys.modules
    assert angler_plugin().dependencies.integrates_with == ("bunnyland.3d",)


@pytest.mark.parametrize(
    ("spec", "matches"),
    [
        (RoomSpec(key="pond", title="Garden", description="a still garden pond"), True),
        (RoomSpec(key="pool", title="Rock Pool"), True),
        (RoomSpec(key="reservoir", title="Reservoir"), True),
        (RoomSpec(key="inside", title="Indoor Pond", indoor=True), False),
        (RoomSpec(key="ocean", title="Ocean Pool", biome="coast"), False),
        (RoomSpec(key="ship", title="Ship Pool", biome="ship"), False),
        (RoomSpec(key="lake", title="Quiet Lake", biome="lake"), False),
    ],
)
def test_pond_matching_rejections(spec, matches):
    actor = WorldActor()
    apply_plugins([angler_plugin()], actor)
    assert fishing_pond_room(_room(actor, spec)) is matches


def test_model_registration_conversion_and_centered_projection(tmp_path, monkeypatch):
    trimesh = pytest.importorskip("trimesh")
    monkeypatch.setenv("BUNNYLAND_MEDIA_DIR", str(tmp_path / "media"))
    actor = WorldActor()
    apply_plugins(_plugins_3d(), actor)
    room = _room(
        actor,
        RoomSpec(key="pond", title="Fishing Garden", description="a quiet garden pond"),
    )

    from bunnyland_3d import HasDecoration3D, PropGroup3DComponent, require_model_registry
    from bunnyland_3d.api import room_scene_view

    model = require_model_registry(actor).models["bunnyland.anglersim/fishing-pond"]
    data = require_model_registry(actor).media.read("models3d", model.url.rsplit("/", 1)[1])
    converted = trimesh.load_scene(io.BytesIO(data), file_type="glb")
    relationships = [
        target
        for edge, target in room.get_relationships(HasDecoration3D)
        if edge.role == "bunnyland.anglersim/fishing-pond"
    ]
    decoration = actor.world.get_entity(relationships[0])
    group = decoration.get_component(PropGroup3DComponent)
    projected = next(
        item
        for item in room_scene_view(actor, str(room.id))["decorations"]
        if item.get("decoration_source3d", {}).get("role")
        == "bunnyland.anglersim/fishing-pond"
    )

    assert model.asset.source.resolve().is_relative_to(model.asset.source.root)
    assert len(converted.geometry) >= 4
    assert group.count == 1
    assert projected["prop_group3d"]["instances"][0]["position"] == {
        "x": 8.0,
        "y": 0.0,
        "z": 8.0,
    }
