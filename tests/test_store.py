import os
import shutil
import tempfile
import unittest
from unittest import mock

from lorekeeper import fm, store
from lorekeeper.store import LoreError, Project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "world")


class WorldCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "world")
        shutil.copytree(FIXTURE, self.root)
        self.p = Project(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, rel):
        with open(os.path.join(self.root, rel), "rb") as fh:
            return fh.read()


class Loading(WorldCase):
    def test_items_notes_and_templates(self):
        names = sorted(i.name for i in self.p.items)
        self.assertEqual(len(names), 9)
        self.assertIn("The flood at Saltmarsh", names)
        self.assertNotIn("Full Name", names)          # _TEMPLATES skipped
        self.assertNotIn("Draft", names)              # no type -> note

    def test_resolution_by_name_stem_alias_and_id(self):
        mara = self.p.find("Mara Quell")
        self.assertIs(self.p.find("the cartographer"), mara)
        self.assertIs(self.p.find("CHAR-MARA-QUELL"), mara)
        self.assertIs(self.p.find("[[Mara Quell|her]]"), mara)
        self.assertIs(self.p.find("Chapter 1"), self.p.find("Chapter 1: Water"))   # stem
        with self.assertRaises(LoreError) as cm:
            self.p.find("Nobody")
        self.assertEqual(cm.exception.code, "NOT_FOUND")

    def test_links_backlinks_and_lag_suffix(self):
        crossing = self.p.find("Crossing Harrow Pass")
        links = self.p.links(crossing)
        self.assertEqual([t for t, _, _ in links["participants"]], ["Mara Quell", "Tess Varga"])
        target, other, rest = links["after"][0]
        self.assertEqual((target, other.name, rest), ("The flood at Saltmarsh", "The flood at Saltmarsh", "+2d"))
        back = self.p.backlinks(self.p.find("Mara Quell"))
        self.assertEqual(sorted(i.name for i in back["participants"]),
                         ["Crossing Harrow Pass", "The flood at Saltmarsh"])

    def test_exact_id_precedes_name_stem_and_alias(self):
        original = store.Item.from_fields("Events/original.md", {"id": "EVENT-A", "type": "event", "name": "Original"})
        collisions = [
            store.Item.from_fields("Events/named.md", {"type": "event", "name": "EVENT-A"}),
            store.Item.from_fields("Events/EVENT-A.md", {"type": "event", "name": "Stem"}),
            store.Item.from_fields("Events/alias.md", {"type": "event", "aliases": ["EVENT-A"]}),
        ]
        for collision in collisions:
            with self.subTest(path=collision.path):
                project = Project.from_items(self.root, {}, [collision, original])
                self.assertIs(project.find("EVENT-A"), original)
                self.assertIs(project.find("event-a"), original)
                self.assertIs(project.find("path:" + collision.path), collision)

    def test_path_refs_disambiguate_duplicate_ids_names_and_missing_ids(self):
        items = [store.Item.from_fields(path, {"type": "event", "name": "Same", "id": ident})
                 for path, ident in (("Events/one.md", "DUP"), ("Events/two.md", "DUP"),
                                     ("Events/no-id.md", ""), ("architecture#CH002", "CH002"))]
        project = Project.from_items(self.root, {}, items)
        for item in items:
            self.assertIs(project.find("path:" + item.path), item)
        for ref in ("path:Events/ONE.md", "path:Events\\one.md", "path:../Events/one.md",
                    "path:Events/./one.md", "path:/Events/one.md", "path:missing.md"):
            with self.subTest(ref=ref), self.assertRaises(LoreError) as cm:
                project.find(ref)
            self.assertEqual(cm.exception.code, "NOT_FOUND")

    def test_crlf_file_loads(self):
        tess = self.p.find("Tess Varga")
        self.assertEqual(tess.fields["born"], "1990")
        self.assertIn(b"\r\n", self.read(tess.path))

    def test_structural_findings(self):
        codes = {(f["code"], f["path"]) for f in self.p.findings()}
        self.assertIn(("BROKEN_LINK", "Locations/Saltmarsh.md"), codes)
        line = [f for f in self.p.findings() if f["code"] == "BROKEN_LINK"][0]["line"]
        self.assertEqual(line, 5)

    def test_duplicate_id_from_conflict_copy(self):
        shutil.copy(os.path.join(self.root, "Characters", "Mara Quell.md"),
                    os.path.join(self.root, "Characters", "Mara Quell-DESKTOP-1.md"))
        codes = [f["code"] for f in Project(self.root).findings()]
        self.assertIn("DUPLICATE_ID", codes)
        self.assertIn("DUPLICATE_NAME", codes)

    def test_skips_temp_and_office_lock_files(self):
        for name in ("~$Mara.md", "x.md.123.tmp"):
            with open(os.path.join(self.root, "Characters", name), "w", encoding="utf-8") as fh:
                fh.write("---\ntype: character\ncanonical_name: Ghost\n---\n")
        self.assertNotIn("Ghost", [i.name for i in Project(self.root).items])

    def test_root_discovery(self):
        sub = os.path.join(self.root, "Characters")
        self.assertEqual(store.find_root(sub), os.path.abspath(self.root))
        with self.assertRaises(LoreError):
            store.find_root(self.tmp.name)


