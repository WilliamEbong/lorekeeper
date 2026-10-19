# Feature 013: A plain-language editor

## Overview
The owner asked on 2026-10-19 for Lorekeeper to be easy, pleasant and mature for creative people who are not programmers, with AI instructions kept separate from the human interface. Feature 012 removed the terminal. This feature goes over the editor itself: every word a person reads there should be a writer's word, and every problem should say what happened and what to do next.

## Clarifications

### Session 2026-10-19
Answered by the build agent with the recommended option.
- Q: What is in scope? → A: Text a person sees in the editor (labels, headings, hints, tooltips, screen-reader labels, empty states, messages, continuity findings as the editor shows them) and how the editor presents errors. Layout and features stay as they are.
- Q: Some messages come from the engine and are shared with the command line and AI tools. Change them there? → A: No. Those messages are precise on purpose, and AI agents rely on them. The editor translates: it keeps a plain message for each error code and shows the engine's own text only where it adds a specific detail (a field name, a date) and reads as plain language.
- Q: Raw field keys (`born`, `date_min`)? → A: The editor shows labels (from the world's settings, else words such as "Earliest date"). A key appears only where the person types one (adding a field of their own).
- Q: File paths? → A: Kept, as quiet secondary text where they help someone find a file on disk; never as the main text.
- Q: Product words (Timeline, Subway, Inspector, Continuity, story wiki, planning wiki)? → A: Kept; the user guide explains them.

## Functional requirements
- **FR-1** No programmer terms in the editor's visible or spoken text: no raw keys, codes, JSON, frontmatter, schema, parser, token, API, operation, hash or version words, except quiet file paths and a field key a person typed.
- **FR-2** Every error the editor shows says, in plain words, what happened and what the person can do. Unknown problems say how to recover (reload, try again, close and reopen Lorekeeper), never "Unknown error".
- **FR-3** One word per idea: an "item" is always an item in the editor (not entry, record or object); a "connection" is always a connection.
- **FR-4** Saga (proposals-only) wording explains what happens to a proposal in a writer's terms.
- **FR-5** Engine messages, the command line and the AI tools are unchanged.

## Success criteria
- The audit list (every flagged string, with file and line) is resolved or explicitly kept with a reason in SESSION-LOG.
- Playwright tour of every tab, the inspector, a save conflict, a date the editor cannot read, a broken connection, the Continuity tab, and a saga's propose flow shows no programmer language, with a clean console, in light, dark and at 390 px.
- `python -m unittest discover -s tests` passes; the Impeccable detector finds nothing new.
