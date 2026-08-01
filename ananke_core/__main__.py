from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .engine import AnankeEngine


def main() -> None:
    parser = argparse.ArgumentParser(prog="ananke_core")
    parser.add_argument("--state", default=os.getenv(
        "ANANKE_STATE_PATH", str(Path(__file__).resolve().parents[1] / "state" / "ananke.sqlite3")
    ))
    sub = parser.add_subparsers(dest="command", required=True)
    train = sub.add_parser("train")
    train.add_argument("file")
    train.add_argument("--objective", default="general")
    infer = sub.add_parser("infer")
    infer.add_argument("prompt")
    infer.add_argument("--objective", default="general")
    infer.add_argument("--max-characters", type=int, default=512)
    relation = sub.add_parser("relation")
    relation.add_argument("source")
    relation.add_argument("target")
    relation.add_argument("dimension")
    relation.add_argument("factor")
    relation.add_argument("--logic", default="general")
    sub.add_parser("stats")
    args = parser.parse_args()

    if args.command in ("infer", "stats"):
        engine = AnankeEngine(args.state, read_only=Path(args.state).exists())
    else:
        engine = AnankeEngine(args.state, read_only=False)
    try:
        if args.command == "train":
            result = engine.trainer.train_file(args.file, args.objective)
        elif args.command == "infer":
            result = engine.infer(args.prompt, args.objective, args.max_characters, include_trace=True)
        elif args.command == "relation":
            with engine.store.transaction() as connection:
                version = engine.store.next_version(connection)
                result = engine.trainer.add_relation_in_transaction(connection, {
                    "source": args.source, "target": args.target, "dimension": args.dimension,
                    "factor": args.factor, "logic": args.logic,
                }, version, args.logic)
                engine.store.journal(connection, version, "manual_relation", result)
            result = {"version": version, "relation": result}
        else:
            result = engine.stats()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        engine.close()


if __name__ == "__main__":
    main()
