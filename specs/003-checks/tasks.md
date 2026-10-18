# Tasks 003: checks
- [x] T001 Move `item_dates`/`calendar_of`/`show_when` to `lorekeeper/timeinfo.py` (ops re-exports); `Item.from_fields`, `Project.from_items` (FR-8)
- [x] T002 [Codex] `lorekeeper/checks.py` + `tests/test_checks.py` (FR-1–FR-7, SC-1–SC-3)
- [x] T003 `check` op runs `checks.run`; ops `where`, `knows` (FR-9) + tests
- [x] T004 Perf: 3,000 items check < 2 s (SC-4)

## Phase 2: Convergence
- [x] T005 [HIGH] FR-9: tests for `where` and `knows` on the fixture world (`tests/test_time_ops.py`)
