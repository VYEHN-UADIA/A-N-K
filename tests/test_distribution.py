from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def test_no_local_http_portal(self) -> None:
        php = (ROOT / "Ananke_spin.php").read_text(encoding="utf-8")
        self.assertNotIn("127.0.0.1", php)
        self.assertNotIn("7138", php)
        self.assertNotIn("curl_init", php)
        self.assertIn("proc_open", php)

    def test_no_server_or_service_directory(self) -> None:
        self.assertFalse((ROOT / "ananke_core" / "server.py").exists())
        self.assertFalse((ROOT / "service").exists())

    def test_frontend_targets_single_spin(self) -> None:
        app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn('./AnankeAI/Ananke_spin.php', app)

    def test_standalone_python_runtime(self) -> None:
        php = (ROOT / "Ananke_spin.php").read_text(encoding="utf-8")
        runtime = ROOT / "Ananke_runtime.py"
        self.assertTrue(runtime.exists())
        self.assertTrue(runtime.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"))
        self.assertIn("Ananke_runtime.py", php)
        self.assertNotIn("-m ananke_core.runtime", php)


if __name__ == "__main__":
    unittest.main()
