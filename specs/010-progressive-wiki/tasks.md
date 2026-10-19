# Tasks 010: Progressive story wiki

## Engine (TDD: test first, watch it fail, then code)
- [x] T1 `wiki.py` stamps and chapter values: every stamp form, en dash, case and spacing, unreadable and reversed markers, `CH003`/`ch 3`/`3`, link-suffix stamps. (SC-1)
- [x] T2 Facts and sections: list items with continuation, paragraphs, comments and fences skipped, untitled lead section, line spans, unstamped inheritance. (SC-1)
- [x] T3 Story layer: companions from `story_wiki` (beside the root too), attachment by `page` or name, standalone companions, never items, never ambiguous; `## Names` as late aliases. (SC-1)
- [x] T4 Visibility, shown names, folding at the reveal chapter, complete mode, spoiler guard for links. (SC-1)
- [x] T5 Index and card builders; worked-out Where, Knows, Relationships; chapter list with labels. (FR-8 to FR-12)
- [x] T6 Fact edits: `fact-add` (creates companions, `--type` standalone), `fact-end` (`--reopen`), `fact-remove`; CONFLICT, refusals with fixes, line endings kept. (FR-7)
- [x] T7 SC-2 fixture world, tested in both layouts (facts in pages; facts in a story-wiki folder).

## Faces
- [x] T8 `ops.py`: the four ops with guides; `check` gains STAMP_UNREADABLE and STAMP_RANGE; `store.py` defaults (`revealed_as`, `kind`, `sections`) and starter sections on `create`. (FR-4 to FR-7, FR-18)
- [x] T9 `cli.py` `--config`, plain-text `wiki` output; `__main__.py` file run; `mcp.py` guides in descriptions, `--saga` filter, instructions; MCP golden extended to the new tools. (FR-7a, FR-8, SC-2)
- [x] T10 `serve.py`: story-wiki folder in the stamp. (FR-16)
- [x] T11 3,000-item timing for index and card under 1 s. (SC-4)

## Editor
- [x] T12 Wiki tab: picker, filter, index, card with toggle, facts with markers, ended and folded and worked-out marks, Add a fact, No longer true after, Undo, saga requests, live reload, 390 px. (FR-13 to FR-17)
- [x] T13 Playwright on the fixture (light, dark, 390 px, console clean) and the Impeccable detector. (SC-3)

## Starter worlds and guides
- [x] T14 Templates: stamped facts, a renamed character, a secret identity in Novel, Series and Campaign. (FR-25)
- [x] T15 User guide, agent skill, README (MCP setup for any world). (FR-26, FR-23)

## Sagas (clones and probes under lk-scratch)
- [x] T16 Before-baseline on probes; fresh clones.
- [x] T17 Re-vendor; `story_wiki` key; `story_wiki_update` skill, README listing and one pointer; `.mcp.json`; saga suites with parity. (FR-19 to FR-21, FR-23)
- [x] T18 MCP handshake test on each clone: lists `wiki`, `fact-add`, `fact-end`; calls `wiki`. (SC-7)
- [x] T19 Backfill, three parallel agents, approved sources only, decisions in `agent_decisions.md`. (FR-22, SC-6)
- [x] T20 Replay on probes: suites, byte-identical status and validate, untouched Wiki, skills, roles and templates, profile packets verify; after-freeze routine re-run from scratch on a probe matches the backfill; reviewer on three characters per saga. (SC-5, SC-6)
- [x] T21 Playwright on `saga.py timeline` (Wiki tab, Add a fact queues a request). (SC-3)
- [x] T22 Land fast-forward only with `land.sh`. (FR-24)

## Finish
- [x] T23 Full suite, stdlib and `open()` scans, saga suites, Playwright, detector, MCP tests; two fresh-context reviews and their fixes. (SC-8)
