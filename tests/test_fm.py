"""Restricted frontmatter examples and byte-preservation checks."""

import unittest

from lorekeeper.fm import (
    FrontmatterError, format_value, link_target, parse, parse_value, update,
)


class ValueTests(unittest.TestCase):
    def test_scalars(self):
        cases = {
            "": "",
            "plain # retained": "plain # retained",
            "[[Darius Cole]]": "[[Darius Cole]]",
            "[[A|b]]": "[[A|b]]",
            '"Chapter 001: Looking at Her"': "Chapter 001: Looking at Her",
            "'Darius''s voice'": "Darius's voice",
            r'"a\"b\\c\n\t\q"': 'a"b\\c\\n\\t\\q',
            '""': "",
            "''": "",
            "[unfinished": "[unfinished",
            '"unfinished': '"unfinished',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_value(raw), expected)

    def test_lists(self):
        cases = {
            "[]": [],
            "[ \t ]": [],
            "[a, b]": ["a", "b"],
            '["[[A]]", "[[B]]"]': ["[[A]]", "[[B]]"],
            "[[[A]], [[B]]]": ["[[A]]", "[[B]]"],
            "[[[A, B|C]], plain]": ["[[A, B|C]]", "plain"],
            '["a,b", \'c,d\', e]': ["a,b", "c,d", "e"],
            r'["a\",b", "c\\", d]': ['a",b', 'c\\', 'd'],
            "['a'',b', c]": ["a',b", "c"],
            "[a,,b,]": ["a", "", "b", ""],
            '["", \'\']': ["", ""],
            '[""]': [""],
            "[,]": ["", ""],
            '[a"b,c"d, e]': ['a"b', 'c"d', "e"],   # quotes only open a token
            "[a'b,c'd, e]": ["a'b", "c'd", "e"],
            "[[[O'Brien, Jr.]], next]": ["[[O'Brien, Jr.]]", "next"],
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_value(raw), expected)

    def test_every_quoting_trigger(self):
        values = [c + "value" for c in '[{\"\'#&*!|>%@`,']
        values += ["[[A]]", "a: b", "a #b", " a", "a ", "\ta", "a\t"]
        for value in values:
            with self.subTest(value=value):
                expected = '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
                self.assertEqual(format_value(value), expected)
                self.assertEqual(parse_value(expected), value)
                self.assertEqual(format_value([value]), "[" + expected + "]")
        self.assertEqual(format_value("Chapter 001: Looking at Her"),
                         '"Chapter 001: Looking at Her"')

    def test_list_only_quoting_and_empty_values(self):
        for value in ["", "a,b", "a]b"]:
            with self.subTest(value=value):
                self.assertEqual(format_value(value), value)
                self.assertEqual(format_value([value]), '["' + value + '"]')
        self.assertEqual(format_value([]), "[]")
        self.assertEqual(format_value(["a", "[[B]]", ""]), '[a, "[[B]]", ""]')

    def test_bare_values_and_non_strings(self):
        for value in ["Darius Cole", "a:b", "a#b", "a{b", 'a"b', "a\\b", "true", "001"]:
            with self.subTest(value=value):
                self.assertEqual(format_value(value), value)
        self.assertEqual(format_value(12), "12")
        self.assertEqual(format_value(True), "True")
        self.assertEqual(format_value([12, False]), "[12, False]")
        self.assertEqual(format_value(' #a\\"b'), '" #a\\\\\\"b"')

    def test_link_targets(self):
        cases = {
            "[[Target]]": "Target",
            "[[Target|shown]]": "Target",
            "[[folder/sub/Target]]": "Target",
            "[[Target#Heading]]": "Target",
            "[[ folder/sub/ Target #Heading|shown ]]": "Target",
            "[[Target|shown/alias#Heading]]": "Target",
            "plain": None,
            '"[[Target]]"': None,
            " [[Target]] ": None,
            "[[A]], [[B]]": None,
            "[[A]][[B]]": None,
            "[[[A]]]": None,
            "[[Target]": None,
            "[[Target\nother]]": None,
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(link_target(value), expected)
        self.assertIsNone(link_target(["[[Target]]"]))


class FrontmatterTests(unittest.TestCase):
    def test_identity(self):
        lf = '---\n# comment\n \t\nname:  "Darius" \t\nquote: \'single\'\n---\n\nBody é.\n'
        mixed = '\ufeff---\r\n# comment\n\t\r\nname:\t"Darius" \t\nquote: \'single\'\r\n---\nBody\r\n'
        for text in [lf, lf.replace("\n", "\r\n"), mixed, "\ufeff" + lf]:
            with self.subTest(text=text):
                self.assertEqual(update(text).encode("utf-8"), text.encode("utf-8"))
                self.assertEqual(update(text, set=parse(text).fields), text)

    def test_saga(self):
        text = (
            "---\n"
            "id: CHAR-DARIUS-COLE\n"
            "type: character\n"
            "canonical_name: Darius Cole\n"
            "first_appearance: CH003\n"
            "last_updated_after_chapter: CH003\n"
            "tags: [species-living-human, faction-united-states, security-nco]\n"
            "voice: _system/knowledge/voice/darius_cole.md\n"
            "# voice: comment lines like this must be preserved\n"
            "---\n\n# Darius Cole\nBody text.\n"
        )
        expected = {
            "id": "CHAR-DARIUS-COLE", "type": "character",
            "canonical_name": "Darius Cole", "first_appearance": "CH003",
            "last_updated_after_chapter": "CH003",
            "tags": ["species-living-human", "faction-united-states", "security-nco"],
            "voice": "_system/knowledge/voice/darius_cole.md",
        }
        fm = parse(text)
        self.assertEqual(fm.fields, expected)
        self.assertEqual(list(fm.fields), list(expected))
        self.assertEqual(fm.lines, dict(zip(expected, range(2, 9))))
        self.assertEqual(fm.unsupported, [])
        self.assertEqual(fm.newline, "\n")
        self.assertEqual(fm.body, "\n# Darius Cole\nBody text.\n")
        self.assertEqual(update(text, set=expected), text)

    def test_edit_preserves_all_other_bytes(self):
        text = '\ufeff---\r\n# kept\n \t\r\na:  \'old\' \t\nb:\t"stay"\r\n---\nBody\r\n'
        self.assertEqual(update(text, set={"a": "new"}),
                         text.replace("a:  'old' \t\n", "a: new\n"))
        self.assertEqual(update(text, set={"b": "changed"}),
                         text.replace('b:\t"stay"\r\n', "b: changed\r\n"))
        self.assertEqual(update(text, set={"a": "old", "b": "stay"}), text)
        self.assertEqual(update(text, set={"a": ""}),
                         text.replace("a:  'old' \t\n", "a:\n"))

    def test_new_keys(self):
        text = "---\r\na: old\n# last comment\n---\nBody"
        expected = "---\r\na: old\n# last comment\nnew: value\r\nempty:\r\n---\nBody"
        self.assertEqual(update(text, set={"new": "value", "empty": ""}), expected)
        self.assertEqual(update("---\n---", set={"a": "b"}), "---\na: b\n---")

    def test_unset(self):
        text = "---\r\na: x\nb: y\r\n# kept\n---\nBody"
        self.assertEqual(update(text, unset=iter(["a", "absent"])),
                         "---\r\nb: y\r\n# kept\n---\nBody")
        self.assertEqual(update(text, unset=["absent"]), text)

    def test_body_boundary_and_replacement(self):
        for ending in ["\n", "\r\n", ""]:
            with self.subTest(ending=ending):
                head = "\ufeff---\r\nname: old\n---" + ending
                tail = "Body\n---\r\nMore\n" if ending else ""
                self.assertEqual(parse(head + tail).body, tail)
                self.assertEqual(update(head + tail, body=""), head)
                self.assertEqual(update(head + tail, body=tail), head + tail)
                if ending:
                    self.assertEqual(update(head + tail, body="New\r\n"), head + "New\r\n")
                    self.assertEqual(update(head + tail, set={"name": "new"}, body="New"),
                                     head.replace("name: old", "name: new") + "New")
                else:
                    result = update(head, body="New\n")
                    self.assertEqual(result, head + "\r\nNew\n")
                    self.assertEqual(parse(result).body, "New\n")

    def test_empty_blocks_and_first_closing_line(self):
        for text in ["---\n---", "---\n---\n", "\ufeff---\r\n---\r\n"]:
            with self.subTest(text=text):
                fm = parse(text)
                self.assertEqual(fm.fields, {})
                self.assertEqual(fm.lines, {})
                self.assertEqual(fm.unsupported, [])
                self.assertEqual(fm.body, "")
        self.assertEqual(parse("---\na: b\n---\na: c\n---\n").body, "a: c\n---\n")

    def test_no_frontmatter_creation(self):
        for text in ["", "Body\n", "Body\r\nTail\n", "\ufeffBody\r\n"]:
            with self.subTest(text=text):
                nl = "\r\n" if "\r\n" in text else "\n"
                bom = "\ufeff" if text.startswith("\ufeff") else ""
                head = bom + "---" + nl + "name: Darius" + nl + "empty:" + nl + "---" + nl
                result = update(text, set={"name": "Darius", "empty": ""})
                self.assertEqual(result, head + text.removeprefix("\ufeff"))
                self.assertEqual(parse(result).body, text.removeprefix("\ufeff"))
                self.assertEqual(update(text, set={"name": "Darius", "empty": ""}, body="New"),
                                 head + "New")
                self.assertEqual(update(text, unset=["missing"]), text)
        self.assertEqual(update("old", body="new"), "---\n---\nnew")
        self.assertEqual(update("old", body=""), "---\n---\n")

    def test_set_and_unset_overlap(self):
        # Removal takes precedence, including keys that were not present yet.
        for text in ["---\na: old\n---\n", ""]:
            with self.subTest(text=text):
                self.assertEqual(update(text, set={"a": "new", "b": "new"}, unset=["a", "b"]),
                                 "---\n---\n")

    def test_edits_reject_line_injection(self):
        for changes in [{"Bad": "value"}, {"bad\nkey": "value"}, {"key": "a\nb"},
                        {"key": ["a\rb"]}]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    update("---\n---\n", set=changes)

    def test_unicode_separators_are_not_file_lines(self):
        text = "---\nname: a\u2028b\vmore\nnext: c\n---\nBody\u2028tail"
        fm = parse(text)
        self.assertEqual(fm.fields, {"name": "a\u2028b\vmore", "next": "c"})
        self.assertEqual(fm.lines, {"name": 2, "next": 3})
        self.assertEqual(update(text, set={"next": "d"}), text.replace("next: c", "next: d"))

    def test_no_frontmatter_detection(self):
        for text in ["", "---", "---\r", "--- \na: b\n---\n", "\n---\n---\n",
                     "text\n---\n---\n", "\ufeff\ufeff---\n---\n"]:
            with self.subTest(text=text):
                self.assertIsNone(parse(text))
                self.assertEqual(update(text), text)

    def test_unterminated_block(self):
        for text in ["---\n", "\ufeff---\r\na: b\r\n", "---\na: b\n ---\n",
                     "---\na: b\n--- \n", "---\na: b\n---\r"]:
            with self.subTest(text=text):
                with self.assertRaises(FrontmatterError) as caught:
                    parse(text)
                self.assertIsInstance(caught.exception, ValueError)
                self.assertEqual(caught.exception.line, 1)

    def test_unsupported_and_duplicates(self):
        text = ("\ufeff---\nname: first\n name: indented\nKey: capital\n-item\n"
                "- item\nname: duplicate\n\t# comment\n \t\nvalid_2:\t value \t\n"
                "bad-key: no\n1key: no\n---\n")
        fm = parse(text)
        self.assertEqual(fm.fields, {"name": "first", "valid_2": "value"})
        self.assertEqual(fm.lines, {"name": 2, "valid_2": 10})
        self.assertEqual(fm.unsupported, [3, 4, 5, 6, 7, 11, 12])
        self.assertEqual(update(text, set={"name": "edited"}),
                         text.replace("name: first", "name: edited"))
        self.assertEqual(update(text, unset=["name"]),
                         text.replace("name: first\n", ""))


class BlockListTests(unittest.TestCase):
    """Obsidian's Properties panel writes lists as "key:" then indented "- item" lines."""
    TEXT = ('---\nid: EVENT-STORM\nparticipants:\n  - "[[Mira Vale]]"\n  # a note\n'
            "  - [[Ivo]]\n  - 'O''Neil'\n  -\nstatus: draft\naliases:\n- the storm\n---\nBody\n")
    LIST = 'participants:\n  - "[[Mira Vale]]"\n  # a note\n  - [[Ivo]]\n  - \'O\'\'Neil\'\n  -\n'

    def test_read(self):
        front = parse(self.TEXT)
        self.assertEqual(front.fields, {"id": "EVENT-STORM", "status": "draft", "aliases": ["the storm"],
                                        "participants": ["[[Mira Vale]]", "[[Ivo]]", "O'Neil", ""]})
        self.assertEqual(front.lines, {"id": 2, "participants": 3, "status": 9, "aliases": 10})
        self.assertEqual(front.unsupported, [])

    def test_round_trip_and_other_edits_are_byte_identical(self):
        for nl in ("\n", "\r\n"):
            text = self.TEXT.replace("\n", nl)
            with self.subTest(nl=nl):
                self.assertEqual(update(text).encode("utf-8"), text.encode("utf-8"))
                self.assertEqual(update(text, set=parse(text).fields), text)
                self.assertEqual(update(text, set={"status": "final", "new": "x"}),
                                 text.replace("status: draft", "status: final")
                                 .replace("---" + nl + "Body", "new: x" + nl + "---" + nl + "Body"))

    def test_edit_and_unset_replace_the_whole_list(self):
        for nl in ("\n", "\r\n"):
            text, block = self.TEXT.replace("\n", nl), self.LIST.replace("\n", nl)
            with self.subTest(nl=nl):
                edited = update(text, set={"participants": ["[[Mira Vale]]", "[[Tess]]"]})
                self.assertEqual(edited, text.replace(block, 'participants: ["[[Mira Vale]]", "[[Tess]]"]' + nl))
                self.assertEqual(parse(edited).fields["participants"], ["[[Mira Vale]]", "[[Tess]]"])
                self.assertEqual(parse(edited).unsupported, [])
                self.assertEqual(update(text, unset=["participants"]), text.replace(block, ""))
                self.assertEqual(update(text, set={"aliases": "storm"}),
                                 text.replace("aliases:" + nl + "- the storm", "aliases: storm"))

    def test_list_as_the_last_key(self):
        text = "---\r\ntype: event\r\ntags:\r\n  - a\r\n  - b\r\n---\r\n"
        self.assertEqual(parse(text).fields["tags"], ["a", "b"])
        self.assertEqual(update(text), text)
        self.assertEqual(update(text, set={"tags": ["a"]}), "---\r\ntype: event\r\ntags: [a]\r\n---\r\n")
        self.assertEqual(update(text, unset=["tags"]), "---\r\ntype: event\r\n---\r\n")
        self.assertEqual(update(text, set={"new": "x"}),
                         "---\r\ntype: event\r\ntags:\r\n  - a\r\n  - b\r\nnew: x\r\n---\r\n")

    def test_empty_key_without_items_reads_as_before(self):
        text = "---\nsummary:\nnext: x\n---\n"
        self.assertEqual(parse(text).fields, {"summary": "", "next": "x"})
        self.assertEqual(update(text, set={"summary": "y"}), "---\nsummary: y\nnext: x\n---\n")
        stray = "---\nname: x\n  - stray\nempty: ''\n  - stray\n---\n"
        self.assertEqual(parse(stray).fields, {"name": "x", "empty": ""})
        self.assertEqual(parse(stray).unsupported, [3, 5])


class HandWrittenLinkTests(unittest.TestCase):
    def test_bare_wikilinks_separated_by_commas_or_spaces(self):
        cases = {
            "[[A]], [[B]]": ["[[A]]", "[[B]]"],
            "[[A]],[[B|b]] [[C#h]]": ["[[A]]", "[[B|b]]", "[[C#h]]"],
            "[[A]] [[B]]": ["[[A]]", "[[B]]"],
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_value(raw), expected)
                self.assertEqual(parse("---\nk: " + raw + "\n---\n").fields, {"k": expected})

    def test_unbalanced_list_item_is_kept_and_refused(self):
        for raw in ("[[A]], [[B]", "[[[A]], [[B]]", "[[A]", "[a, [[b]"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_value(raw)
        text = "---\nparticipants: [[A]], [[B]\nstatus: x\n---\n"
        front = parse(text)
        self.assertEqual(front.fields, {"status": "x"})
        self.assertEqual(front.unsupported, [2])
        self.assertEqual(update(text), text)
        self.assertEqual(update(text, set={"status": "y"}), text.replace("status: x", "status: y"))
        for edit in ({"set": {"participants": ["[[C]]"]}}, {"unset": ["participants"]}):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                update(text, **edit)
        self.assertEqual(front.lines["participants"], 2)
        self.assertEqual(parse("---\nk: [[A]\nk: b\n---\n").unsupported, [2, 3])   # still the first k


class YamlSafeWritingTests(unittest.TestCase):
    def test_yaml_indicators_are_quoted(self):
        for value in ["- draft", "-", "-\tx", "? x", "?", ":", "Note:", "a:\tb", "a\t#b", "]x", "}x"]:
            with self.subTest(value=value):
                self.assertEqual(format_value(value), '"' + value + '"')
                self.assertEqual(parse_value(format_value(value)), value)
                self.assertEqual(parse_value(format_value([value])), [value])
        for value in ["a{b", "a}b", "?x", ":x"]:
            with self.subTest(value=value):
                self.assertEqual(format_value([value]), '["' + value + '"]')
        for value in ["-x", "?x", ":x", "a:b", "a-b", "x - y", "a?", "1st"]:
            with self.subTest(value=value):
                self.assertEqual(format_value(value), value)


if __name__ == "__main__":
    unittest.main()