class Writing(WorldCase):
    def test_create_writes_saga_style_file(self):
        item = self.p.create("character", "Ana Ruiz: the Younger", {"born": "2001-03-14", "tags": ["minor"]})
        self.assertEqual(item.path, "Characters/Ana Ruiz- the Younger.md")
        self.assertEqual(item.id, "CHAR-ANA-RUIZ-THE-YOUNGER")
        text = self.read(item.path).decode("utf-8")
        self.assertTrue(text.startswith("---\nid: CHAR-ANA-RUIZ-THE-YOUNGER\ntype: character\n"))
        self.assertIn('canonical_name: "Ana Ruiz: the Younger"\n', text)
        self.assertIn("tags: [minor]\n", text)
        self.assertEqual(item.version, store.sha256(text.encode("utf-8")))

    def test_create_refuses_duplicates_and_unknown_types(self):
        for args in (("character", "mara"), ("character", "The Cartographer"), ("dragon", "Smaug"), ("character", "")):
            with self.assertRaises(LoreError):
                self.p.create(*args)

    def test_update_touches_only_edited_lines(self):
        before = self.read("Characters/Tess Varga.md")
        item = self.p.find("Tess Varga")
        version, merged = self.p.update(item, {"died": "2051"}, (), None, item.version, {})
        after = self.read(item.path)
        self.assertFalse(merged)
        self.assertEqual(after, before.replace(b"---\r\n\r\n", b"died: 2051\r\n---\r\n\r\n", 1))
        self.assertEqual(version, store.sha256(after))

    def test_stale_write_merges_disjoint_keys(self):
        item = self.p.find("Mara Quell")
        old = item.fields["born"]
        other = Project(self.root).find("Mara Quell")          # someone else edits another key first
        self.p.update(other, {"status": "locked"}, (), None, other.version, {})
        version, merged = self.p.update(item, {"born": "1988-04-03"}, (), None, item.version, {"born": old})
        self.assertTrue(merged)
        fields = fm.parse(self.read(item.path).decode("utf-8")).fields
        self.assertEqual((fields["born"], fields["status"]), ("1988-04-03", "locked"))

    def test_stale_write_same_key_conflicts_and_keeps_file(self):
        item = self.p.find("Mara Quell")
        other = Project(self.root).find("Mara Quell")
        self.p.update(other, {"born": "1987"}, (), None, other.version, {})
        before = self.read(item.path)
        with self.assertRaises(LoreError) as cm:
            self.p.update(item, {"born": "1989"}, (), None, item.version, {"born": "1988-04-02"})
        self.assertEqual(cm.exception.code, "CONFLICT")
        self.assertEqual(cm.exception.data["current"], {"born": "1987"})
        self.assertEqual(self.read(item.path), before)

    def test_stale_write_without_expect_conflicts(self):
        item = self.p.find("Mara Quell")
        other = Project(self.root).find("Mara Quell")
        self.p.update(other, {"status": "open"}, (), None, other.version, {})
        with self.assertRaises(LoreError):
            self.p.update(item, {"born": "1"}, (), None, item.version, None)

    def test_atomic_write_retries_once_on_onedrive_lock(self):
        path = os.path.join(self.root, "x.md")
        real = os.replace
        calls = []

        def flaky(src, dst):
            calls.append(1)
            if len(calls) == 1:
                raise PermissionError("locked")
            real(src, dst)
        with mock.patch.object(store.os, "replace", flaky), mock.patch.object(store.time, "sleep"):
            store.atomic_write(path, "hi\n")
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.read("x.md"), b"hi\n")
        self.assertEqual([n for n in os.listdir(self.root) if n.endswith(".tmp")], [])

    def test_atomic_write_gives_up_cleanly(self):
        path = os.path.join(self.root, "y.md")
        with mock.patch.object(store.os, "replace", side_effect=PermissionError("locked")), \
                mock.patch.object(store.time, "sleep"):
            with self.assertRaises(LoreError) as cm:
                store.atomic_write(path, "hi\n")
        self.assertEqual(cm.exception.code, "IO_ERROR")
        self.assertFalse(os.path.exists(path))
        self.assertEqual([n for n in os.listdir(self.root) if n.endswith(".tmp")], [])

    def test_written_files_match_saga_regex(self):
        import re
        item = self.p.create("event", "Night: the second", {"participants": ["[[Mara Quell]]"], "date": "2020-04"})
        front = re.match(r"\A---\n(.*?)\n---(?:\n|$)", self.read(item.path).decode("utf-8"), re.S)
        fields = dict(re.findall(r"^([a-z_]+):[ \t]*(.*?)[ \t]*$", front[1], re.M))
        self.assertEqual(fields["participants"], '["[[Mara Quell]]"]')
        self.assertEqual(fields["type"], "event")


