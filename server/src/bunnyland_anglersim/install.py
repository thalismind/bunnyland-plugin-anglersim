"""Runtime wiring: register the restock consequence on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .restock import RestockConsequence


def install_anglersim(actor: WorldActor) -> None:
    """Register the per-tick fishing-spot restock consequence (a ``service_factories`` entry)."""
    actor.register_consequence(RestockConsequence())


__all__ = ["install_anglersim"]
