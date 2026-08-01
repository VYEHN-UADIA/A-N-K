#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ananke_runtime.py — exécutable local autonome d'ANANKÉ.

Contrat :
- lancé directement par Ananke_spin.php avec ``python3 Ananke_runtime.py`` ;
- reçoit une requête JSON complète sur stdin ;
- écrit une seule réponse JSON sur stdout ;
- n'ouvre aucun port et ne lance aucun service HTTP ;
- conserve stderr pour les diagnostics techniques ;
- utilise le paquet local ``ananke_core`` depuis le dossier courant.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ananke_core.runtime import execute  # noqa: E402


def _write_runtime_log(message: str) -> None:
    """Journal local sans polluer stdout, qui reste réservé au JSON."""
    try:
        log_path = BASE_DIR / "state" / "ananke_python.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


def _emit(payload: dict[str, Any], exit_code: int = 0) -> "NoReturn":
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.flush()
    raise SystemExit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(prog="Ananke_runtime.py")
    parser.add_argument(
        "--state",
        default=os.getenv(
            "ANANKE_STATE_PATH",
            str(BASE_DIR / "state" / "ananke.sqlite3"),
        ),
    )
    args = parser.parse_args()

    try:
        raw = sys.stdin.read()
        request = json.loads(raw or "{}")
        if not isinstance(request, dict):
            _emit({"error": "invalid_request", "detail": "La requête JSON doit être un objet."}, 1)

        result = execute(Path(args.state).resolve(), request)
        if not isinstance(result, dict):
            _emit({"error": "invalid_runtime_result"}, 1)
        _emit(result, 0)
    except json.JSONDecodeError as exc:
        _write_runtime_log(f"JSON invalide: {exc}")
        _emit({"error": "invalid_json", "detail": str(exc)}, 1)
    except SystemExit:
        raise
    except Exception as exc:
        _write_runtime_log(traceback.format_exc())
        _emit({"error": "ananke_runtime_error", "detail": str(exc)}, 1)


if __name__ == "__main__":
    main()
