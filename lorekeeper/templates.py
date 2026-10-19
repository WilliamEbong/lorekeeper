"""Small starter worlds as Python data, so vendoring needs no template directory."""

WORLD_ITEMS = [
    {"type": "character", "name": "Mira Vale", "fields": {"born": "1990", "first_appearance": "1"},
     "body": "\n# Mira Vale\n\nA mapmaker looking for her missing sister. Replace these example details with your own.\n"
             "<!-- A chapter stamp such as [ch 2] at the end of a fact says from which chapter the reader knows it. "
             "Open the Wiki tab to see it work. -->\n"
             "\n## Beliefs\n\n- Believes her sister is still alive. [ch 1]\n"
             "\n## Wants\n\n- To find her sister. [ch 1]\n"
             "\n## Important events\n\n- Read a letter in her sister's hand. [ch 1]\n- Left Lantern Harbour with [[Ash]]. [ch 2]\n"},
    {"type": "character", "name": "Ash", "fields": {"first_appearance": "1"},
     "body": "\n# Ash\n\n<!-- Seen in chapter 1 before the reader learns the name: see Names. -->\n"
             "\n## Names\n\n- the stranger in the grey coat [ch 1-1]\n- Ash [ch 2]\n"
             "\n## Important events\n\n- Watched Mira read the letter. [ch 1]\n- Offered to guide Mira. [ch 2]\n"},
    {"type": "character", "name": "The Cartographer",
     "fields": {"first_appearance": "1", "revealed_as": "[[Ash]] [ch 2]"},
     "body": "\n# The Cartographer\n\n<!-- A secret identity: a separate card until chapter 2 reveals it is Ash. -->\n"
             "\n## Important events\n\n- Signed the maps Mira follows. [ch 1]\n"},
    {"type": "location", "name": "Lantern Harbour", "fields": {},
     "body": "\n# Lantern Harbour\n\nA harbour where a letter begins the journey.\n"},
    {"type": "event", "name": "The Letter",
     "fields": {"date": "2025-04-01 09:00", "participants": ["[[Mira Vale]]"],
                "location": "[[Lantern Harbour]]"},
     "body": "\n# The Letter\n\nMira receives a letter from her sister.\n"},
    {"type": "event", "name": "Departure",
     "fields": {"date": "2025-04-02 09:00", "participants": ["[[Mira Vale]]"],
                "location": "[[Lantern Harbour]]", "after": ["[[The Letter]]"]},
     "body": "\n# Departure\n\nMira sets out to find her sister.\n"},
]

CHAPTERS = [
    {"type": "chapter", "name": "Chapter 1", "fields": {"date": "2025-04-01", "order": "1"},
     "body": "\n# Chapter 1\n\nBegin with [[The Letter]].\n"},
    {"type": "chapter", "name": "Chapter 2", "fields": {"date": "2025-04-02", "order": "2"},
     "body": "\n# Chapter 2\n\nFollow Mira's [[Departure]].\n"},
]

NOVEL_NARRATIVE = "# Narrative\n\n- [[Chapter 1]]\n- [[Chapter 2]]\n"
SESSIONS_NARRATIVE = "# Sessions\n\n- [[Session 1]]\n- [[Session 2]]\n"

TEMPLATES = {
    "novel": {
        "config": {"properties": {"order": {"label": "Story order", "format": "number"}},
                   "checks": {"story_order": True}},
        "items": WORLD_ITEMS + CHAPTERS,
        "files": {"narrative.md": NOVEL_NARRATIVE},
    },
    "series": {
        "config": {
            "types": {"book": {"label": "Book", "plural": "Books", "id_prefix": "BOOK", "category": "narrative"}},
            "properties": {"order": {"label": "Story order", "format": "number"},
                           "series_order": {"label": "Series order", "format": "number"}},
            "rules": [{"rule": "monotonic", "select": {"type": "book"}, "order": "series_order"}],
            "checks": {"story_order": True},
        },
        "items": WORLD_ITEMS + CHAPTERS + [
            {"type": "book", "name": "Book 1", "fields": {"date": "2025", "series_order": "1"},
             "body": "\n# Book 1\n\nThe search begins. Chapters: [[Chapter 1]], [[Chapter 2]].\n"},
            {"type": "book", "name": "Book 2", "fields": {"date": "2026", "series_order": "2"},
             "body": "\n# Book 2\n\nWhat happens after the search?\n"},
        ],
        "files": {"narrative.md": NOVEL_NARRATIVE},
    },
    "campaign": {
        "config": {
            "types": {
                "faction": {"label": "Faction", "plural": "Factions", "id_prefix": "FAC", "category": "group"},
                "session": {"label": "Session", "plural": "Sessions", "id_prefix": "SES", "category": "narrative"},
                "quest": {"label": "Quest", "plural": "Quests", "id_prefix": "QUEST", "category": "thing"},
            },
            "roles": {"members": {"label": "Members", "inverse": "Member of faction", "to": ["character"]}},
            "properties": {"order": {"label": "Session order", "format": "number"}},
            "checks": {"story_order": True},
        },
        "items": WORLD_ITEMS + [
            {"type": "faction", "name": "Harbour Guild", "fields": {"members": ["[[Mira Vale]]"]},
             "body": "\n# Harbour Guild\n\nMapmakers and sailors who share news.\n"},
            {"type": "quest", "name": "Find the Sister", "fields": {},
             "body": "\n# Find the Sister\n\nFollow the clue in [[The Letter]].\n"},
            {"type": "session", "name": "Session 1", "fields": {"date": "2025-04-01", "order": "1"},
             "body": "\n# Session 1\n\nIntroduce [[Harbour Guild]] and [[Find the Sister]]. The date is in-world.\n"},
            {"type": "session", "name": "Session 2", "fields": {"date": "2025-04-02", "order": "2"},
             "body": "\n# Session 2\n\nPlay through [[Departure]] and record the party's choices.\n"},
        ],
        "files": {"narrative.md": SESSIONS_NARRATIVE,
                  "sessions.md": "# Session notes\n\nSee [[narrative]] for session order.\n\n- [[Session 1]]\n- [[Session 2]]\n"},
    },
}
