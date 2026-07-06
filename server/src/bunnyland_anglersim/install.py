"""Runtime wiring: register the restock and fishing-run consequences and the record journal."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .records import RecordMemoryReactor
from .restock import RestockConsequence
from .runs import install_runs


def install_anglersim(actor: WorldActor) -> None:
    """Register anglersim's runtime services (a ``service_factories`` entry).

    - the per-tick fishing-spot restock consequence,
    - the seasonal fishing-run storyteller consequence (plus its pacing marker), and
    - a reactor that journals record-setting catches into the core memory store (resolved
      lazily so plugin order never matters; dormant if no memory store is installed).
    """
    actor.register_consequence(RestockConsequence())
    install_runs(actor)
    RecordMemoryReactor(lambda: getattr(actor, "memory_store", None)).subscribe(actor.bus)


__all__ = ["install_anglersim"]
