"""Feature 010: chapter stamps, story pages and the progressive wiki."""
import json
import os
import shutil
import tempfile
import time
import unittest

from lorekeeper import ops, store, wiki
from lorekeeper.store import LoreError


def write(root, rel, text, newline="\n"):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace("\n", newline))
    return path


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8", newline="") as fh:
        return fh.read()


def page(type_, name, fields="", body=""):
    return f"---\ntype: {type_}\ncanonical_name: {name}\n{fields}---\n\n# {name}\n{body}"


# The SC-2 world. Each entry: (folder, type, name, frontmatter lines, working body, stamped facts).
# The working body is written for the present (it would leak); stamped facts are the reader's view.
WORLD = [
    ("Characters", "character", "Kresh", "first_appearance: CH002\n",
     "\nKresh, once Lord Vane, rules the river city.\n",
     "\n## Names\n- the hooded rider [ch 2-5]\n- Kresh [ch 6]\n\n## Beliefs\n"
     "- Believes the far side is unarmed. [ch 2-5]\n\n## Important events\n"
     "- Watched the Gate from the ridge. [ch 2]\n- Named himself at the bridge. [ch 6]\n"),
    ("Characters", "character", "Lord Vane", "first_appearance: CH003\n", "\nA mask Kresh wore.\n",
     "\n## Current state\n- Rules the river city. [ch 3]\n\n## Important events\n- Unmasked at the feast. [ch 9]\n"
     "\n## Allies\n- Trusts no one. [ch 4]\n"),
    ("Characters", "character", "Darius", "first_appearance: 1\nspouse: \"[[Mira]] [ch 8]\"\n",
     "\nDarius lost his hand and married Mira.\n",
     "\n## Beliefs\n- Believes the far side is unarmed. [ch 2-5]\n\n## Important events\n"
     "- Lost his left hand at the Gate. [ch 4]\n- Fought [[Kresh]] at the Gate. [ch 4]\n"
     "- Saw [[Old Grudge]] in the dark. [ch 4]\n"),
    ("Characters", "character", "Mira", "first_appearance: 8\n", "\nMira.\n", ""),
    ("Technology", "technology", "Standard alien battle tank", "first_appearance: 4\n", "\nA tank.\n",
     "\n## What it does\n- Carries a plasma lance. [ch 4]\n"),
    ("Items", "item", "Old Grudge", "first_appearance: 7\nkind: \"[[Standard alien battle tank]]\"\n",
     "\nA named tank.\n", "\n## Held by\n- Held by [[Darius]]. [ch 7]\n"),
    ("Locations", "location", "The Gate", "first_appearance: 1\n", "\nThe Gate.\n", ""),
    ("Events", "event", "Battle at the Gate",
     "first_appearance: 4\ndate: 2030-01-02\nlocation: \"[[The Gate]]\"\nparticipants: [\"[[Darius]]\"]\n"
     "learns: [\"[[The Gate]]\", \"[[Old Grudge]]\"]\n", "\nThe battle.\n", ""),
    ("Chapters", "chapter", "Chapter 1", "order: 1\n", "\nOpening.\n", ""),
    ("Chapters", "chapter", "Chapter 2", "order: 2\n", "\nThe rider.\n", ""),
]
REVEAL = 'revealed_as: "[[Kresh]] [ch 9]"\n'


def build(layout):
    """layout 'pages': stamps in the pages. 'story': stamps in a story-wiki folder beside the project."""
    base = tempfile.mkdtemp(prefix="lk-wiki-")
    root = os.path.join(base, "world")
    config = {"lorekeeper": 1, "name": "Fixture"}
    if layout == "story":
        config["story_wiki"] = "../story"
    write(root, "lore.json", json.dumps(config))
    for folder, type_, name, fields, body, facts in WORLD:
        reveal = REVEAL if name == "Lord Vane" else ""
        if layout == "pages":   # the page is the reader's view: no present-day text
            write(root, f"{folder}/{name}.md", page(type_, name, fields + reveal, facts))
        else:
            write(root, f"{folder}/{name}.md", page(type_, name, fields, body))
            if facts or reveal:
                appear = next(line for line in fields.splitlines() if line.startswith("first_appearance"))
                write(base, f"story/{folder}/{name} (story).md",
                      f"---\ntype: {type_}\npage: \"[[{name}]]\"\n{appear}\n{reveal}---\n{facts}")
    return base, root


