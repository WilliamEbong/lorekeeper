# KICKOFF PROMPT — run 5: build the planning wiki (feature 011)

The prompts for runs 1–4 are in git history.

## How to start
1. Open a **new** Claude Code session with its working folder set to `C:\Users\Owner\OneDrive\Documents\Lorekeeper`.
2. Make sure the session can reach these folders (add any that are refused in the app):
   - `C:\Users\Owner\OneDrive\Documents\Creative writing`
   - `C:\Users\Owner\lk-scratch`
3. Paste everything inside the first box below as your first message.
4. If the run is interrupted (usage limit, crash), open or resume a session in the same folder and paste the **resume prompt**.

---

## Prompt (paste this)

```
Use the build-continuously skill, to its full extent. I am handing this off and walking away. Build feature 011, the planning wiki, into Lorekeeper AND integrate it into my three creative writing projects (Realm, Space and Zombies sagas). Make it easy for AI to use, through MCP and the CLI. Don't stop to ask me anything except the skill's real blockers.

STEP 0. Read these in full, in this order, before any other action:
1. docs/build/HANDOFF.md (authoritative: current state, the locked decisions for 011 in section 3, the gotchas for this run in section 4)
2. docs/build/BUILD-PLAN.md, "Feature requests from the owner" → "Planning wiki" (my request, the confirmed shape, sources, linking, undecided material), and the "Run 4" section (how the last run was laid out)
3. specs/010-progressive-wiki/spec.md (what 011 builds on: the Wiki tab, cards, fact operations, the Story Wiki layer)
4. the last 60 lines of docs/build/SESSION-LOG.md
5. In the Realm saga (read only): _system/workflow/AUTHORITY.md, _system/skills/impact_analyze_human_change.md, and the head of _system/knowledge/overrides.md (how canon changes and HUMAN OVERRIDEs work today)

STEP 1. Set up to run unattended, exactly as the skill says:
- Load CronCreate, CronDelete, request_keep_awake and PushNotification in one ToolSearch call.
- Schedule the hourly resume cron on an off-minute with the skill's resume prompt, and log its job ID in SESSION-LOG.
- Call request_keep_awake.
- Put the whole plan in the app's task list (update_plan) and keep it current. That list is how I check progress from my phone.
- Create the branch feat/011-planning-wiki from main. If anything is uncommitted, commit it first ("docs: ...").
- Re-check the live state yourself: the Lorekeeper test suite, and each saga's HEAD, vendored engine version and chapter stages. Treat the handoff's numbers as leads, not facts.
- Add a "Run 5" section to BUILD-PLAN.md with the skill's deepened brief (four points), the acceptance checks (the spec's success criteria plus the AI-use checks below) and the ordered steps. Link to the spec's plan.md and tasks.md rather than copying them.
- Keep the three build docs current the whole way: SESSION-LOG appended as you go (every decision with how to undo it), BUILD-PLAN steps ticked, and HANDOFF.md rewritten at about 94% context, on a blocker, and at the end.

My decisions, which are locked:
- The planning wiki is the intended end state of each story: everything I have designed, including what no reader knows yet, as well-linked pages. It is a back-end reference for me and the AI. Flow: planning wiki → chapter cards → drafting → the full and progressive wikis.
- The World Bible stays the master. The planning wiki is a derived, per-entity view of all my planning documents (World Bible, military bible, Conversations dialogue documents, character/species/faction/combatant card libraries, tech ledgers, rulings and overrides, mystery and setup/payoff ledgers). Every planning fact cites its source document and section. Each saga's AUTHORITY.md ranking decides conflicts.
- When I change a planning fact, or tell the AI to, it is recorded as a HUMAN OVERRIDE in the override register and written back into the World Bible by the AI. An impact review then covers the matching planning pages, bible sections, unwritten chapter cards and the in-progress chapter. Anything that contradicts a frozen chapter is flagged to me, never applied to approved prose.
- Pages are well linked: kind pages list their notable members, a character lists the saved dialogues that feature them, and things list the chapters they appear in. Lorekeeper computes these link lists mechanically (tags, Conversations headings and speakers, a whole-word name and alias search over the parsed chapter cards, with an exclusion list for names that are ordinary words). The AI never writes them and never reads all the cards to make them.
- Undecided material (plot ideas, opportunities portfolios, unapproved-decisions reports) is shown, clearly labelled as ideas and kept apart from decided facts. It is never used as canon: not for cards, impact reviews or link lists.
- The Wiki tab's picker becomes Planning | Complete | Chapter N. Planning facts never appear in Complete or Chapter N, and never in a profile packet or drafting context.
- My three saga systems must keep working exactly the way they work now. The planning wiki is added on top.

BUILD IT INTO LOREKEEPER (the engine, CLI, MCP server and editor):
- Spec Kit: no spec exists yet. Run specify (write specs/011-planning-wiki/spec.md from my request in BUILD-PLAN and the decisions above), then clarify (answer the questions yourself with the recommended option, record the answers in the spec, and log them), then plan, tasks, analyze, implement and converge. Don't change my locked decisions.
- Keep it general: any Lorekeeper world can have a planning layer, not only the sagas. Reuse 010's Wiki tab, cards and fact operations rather than building a parallel system.
- Ponytail and standard-library Python only. Every open() passes encoding="utf-8". Tests use unittest. Preserve line endings. Use TDD for the source-section reader, the mechanical link lists (with the exclusion list), the ideas labelling, the override and write-back step, the impact search, and the rule that planning facts never leak into the other modes.
- Use systematic debugging for every failure, and verification-before-completion before claiming anything done.
- Playwright verifies every editor change: the Planning choice in the picker, a planning card with its source citations and link lists, ideas visibly labelled, the edit flow (in a saga it queues a change request), light, dark and 390 px, no console errors. Also run the Impeccable detector.
- Lorekeeper git: commit locally on feat/011-planning-wiki at each green checkpoint. Never push, and never merge into main; I'll approve those at the end.

MAKE IT EASY FOR AI TO USE:
- Every new capability (reading the planning wiki, proposing or recording a planning change, running the impact review) is an operation in the one operations table, so it is automatically a CLI command with --json, an MCP tool, and an editor API.
- Write each tool's description and parameters for an AI reader: what it does, when to use it, what it returns, and one example.
- Errors must say what went wrong and how to fix it.
- Extend the MCP golden test to the new tools (MCP output equals CLI --json), and keep lore mcp --saga safe: no tool may write an authority document or a Wiki page directly.
- Update docs/agent-skill.md so an agent can use the planning wiki from it alone: when to read it, how a planning change flows (override, write-back, impact review), and the saga routines.
- The README and user guide explain the planning wiki for any world.

INTEGRATE IT INTO MY THREE SAGAS:
- Work only in fresh clones and probes under C:\Users\Owner\lk-scratch, with the run-4 method (tools in lk-scratch\snap):
  - take a before-baseline;
  - make the changes in the clones;
  - replay them on the probes;
  - require all of these before landing: green saga suites with parity, byte-identical status, validate and health output for every chapter, an untouched Wiki/, Story Wiki/, roles, templates and existing skills, and in-progress profile packets that still verify.
- Never edit a live authority document (World Bible, architecture, style bible, Conversations) during this run: each in-progress chapter's provenance records their hashes. Prove the full change flow (edit → HUMAN OVERRIDE → write-back → impact review → refresh-sources for the unfrozen chapter → frozen-chapter conflicts flagged) on a probe copy only, and show me the impact report it produced.
- Each saga must end up with:
  - the re-vendored engine;
  - a planning-wiki key in _system/lorekeeper.json;
  - a planning wiki built from that saga's planning documents, every fact citing its source section, ideas labelled;
  - computed link lists (notable members, dialogues, appears-in chapters);
  - a shared skill for planning changes that follows the saga's existing human-change route (impact_analyze_human_change, the override register, refresh-sources), with its one pointer;
  - the Planning choice working in saga.py timeline, checked in Playwright.
- Read each large planning document once, split by section; use mechanical search for everything else. Never paste whole bibles into context. Record any value you have to decide in that saga's agent_decisions.md.
- Run the three sagas' planning-wiki builds as parallel subagents, one per saga, each with a complete, self-contained brief.
- Landing: you are authorized to land into the three live saga repos by fast-forward only with land.sh, once every saga check passes. If a live repo moved, re-clone and redo. Never force. Never stage in-progress chapters, _system/state, provenance or saga.log. Use "system:" for engine and config commits, "wiki:" for wiki content and "knowledge:" for decision rows.

FINISH, as the skill says:
- Run every check again: the Lorekeeper suite, the saga suites, Playwright, the detector and the MCP tests.
- Run two fresh-context reviewers (one on the Lorekeeper diff, one on the saga diffs, including a spot-check of planning facts against their cited sources and a check that no planning fact leaks into Complete or Chapter N) and fix every finding you confirm.
- Update the README, user guide and agent skill, rewrite HANDOFF.md as the final state, update memory, and delete the resume cron.
- Send me a PushNotification saying done or blocked. Send the key Playwright screenshots (a planning card, the picker with Planning, the saga Wiki tab) and the probe's impact report with SendUserFile.
- Report in plain language in the skill's order: built, evidence, decisions I might want to change, not done, how to see it, git. Tell me what to try first.
```

---

## Resume prompt (paste this after an interruption)

```
build-continuously resume: if a build turn is in progress or waiting on background work, do nothing. Otherwise read docs/build/BUILD-PLAN.md, docs/build/SESSION-LOG.md and docs/build/HANDOFF.md, then continue run 5 (feature 011, the planning wiki) from the plan. All locked decisions and authorizations in docs/build/KICKOFF-PROMPT.md still apply.
```
