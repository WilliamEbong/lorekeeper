# Feature 009: Editor follow-ups (owner review of 008)

## Overview
The owner reviewed feature 008 and asked for three things: dragging a timeline bar by its start, its end or the whole block; relationships kept apart from ages; and BC dates finer than a year shown properly. The owner also asked for judgment calls on the remaining open items, recorded in docs/build/SESSION-LOG.md.

## Functional requirements
- **FR-1 Drag handles.** On a timeline bar whose start and end are both written and exact, the first 10 px at each end of the bar is a handle with a resize cursor. Dragging the start handle changes only the start, and dragging the end handle changes only the end. Dragging elsewhere on the bar, or on a point mark, moves the whole item, as in 008. A handle cannot be dragged past the other end of the bar. While dragging, the new date shows beside the item. After the drop, a message offers Undo. Bars narrower than 24 px have no handles; zoom in to resize them. Keyboard users edit the same dates in the inspector.
- **FR-2 Relationships view.** A Relationships tab shows who is related to whom: one card per person or group with at least one relationship. A relationship is a resolved link between two items whose type category is person or group, such as parent, spouse or member of. Event participation, places and timing links are left out. Each card lists its relationships grouped by kind; links pointing at the card use the role's inverse label (Children, Members), and the second direction of a two-way pair is not repeated. Names select the item. A filter box narrows the cards. The empty state explains how to add a relationship.
- **FR-3 Ages stays separate.** The age grid keeps the name Ages, and its tab is renamed to match (`tab-ages`). Its hint points to Relationships for who is related to whom.
- **FR-4 BC display.** The editor writes and reads BC dates finer than a year in the engine's new form (`0044-03 BC`, `0044-03-15 BC`, `0044-03-15 09:30 BC`) and words them ("15 March 44 BC").

## Success criteria
- **SC-1** In the browser, dragging a bar's start handle changes only the start, the end handle only the end, and the middle both; each offers Undo, and the file changes accordingly.
- **SC-2** The Relationships tab shows parents, children, spouses and members on the Wuthering Heights import, and no events.
- **SC-3** `tests/test_editor_dates.py` passes against the engine's new BC formats.
- **SC-4** The full suite passes and the Impeccable detector is clean.
