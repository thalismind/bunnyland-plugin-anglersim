# bunnyland-anglersim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_anglersim`.

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_anglersim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `FishingSpotComponent` (a castable spot), `FishComponent` (a caught
  fish), `BaitComponent` (a consumable that biases the roll), `CatchLogComponent` (the
  angler's trophy log).
- **The `fish` verb** — casts at a reachable spot, rolls a deterministic catch keyed by
  biome and time-of-day, spawns the fish, consumes bait, advances the spot, updates the
  trophy log, and emits `FishCaughtEvent`/`LegendaryCatchEvent`.
- **A restock consequence** that refills fished-out spots over time.
- **Prompt fragments** rendering the trophy log and reachable spots into prompts.
- **A worldgen hook** seeding fishing spots into generated water biomes.
- **Spawn factories** — `spawn_fishing_spot`, `attach_fishing_spot`, `spawn_bait`,
  `spawn_fish`.

## Determinism

Catches are derived from a `blake2b` digest of `(spot id, character id, epoch, cast count)`
reduced over sorted, weighted tier and species tables. No `random`, no `time`, no
hash-ordered iteration — the same inputs always yield the same fish.
