"""Regression checks for the feature-001 adversarial review findings."""
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from lorekeeper import fm, mcp, ops, store
from lorekeeper.store import LoreError, Project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "world")


class Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "w")
        shutil.copytree(FIXTURE, self.root)
        self.p = Project(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def run_op(self, name, **args):
        return ops.run(name, args, root=self.root)

    def test_retry_rechecks_version_so_a_concurrent_edit_survives(self):
        item = self.p.find("Mara Quell")
        path = os.path.join(self.root, item.path)
        real_replace = os.replace
        state = {"calls": 0}

        def flaky(src, dst):
            state["calls"] += 1
            if state["calls"] == 1:
                raise PermissionError("locked")
            real_replace(src, dst)

        def human_edits(_):
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("human line\n")
        with mock.patch.object(store.os, "replace", flaky), mock.patch.object(store.time, "sleep", human_edits):
            with self.assertRaises(LoreError) as cm:
                self.p.update(item, {"born": "1"}, (), None, item.version, {})
        self.assertEqual(cm.exception.code, "CONFLICT")
        with open(path, encoding="utf-8") as fh:
            self.assertTrue(fh.read().endswith("human line\n"))

    def test_create_never_clobbers(self):
        path = os.path.join(self.root, "new.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("mine\n")
        with self.assertRaises(LoreError) as cm:
            store.atomic_write(path, "theirs\n", create=True)
        self.assertEqual(cm.exception.code, "CONFLICT")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "mine\n")

    def test_single_role_link_refuses_to_replace(self):
        with self.assertRaises(LoreError) as cm:
            self.run_op("link", item="Crossing Harrow Pass", role="location", target="Saltmarsh")
        self.assertEqual(cm.exception.code, "CONFLICT")
        self.assertEqual(Project(self.root).find("Crossing Harrow Pass").fields["location"], "[[Harrow Pass]]")

    def test_unlink_a_broken_link(self):
        self.run_op("unlink", item="Saltmarsh", role="located_in", target="The Coast")
        self.assertNotIn("located_in", Project(self.root).find("Saltmarsh").fields)

    def test_list_values_with_quotes_and_brackets_round_trip(self):
        for value in (["O'Brien", "next"], ['a"b', "c"], ["x]", "[y"], ["[[A]]", "plain"]):
            self.assertEqual(fm.parse_value(fm.format_value(value)), value)

    def test_names_that_break_wikilinks_are_refused(self):
        for name in ("A#1", "A|B", "AC/DC", "[x]"):
            with self.assertRaises(LoreError):
                self.p.create("character", name)

    def test_create_body_is_body_and_fields_cannot_override_identity(self):
        item = self.p.create("character", "Body Test", body="---\nprivate: note\n---\nActual\n")
        self.assertEqual(item.body, "---\nprivate: note\n---\nActual\n")
        self.assertNotIn("private", item.fields)
        with self.assertRaises(LoreError):
            self.p.create("character", "Other", {"canonical_name": "Mara Quell"})

    def test_generated_ids_never_collide(self):
        a = self.p.create("character", "A-B")
        b = Project(self.root).create("character", "A B")
        self.assertEqual((a.id, b.id), ("CHAR-A-B", "CHAR-A-B-2"))

    def test_unchanged_empty_list_merges(self):
        item = self.p.create("character", "Tagless", {"tags": []})
        other = Project(self.root).find("Tagless")
        Project(self.root).update(other, {"status": "open"}, (), None, other.version, {})
        _, merged = self.p.update(item, {"tags": ["x"]}, (), None, item.version, {"tags": []})
        self.assertTrue(merged)

    def test_body_conflict_reports_current_body(self):
        item = self.p.find("Mara Quell")
        other = Project(self.root).find("Mara Quell")
        Project(self.root).update(other, {}, (), "changed\n", other.version, {})
        with self.assertRaises(LoreError) as cm:
            self.p.update(item, {}, (), "mine\n", item.version, {"body": item.body})
        self.assertEqual(cm.exception.data["current"]["body"], "changed\n")

    def test_bad_input_is_a_lore_error_not_a_traceback(self):
        with self.assertRaises(LoreError) as cm:
            self.run_op("set", item="Mara Quell", field={"born": "a\nb"})
        self.assertEqual(cm.exception.code, "INVALID")
        with self.assertRaises(LoreError):
            self.run_op("set", item="Mara Quell", field={"act_2": "x"})   # the saga regex cannot read digits

    def test_paths_cannot_escape_the_project(self):
        with self.assertRaises(LoreError):
            Project(self.root, {"paths": ["../"]})
        p = Project(self.root, {"types": {"character": {"label": "C", "folder": "../outside"}}})
        with self.assertRaises(LoreError):
            p.create("character", "Escapee")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "outside")))

    def test_mcp_survives_lone_surrogates_and_rejects_bad_envelopes(self):
        out = io.BytesIO()
        lines = b'{"jsonrpc":"2.0","id":"\\ud800","method":"ping"}\n{"jsonrpc":"1.0","id":2,"method":"ping"}\n'
        mcp.serve(FIXTURE, io.BytesIO(lines), out)
        responses = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(responses[0]["result"], {})
        self.assertEqual(responses[1]["error"]["code"], -32600)
        modern = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "ping",
                             "params": {"_meta": {mcp.VERSION_KEY: "2026-07-28"}}}, FIXTURE)
        self.assertEqual(modern["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
