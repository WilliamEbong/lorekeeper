# KICKOFF PROMPT — run 4: build the progressive story wiki (feature 010)

The prompts for runs 1–3 are in git history.

## How to start
1. Open a **new** Claude Code session with its working folder set to `C:\Users\Owner\OneDrive\Documents\Lorekeeper`.
2. Make sure the session can reach these folders. `.claude/settings.json` already lists them; add any that are refused in the app.
   - `C:\Users\Owner\OneDrive\Documents\Creative writing`
   - `C:\Users\Owner\lk-scratch`
3. Paste everything inside the first box below as your first message.
4. If the run is interrupted (usage limit, crash), open or resume a session in the same folder and paste the **resume prompt**.

---

## Prompt (paste this)

```
Use the build-continuously skill. Build feature 010, the progressive story wiki, to completion, and apply it to my three sagas. Don't stop to ask me anything except the skill's real blockers.

FIRST read these in full, in this order, before any other action:
1. docs/build/HANDOFF.md (authoritative: current state, decisions 26–34, gotchas for this run)
2. specs/010-progressive-wiki/spec.md (the requirements; its success criteria are the definition of done)
3. docs/build/BUILD-PLAN.md (the "Feature requests from the owner" section, and how earlier runs were laid out)
4. the last 60 lines of docs/build/SESSION-LOG.md

THEN:
- Check out the branch feat/010-progressive-wiki. If the spec and docs are uncommitted, commit them first ("docs: specify the progressive story wiki").
- Re-check the live state yourself: Lorekeeper tests, and each saga's HEAD, vendored engine and chapter stages. Treat the handoff's numbers as leads, not facts.
- Add a "Run 4" section to BUILD-PLAN.md with the deepened brief, the acceptance checks (the spec's SC-1 to SC-8) and the ordered steps, linking to the spec's plan.md and tasks.md rather than copying them.

My decisions, which are locked:
- Progressive mode: an index per type that lists only what the reader has met by chapter N, under the names the reader knows. Someone seen before being named is listed under the reader's description until named.
- Each entry opens a card with its own chapter toggle. Character cards cover status, where they are, beliefs, what they know, wants, relationships and key events. Factions, locations, important items and vehicles, and kinds of things such as "standard alien battle tank", get the same kind of card.
- A secret identity is a separate card until the reveal chapter, then the cards merge.
- Complete mode shows everything, with one card holding all of a character's identities.
- My three saga systems must keep working exactly the way they work now. The progressive wiki is added on top: a separate Story Wiki layer, written after each chapter is frozen, from approved outputs only, never from drafts.
- Lorekeeper is easy for AI to use: the built-in MCP server (registered in each saga's .mcp.json) and the CLI with --json, writing facts only through the new fact operations.

How to work:
- Spec Kit: the spec exists. Run clarify (answer the questions yourself and record the answers in the spec), then plan, tasks, analyze, implement and converge. Don't change my locked decisions. Anything else you decide, log it in SESSION-LOG with how to undo it.
- Ponytail and standard-library Python only. Every open() passes encoding="utf-8". Tests use unittest. Preserve line endings. Use TDD for the stamp parser, visibility and folding logic.
- Playwright verifies every editor change: light, dark and 390 px, with no console errors. Run the Impeccable detector.
- Lorekeeper git: commit locally on feat/010-progressive-wiki at each green checkpoint. Never push, and never merge into main; I'll approve those at the end.
- Sagas: work only in fresh clones and probes under C:\Users\Owner\lk-scratch, using the run-3b method:
  - take a before-baseline;
  - make the changes in the clones;
  - replay them on the probes;
  - require green suites with parity, byte-identical status and validate output for every chapter, an untouched Wiki/, and in-progress profile packets that still verify;
  - backfill every frozen chapter's Story Wiki from approved sources only, and record any value you have to decide in that saga's agent_decisions.md;
  - read only what the backfill needs: each frozen chapter's CURRENT_WORLD_BIBLE_OUT.md and approved deltas, plus the Wiki's git diffs between freeze commits. Search chapter text for specific questions instead of reading it whole. Never read the chapter architecture (the planned cards) or plans for unwritten chapters.
- Landing in the sagas: you are authorized to land into the three live saga repos by fast-forward only with land.sh, once every saga check passes. If a live repo moved, re-clone and redo. Never force. Never stage in-progress chapters, _system/state, provenance or saga.log. Use "system:" for engine and config commits and "wiki:" for Story Wiki content.
- Use subagents for broad searches and for independent pieces with no overlapping files. Finish with a fresh-context review of the Lorekeeper diff and one of the saga diffs, and fix what they confirm.

Definition of done:
- Every success criterion SC-1 to SC-8 in the spec passes, with evidence from this run.
- The sagas are landed, with their systems unchanged and a working Story Wiki backfilled through their last frozen chapter.
- README, user guide and agent skill are updated.
- BUILD-PLAN and SESSION-LOG are current, HANDOFF.md is rewritten as the final state, and memory is updated.

Then report to me in plain language, in the skill's order (built, evidence, decisions I might want to change, not done, how to see it, git), and tell me what to try first in the Wiki tab.
```

---

## Resume prompt (after any interruption)

```
build-continuously resume for Lorekeeper run 4 (feature 010). Read docs/build/HANDOFF.md, docs/build/BUILD-PLAN.md (the Run 4 section), specs/010-progressive-wiki/ (spec, plan, tasks) and the last 150 lines of docs/build/SESSION-LOG.md first. Check git status and log in Lorekeeper and in the saga clones under C:\Users\Owner\lk-scratch to confirm where you stopped. Then continue from the first unfinished step, following the rules in docs/build/KICKOFF-PROMPT.md. Stop only when done or on a real blocker.
```
