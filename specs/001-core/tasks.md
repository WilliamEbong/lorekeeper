# Tasks 001: core

## Setup
- [x] T001 Package skeleton: `lorekeeper/__init__.py`, `lorekeeper/__main__.py`, `tests/__init__.py`
- [x] T002 Fixture project `tests/fixtures/world/` (lore.json + ~12 items, mixed LF/CRLF, comments, quoted values, aliases, a broken link)

## Foundational
- [x] T003 [Codex] `lorekeeper/fm.py` + `tests/test_fm.py` per plan contract (FR-2, FR-3, FR-4, FR-5 link_target)
- [x] T004 `lorekeeper/store.py`: schema defaults, scanning, items, link resolution, backlinks, structural findings (FR-1, FR-5–FR-9)
- [x] T005 `lorekeeper/store.py`: atomic_write, versions, create, update with merge/409 (FR-9–FR-12)
- [x] T006 `lorekeeper/ops.py`: LoreError, Param/Op, OPS (init, schema, query, show, create, set, link, unlink, check), run, to_json (FR-13–FR-15)

## User stories
- [x] T007 US1 `lorekeeper/cli.py` generated from OPS; exit codes; human/JSON output (FR-16)
- [x] T008 US2 [Codex] `lorekeeper/mcp.py` + `tests/test_mcp.py` dual-era server, golden test vs CLI (FR-17, SC-3)
- [x] T009 US3 `tests/test_store.py`: links/backlinks, duplicates, create ids/paths, merge + 409 + stale-write safety, OneDrive retry (SC-4)
- [x] T010 US1 `tests/test_cli.py`: init/create/show/set/link/check end-to-end through `python -m lorekeeper`
- [x] T011 US4 `tests/test_sagas.py`: three saga Wikis round-trip byte-identical and load without parser FAILs (SC-1, SC-2)

## Polish
- [x] T012 `tests/test_rules.py`: stdlib-only import scan, no bare open(, every op in CLI + MCP (SC-6, SC-7, SC-9)
- [x] T013 `tests/test_perf.py`: 3,000 items load < 1.5 s (SC-5)
- [x] T014 Saga-regex compatibility check of written files (SC-8)
