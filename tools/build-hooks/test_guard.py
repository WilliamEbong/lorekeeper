"""One check per guard mode. Run: python -m unittest tools/build-hooks/test_guard.py"""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guard  # noqa: E402


def transcript(path, tokens, user="carry on with 001"):
    rows = [{"type": "user", "message": {"role": "user", "content": user}},
            {"type": "assistant", "message": {"usage": {"input_tokens": tokens, "cache_creation_input_tokens": 0,
                                                        "cache_read_input_tokens": 0}}}]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(r) for r in rows) + "\n")


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(guard.build(self.root))
        for name in guard.DOCS:
            with open(guard.build(self.root, name), "w", encoding="utf-8") as fh:
                fh.write(f"# {name}\n")
        open(guard.build(self.root, "ACTIVE"), "w", encoding="utf-8").close()
        self.tr = os.path.join(self.root, "t.jsonl")
        os.environ["ECC_CONTEXT_WINDOW_TOKENS"] = "1000000"

    def tearDown(self):
        self.tmp.cleanup()

    def run_mode(self, mode, payload):
        out = io.BytesIO()
        with mock.patch.object(sys, "stdout", mock.Mock(buffer=out)):
            code = guard.main(mode, {"session_id": "s1", "transcript_path": self.tr, **payload}, self.root)
        return code, out.getvalue().decode("utf-8")

    def test_inactive_is_noop(self):
        os.remove(guard.build(self.root, "ACTIVE"))
        self.assertEqual(guard.main("pre", {"session_id": "s1"}, self.root), 0)

    def test_start_prints_handoff_and_resets_reads(self):
        _, out = self.run_mode("start", {"source": "compact"})
        self.assertIn("# HANDOFF.md", out)
        self.assertIn("Before any action", out)
        self.assertEqual(guard.load_state(self.root)["sessions"]["s1"], {"started": True, "reads": []})

    def test_pre_blocks_until_all_docs_read(self):
        transcript(self.tr, 1000)
        self.run_mode("start", {})
        with redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_mode("pre", {"tool_name": "Edit"})[0], 2)
        for name in guard.DOCS:
            self.run_mode("post", {"tool_name": "Read", "tool_input": {"file_path": guard.build(self.root, name)}})
        self.assertEqual(self.run_mode("pre", {"tool_name": "Edit"})[0], 0)

    def test_other_sessions_neither_reset_nor_block(self):
        transcript(self.tr, 1000)
        self.run_mode("start", {})
        out = io.BytesIO()
        with mock.patch.object(sys, "stdout", mock.Mock(buffer=out)):
            guard.main("post", {"session_id": "sub", "transcript_path": self.tr, "tool_name": "Bash"}, self.root)
            self.assertEqual(guard.main("pre", {"session_id": "sub", "tool_name": "Edit"}, self.root), 0)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_mode("pre", {"tool_name": "Edit"})[0], 2)   # main session still must read

    def test_post_tiers_fire_once_and_92_repeats_until_handoff_newer(self):
        self.run_mode("start", {})
        transcript(self.tr, 870_000)
        self.assertIn("86%", self.run_mode("post", {"tool_name": "Bash"})[1])
        self.assertEqual(self.run_mode("post", {"tool_name": "Bash"})[1], "")
        transcript(self.tr, 905_000)
        self.assertIn("90%", self.run_mode("post", {"tool_name": "Bash"})[1])
        transcript(self.tr, 925_000)
        self.assertIn("92%", self.run_mode("post", {"tool_name": "Bash"})[1])
        self.assertIn("92%", self.run_mode("post", {"tool_name": "Bash"})[1])  # repeats
        future = time.time() + 5
        os.utime(guard.build(self.root, "HANDOFF.md"), (future, future))
        self.assertEqual(self.run_mode("post", {"tool_name": "Bash"})[1], "")
        transcript(self.tr, 100_000)
        self.run_mode("post", {"tool_name": "Bash"})
        self.assertEqual(guard.load_state(self.root)["warned"], 0)  # re-armed below 80%

    def test_compact_logs_snapshots_and_calibrates(self):
        transcript(self.tr, 900_000, user="please continue")
        self.run_mode("compact", {"trigger": "auto"})
        with open(guard.build(self.root, "SESSION-LOG.md"), encoding="utf-8") as fh:
            self.assertIn("compaction auto", fh.read())
        with open(guard.build(self.root, "AUTO-SNAPSHOT.md"), encoding="utf-8") as fh:
            self.assertIn("please continue", fh.read())
        self.assertTrue(os.listdir(guard.build(self.root, "handoff-history")))
        self.assertEqual(guard.load_state(self.root)["window"], 900_000)


if __name__ == "__main__":
    unittest.main()