def run(root, op_name, **args):
    return ops.run(op_name, args, root=root)


def names(index):
    return sorted(e["name"] for g in index["groups"] for e in g["entries"])


def facts(card):
    return [f["text"] for s in card["sections"] for f in s["facts"]]


class StampTests(unittest.TestCase):
    def test_forms(self):
        cases = {"Lost a hand. [ch 7]": (7, None), "x [CH 7]": (7, None), "x [ch7]": (7, None),
                 "x [ ch 2 - 5 ]": (2, 5), "x [ch 2–5]": (2, 5), "x [Ch 0]  ": (0, None), "x [ch 12-12]": (12, 12)}
        for text, (start, end) in cases.items():
            with self.subTest(text=text):
                clean, a, b = wiki.read_stamp(text)
                self.assertEqual((a, b), (start, end))
                self.assertFalse(clean.endswith("]"))
        self.assertEqual(wiki.read_stamp("No stamp here."), ("No stamp here.", None, None))
        self.assertEqual(wiki.read_stamp("Mid [ch 3] text")[1:], (None, None))

    def test_problems(self):
        self.assertEqual([x[0] for x in wiki.stamp_problems("Bad [ch x]")], ["STAMP_UNREADABLE"])
        self.assertEqual([x[0] for x in wiki.stamp_problems("Odd [ch 5-2]")], ["STAMP_RANGE"])
        self.assertEqual([x[0] for x in wiki.stamp_problems("Mid [ch 3] then more")], ["STAMP_UNREADABLE"])
        self.assertEqual(wiki.stamp_problems("Fine [ch 3]"), [])
        self.assertEqual(wiki.stamp_problems("**CH003** — a saga marker, [check] and [chess]"), [])

    def test_chapter_values(self):
        for value, n in (("CH003", 3), ("ch 3", 3), ("3", 3), (" 12 ", 12), ("0", 0)):
            self.assertEqual(wiki.chapter(value), n)
        for value in ("", None, "soon", "CH", [], "3a"):
            self.assertIsNone(wiki.chapter(value))


class SectionTests(unittest.TestCase):
    BODY = ("\n# Title\n\nLead paragraph,\ncontinued. [ch 2]\n\n## Beliefs\n- One\n  more of one\n"
            "  - nested [ch 1]\n- Two\n* Three [ch 3-4]\n\n<!-- a comment [ch x] -->\n\nA paragraph.\n\n"
            "```\n## not a heading\n```\n\n### Deeper\n1. Numbered [ch 5]\n")

    def test_sections_and_facts(self):
        out = wiki.sections(self.BODY, inherit=9)
        self.assertEqual([s["heading"] for s in out], ["", "Beliefs", "Deeper"])
        lead, beliefs, deeper = out
        self.assertEqual([(f["text"], f["from"], f["to"]) for f in lead["facts"]],
                         [("Lead paragraph,\ncontinued.", 2, None)])
        self.assertEqual([(f["text"], f["from"], f["to"]) for f in beliefs["facts"]], [
            ("One\nmore of one\n- nested", 1, None), ("Two", 9, None), ("Three", 3, 4), ("A paragraph.", 9, None),
            ("```\n## not a heading\n```", 9, None)])
        self.assertEqual([(f["text"], f["from"]) for f in deeper["facts"]], [("Numbered", 5)])
        lines = self.BODY.split("\n")
        one = beliefs["facts"][0]
        self.assertEqual(lines[one["first"]:one["last"] + 1], ["- One", "  more of one", "  - nested [ch 1]"])

    def test_no_appearance_means_always(self):
        self.assertIsNone(wiki.sections("- A fact\n", inherit=None)[0]["facts"][0]["from"])


