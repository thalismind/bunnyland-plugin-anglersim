# Bunnyland Anglersim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin that adds an expansion-pack-sized **fishing** pack. Water-biome rooms (marsh, river, lake, ship, coast)
grow fishing spots, and characters — human or AI — cast a line with the `fish` verb to land
a **deterministically** rolled catch, keep a trophy log, and chase legendaries.

Everything is derived from stable inputs (a `blake2b` digest of the spot, angler, epoch, and
cast count reduced over sorted, weighted tables), so the pack never touches `random` or
`time` and stays reproducible under Bunnyland's strict determinism and coverage gates.

This repo intentionally keeps all fishing work outside the main `bunnyland-server` repo.

## Layout

- `server/` - Python Bunnyland plugin package with the fishing components, the catch table,
  the `fish` verb, a restock consequence, prompt fragments, a worldgen enrichment hook,
  spawn factories, and tests.

## Mechanics

1. **Fishing spots** — `FishingSpotComponent` on a room or object, seeded into water biomes
   by the worldgen hook (`AnglerWorldgenHook`), classified by biome and watery keywords.
2. **The `fish` verb** — cast at a reachable spot; a deterministic weighted catch table
   keyed by biome and time-of-day yields a fish item, with a per-spot cooldown and precise
   rejection reasons.
3. **Rarity** — weighted `common`/`uncommon`/`rare`/`legendary` tiers; a legendary catch
   emits a room-wide `LegendaryCatchEvent`.
4. **Bait** — `BaitComponent` items in the angler's inventory bias the roll toward rarer
   catches and are consumed on use.
5. **Trophy log** — `CatchLogComponent` records each angler's best weight per species and a
   recent haul, surfaced as a prompt fragment.

A restock consequence slowly refills depleted spots over time.

## Server Plugin

The plugin exposes `bunnyland_anglersim.bunnyland_plugins()` and contributes:

- `FishingSpotComponent`, `FishComponent`, `BaitComponent`, `CatchLogComponent`.
- `FishHandler` (the `fish` verb) and its `ActionDefinition`.
- `RestockConsequence` - refills fished-out spots each tick.
- `anglersim_fragments` - renders the trophy log and reachable spots into prompts.
- `AnglerWorldgenHook` - seeds fishing spots in generated water biomes.
- `spawn_fishing_spot`, `attach_fishing_spot`, `spawn_bait`, `spawn_fish` - spawn factories.

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_anglersim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_anglersim` package must be importable by the server (installed into the server's
environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
