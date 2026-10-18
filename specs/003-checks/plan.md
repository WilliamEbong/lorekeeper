# Plan 003: checks

## Files
- `lorekeeper/checks.py` [Codex]: `run(project) -> list[finding]`, covering FR-1–FR-6. It uses `ops.item_dates`, `Project.links`, `Project.schema` and `dates`. Pure: it reads the project and never writes.
- `lorekeeper/store.py`: `Item.from_fields(path, fields, body="")` builds an in-memory item from synthetic frontmatter text (FR-8). `Project.from_items(root, config, items)` builds a project around in-memory items without scanning.
- `lorekeeper/ops.py`:
  - `check` adds `checks.run(p)`.
  - The ops `where` and `knows` (FR-9).
  - `item_dates` moves to a new module `lorekeeper/timeinfo.py`, so that checks.py can import it without a cycle (ops imports checks). Ops re-exports it.
- `tests/test_checks.py` [Codex]: one vector per check (definite → FAIL, possible → WARN, satisfied → nothing), the provisional cap, and the fixture expectations (SC-1).
- `tests/test_perf.py`: adds "3,000 items check in under 2 s" (SC-4).

## checks.py contract
```python
def run(project) -> list[dict]           # findings: {severity, code, detail, path, line}
# helpers (module-level, tested directly):
def possible(x, y)                        # x, y: When -> (min, max) minute range [lo, hi-1]
def compare_ge(x, y, lag) -> str|None     # "FAIL" | "WARN" | None for X >= Y + lag
def compare_eq(x, y, lag) -> str|None
def same_place(project, a, b) -> bool     # equal, or linked by located_in (transitively, either way)
```
- **Severity cap:** if either item involved has `status: provisional`, or a date with `provisional: True`, a FAIL becomes a WARN.
- **Config:** checks settings come from `config.get("checks", {})`: `min_parent_age` (12), `max_age` (130), `two_places` (`"on"`), `story_order` (False). Rules come from `config.get("rules", [])`.

## Decisions
- **No auto-scheduling solver** (constitution V): we report and never move.
- **Two-places WARN only at hour/minute precision**, to avoid day-level noise.
- **Story order (flashback) check is off by default.**