class WikiWorldTests(unittest.TestCase):
    """SC-2, run on both layouts."""
    layout = "pages"

    def setUp(self):
        self.base, self.root = build(self.layout)
        self.addCleanup(shutil.rmtree, self.base, True)

    def test_index_names_by_chapter(self):
        at5 = run(self.root, "wiki", as_of=5)
        self.assertIn("the hooded rider", names(at5))
        self.assertIn("Lord Vane", names(at5))
        self.assertNotIn("Kresh", names(at5))
        self.assertNotIn("Mira", names(at5))
        at6 = names(run(self.root, "wiki", as_of=6))
        self.assertIn("Kresh", at6)
        self.assertIn("Lord Vane", at6)
        for index in (run(self.root, "wiki", as_of=9), run(self.root, "wiki")):
            self.assertNotIn("Lord Vane", names(index))
            kresh = [e for g in index["groups"] for e in g["entries"] if e["name"] == "Kresh"][0]
            self.assertEqual(kresh["also"], ["Lord Vane"])
        self.assertEqual(run(self.root, "wiki")["mode"], "complete")

    def test_index_shape(self):
        index = run(self.root, "wiki", as_of=4)
        self.assertEqual([g["label"] for g in index["groups"]], ["Characters", "Events", "Locations", "Technology"])
        self.assertNotIn("Chapter 1", names(index))           # narrative items label chapters, never entries
        self.assertEqual(index["chapters"][:2], [{"n": 1, "name": "Chapter 1"}, {"n": 2, "name": "Chapter 2"}])
        self.assertEqual([c["n"] for c in index["chapters"]], list(range(1, 10)))
        darius = [e for g in index["groups"] for e in g["entries"] if e["name"] == "Darius"][0]
        self.assertEqual((darius["type"], darius["appears"], darius["page"]), ("character", 1, "Characters/Darius.md"))

    def test_progressive_card(self):
        card = run(self.root, "wiki", item="Kresh", as_of=5)
        self.assertEqual(card["name"], "the hooded rider")
        self.assertTrue(all(f["from"] is None or f["from"] < 6 for s in card["sections"] for f in s["facts"]))
        self.assertIn("Watched the Gate from the ridge.", facts(card))
        self.assertNotIn("fields", card)
        self.assertNotIn("body", card)
        self.assertEqual(run(self.root, "wiki", item="the hooded rider", as_of=3)["name"], "the hooded rider")
        with self.assertRaises(LoreError) as caught:
            run(self.root, "wiki", item="Kresh", as_of=1)   # not met yet: the same answer as no such page
        self.assertEqual(caught.exception.code, "NOT_FOUND")
        with self.assertRaises(LoreError):
            run(self.root, "wiki", item="Mira", as_of=7)

    def test_beliefs_and_ranges(self):
        at3, at6 = (facts(run(self.root, "wiki", item="Darius", as_of=n)) for n in (3, 6))
        self.assertIn("Believes the far side is unarmed.", at3)
        self.assertNotIn("Lost his left hand at the Gate.", at3)
        self.assertNotIn("Believes the far side is unarmed.", at6)
        self.assertIn("Lost his left hand at the Gate.", at6)
        full = run(self.root, "wiki", item="Darius")
        belief = [f for s in full["sections"] for f in s["facts"] if f["text"].startswith("Believes")][0]
        self.assertEqual((belief["from"], belief["to"]), (2, 5))
        self.assertIn("fields", full)

    def test_reveal_folds_identities(self):
        at8 = run(self.root, "wiki", item="Kresh", as_of=8)
        self.assertNotIn("Unmasked at the feast.", facts(at8))
        at9 = run(self.root, "wiki", item="Kresh", as_of=9)
        self.assertEqual(at9["also"], ["Lord Vane"])
        merged = {f["text"]: f.get("as") for s in at9["sections"] for f in s["facts"]}
        self.assertEqual(merged["Rules the river city."], "Lord Vane")
        self.assertIsNone(merged["Named himself at the bridge."])
        events = [s for s in at9["sections"] if s["heading"] == "Important events"][0]
        self.assertIn("Unmasked at the feast.", [f["text"] for f in events["facts"]])
        self.assertEqual(at9["sections"][-1]["heading"], "Allies")       # unmatched headings come after
        vane = run(self.root, "wiki", item="Lord Vane", as_of=9)
        self.assertEqual((vane["name"], vane["opened"]), ("Kresh", "Lord Vane"))
        self.assertEqual(run(self.root, "wiki", item="Lord Vane", as_of=8)["name"], "Lord Vane")
        full = run(self.root, "wiki", item="Lord Vane")
        self.assertEqual(full["name"], "Kresh")
        self.assertEqual([n["name"] for n in full["names"]], ["the hooded rider", "Kresh"])
        self.assertEqual((full["names"][0]["from"], full["names"][0]["to"]), (2, 5))

    def test_hidden_links_become_text(self):
        card = run(self.root, "wiki", item="Darius", as_of=4)
        self.assertIn("Fought [[Kresh|the hooded rider]] at the Gate.", facts(card))
        self.assertIn("Saw Old Grudge in the dark.", facts(card))
        self.assertIn("Fought [[Kresh]] at the Gate.", facts(run(self.root, "wiki", item="Darius")))
        self.assertIn("Saw [[Old Grudge]] in the dark.", facts(run(self.root, "wiki", item="Darius", as_of=7)))

    def test_worked_out(self):
        def section(card, heading):
            return [(f["text"], f.get("worked_out")) for s in card["sections"] if s["heading"] == heading
                    for f in s["facts"]]
        at3, at4, at9 = (run(self.root, "wiki", item="Darius", as_of=n) for n in (3, 4, 9))
        self.assertEqual(section(at3, "Where"), [])
        self.assertEqual(section(at4, "Where"), [("[[The Gate]] (Battle at the Gate)", True)])
        self.assertEqual(section(at4, "Knows"), [("[[The Gate]] (Battle at the Gate)", True)])   # Old Grudge is hidden
        self.assertEqual(section(at4, "Relationships"), [])
        self.assertEqual(section(at9, "Relationships"), [("Spouse: [[Mira]]", True)])
        self.assertEqual(section(run(self.root, "wiki", item="Mira", as_of=9), "Relationships"),
                         [("Spouse of: [[Darius]]", True)])

    def test_kinds_of_things(self):
        tank = run(self.root, "wiki", item="Standard alien battle tank", as_of=4)
        self.assertEqual(facts(tank), ["Carries a plasma lance."])
        grudge = run(self.root, "wiki", item="Old Grudge", as_of=7)
        self.assertIn("Held by [[Darius]].", facts(grudge))
        self.assertIn("kind", store.DEFAULT_SCHEMA["roles"])

    def test_cli_json_equals_mcp(self):
        from lorekeeper import mcp
        for args in ({}, {"as_of": 5}, {"item": "Kresh", "as_of": 9}, {"item": "Darius"}):
            with self.subTest(args=args):
                response = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                       "params": {"name": "wiki", "arguments": args}}, self.root)
                self.assertEqual(response["result"]["structuredContent"], run(self.root, "wiki", **args))

    def test_check_is_clean(self):
        found = run(self.root, "check")["findings"]
        self.assertEqual([f for f in found if f["code"].startswith("STAMP") or f["code"] == "AMBIGUOUS_NAME"], [])


