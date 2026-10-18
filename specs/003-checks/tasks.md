# Tasks 003: checks
- [ ] T001 Move `item_dates`/`calendar_of`/`show_when` to `lorekeeper/timeinfo.py` (ops re-exports); `Item.from_fields`, `Project.from_items` (FR-8)
- [ ] T002 [Codex] `lorekeeper/checks.py` + `tests/test_checks.py` (FR-1–FR-7, SC-1–SC-3)
- [ ] T003 `check` op runs `checks.run`; ops `where`, `knows` (FR-9) + tests
- [ ] T004 Perf: 3,000 items check < 2 s (SC-4)
