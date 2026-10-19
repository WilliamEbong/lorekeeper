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
Use the build-continuously skill, to its full extent. I am handing this off and walking away. Build feature 010, the progressive story wiki, into Lorekeeper AND integrate it into my three creative writing projects (Realm, Space and Zombies sagas). Make it easy for AI to use, through MCP and the CLI. Don't stop to ask me anything except the skill's real blockers.

STEP 0. Read these in full, in this order, before any other action:
1. docs/build/HANDOFF.md (authoritative: current state, decisions 26–34, gotchas for this run)
2. specs/010-progressive-wiki/spec.md (the requirements; success criteria SC-1 to SC-8 are the definition of done)
3. docs/build/BUILD-PLAN.md (the "Feature requests from the owner" section, and how earlier runs were laid out)
4. the last 60 lines of docs/build/SESSION-LOG.md

STEP 1. Set up to run unattended, exactly as the skill says:
- Load CronCreate, CronDelete, request_keep_awake and PushNotification in one ToolSearch call.
- Schedule the hourly resume cron on an off-minute with the skill's resume prompt, and log its job ID in SESSION-LOG.
- Call request_keep_awake.
- Put the whole plan in the app's task list (update_plan) and keep it current. That list is how I check progress from my phone.
- Check out the branch feat/010-progressive-wiki. If anything is uncommitted, commit it first ("docs: ...").
- Re-check the live state yourself: the Lorekeeper test suite, and each saga's HEAD, vendored engine version and chapter stages. Treat the handoff's numbers as leads, not facts.
- Add a "Run 4" section to BUILD-PLAN.md with the skill's deepened brief (four points), the acceptance checks (SC-1 to SC-8 plus the AI-use checks below) and the ordered steps. Link to the spec's plan.md and tasks.md rather than copying them.
- Keep the three build docs current the whole way: SESSION-LOG appended as you go (every decision with how to undo it), BUILD-PLAN steps ticked, and HANDOFF.md rewritten at about 94% context, on a blocker, and at the end.

My decisions, which are locked:
- Progressive mode: an index per type that lists only what the reader has met by chapter N, under the names the reader knows. Someone seen before being named is listed under the reader's description until named.
- Each entry opens a card with its own chapter toggle. Character cards cover status, where they are, beliefs, what they know, wants, relationships and key events. Factions, locations, important items and vehicles, and kinds of things such as "standard alien battle tank", get the same kind of card.
- A secret identity is a separate card until the reveal chapter, then the cards merge.
- Full (complete) mode is the most recent state: everything as of the latest approved chapter, with all identities on one card and the chapter-by-chapter history folded underneath.
- My three saga systems must keep working exactly the way they work now. The wikis are added on top: a separate Story Wiki layer, written after each chapter is frozen, from approved outputs only, never from drafts.
- Out of scope for this run: the planning wiki (feature 011, in BUILD-PLAN under "Planning wiki"). Don't build any of it.

BUILD IT INTO LOREKEEPER (the engine, CLI, MCP server and editor):
- Spec Kit: the spec exists. Run clarify (answer the questions yourself with the recommended option, record the answers in the spec, and log them), then plan, tasks, analyze, implement and converge. Don't change my locked decisions.
- Ponytail and standard-library Python only. Every open() passes encoding="utf-8". Tests use unittest. Preserve line endings. Use TDD for the stamp parser, the visibility rules, name changes and identity folding.
- Use systematic debugging for every failure, and verification-before-completion before claiming anything done.
- Playwright verifies every editor change: the Wiki tab, the chapter picker, the card toggle, Add a fact with Undo, light, dark and 390 px, no console errors. Also run the Impeccable detector.
- Lorekeeper git: commit locally on feat/010-progressive-wiki at each green checkpoint. Never push, and never merge into main; I'll approve those at the end.

MAKE IT EASY FOR AI TO USE:
- Every new capability (wiki index, wiki card, fact-add, fact-end) is an operation in the one operations table, so it is automatically a CLI command with --json, an MCP tool, and an editor API.
- Write each tool's description and parameters for an AI reader: what it does, when to use it, what it returns, and one example.
- Errors must say what went wrong and how to fix it.
- AI writes facts only through fact-add and fact-end, never by hand-editing stamps.
- Extend the MCP golden test to the new tools (MCP output equals CLI --json).
- Update docs/agent-skill.md so an agent can use the wikis from it alone: when to read the wiki, how to add and end facts, and the saga after-freeze routine.
- Each saga gets a project .mcp.json that runs its vendored engine's MCP server on that saga. Prove it with an MCP handshake test that lists the tools and calls wiki on a saga clone.
- The README shows the same MCP setup for any world.

INTEGRATE IT INTO MY THREE SAGAS:
- Work only in fresh clones and probes under C:\Users\Owner\lk-scratch, with the run-3b method:
  - take a before-baseline;
  - make the changes in the clones;
  - replay them on the probes;
  - require all of these before landing: green saga suites with parity, byte-identical status and validate output for every chapter, an untouched Wiki/ and existing skills, roles and templates, and in-progress profile packets that still verify.
- Each saga must end up with:
  - the re-vendored engine;
  - the story_wiki key in _system/lorekeeper.json;
  - a Story Wiki/ folder backfilled through its last frozen chapter;
  - the shared after-freeze skill (story_wiki_update) with its one pointer;
  - the .mcp.json;
  - the Wiki tab working in saga.py timeline, checked in Playwright.
- Backfill from approved sources only: each frozen chapter's CURRENT_WORLD_BIBLE_OUT.md and approved deltas, plus the Wiki's git diffs between freeze commits. Search chapter text for specific questions instead of reading it whole. Never read the chapter architecture (the planned cards) or plans for unwritten chapters. Record any value you have to decide in that saga's agent_decisions.md.
- Run the three sagas' backfills as parallel subagents, one per saga, each with a complete, self-contained brief.
- Prove the after-freeze routine on a probe: run the skill for the last frozen chapter from scratch and compare the result with the backfill.
- Landing: you are authorized to land into the three live saga repos by fast-forward only with land.sh, once every saga check passes. If a live repo moved, re-clone and redo. Never force. Never stage in-progress chapters, _system/state, provenance or saga.log. Use "system:" for engine and config commits and "wiki:" for Story Wiki content.

FINISH, as the skill says:
- Run every check again: the Lorekeeper suite, the saga suites, Playwright, the detector and the MCP tests.
- Run two fresh-context reviewers (one on the Lorekeeper diff, one on the saga diffs) and fix every finding you confirm.
- Update the README, user guide and agent skill, rewrite HANDOFF.md as the final state, update memory, and delete the resume cron.
- Send me a PushNotification saying done or blocked. Send the key Playwright screenshots (a progressive card, a full card, the saga Wiki tab) with SendUserFile.
- Report in plain language in the skill's order: built, evidence, decisions I might want to change, not done, how to see it, git. Tell me what to try first in the Wiki tab.
```

---

## Resume prompt (after any interruption)

```
build-continuously resume for Lorekeeper run 4 (feature 010). Read docs/build/HANDOFF.md, docs/build/BUILD-PLAN.md (the Run 4 section), specs/010-progressive-wiki/ (spec, plan, tasks) and the last 150 lines of docs/build/SESSION-LOG.md first. Check git status and log in Lorekeeper and in the saga clones under C:\Users\Owner\lk-scratch to confirm where you stopped. Re-create the hourly resume cron and keep-awake if they are gone. Then continue from the first unfinished step, following docs/build/KICKOFF-PROMPT.md. Stop only when done or on a real blocker.
```