class StoryFolderTests(WikiWorldTests):
    layout = "story"

    def test_companions_are_not_items(self):
        listed = [i["name"] for i in run(self.root, "query")["items"]]
        self.assertEqual(len(listed), len(WORLD))
        self.assertNotIn("Kresh (story)", listed)
        with self.assertRaises(LoreError):
            run(self.root, "show", item="Kresh (story)")

    def test_complete_card_has_working_body(self):
        full = run(self.root, "wiki", item="Kresh")
        self.assertIn("rules the river city", full["body"])
        self.assertEqual(full["story_page"], "../story/Characters/Kresh (story).md")
        self.assertNotIn("body", run(self.root, "wiki", item="Kresh", as_of=9))

    def test_page_without_companion(self):
        card = run(self.root, "wiki", item="The Gate", as_of=2)
        self.assertEqual((card["sections"], card["story_page"], card["version"]), ([], None, None))

    def test_names_resolve_links(self):
        write(self.root, "Events/Ambush.md", page("event", "Ambush", 'participants: ["[[the hooded rider]]"]\n'))
        found = run(self.root, "check")["findings"]
        self.assertEqual([f for f in found if f["code"] == "BROKEN_LINK"], [])


class FactOpTests(unittest.TestCase):
    def setUp(self):
        self.base, self.root = build("story")
        self.addCleanup(shutil.rmtree, self.base, True)

    def test_add_to_existing_section(self):
        card = run(self.root, "wiki", item="Darius", as_of=5)
        out = run(self.root, "fact-add", item="Darius", section="beliefs", text="Trusts the Gate.",
                  version=card["version"], **{"from": 5})
        text = read(self.base, "story/Characters/Darius (story).md")
        self.assertIn("- Believes the far side is unarmed. [ch 2-5]\n- Trusts the Gate. [ch 5]\n\n## Important", text)
        self.assertEqual(out["version"], store.sha256(text.encode("utf-8")))
        self.assertFalse(out["created"])
        with self.assertRaises(LoreError) as caught:   # the version is now stale
            run(self.root, "fact-add", item="Darius", section="Beliefs", text="Again.", version=card["version"],
                **{"from": 5})
        self.assertEqual(caught.exception.code, "CONFLICT")
        self.assertEqual(caught.exception.data["version"], out["version"])

    def test_live_reload_sees_story_folder(self):
        from lorekeeper import serve
        before = serve.stamp(self.root)
        run(self.root, "fact-add", item="Darius", section="Wants", text="To go home.", **{"from": 5})
        self.assertNotEqual(serve.stamp(self.root), before)

    def test_new_section_and_range(self):
        run(self.root, "fact-add", item="Darius", section="Wants", text="To go home.", to=7, **{"from": 5})
        self.assertTrue(read(self.base, "story/Characters/Darius (story).md").endswith("\n## Wants\n\n- To go home. [ch 5-7]\n"))

    def test_creates_companion_with_starter_sections(self):
        out = run(self.root, "fact-add", item="Mira", section="Wants", text="Peace.", **{"from": 8})
        self.assertTrue(out["created"])
        text = read(self.base, "story/Characters/Mira (story).md")
        self.assertIn('page: "[[Mira]]"', text)
        self.assertLess(text.index("## Names"), text.index("## Wants\n\n- Peace. [ch 8]"))
        self.assertIn("## Important events", text)
        self.assertIn("Peace.", facts(run(self.root, "wiki", item="Mira", as_of=8)))

    def test_standalone_companion(self):
        with self.assertRaises(LoreError) as caught:
            run(self.root, "fact-add", item="The Stranger", section="Where", text="At the inn.", **{"from": 5})
        self.assertEqual(caught.exception.code, "NOT_FOUND")
        self.assertIn("--type", caught.exception.message)
        run(self.root, "fact-add", item="The Stranger", section="Where", text="At the inn.", type="character",
            **{"from": 5})
        self.assertIn("first_appearance: 5", read(self.base, "story/Characters/The Stranger (story).md"))
        self.assertIn("The Stranger", names(run(self.root, "wiki", as_of=5)))
        self.assertNotIn("The Stranger", names(run(self.root, "wiki", as_of=4)))
        card = run(self.root, "wiki", item="The Stranger", as_of=5)
        self.assertIsNone(card["page"])

    def test_refusals_name_the_fix(self):
        bad = [dict(text="Two\nlines"), dict(text="Stamped [ch 4]"), dict(text="  "), dict(to=3),
               {"from": -1}, dict(section="  ")]
        for extra in bad:
            args = {"item": "Darius", "section": "Beliefs", "text": "Fine.", "from": 5, **extra}
            with self.subTest(extra=extra), self.assertRaises(LoreError) as caught:
                ops.run("fact-add", args, root=self.root)
            self.assertEqual(caught.exception.code, "INVALID")

    def test_end_reopen_remove(self):
        out = run(self.root, "fact-end", item="Darius", section="Beliefs", fact="believes  THE far", after=3)
        self.assertEqual((out["from"], out["to"]), (2, 3))
        path = "story/Characters/Darius (story).md"
        self.assertIn("- Believes the far side is unarmed. [ch 2-3]", read(self.base, path))
        run(self.root, "fact-end", item="Darius", section="Beliefs", fact="Believes", reopen=True)
        self.assertIn("- Believes the far side is unarmed. [ch 2]\n", read(self.base, path))
        with self.assertRaises(LoreError) as caught:
            run(self.root, "fact-end", item="Darius", section="Beliefs", fact="Believes", after=1)
        self.assertEqual(caught.exception.code, "INVALID")
        with self.assertRaises(LoreError) as caught:
            run(self.root, "fact-end", item="Darius", section="Beliefs", fact="Nothing like it", after=6)
        self.assertEqual(caught.exception.code, "NOT_FOUND")
        with self.assertRaises(LoreError):
            run(self.root, "fact-end", item="Darius", section="Beliefs", fact="Believes")   # neither after nor reopen
        run(self.root, "fact-remove", item="Darius", section="Important events", fact="Saw")
        self.assertNotIn("Old Grudge", read(self.base, path))
        self.assertIn("- Fought [[Kresh]] at the Gate. [ch 4]\n", read(self.base, path))

    def test_end_unstamped_fact_takes_appearance(self):
        write(self.base, "story/Characters/Mira (story).md",
              '---\ntype: character\npage: "[[Mira]]"\n---\n\n## Wants\n- Peace.\n')
        out = run(self.root, "fact-end", item="Mira", section="Wants", fact="Peace", after=9)
        self.assertEqual((out["from"], out["to"]), (8, 9))   # Mira's page appears in chapter 8

    def test_crlf_kept(self):
        write(self.base, "story/Characters/Mira (story).md",
              '---\ntype: character\npage: "[[Mira]]"\n---\n\n## Wants\n- Peace. [ch 8]\n\n## Knows\n', "\r\n")
        run(self.root, "fact-add", item="Mira", section="Wants", text="Quiet.", **{"from": 9})
        text = read(self.base, "story/Characters/Mira (story).md")
        self.assertNotIn("\n", text.replace("\r\n", ""))
        self.assertIn("- Peace. [ch 8]\r\n- Quiet. [ch 9]\r\n\r\n## Knows", text)

    def test_pages_layout_writes_the_page(self):
        base, root = build("pages")
        self.addCleanup(shutil.rmtree, base, True)
        run(root, "fact-add", item="Darius", section="Wants", text="Home.", **{"from": 3})
        self.assertTrue(read(root, "Characters/Darius.md").endswith("\n## Wants\n\n- Home. [ch 3]\n"))
        with self.assertRaises(LoreError) as caught:
            run(root, "fact-add", item="Nobody", section="Wants", text="Home.", type="character", **{"from": 3})
        self.assertIn("lore create", caught.exception.message)

    def test_check_codes(self):
        write(self.base, "story/Characters/Mira (story).md",
              '---\ntype: character\npage: "[[Mira]]"\n---\n\n## Wants\n- Bad [ch x]\n- Odd [ch 5-2]\n')
        found = [(f["code"], f["line"], f["path"]) for f in run(self.root, "check")["findings"]
                 if f["code"].startswith("STAMP")]
        path = "../story/Characters/Mira (story).md"
        self.assertEqual(found, [("STAMP_UNREADABLE", 7, path), ("STAMP_RANGE", 8, path)])