class AuditFixes(WorldCase):
    def ambiguous(self, project):
        return [(f["path"], f["line"], f["detail"]) for f in project.findings() if f["code"] == "AMBIGUOUS_NAME"]

    def test_shared_alias_name_and_stem_warn_but_resolve_as_before(self):
        self.assertEqual(self.ambiguous(self.p), [])
        ahab = store.Item.from_fields("Characters/Ahab.md", {"type": "character", "name": "Ahab",
                                                             "aliases": ["the Captain"]})
        nemo = store.Item.from_fields("Characters/Nemo.md", {"type": "character", "name": "Nemo",
                                                             "aliases": ["The Captain", "ahab", "Nemo"]})
        storm = store.Item.from_fields("Events/Storm.md", {"type": "event", "name": "Storm"})
        coast = store.Item.from_fields("Places/Storm.md", {"type": "location", "name": "Storm Coast"})
        p = Project.from_items(self.root, {}, [ahab, nemo, storm, coast])
        self.assertEqual(self.ambiguous(p), [
            ("Characters/Nemo.md", 4, "[[The Captain]] could mean Ahab (Characters/Ahab.md) or Nemo "
                                      "(Characters/Nemo.md)"),
            ("Characters/Nemo.md", 4, "[[ahab]] could mean Ahab (Characters/Ahab.md) or Nemo (Characters/Nemo.md)"),
            ("Places/Storm.md", 1, "[[Storm]] could mean Storm (Events/Storm.md) or Storm Coast (Places/Storm.md)"),
        ])
        self.assertEqual([f["severity"] for f in p.findings() if f["code"] == "AMBIGUOUS_NAME"], ["WARN"] * 3)
        self.assertIs(p.find("the captain"), ahab)
        self.assertIs(p.find("Ahab"), ahab)
        self.assertIs(p.find("Storm"), storm)

    def test_create_with_another_items_name_as_alias_warns(self):
        item = self.p.create("character", "Ola", {"aliases": ["Mara Quell"]})
        self.assertEqual([(path, line) for path, line, _ in self.ambiguous(self.p)], [(item.path, 5)])

    def test_create_updates_the_index(self):
        before = len(self.p.items)
        item = self.p.create("location", "The Coast", {"aliases": ["the shore"], "located_in": "[[Harrow Pass]]"})
        self.assertEqual(len(self.p.items), before + 1)
        for ref in ("The Coast", "the shore", item.id, "path:" + item.path, "[[The Coast|it]]"):
            self.assertIs(self.p.find(ref), item, ref)
        saltmarsh = self.p.find("Saltmarsh")                 # its broken link now resolves
        self.assertIs(self.p.links(saltmarsh)["located_in"][0][1], item)
        self.assertEqual(self.p.backlinks(item)["located_in"], [saltmarsh])
        self.assertIs(self.p.links(item)["located_in"][0][1], self.p.find("Harrow Pass"))
        self.assertNotIn("BROKEN_LINK", [f["code"] for f in self.p.findings() if f["path"] == saltmarsh.path])
        with self.assertRaises(LoreError):
            self.p.create("character", "the SHORE")
        self.p.items.append(item)                            # older callers re-add and re-index
        self.p._index()
        self.assertEqual(len(self.p.items), before + 1)
        self.assertIs(self.p.find("The Coast"), item)
        self.assertNotIn("DUPLICATE_ID", [f["code"] for f in self.p.findings()])

    def test_set_refuses_blank_type_and_bad_names(self):
        item = self.p.find("Tess Varga")
        before = self.read(item.path)
        cases = [({"type": ""}, (), "INVALID"), ({"type": " "}, (), "INVALID"), ({}, ("type",), "INVALID"),
                 ({"canonical_name": "A [b]"}, (), "INVALID"), ({"canonical_name": "a|b"}, (), "INVALID"),
                 ({"canonical_name": ""}, (), "INVALID"), ({"name": "x#y"}, (), "INVALID"),
                 ({"canonical_name": ["Tess"]}, (), "INVALID"),
                 ({"canonical_name": "mara quell"}, (), "CONFLICT"), ({"name": "THE CARTOGRAPHER"}, (), "CONFLICT"),
                 ({"canonical_name": "chapter 1"}, (), "CONFLICT")]
        for set_, unset, code in cases:
            with self.subTest(set=set_, unset=unset):
                with self.assertRaises(LoreError) as cm:
                    self.p.update(item, set_, unset, None, item.version, {})
                self.assertEqual(cm.exception.code, code)
        self.assertEqual(self.read(item.path), before)
        self.p.update(item, {"canonical_name": "Tess Varga", "type": "character"}, (), None, item.version, {})
        self.assertEqual(self.read(item.path), before)
        version, _ = self.p.update(item, {"canonical_name": " Tess Orme "}, (), None, item.version, {})
        self.assertEqual(self.read(item.path), before.replace(b"Tess Varga\r\nborn", b"Tess Orme\r\nborn"))

    def test_windows_device_names_get_a_safe_file_name(self):
        cases = {"Con": "Con_", "aux": "aux_", "NUL.txt": "NUL_.txt", "Prn .x": "Prn_ .x", "Com1": "Com1_",
                 "lpt9": "lpt9_", "Console": "Console", "Con Air": "Con Air", "Falcon": "Falcon"}
        for name, stem in cases.items():
            with self.subTest(name=name):
                self.assertEqual(os.path.basename(self.p.path_for("character", name)), stem + ".md")
        item = self.p.create("character", "Con")
        self.assertEqual((item.path, item.name), ("Characters/Con_.md", "Con"))
        self.assertEqual(Project(self.root).find("Con").path, "Characters/Con_.md")

    def test_paths_may_be_a_single_folder_string(self):
        with open(os.path.join(self.root, "lore.json"), "w", encoding="utf-8") as fh:
            fh.write('{"lorekeeper": 1, "paths": "Characters"}\n')
        p = Project(self.root)
        self.assertEqual(sorted(i.name for i in p.items), ["Ivo Brandt", "Mara Quell", "Tess Varga"])
        self.assertEqual(p.create("event", "Bob").path, "Characters/Events/Bob.md")

    def test_bad_key_message_matches_the_rule(self):
        with self.assertRaises(LoreError) as cm:
            store.clean_fields({"k2": "x"})
        self.assertEqual(cm.exception.message, "bad key 'k2': use lowercase letters and _")

    @unittest.skipIf(os.name == "nt", "file modes are POSIX")
    def test_rewrite_keeps_the_file_mode(self):
        path = os.path.join(self.root, "Characters", "Tess Varga.md")
        os.chmod(path, 0o644)
        item = self.p.find("Tess Varga")
        self.p.update(item, {"died": "2051"}, (), None, item.version, {})
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
