from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .engine import AnankeEngine

READ_ONLY_ACTIONS = {"infer", "chat", "stats", "referential_view"}


def _prompt_from_payload(payload: dict) -> str:
    if isinstance(payload.get("prompt"), str):
        return str(payload["prompt"])
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return ""
    # La ligne active est le dernier input utilisateur. Les anciennes réponses,
    # notamment les abstentions d'ANANKÉ, ne doivent jamais contaminer le calcul
    # relationnel du nouvel input.
    for item in reversed(messages):
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "") != "user":
            continue
        content = str(item.get("content", ""))
        if content:
            return content
    return ""


def execute(state_path: Path, request: dict) -> dict:
    action = str(request.get("action") or "infer")
    read_only = action in READ_ONLY_ACTIONS and state_path.exists()
    if action in READ_ONLY_ACTIONS and not state_path.exists():
        return {"error": "referential_not_initialized", "detail": "Entraînez d'abord ANANKÉ avec un corpus."}
    engine = AnankeEngine(state_path, read_only=read_only)
    try:
        if action in ("infer", "chat"):
            return engine.infer(
                _prompt_from_payload(request),
                str(request.get("objective") or "general"),
                min(max(1, int(request.get("max_characters") or 512)), 4096),
                bool(request.get("include_trace", False)),
            )
        if action == "stats":
            return engine.stats()
        if action == "referential_view":
            return engine.referential_view(
                str(request.get("query") or ""),
                int(request.get("object_limit") or 80),
                int(request.get("dimension_limit") or 80),
            )
        if action == "learning_analyze":
            return engine.analyze_file(
                path=str(request["path"]), filename=str(request.get("filename") or Path(str(request["path"])).name),
                objective=str(request.get("objective") or "general"), user_id=int(request["user_id"]),
            )
        if action == "learning_commit":
            return engine.commit_analysis(str(request["analysis_id"]), int(request["user_id"]))
        if action == "learning_discard":
            return engine.discard_analysis(str(request["analysis_id"]), int(request["user_id"]))
        raise ValueError(f"Action inconnue: {action}")
    finally:
        engine.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="ananke_runtime")
    parser.add_argument("--state", default=os.getenv(
        "ANANKE_STATE_PATH", str(Path(__file__).resolve().parents[1] / "state" / "ananke.sqlite3")
    ))
    args = parser.parse_args()
    try:
        raw = sys.stdin.read()
        request = json.loads(raw or "{}")
        result = execute(Path(args.state), request)
        sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    except Exception as exc:
        sys.stdout.write(json.dumps({"error": "ananke_runtime_error", "detail": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
