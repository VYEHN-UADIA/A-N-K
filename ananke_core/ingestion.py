from __future__ import annotations

import csv
import html
import io
import json
import re
import shutil
import subprocess
from pathlib import Path

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl", ".html", ".htm",
    ".xml", ".log", ".sql", ".php", ".js", ".ts", ".py", ".css", ".yaml", ".yml"
}

TAG_RE = re.compile(r"<[^>]+>")


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _flatten_json(value, output: list[str]) -> None:
    if isinstance(value, str):
        output.append(value)
    elif isinstance(value, (int, float, bool)):
        output.append(str(value))
    elif isinstance(value, list):
        for item in value:
            _flatten_json(item, output)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key != "relations":
                _flatten_json(item, output)


def extract_content(path: str | Path) -> dict:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    relations: list[dict] = []
    if suffix == ".pdf":
        executable = shutil.which("pdftotext")
        if executable is None:
            raise ValueError("Le serveur doit disposer de pdftotext pour apprendre depuis un PDF.")
        process = subprocess.run(
            [executable, "-layout", str(file_path), "-"], capture_output=True, check=False, timeout=300
        )
        if process.returncode != 0:
            raise ValueError("Extraction PDF impossible.")
        text = _decode(process.stdout)
    elif suffix in {".json", ".jsonl"}:
        raw_text = _decode(file_path.read_bytes())
        values = []
        if suffix == ".jsonl":
            for line in raw_text.splitlines():
                if line.strip():
                    values.append(json.loads(line))
        else:
            values = [json.loads(raw_text)]
        output: list[str] = []
        for value in values:
            if isinstance(value, dict) and isinstance(value.get("relations"), list):
                relations.extend(item for item in value["relations"] if isinstance(item, dict))
            _flatten_json(value, output)
        text = "\n".join(output)
    elif suffix in {".csv", ".tsv"}:
        raw_text = _decode(file_path.read_bytes())
        dialect = "excel-tab" if suffix == ".tsv" else "excel"
        reader = csv.reader(io.StringIO(raw_text), dialect=dialect)
        text = "\n".join(" ".join(cell for cell in row if cell) for row in reader)
    elif suffix in {".html", ".htm", ".xml"}:
        raw_text = _decode(file_path.read_bytes())
        text = html.unescape(TAG_RE.sub(" ", raw_text))
    elif suffix in TEXT_EXTENSIONS:
        text = _decode(file_path.read_bytes())
    else:
        raise ValueError(f"Format non pris en charge: {suffix or 'sans extension'}")
    text = text.replace("\x00", "")
    if not text.strip() and not relations:
        raise ValueError("Le contenu extrait est vide.")
    return {"text": text, "relations": relations, "bytes": file_path.stat().st_size, "extension": suffix}
