"""Interop acceptance tests. Proprietary templates are inspected only in memory."""
import copy
import csv
import io
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile
import unittest

from lorekeeper import dates, interop, store
from lorekeeper.timeinfo import item_dates

FIXTURE = Path(__file__).parent / "fixtures" / "world"
OURS = Path(__file__).parent / "fixtures" / "ours"
TEMPLATES = Path(r"C:\Users\Owner\lk-scratch\aeon_extract\3003")


def archive(entries, root=False, version=1):
    """Independent fixture encoder, including the v2 stored-size field."""
    payload, index = b"", b""
    for ident, name, content in entries:
        ident, name = ident.encode("utf-8"), name.encode("utf-8")
        if root:
            index += struct.pack("<QQQQI", len(payload), len(content), 0, 0, len(name)) + name
        else:
            extra = bytearray(28)
            if version == 2:
                struct.pack_into("<Q", extra, 12, len(content))
            index += struct.pack("<QQ", len(payload), len(content)) + extra
            index += struct.pack("<II", len(ident), len(name)) + ident + name
        payload += content
    marker = b"\x33" * 4 + b"\x11" * 8 + (b"\x22" * 8 if version == 1 else b"HDJDJZWQ")
    return payload + index + struct.pack("<IIQI", version, 40, len(index), len(entries)) + marker


def container(document, version=1, attachments=()):
    timeline = json.dumps(document, ensure_ascii=False).encode("utf-8") + b"\n"
    return archive([("", "attachments", archive(attachments, version=version)),
                    ("", "timeline", archive([("timeline3.json", "", timeline)], version=version))],
                   root=True, version=version)


def timeline_json(blob):
    """Independent test decoder: locate root timeline and its first leaf payload."""
    index_size, = struct.unpack_from("<Q", blob, len(blob) - 32)
    cursor = len(blob) - 40 - index_size
    count, = struct.unpack_from("<I", blob, len(blob) - 24)
    for _ in range(count):
        offset, size, _, _, length = struct.unpack_from("<QQQQI", blob, cursor)
        name = blob[cursor + 36:cursor + 36 + length]
        cursor += 36 + length
        if name == b"timeline":
            child = blob[offset:offset + size]
            child_index, = struct.unpack_from("<Q", child, len(child) - 32)
            start, length = struct.unpack_from("<QQ", child, len(child) - 40 - child_index)
            return json.loads(child[start:start + length])
    raise AssertionError("no timeline entry")


def sample(version=14):
    items = {key: {"id": key, "type": "ev", "label": name, "summary": "", "tags": {}, "propertyValues": {}}
             for key, name in (("a", "First"), ("b", "Second"), ("c", "Third"))}
    data = {"itemsById": items, "itemDatesById": {"a": {"startDate": {
        "era": 1, "year": 2004, "month": 2, "day": 29, "hour": 16, "minute": 23,
        "precision": 7, "timestamp": -999999999}}},
        "relationshipsById": {}, "dependenciesById": {}, "narrative": {"sacOrderById": {
            "narrativeRoot": {"super": None, "childOrder": {"b": 0}},
            "b": {"super": "narrativeRoot", "childOrder": {"a": 0}},
            "a": {"super": "b", "childOrder": {}}}}}
    if version == 14:
        data.update(itemOrderByType={"ev": {"c": 0, "b": 1, "a": 2}},
                    superAndChildOrderById={"c": {"super": None, "childOrder": {}},
                                            "b": {"super": None, "childOrder": {"a": 0}},
                                            "a": {"super": "b", "childOrder": {}}})
    else:
        data.update(customOrder={"c": 0, "b": 1, "a": 2}, superById={"a": "b", "b": None, "c": None})
    return {"fileVersion": version, "core": {"coreFileVersion": version, "definitions": {
        "calendar": interop._calendar(), "types": {"byId": {"ev": {"label": "Occurrence", "canHaveDate": True}}},
        "references": {"byId": {}}, "properties": {"byId": {}}}, "data": data}}