class CliTests(unittest.TestCase):
    """A saga keeps its settings in another file and runs the engine from a vendored folder."""

    def test_config_file_and_folder_launch(self):
        import subprocess
        import sys
        base, root = build("story")
        self.addCleanup(shutil.rmtree, base, True)
        os.rename(os.path.join(root, "lore.json"), os.path.join(base, "settings.json"))
        vendor = os.path.join(base, "vendor")
        shutil.copytree(os.path.dirname(wiki.__file__), os.path.join(vendor, "lorekeeper"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTHONPATH", None)
        command = [sys.executable, os.path.join(vendor, "lorekeeper"), "--root", root,
                   "--config", os.path.join(base, "settings.json")]
        out = subprocess.run(command + ["wiki", "--json", "--as-of", "5"], cwd=base, env=env,
                             capture_output=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("the hooded rider", names(json.loads(out.stdout)))
        text = subprocess.run(command + ["wiki", "Kresh", "--as-of", "9"], cwd=base, env=env,
                              capture_output=True, encoding="utf-8")
        self.assertIn("Kresh (character), as of chapter 9", text.stdout)
        self.assertIn("- Rules the river city.  [ch 3] as Lord Vane", text.stdout)
        missing = subprocess.run(command[:-1] + [os.path.join(base, "nope.json"), "wiki"], cwd=base, env=env,
                                 capture_output=True, encoding="utf-8")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("cannot read --config", missing.stderr)


class TemplateTests(unittest.TestCase):
    def test_starter_worlds_show_the_progressive_wiki(self):   # FR-25
        for template in ("novel", "series", "campaign"):
            with self.subTest(template=template):
                base = tempfile.mkdtemp(prefix="lk-wiki-")
                self.addCleanup(shutil.rmtree, base, True)
                ops.run("init", {"template": template}, root=base)
                self.assertIn("the stranger in the grey coat", names(run(base, "wiki", as_of=1)))
                at2 = run(base, "wiki", as_of=2)
                ash = [e for g in at2["groups"] for e in g["entries"] if e["name"] == "Ash"][0]
                self.assertEqual(ash["also"], ["The Cartographer"])
                self.assertEqual(run(base, "check")["findings"], [])


class CreateTests(unittest.TestCase):
    def test_starter_sections_only_without_story_folder(self):
        base = tempfile.mkdtemp(prefix="lk-wiki-")
        self.addCleanup(shutil.rmtree, base, True)
        write(base, "a/lore.json", "{}")
        write(base, "b/lore.json", '{"story_wiki": "story"}')
        run(os.path.join(base, "a"), "create", type="character", name="Ann")
        run(os.path.join(base, "b"), "create", type="character", name="Bea")
        self.assertIn("## Names\n\n## Current state\n", read(base, "a/Characters/Ann.md"))
        self.assertEqual(read(base, "b/Characters/Bea.md").split("---\n")[-1], "\n# Bea\n")
        run(os.path.join(base, "a"), "create", type="event", name="Party")
        self.assertEqual(read(base, "a/Events/Party.md").split("---\n")[-1], "\n# Party\n")


class SpeedTests(unittest.TestCase):
    def test_large_world(self):   # SC-4: 3,000 items
        base = tempfile.mkdtemp(prefix="lk-wiki-")
        self.addCleanup(shutil.rmtree, base, True)
        write(base, "lore.json", "{}")
        for n in range(3000):
            body = f"\n## Beliefs\n- Belief {n} [ch {n % 50 + 1}-{n % 50 + 3}]\n\n## Names\n- Person {n} [ch {n % 50 + 1}]\n"
            write(base, f"Characters/P{n}.md", page("character", f"P{n}", f"first_appearance: {n % 50 + 1}\n", body))
        p = store.Project(base)
        start = time.perf_counter()
        index = ops.run("wiki", {"as_of": 25}, project=p)
        middle = time.perf_counter()
        ops.run("wiki", {"item": "P10", "as_of": 25}, project=p)
        end = time.perf_counter()
        self.assertGreater(index["count"], 1000)
        self.assertLess(middle - start, 1.0)
        self.assertLess(end - middle, 1.0)


if __name__ == "__main__":
    unittest.main()
