"""Restock consequence: slowly refill fishing spots depleted by casting.

Every cast removes one unit of a spot's ``stock``; once a spot is fished out the ``fish``
verb rejects until it recovers. This per-tick consequence refills stock deterministically,
one unit per ``restock_interval`` game-seconds, capped at the spot's ``capacity``. It is
registered via :func:`bunnyland_anglersim.install.install_anglersim`.

The first time the consequence sees an understocked spot it merely *anchors* the restock
clock (``restocked_at_epoch``) to the current epoch, so refills are always measured from a
known point rather than the zero default.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent
from relics import World

from .components import FishingSpotComponent


class RestockConsequence:
    """Refill depleted fishing spots over time."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        for spot in list(world.query().with_all([FishingSpotComponent]).execute_entities()):
            state = spot.get_component(FishingSpotComponent)
            if state.stock >= state.capacity:
                continue
            if state.restocked_at_epoch <= 0:
                # Anchor the restock clock without granting free stock the first time.
                replace_component(spot, replace(state, restocked_at_epoch=epoch))
                continue
            elapsed = epoch - state.restocked_at_epoch
            if elapsed < state.restock_interval:
                continue
            gained = elapsed // state.restock_interval
            new_stock = min(state.capacity, state.stock + gained)
            replace_component(spot, replace(state, stock=new_stock, restocked_at_epoch=epoch))
        return []


__all__ = ["RestockConsequence"]
