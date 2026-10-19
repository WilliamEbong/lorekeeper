"""Feature 011: the planning wiki (source reader, citations, link lists, ideas, impact, change, no leaks)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from lorekeeper import ops, planning, store
from lorekeeper.store import LoreError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "planning")
MARK = "PLANMARK-7Q"


def copy_fixture(crlf=False):
    """A writable copy of the fixture; with crlf, every text file uses CRLF line endings."""
    base = tempfile.mkdtemp(prefix="lk-plan-")
    dest = os.path.join(base, "planning")
    shutil.copytree(FIXTURE, dest)
    if crlf:
        for dirpath, _, names in os.walk(dest):
            for name in names:
                path = os.path.join(dirpath, name)
                with open(path, "rb") as fh:
                    data = fh.read()
                with open(path, "wb") as fh:
                    fh.write(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    return base, os.path.join(dest, "world")


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def run(name, args=None, root=None):
    return ops.run(name, args or {}, root=root or os.path.join(FIXTURE, "world"))


class SourceReaderTests(unittest.TestCase):
    def setUp(self):
        self.src = planning.Source("Bible", os.path.join(FIXTURE, "docs", "bible.md"), 1, None)

    def test_outline_numbers_titles_levels_and_fences(self):
        refs = [(s["ref"], s["level"]) for s in self.src.outline()]
        self.assertIn(("1.1", 3), refs)
        self.assertIn(("2", 2), refs)
        self.assertIn(("B.2A", 3), refs)
        self.assertIn(("Canon inheritance rule", 2), refs)
        self.assertIn(("2.1", 3), refs)   # after an unbalanced bare fence line

    def test_find_by_number_section_sign_title_and_prefix(self):
        self.assertEqual(self.src.find("§2.1")["title"], "2.1 Sava")
        self.assertEqual(self.src.find("2.1")["title"], "2.1 Sava")
        self.assertEqual(self.src.find("b.2a")["title"], "§B.2A Hangars")
        self.assertEqual(self.src.find("canon inheritance rule")["ref"], "Canon inheritance rule")
        self.assertEqual(self.src.find("Canon inheritance")["ref"], "Canon inheritance rule")

    def test_section_text_runs_to_next_heading_of_same_or_higher_level(self):
        text = self.src.text(self.src.find("3"))
        self.assertIn("Mach 20", text)
        self.assertIn("two fighters", text)          # the 3.x subsections belong to 3
        self.assertNotIn("appears in the notes", text)
        self.assertNotIn("two fighters", self.src.text(self.src.find("3.1")))

    def test_missing_and_ambiguous(self):
        with self.assertRaises(LoreError) as cm:
            self.src.find("9.9")
        self.assertEqual(cm.exception.code, "NOT_FOUND")
        self.assertIn("planning-source", cm.exception.message)
        with self.assertRaises(LoreError) as cm:
            self.src.find("H")   # Humans and Hangars
        self.assertEqual(cm.exception.code, "INVALID")
        self.assertIn("1.2 Humans", cm.exception.message)
        self.assertEqual(self.src.find("Sava")["ref"], "2.1")   # a title without its number
        with self.assertRaises(LoreError) as cm:
            planning.Source("C", os.path.join(FIXTURE, "docs", "conversations.md"), 1, None).find("§")
        self.assertEqual(cm.exception.code, "INVALID")

    def test_override_register_entries(self):
        reg = planning.Source("Overrides", os.path.join(FIXTURE, "docs", "overrides.md"), 6, "overrides")
        self.assertIn("Sava keeps her title", reg.text(reg.find("HO-001")))
        self.assertNotIn("EXAMPLE", reg.text(reg.find("HO-001")))
        self.assertEqual(reg.next_id(), "HO-002")

    def test_dialogue_entry_ids(self):
        conv = planning.Source("Conversations", os.path.join(FIXTURE, "docs", "conversations.md"), 2, "dialogues")
        self.assertEqual(conv.find("A.252")["title"], "§A.252 — The Bound (Dec 2048)")


class ReviewFindingTests(unittest.TestCase):
    """Fixes from the run-5 review (each failed before its fix)."""

    def source(self, text, role=None):
        d = tempfile.mkdtemp(prefix="lk-src-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "doc.md")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return planning.Source("Doc", path, 1, role)

    def test_numbers_match_numbers_only_and_duplicates_need_a_title(self):
        src = self.source("## 1.10 Ten\nx\n## X.7 Fleet doctrine\na\n## X.7 Fleet losses\nb\n## VIII.2 Late part\nc\n")
        with self.assertRaises(LoreError) as cm:
            src.find("1.1")   # not "1.10 Ten"
        self.assertEqual(cm.exception.code, "NOT_FOUND")
        self.assertIn("1.10", cm.exception.message)   # close matches are listed
        with self.assertRaises(LoreError) as cm:
            src.find("X.7")
        self.assertIn("X.7 Fleet losses", cm.exception.message)
        self.assertEqual(src.find("§X.7 Fleet losses")["title"], "X.7 Fleet losses")
        self.assertEqual(src.find("X.7 Fleet d")["title"], "X.7 Fleet doctrine")
        self.assertEqual(src.find("VIII.2")["title"], "VIII.2 Late part")

    def test_register_skips_examples_and_numbers_within_the_main_prefix(self):
        reg = self.source("## Register\n\n### EXAMPLE ENTRY\n\n**ID:** `HO-000` *(example)*\n", "overrides")
        self.assertEqual(reg.next_id(), "HO-001")
        text = planning._register(reg, ["**ID:** `HO-001`"])
        self.assertLess(text.index("`HO-001`"), text.index("EXAMPLE"))
        mixed = self.source("**ID:** `HO-031`\n\n**ID:** `AD-050`\n\n**ID:** `HO-032`\n", "overrides")
        self.assertEqual(mixed.next_id(), "HO-033")
        # an entry written as a heading that also carries its **ID:** line is one entry, not two
        headed = self.source("## HO-104 — The pumps\n\n**ID:** `HO-104`\n\nText.\n", "overrides")
        self.assertEqual(headed.find("HO-104")["title"], "HO-104 — The pumps")
        self.assertEqual(headed.next_id(), "HO-105")

    def test_write_back_to_a_parent_section_goes_before_its_first_subsection(self):
        src = self.source("## 3. Machines\nIntro.\n\n### 3.1 Fighter\nFast.\n")
        text, _ = planning._amend(src, src.find("3"), "> **Amended:** x")
        self.assertLess(text.index("Amended"), text.index("### 3.1"))
        self.assertGreater(text.index("Amended"), text.index("Intro."))

    def test_dialogue_entries_survive_a_deeper_heading(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        path = os.path.join(base, "planning", "docs", "conversations.md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace("**Sava:** asks about the data.\n", "#### Beats\n**Sava:** asks about the data.\n"))
        self.assertEqual([d["section"] for d in run("planning", {"item": "Sava"}, root)["links"]["dialogues"]],
                         ["A.252"])

    def test_canonical_names_win_over_aliases(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        with open(os.path.join(root, "Planning", "Characters", "Aaron (plan).md"), "w", encoding="utf-8",
                  newline="") as fh:
            fh.write("---\ntype: character\ncanonical_name: Aaron\naliases: [Sava]\n---\n\n# Aaron\n")
        self.assertEqual(run("planning", {"item": "Sava"}, root)["name"], "Sava")

    def test_written_default_ignores_wiki_first_appearance(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        path = os.path.join(root, "Characters", "Edran.md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace("first_appearance: 2", "first_appearance: 9"))
        self.assertEqual(run("planning-impact", {"terms": ["Sava"]}, root)["written"], 2)

    def test_change_refuses_a_missing_cited_section_before_writing(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        docs = os.path.join(base, "planning", "docs")
        before = read_bytes(os.path.join(docs, "overrides.md"))
        card = run("planning", {"item": "Will Marsh"}, root)   # cites World Bible §9.9, which does not exist
        with self.assertRaises(LoreError) as cm:
            run("planning-change", {"item": "Will Marsh", "fact": card["sections"][0]["facts"][0]["id"],
                                    "text": "x", "decision": "y"}, root)
        self.assertEqual(cm.exception.code, "INVALID")
        self.assertIn("planning-source", cm.exception.message)
        self.assertEqual(read_bytes(os.path.join(docs, "overrides.md")), before)

    def test_change_on_an_entry_with_only_a_short_name(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        out = run("planning-change", {"item": "Bo", "section": "Identity", "text": "Bo hums.", "decision": "He hums."},
                  root)
        self.assertEqual(out["override"], "HO-002")

    def test_settings_refuse_overlapping_folders_and_bad_prose_patterns(self):
        for cfg, word in (({"folder": ".", "sources": []}, "folder"),
                          ({"folder": "..", "sources": []}, "folder"),
                          ({"folder": "Story", "sources": []}, "story"),
                          ({"folder": "P", "sources": [{"name": "C", "file": "CH{n}-{title}.md", "prose": True}]},
                           "{n}")):
            with self.subTest(cfg=cfg):
                p = store.Project(tempfile.mkdtemp(), {"story_wiki": "Story", "planning_wiki": cfg})
                with self.assertRaises(LoreError) as cm:
                    planning.plan(p)
                self.assertIn(word, cm.exception.message)

    def test_a_readme_in_the_planning_folder_is_not_a_problem(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        with open(os.path.join(root, "Planning", "README.md"), "w", encoding="utf-8") as fh:
            fh.write("What this folder is.\n")
        self.assertNotIn("README.md", json.dumps(run("planning", {}, root)["problems"]))


class CitationTests(unittest.TestCase):
    def test_read_citation(self):
        self.assertEqual(planning.read_citation("Born in 1782. [src: World Bible 2.1; Conversations §A.252]"),
                         ("Born in 1782.", ["World Bible 2.1", "Conversations §A.252"]))
        self.assertEqual(planning.read_citation("No source here."), ("No source here.", []))
        self.assertEqual(planning.read_citation("Odd [SRC:Bible §1 ]"), ("Odd", ["Bible §1"]))

    def test_resolve_longest_source_name_first(self):
        p = store.Project(os.path.join(FIXTURE, "world"))
        plan = planning.plan(p)
        ref = plan.resolve("World Bible §2.1")
        self.assertEqual((ref["source"], ref["section"], ref["title"], ref["rank"], ref["found"]),
                         ("World Bible", "2.1", "2.1 Sava", 1, True))
        self.assertFalse(plan.resolve("World Bible §9.9")["found"])
        self.assertIsNone(plan.resolve("Lore Book §1")["source"])


class SettingsTests(unittest.TestCase):
    def test_errors_name_the_key(self):
        bad = [({"folder": "P", "sources": [{"name": "X", "file": "x.md", "colour": True}]}, "colour"),
               ({"folder": "P", "sources": [{"name": "X", "file": "x.md", "ideas": True, "chapters": True}]}, "one"),
               ({"folder": "P", "sources": [{"name": "A", "file": "a", "overrides": True},
                                            {"name": "B", "file": "b", "overrides": True}]}, "overrides"),
               ({"sources": []}, "folder"),
               ({"folder": "P", "sources": [{"file": "x.md"}]}, "name")]
        for config, word in bad:
            with self.subTest(word=word):
                p = store.Project(tempfile.mkdtemp(), {"planning_wiki": config})
                with self.assertRaises(LoreError) as cm:
                    planning.plan(p)
                self.assertIn("planning_wiki", cm.exception.message)
                self.assertIn(word, cm.exception.message)

    def test_world_without_planning(self):
        p = store.Project(tempfile.mkdtemp(), {})
        with self.assertRaises(LoreError) as cm:
            ops.run("planning", {}, project=p)
        self.assertIn("planning_wiki", cm.exception.message)


class ViewTests(unittest.TestCase):
    def test_index_groups_and_problems(self):
        index = run("planning")
        names = {g["label"]: [e["name"] for e in g["entries"]] for g in index["groups"]}
        self.assertEqual(names["Characters"], ["Bo", "Edran", "Mirela", "Sava", "Will Marsh"])
        self.assertEqual(names["Organizations"], ["Vampires"])
        self.assertEqual(names["Technology"], ["Nightjar fighter"])
        sava = next(e for g in index["groups"] for e in g["entries"] if e["name"] == "Sava")
        self.assertEqual((sava["page"], sava["facts"], sava["ideas"]), ("Sava", 3, 1))
        codes = sorted((f["code"], os.path.basename(f["path"])) for f in index["problems"])
        self.assertEqual(codes, [("PLAN_IDEA_AS_FACT", "Nightjar fighter (plan).md"),
                                 ("PLAN_PAGE_UNREADABLE", "Notes.md"),
                                 ("PLAN_SECTION_MISSING", "Will Marsh (plan).md"),
                                 ("PLAN_SOURCE_UNKNOWN", "Bo (plan).md"),
                                 ("PLAN_UNCITED", "Edran (plan).md")])
        for f in index["problems"]:
            self.assertEqual(f["severity"], "WARN")
            self.assertGreater(f["line"], 0)

    def test_card_sections_sources_and_ideas_kept_apart(self):
        card = run("planning", {"item": "Sava"})
        self.assertEqual((card["name"], card["type"], card["page"]), ("Sava", "character", "Sava"))
        facts = card["sections"][0]["facts"]
        self.assertEqual(card["sections"][0]["heading"], "Identity")
        self.assertEqual(facts[1]["text"], "Born in 1782.")
        self.assertEqual([(s["source"], s["section"], s["found"]) for s in facts[1]["sources"]],
                         [("World Bible", "2.1", True), ("Conversations", "A.252", True)])
        self.assertTrue(all(s["heading"].lower() != "ideas" for s in card["sections"]))
        self.assertEqual([f["text"] for f in card["ideas"]["facts"]], ["Sava could betray the Bound."])
        self.assertTrue(all(f["idea"] for f in card["ideas"]["facts"]))
        self.assertEqual([s["section"] for s in card["ideas"]["sections"]], ["4.12"])
        self.assertTrue(card["key"].startswith("plan:"))
        self.assertEqual(run("planning", {"item": card["key"]})["name"], "Sava")
        self.assertEqual(run("planning", {"item": "the captain"})["name"], "Sava")   # the item's alias

    def test_link_lists(self):
        sava = run("planning", {"item": "Sava"})["links"]
        self.assertEqual([c["n"] for c in sava["appears_in"]], [1, 3])
        self.assertEqual(sava["appears_in"][0]["title"], "Night Arrives")
        self.assertEqual([d["section"] for d in sava["dialogues"]], ["A.252"])
        edran = run("planning", {"item": "Edran"})["links"]
        self.assertEqual([c["n"] for c in edran["appears_in"]], [2, 3, 4])   # not 1: Meanwhile lines skipped
        self.assertEqual([d["section"] for d in edran["dialogues"]], ["A.252"])   # setting text is not a speaker
        will = run("planning", {"item": "Will Marsh"})["links"]
        self.assertEqual([c["n"] for c in will["appears_in"]], [1])
        self.assertEqual([d["section"] for d in will["dialogues"]], ["A.253"])
        bo = run("planning", {"item": "Bo"})["links"]
        self.assertEqual((bo["appears_in"], bo["dialogues"]), ([], []))   # two letters never match
        vampires = run("planning", {"item": "Vampires"})["links"]
        self.assertEqual([m["name"] for m in vampires["members"]], ["Mirela", "Sava"])
        jet = run("planning", {"item": "Nightjar fighter"})["links"]
        self.assertEqual([c["n"] for c in jet["appears_in"]], [1, 3])
        self.assertEqual(jet["dialogues"], [])

    def test_exclusion_list_and_case(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        path = os.path.join(root, "Planning", "Characters", "Will Marsh (plan).md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace("canonical_name: Will Marsh", "canonical_name: Will"))
        will = run("planning", {"item": "Will"}, root)["links"]
        self.assertEqual((will["appears_in"], will["dialogues"]), ([], []))   # excluded; "the will" lower case

    def test_source_op(self):
        outline = run("planning-source", {"source": "World Bible"})
        self.assertIn("2.1", [s["ref"] for s in outline["sections"]])
        one = run("planning-source", {"source": "world bible", "section": "§3.1"})
        self.assertIn("Mach 20", one["text"])
        self.assertEqual(one["title"], "3.1 Nightjar fighter")
        with self.assertRaises(LoreError) as cm:
            run("planning-source", {"source": "Lore Book"})
        self.assertIn("World Bible", cm.exception.message)   # lists the sources


class LeakTests(unittest.TestCase):
    """Planning facts never reach the story wiki, item views, export or check (FR-15)."""

    def test_marker_never_leaks(self):
        root = os.path.join(FIXTURE, "world")
        outputs = [run("wiki"), run("wiki", {"as_of": 3}), run("wiki", {"item": "Sava"}),
                   run("wiki", {"item": "Sava", "as_of": 2}), run("query"), run("query", {"text": "PLANMARK"}),
                   run("show", {"item": "Sava"}), run("graph"), run("check")]
        for out in outputs:
            self.assertNotIn(MARK, json.dumps(out))
        self.assertNotIn("Planning/", json.dumps(run("query")))
        with self.assertRaises(LoreError):
            run("show", {"item": "Mirela"})   # a planning-only name is not an item
        out = os.path.join(tempfile.mkdtemp(), "x.md")
        run("export", {"format": "md", "out": out})
        with open(out, encoding="utf-8") as fh:
            self.assertNotIn(MARK, fh.read())
        self.assertIn(MARK, json.dumps(run("planning", {"item": "Sava"})))
        self.assertEqual(root, os.path.join(FIXTURE, "world"))


class FactTests(unittest.TestCase):
    def setUp(self):
        self.base, self.root = copy_fixture()
        self.addCleanup(shutil.rmtree, self.base, True)

    def page(self, name, folder="Characters"):
        with open(os.path.join(self.root, "Planning", folder, f"{name} (plan).md"), "rb") as fh:
            return fh.read().decode("utf-8")

    def test_add_replace_remove(self):
        added = run("planning-fact", {"item": "Edran", "section": "Identity", "text": "Edran is old.",
                                      "source": ["World Bible §2.2"]}, self.root)
        self.assertIn("- Edran is old. [src: World Bible §2.2]\n", self.page("Edran"))
        card = run("planning", {"item": "Edran"}, self.root)
        fid = next(f["id"] for f in card["sections"][0]["facts"] if f["text"] == "Edran is old.")
        self.assertEqual(added["id"], fid)
        run("planning-fact", {"item": "Edran", "fact": fid, "text": "Edran is very old.",
                              "source": ["World Bible §2.2"], "version": card["version"]}, self.root)
        self.assertIn("- Edran is very old. [src: World Bible §2.2]\n", self.page("Edran"))
        self.assertNotIn("Edran is old.", self.page("Edran"))
        card = run("planning", {"item": "Edran"}, self.root)
        fid = next(f["id"] for f in card["sections"][0]["facts"] if f["text"] == "Edran is very old.")
        run("planning-fact", {"item": "Edran", "fact": fid, "remove": True}, self.root)
        self.assertNotIn("very old", self.page("Edran"))

    def test_create_page_and_refusals(self):
        made = run("planning-fact", {"item": "Ilyra", "type": "character", "section": "Identity",
                                     "text": "Ilyra is a pilot.", "source": ["World Bible §1.1"]}, self.root)
        self.assertTrue(made["created"])
        self.assertIn("type: character", self.page("Ilyra"))
        self.assertEqual(run("planning", {"item": "Ilyra"}, self.root)["sections"][0]["facts"][0]["text"],
                         "Ilyra is a pilot.")
        cases = [({"item": "Nobody", "section": "A", "text": "x", "source": ["World Bible §1"]}, "NOT_FOUND", "type"),
                 ({"item": "Edran", "section": "A", "text": "a\nb", "source": ["World Bible §1"]}, "INVALID", "one line"),
                 ({"item": "Edran", "section": "A", "text": "x [src: World Bible §1]"}, "INVALID", "source"),
                 ({"item": "Edran", "section": "A", "text": "x", "source": ["Lore Book §1"]}, "INVALID", "World Bible"),
                 ({"item": "Edran", "section": "A", "text": "x", "source": ["World Bible §1"],
                   "version": "0" * 64}, "CONFLICT", "changed"),
                 ({"item": "Edran", "fact": "fact:000000000000", "remove": True}, "NOT_FOUND", "card")]
        for args, code, word in cases:
            with self.subTest(args=args):
                with self.assertRaises(LoreError) as cm:
                    run("planning-fact", args, self.root)
                self.assertEqual(cm.exception.code, code)
                self.assertIn(word, cm.exception.message)


class ImpactTests(unittest.TestCase):
    def test_groups_and_statuses(self):
        out = run("planning-impact", {"item": "Nightjar fighter", "written": 1})
        self.assertEqual(out["written"], 1)
        self.assertEqual([h["entry"] for h in out["planning"]], ["Nightjar fighter"])   # decided facts only
        bible = next(g for g in out["sources"] if g["source"] == "World Bible")
        self.assertEqual([h["section"] for h in bible["hits"]], ["1.1", "3.1", "4"])   # one hit per section
        self.assertEqual(len(bible["hits"][1]["lines"]), 2)   # the heading and the speed line
        self.assertNotIn("Plot ideas", [g["source"] for g in out["sources"]])   # ideas never searched
        chapters = {(h["n"], h["kind"]): h["status"] for h in out["chapters"]}
        self.assertEqual(chapters, {(1, "card"): "frozen", (3, "card"): "planned",
                                    (1, "prose"): "frozen", (2, "prose"): "current"})
        story = [h for h in out["pages"] if h.get("from") is not None]
        self.assertEqual([(h["from"], h["status"]) for h in story], [(2, "current")])

    def test_terms_and_limit(self):
        out = run("planning-impact", {"terms": ["mach 20"], "written": 2, "limit": 1})
        bible = next(g for g in out["sources"] if g["source"] == "World Bible")
        self.assertEqual(len(bible["hits"]), 1)
        self.assertEqual(out["chapters"][0]["status"], "frozen")
        with self.assertRaises(LoreError) as cm:
            run("planning-impact", {})
        self.assertIn("item or terms", cm.exception.message)

    def test_written_defaults_to_the_story_wiki(self):
        self.assertEqual(run("planning-impact", {"terms": ["Sava"]})["written"], 2)


class ChangeTests(unittest.TestCase):
    def change(self, crlf):
        base, root = copy_fixture(crlf)
        self.addCleanup(shutil.rmtree, base, True)
        card = run("planning", {"item": "Nightjar fighter"}, root)
        fact = card["sections"][0]["facts"][0]
        out = run("planning-change", {"item": "Nightjar fighter", "fact": fact["id"],
                                      "text": "The Nightjar fighter's top speed is Mach 30.",
                                      "decision": "Make the jet faster: Mach 30.", "written": 1}, root)
        docs = os.path.join(base, "planning", "docs")
        with open(os.path.join(docs, "bible.md"), "rb") as fh:
            bible = fh.read().decode("utf-8")
        with open(os.path.join(docs, "overrides.md"), "rb") as fh:
            register = fh.read().decode("utf-8")
        with open(os.path.join(root, "Planning", "Technology", "Nightjar fighter (plan).md"), "rb") as fh:
            page = fh.read().decode("utf-8")
        return out, bible, register, page, root

    def test_change_records_writes_back_and_reviews(self):
        for crlf in (False, True):
            with self.subTest(crlf=crlf):
                out, bible, register, page, root = self.change(crlf)
                nl = "\r\n" if crlf else "\n"
                self.assertEqual(out["override"], "HO-002")
                # write-back: at the end of 3.1, before the next heading
                amended = f"Its pilots train for years.{nl}{nl}> **Amended by HO-002 ("
                self.assertIn(amended, bible)
                self.assertIn(f"Mach 30.{nl}{nl}### §B.2A Hangars", bible)
                if crlf:
                    self.assertNotIn("\n", bible.replace("\r\n", ""))
                # the register: after the last real entry, before the example
                self.assertLess(register.index("`HO-002`"), register.index("EXAMPLE ENTRY"))
                self.assertIn('> *"Make the jet faster: Mach 30."*', register)
                self.assertIn("World Bible §3.1", register)
                self.assertIn("**Status:** `ACTIVE`", register)
                # the planning fact cites the override first
                self.assertIn("- The Nightjar fighter's top speed is Mach 30. [src: Overrides HO-002; World Bible §3.1]",
                              page)
                self.assertNotIn("Mach 20. [src", page)
                card = run("planning", {"item": "Nightjar fighter"}, root)
                self.assertTrue(all(s["found"] for s in card["sections"][0]["facts"][0]["sources"]))
                statuses = {(h["n"], h["kind"]): h["status"] for h in out["impact"]["chapters"]}
                self.assertEqual(statuses[(1, "card")], "frozen")
                self.assertEqual(statuses[(3, "card")], "planned")
                self.assertIn("HO-002", out["report"])
                self.assertIn("Frozen", out["report"])

    def test_validation_before_any_write(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        docs = os.path.join(base, "planning", "docs")
        before = {n: read_bytes(os.path.join(docs, n)) for n in ("bible.md", "overrides.md")}
        card = run("planning", {"item": "Nightjar fighter"}, root)
        with self.assertRaises(LoreError) as cm:
            run("planning-change", {"item": "Nightjar fighter", "fact": card["sections"][0]["facts"][0]["id"],
                                    "text": "x", "decision": "y", "version": "0" * 64}, root)
        self.assertEqual(cm.exception.code, "CONFLICT")
        with self.assertRaises(LoreError) as cm:
            run("planning-change", {"item": "Nightjar fighter", "fact": card["sections"][0]["facts"][0]["id"],
                                    "text": "x"}, root)
        self.assertIn("decision", cm.exception.message)
        for n, data in before.items():
            with open(os.path.join(docs, n), "rb") as fh:
                self.assertEqual(fh.read(), data)

    def test_remove_and_new_fact(self):
        base, root = copy_fixture()
        self.addCleanup(shutil.rmtree, base, True)
        card = run("planning", {"item": "Edran"}, root)
        out = run("planning-change", {"item": "Edran", "fact": card["sections"][0]["facts"][0]["id"],
                                      "remove": True, "decision": "Edran is no scholar."}, root)
        self.assertEqual(out["override"], "HO-002")
        with open(os.path.join(base, "planning", "docs", "bible.md"), encoding="utf-8") as fh:
            self.assertIn("No longer true: Edran is a scholar of the Bound.", fh.read())
        out = run("planning-change", {"item": "Edran", "section": "Identity", "text": "Edran sails.",
                                      "decision": "He sails now."}, root)
        self.assertEqual(out["override"], "HO-003")
        self.assertIsNone(out["write_back"])   # a new fact cites no source section to amend
        facts = run("planning", {"item": "Edran"}, root)["sections"][0]["facts"]
        self.assertEqual(facts[-1]["text"], "Edran sails.")
        self.assertEqual(facts[-1]["sources"][0]["section"], "HO-003")


class StoreScanTests(unittest.TestCase):
    def test_planning_folder_is_not_scanned_for_items(self):
        p = store.Project(os.path.join(FIXTURE, "world"))
        self.assertFalse([i for i in p.items if i.path.startswith("Planning/")])
        self.assertFalse([f for f in p.problems if "Planning/" in f["path"]])


class CliTests(unittest.TestCase):
    def test_cli_text(self):
        env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
        out = subprocess.run([sys.executable, "-m", "lorekeeper", "--root", os.path.join(FIXTURE, "world"),
                              "planning", "Sava"], cwd=REPO, env=env, capture_output=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("World Bible §2.1", out.stdout)
        self.assertIn("Ideas (not decided)", out.stdout)
        self.assertIn("Appears in: 1 Night Arrives, 3 Sava Returns", out.stdout)


if __name__ == "__main__":
    unittest.main()