class InteropTests(unittest.TestCase):
    def setUp(self):
        # Keep all generated files, including temporary project copies, in the allowlisted tree.
        OURS.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=OURS)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.world = self.root / "world"
        shutil.copytree(FIXTURE, self.world)
        self.project = store.Project(self.world)

    def empty(self, name="empty", config=None):
        root = self.root / name
        root.mkdir()
        store.atomic_write(root / "lore.json", json.dumps(config or {"lorekeeper": 1}))
        return store.Project(root)

    def read_document(self, document, version=1, attachments=()):
        path = self.root / "synthetic.aeon"
        path.write_bytes(container(document, version, attachments))
        return interop.read_aeon(path)

    def assert_invalid(self, path, message=None):
        with self.assertRaises(store.LoreError) as caught:
            interop.read_aeon(path)
        self.assertEqual(caught.exception.code, "INVALID")
        if message:
            self.assertIn(message, caught.exception.message)

    @unittest.skipUnless(TEMPLATES.is_dir(), "Aeon bundled templates are not extracted")
    def test_sc1_all_nineteen_templates(self):
        paths = [path for path in sorted(TEMPLATES.glob("*.bin")) if path.read_bytes()[-20:-16] == b"\x33" * 4]
        self.assertEqual(len(paths), 19)
        for path in paths:
            with self.subTest(template=path.name):
                raw = timeline_json(path.read_bytes())["core"]["data"]
                result = interop.read_aeon(path)
                self.assertEqual(len(result["items"]), len(raw["itemsById"]))
                by_id = {item["id"]: item for item in result["items"]}
                for ident, record in raw["itemDatesById"].items():
                    for source, dest in (("startDate", "start"), ("endDate", "end")):
                        if record.get(source):
                            self.assertIsNotNone(dates.parse(by_id[ident][dest], self.project.calendars))

    def test_sc2_aeon_roundtrip_and_import(self):
        store.atomic_write(self.world / "narrative.md", "# Narrative\n- [[Crossing Harrow Pass]]\n- [[The flood at Saltmarsh]]\n")
        # Exercise all dependency kinds; the base fixture already has FS with a lag.
        crossing = self.project.find("Crossing Harrow Pass")
        self.project.update(crossing, {role: "[[The flood at Saltmarsh]]" for role in ("same_start", "same_end", "sf")})
        self.project = store.Project(self.world)
        path = self.root / "world.aeon"
        interop.write_aeon(self.project, path)
        doc = timeline_json(path.read_bytes())
        self.assertEqual(doc["fileVersion"], 14)
        self.assertEqual(set(doc), {"fileVersion", "core"})
        core = doc["core"]
        self.assertEqual(set(core["data"]), {"itemsById", "itemOrderByType", "itemDatesById",
            "superAndChildOrderById", "relationshipsById", "mindmaps", "narrative", "sequenceOrder", "tags",
            "calendarMarkers", "savedFiltersById", "dependenciesById", "dateConstraintsById", "attachmentsById",
            "timelineRange", "lastTodayDate"})
        self.assertEqual(core["data"]["calendarMarkers"], {"byId": {}, "sortOrder": {}})
        self.assertEqual(core["definitions"]["calendar"]["leapCycles"], [4, 100, 400])
        self.assertEqual(struct.unpack_from("<I", path.read_bytes(), len(path.read_bytes()) - 40)[0], 1)
        result = interop.read_aeon(path)
        names = {item["id"]: item["name"] for item in result["items"]}
        self.assertEqual(set(names.values()), {item.name for item in self.project.items})
        self.assertTrue(all(re.fullmatch(r"[a-zA-Z0-9]{21}", ident) for ident in names))
        for item in result["items"]:
            original = self.project.find(item["name"])
            self.assertEqual(item["summary"], original.body)
            self.assertEqual(item["tags"], original.fields.get("tags", []))
            start, end, _ = item_dates(self.project, original)
            for actual, expected in ((item["start"], start), (item["end"], end)):
                if expected is None:
                    self.assertIsNone(actual)
                else:
                    # Aeon carries the nominal year; circa text is preserved as a property.
                    nominal = dates.parse(expected.text.lstrip("~"), self.project.calendars)
                    self.assertEqual(actual, interop.GREGORIAN.format(nominal.lo, nominal.precision))
        roles = {key: spec["label"] for key, spec in result["roles"].items()}
        actual_links = {(names[r["subject"]], roles[r["role"]], names[r["object"]]) for r in result["relationships"]}
        expected_links = {(item.name, role, other.name) for item in self.project.items
                          for role, links in self.project.links(item).items() if role not in interop.DEPENDENCIES.values()
                          for _, other, _ in links if other}
        self.assertEqual(actual_links, expected_links)
        self.assertEqual({(names[d["subject"]], names[d["object"]], d["kind"]) for d in result["dependencies"]},
                         {("Crossing Harrow Pass", "The flood at Saltmarsh", kind) for kind in interop.DEPENDENCIES})
        self.assertEqual([names[key] for key in result["narrative"]], ["Crossing Harrow Pass", "The flood at Saltmarsh"])
        target = self.empty()
        counts = interop.import_into(target, result)
        self.assertEqual(counts, {"created": len(self.project.items), "skipped": 0, "warnings": []})
        loaded = store.Project(target.root)
        for item in self.project.items:
            imported = loaded.find(item.name)
            self.assertEqual(imported.type, item.type)
            self.assertEqual(imported.body, item.body)
            for actual, expected in zip(item_dates(loaded, imported)[:2], item_dates(self.project, item)[:2]):
                self.assertEqual(actual[:5] if actual else None, expected[:5] if expected else None)
        self.assertEqual(loaded.find("Ivo Brandt").fields["born"], "~1951")
        self.assertEqual([i.name for i in interop._narrative(loaded)], ["Crossing Harrow Pass", "The flood at Saltmarsh"])
        self.assertEqual(set(loaded.links(loaded.find("Crossing Harrow Pass"))) & set(interop.DEPENDENCIES.values()),
                         set(interop.DEPENDENCIES.values()))

    def test_sc3_csv_roundtrip(self):
        path = self.root / "world.csv"
        interop.write_csv(self.project, path)
        self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
        header = next(csv.reader(io.StringIO(path.read_text(encoding="utf-8").lstrip("\ufeff"))))
        self.assertEqual(header[:7], interop.CSV_COLUMNS)
        self.assertIn("participants", header)
        self.assertIn("born", header)
        target = self.empty()
        result = interop.import_into(target, interop.read_csv(path))
        self.assertEqual(result["created"], len(self.project.items))
        target = store.Project(target.root)
        for item in self.project.items:
            actual = target.find(item.name)
            self.assertEqual(actual.type, item.type)
            self.assertEqual(actual.body, item.body)
            self.assertEqual(item_dates(target, actual)[:2], item_dates(self.project, item)[:2])
            for role in self.project.links(item):
                self.assertEqual(actual.fields[role], item.fields[role])

    def test_v1_v2_v14_v27_and_date_fields_override_timestamp(self):
        for container_version in (1, 2):
            for file_version in (14, 27):
                with self.subTest(container=container_version, file=file_version):
                    result = self.read_document(sample(file_version), container_version,
                                                [("attachment", "ours.txt", b"our generated content")])
                    self.assertEqual([i["id"] for i in result["items"]], ["c", "b", "a"])
                    self.assertEqual(next(i for i in result["items"] if i["id"] == "a")["start"], "2004-02-29 16:23")
                    self.assertEqual(result["narrative"], ["b", "a"])
                    self.assertEqual(result["attachments"], ["ours.txt"])

    def test_invalid_container_and_file_versions(self):
        path = self.root / "invalid.aeon"
        for blob in (b"not an aeon file", b"x" * 100, container(sample())[:-1]):
            path.write_bytes(blob)
            self.assert_invalid(path)
        document = sample()
        document["fileVersion"] = 28
        path.write_bytes(container(document))
        self.assert_invalid(path, "fileVersion")

    def test_bounds_duplicate_entries_and_bad_json(self):
        path = self.root / "invalid.aeon"
        blob = bytearray(container(sample()))
        struct.pack_into("<Q", blob, len(blob) - 32, len(blob) * 2)
        path.write_bytes(blob)
        self.assert_invalid(path, "index")
        blob = bytearray(container(sample()))
        size, = struct.unpack_from("<Q", blob, len(blob) - 32)
        struct.pack_into("<Q", blob, len(blob) - 40 - size, len(blob) * 2)
        path.write_bytes(blob)
        self.assert_invalid(path, "outside")
        path.write_bytes(archive([("", "timeline", archive([])), ("", "timeline", archive([]))], root=True))
        self.assert_invalid(path, "duplicate")
        path.write_bytes(archive([("", "attachments", archive([])),
                                 ("", "timeline", archive([("timeline3.json", "", b"not json")]))], root=True))
        self.assert_invalid(path, "invalid Aeon")

    def test_dates_bc_ad_precision_and_timestamps(self):
        for text, stamp in (("0001-01-01", 0), ("1970-01-01", 62135596800),
                            ("1 BC", -365 * 86400), ("2000-02-29 12:34", 63087424440)):
            with self.subTest(text=text):
                when = interop.GREGORIAN.parse(text)
                encoded = interop._aeon_date(when)
                self.assertEqual(encoded["timestamp"], stamp)
                self.assertEqual(interop.GREGORIAN.parse(interop._date_text(encoded, interop._calendar())).lo, when.lo)
        for precision, text in ((2, "2004"), (3, "2004-02"), (5, "2004-02-29"),
                                (6, "2004-02-29 16:00..2004-02-29 16:59"), (7, "2004-02-29 16:23")):
            doc = sample()
            doc["core"]["data"]["itemDatesById"]["a"]["startDate"]["precision"] = precision
            result = self.read_document(doc)
            self.assertEqual(next(i for i in result["items"] if i["id"] == "a")["start"], text)

    def test_import_schema_and_into_and_repeated_import(self):
        doc = sample()
        defs, data = doc["core"]["definitions"], doc["core"]["data"]
        defs["types"]["byId"].update(person={"label": "Actor", "category": "PERSON"},
                                      place={"label": "Venue", "category": "LOCATION"},
                                      other={"label": "Plot Thread", "canHaveDate": False})
        data["itemsById"]["a"]["type"] = "person"
        data["itemsById"]["b"]["type"] = "place"
        data["itemsById"]["c"]["type"] = "other"
        defs["references"]["byId"] = {"r": {"label": "Visits", "types": {"place": True}}}
        defs["properties"]["byId"] = {"p": {"label": "Motivation", "format": "text"}}
        data["itemsById"]["a"]["propertyValues"] = {"p": "Find the map"}
        data["relationshipsById"] = {"r": {"subject": "a", "reference": "r", "object": "b"}}
        data["dependenciesById"] = {"d": {"subject": "c", "object": "a", "dependencyType": "FS"}}
        target = self.empty(config={"paths": ["Wiki"]})
        result = self.read_document(doc)
        self.assertEqual(interop.import_into(target, result, into="Imported")["created"], 3)
        reloaded = store.Project(target.root)
        self.assertEqual({i.type for i in reloaded.items}, {"character", "location", "plot_thread"})
        self.assertTrue(all(i.path.startswith("Imported/") for i in reloaded.items))
        self.assertEqual(reloaded.find("First").fields["motivation"], "Find the map")
        self.assertEqual(reloaded.links(reloaded.find("First"))["visits"][0][1].name, "Second")
        self.assertIn("visits", reloaded.config["roles"])
        self.assertIn("plot_thread", reloaded.config["types"])
        before = {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()}
        again = interop.import_into(reloaded, result)
        self.assertEqual((again["created"], again["skipped"]), (0, 3))
        self.assertEqual(len(again["warnings"]), 3)
        self.assertEqual(before, {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()})

    def test_csv_custom_properties_and_quoted_unicode(self):
        path = self.root / "custom.csv"
        store.atomic_write(path, '\ufefflabel,type,startDate,summary,tags,custom,ignored\r\n"Café, north",event,2001,"Line one\nLine two","[""red,blue"", ""雪""]",value,no\r\n')
        data = interop.read_csv(path)
        target = self.empty(config={"properties": {"custom": {"format": "text"}}})
        interop.import_into(target, data)
        item = store.Project(target.root).find("Café, north")
        self.assertEqual(item.body, "Line one\nLine two")
        self.assertEqual(item.fields["tags"], ["red,blue", "雪"])
        self.assertEqual(item.fields["custom"], "value")
        self.assertNotIn("ignored", item.fields)

    def test_csv_derived_duration_end(self):
        target = self.empty()
        target.create("event", "Journey", {"date": "2000-01-01 12:00", "duration": "2d"})
        target = store.Project(target.root)
        path = self.root / "duration.csv"
        interop.write_csv(target, path)
        record = interop.read_csv(path)["items"][0]
        self.assertEqual(record["start"], "2000-01-01 12:00")
        self.assertEqual(record["end"], "2000-01-03 12:00")

    def test_csv_malformed_rows_headers_and_encoding(self):
        path = self.root / "bad.csv"
        for content in (b"label,type,type\na,event,event\n", b"name,type\na,event\n",
                        b"label,type\na,event,extra\n", b"label,type\na\n", b"label,type\na,\n",
                        b"label,type\n\xff,event\n"):
            path.write_bytes(content)
            with self.assertRaises(store.LoreError) as caught:
                interop.read_csv(path)
            self.assertEqual(caught.exception.code, "INVALID")

    def test_invalid_date_does_not_read_timestamp(self):
        for change in ({"month": 0}, {"day": 30}, {"era": -1}, {"era": 9}):
            with self.subTest(change=change):
                doc = sample()
                doc["core"]["data"]["itemDatesById"]["a"]["startDate"].update(change)
                with self.assertRaises(store.LoreError) as caught:
                    self.read_document(doc)
                self.assertEqual(caught.exception.code, "INVALID")

    def test_import_duplicate_names_and_no_existing_subject_updates(self):
        result = self.read_document(sample())
        duplicate = copy.deepcopy(result["items"][0])
        duplicate["id"] = "duplicate"
        result["items"].append(duplicate)
        target = self.empty()
        counts = interop.import_into(target, result)
        self.assertEqual((counts["created"], counts["skipped"]), (3, 1))
        self.assertEqual(len(store.Project(target.root).items), 3)

    def test_import_refuses_outside_destination_before_writes(self):
        target = self.empty()
        before = Path(target.root, "lore.json").read_bytes()
        with self.assertRaises(store.LoreError):
            interop.import_into(target, self.read_document(sample()), into="../outside")
        self.assertEqual(Path(target.root, "lore.json").read_bytes(), before)

    def test_markdown_chronology_and_fields(self):
        path = self.root / "world.md"
        interop.write_markdown(self.project, path)
        text = path.read_text(encoding="utf-8")
        self.assertLess(text.index("| Ivo Brandt |"), text.index("| Mara Quell |"))
        self.assertLess(text.index("| The flood at Saltmarsh |"), text.index("| Crossing Harrow Pass |"))
        self.assertIn("| Date | Name | Type | Location | Participants |", text)
        self.assertIn("| Saltmarsh | Mara Quell, Ivo Brandt |", text)
        for item in self.project.items:
            self.assertIn(f"## {item.name}", text)
            for key in item.fields:
                self.assertIn(f"**{key}**:", text)
