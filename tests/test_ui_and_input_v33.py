from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AnankeV33Tests(unittest.TestCase):
    def runtime(self, payload: dict) -> dict:
        result = subprocess.run(
            ["python3", str(ROOT / "Ananke_runtime.py"), "--state", str(ROOT / "state" / "ananke.sqlite3")],
            input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True, check=True,
        )
        return json.loads(result.stdout)

    def test_latest_user_message_is_active_line(self):
        data = self.runtime({
            "action": "infer", "max_characters": 12,
            "messages": [
                {"role": "user", "content": "hey"},
                {"role": "assistant", "content": "⊥"},
                {"role": "user", "content": "je suis"},
            ],
        })
        self.assertTrue(data["output"].startswith(" là"), data)

    def test_initial_lowercase_alias_is_declared(self):
        data = self.runtime({"action": "infer", "prompt": "je", "max_characters": 8})
        self.assertTrue(data["output"].startswith(" suis"), data)
        self.assertEqual(data.get("normalizations", [])[0]["from"], "j")
        self.assertEqual(data.get("normalizations", [])[0]["to"], "J")

    def test_unknown_character_is_explained(self):
        data = self.runtime({"action": "infer", "prompt": "hey", "max_characters": 8})
        self.assertTrue(data["abstained"])
        self.assertEqual(data["stop_reason"], "unknown_object")
        self.assertEqual(data["unknown_object"], "h")

    def test_front_has_fixed_composer_and_delete_control(self):
        html = (ROOT.parent / "Ananke.html").read_text(encoding="utf-8")
        app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("min-height:0;height:100%;overflow:hidden", html)
        self.assertIn("flex:1 1 auto;min-height:0", html)
        self.assertIn("flex:0 0 auto;position:relative", html)
        self.assertIn("function deleteConversation", app)
        self.assertIn("conv-delete", app)


if __name__ == "__main__":
    unittest.main()
