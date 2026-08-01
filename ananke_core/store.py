from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
from typing import Iterator

from .coordinates import BASE_DIMENSIONS, object_kind
from .numbers import decode_fraction, encode_fraction, positive_fraction

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS objects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  value TEXT NOT NULL,
  kind TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  created_version INTEGER NOT NULL,
  UNIQUE(value, kind)
);
CREATE INDEX IF NOT EXISTS idx_objects_value ON objects(value);
CREATE TABLE IF NOT EXISTS dimensions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  address TEXT NOT NULL UNIQUE,
  logic TEXT NOT NULL,
  kind TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  parent_address TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS coordinates (
  object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  dimension_id INTEGER NOT NULL REFERENCES dimensions(id) ON DELETE CASCADE,
  value TEXT NOT NULL,
  source TEXT NOT NULL,
  version INTEGER NOT NULL,
  PRIMARY KEY(object_id, dimension_id)
);
CREATE INDEX IF NOT EXISTS idx_coordinates_dimension_value ON coordinates(dimension_id, value, object_id);
CREATE TABLE IF NOT EXISTS lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  objective TEXT NOT NULL,
  text TEXT NOT NULL,
  source TEXT NOT NULL,
  source_bytes INTEGER NOT NULL DEFAULT 0,
  user_id INTEGER,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS object_stats (
  object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  objective TEXT NOT NULL,
  total INTEGER NOT NULL DEFAULT 0,
  after_space INTEGER NOT NULL DEFAULT 0,
  before_space INTEGER NOT NULL DEFAULT 0,
  word_start INTEGER NOT NULL DEFAULT 0,
  word_end INTEGER NOT NULL DEFAULT 0,
  uppercase INTEGER NOT NULL DEFAULT 0,
  vowel INTEGER NOT NULL DEFAULT 0,
  punctuation INTEGER NOT NULL DEFAULT 0,
  digit INTEGER NOT NULL DEFAULT 0,
  whitespace INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(object_id, objective)
);
CREATE TABLE IF NOT EXISTS neighbor_observations (
  objective TEXT NOT NULL,
  source_object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  target_object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  support INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY(objective, source_object_id, target_object_id)
);
CREATE TABLE IF NOT EXISTS relations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  target_object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  dimension_id INTEGER NOT NULL REFERENCES dimensions(id) ON DELETE CASCADE,
  factor TEXT NOT NULL,
  support INTEGER NOT NULL DEFAULT 1,
  source TEXT NOT NULL,
  version INTEGER NOT NULL,
  UNIQUE(source_object_id, target_object_id, dimension_id)
);
CREATE TABLE IF NOT EXISTS relation_rules (
  objective TEXT NOT NULL,
  context_length INTEGER NOT NULL,
  trajectory_hash TEXT NOT NULL,
  trajectory_power_hash TEXT NOT NULL,
  trajectory_json TEXT NOT NULL,
  next_relation_hash TEXT NOT NULL,
  next_relation_json TEXT NOT NULL,
  support INTEGER NOT NULL,
  last_version INTEGER NOT NULL,
  PRIMARY KEY(objective, context_length, trajectory_hash, next_relation_hash)
);
CREATE INDEX IF NOT EXISTS idx_relation_rules_exact ON relation_rules(objective, context_length, trajectory_hash);
CREATE INDEX IF NOT EXISTS idx_relation_rules_power ON relation_rules(objective, context_length, trajectory_power_hash);
CREATE TABLE IF NOT EXISTS learning_analyses (
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  objective TEXT NOT NULL,
  filename TEXT NOT NULL,
  staging_path TEXT NOT NULL,
  base_version INTEGER NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  committed_at TEXT
);
CREATE TABLE IF NOT EXISTS journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version INTEGER NOT NULL,
  action TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class AnankeStore:
    def __init__(self, path: str | Path, read_only: bool = False):
        self.path = Path(path)
        self.read_only = read_only
        self._lock = threading.RLock()
        if read_only:
            if not self.path.exists():
                raise FileNotFoundError(f"Référentiel introuvable: {self.path}")
            uri = f"file:{self.path.resolve()}?mode=ro"
            self._connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys=ON")
        if not read_only:
            self._connection.executescript(SCHEMA)
            self._connection.execute("INSERT OR IGNORE INTO metadata(key,value) VALUES('version','0')")
            self._connection.commit()
            self._ensure_base_dimensions()

    def _ensure_base_dimensions(self) -> None:
        version = self.version()
        with self.transaction() as connection:
            for address in BASE_DIMENSIONS:
                connection.execute(
                    "INSERT OR IGNORE INTO dimensions(address,logic,kind,label,parent_address,created_version) VALUES(?,?,?,?,?,?)",
                    (address, "fundamental", "measured", f"Coordonnée fondamentale mesurée {address.upper()}", None, version),
                )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        if self.read_only:
            raise RuntimeError("Le référentiel est ouvert en lecture seule.")
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def version(self) -> int:
        row = self._connection.execute("SELECT value FROM metadata WHERE key='version'").fetchone()
        return int(row[0]) if row else 0

    def next_version(self, connection: sqlite3.Connection) -> int:
        version = self.version() + 1
        connection.execute("UPDATE metadata SET value=? WHERE key='version'", (str(version),))
        return version

    def ensure_object(self, value: str, kind: str | None = None, version: int | None = None,
                      label: str = "", connection: sqlite3.Connection | None = None) -> int:
        if self.read_only:
            raise RuntimeError("ensure_object est interdit en lecture seule.")
        if value == "":
            raise ValueError("Un objet vide ne peut pas être inscrit.")
        db = connection or self._connection
        version = self.version() if version is None else version
        kind = kind or object_kind(value)
        db.execute(
            """INSERT INTO objects(value,kind,label,created_version) VALUES(?,?,?,?)
               ON CONFLICT(value,kind) DO UPDATE SET
                 label=CASE WHEN excluded.label<>'' THEN excluded.label ELSE objects.label END""",
            (value, kind, label, version),
        )
        row = db.execute("SELECT id FROM objects WHERE value=? AND kind=?", (value, kind)).fetchone()
        if connection is None:
            self._connection.commit()
        return int(row[0])

    def object_id(self, value: str, kind: str | None = None) -> int | None:
        if kind:
            row = self._connection.execute("SELECT id FROM objects WHERE value=? AND kind=?", (value, kind)).fetchone()
        else:
            row = self._connection.execute("SELECT id FROM objects WHERE value=? ORDER BY id LIMIT 1", (value,)).fetchone()
        return int(row[0]) if row else None

    def object_value(self, object_id: int) -> str:
        row = self._connection.execute("SELECT value FROM objects WHERE id=?", (object_id,)).fetchone()
        if row is None:
            raise KeyError(object_id)
        return str(row[0])

    def ensure_dimension(self, address: str, logic: str, kind: str, version: int,
                         parent_address: str | None = None, label: str = "",
                         connection: sqlite3.Connection | None = None) -> int:
        if self.read_only:
            raise RuntimeError("ensure_dimension est interdit en lecture seule.")
        db = connection or self._connection
        db.execute(
            """INSERT INTO dimensions(address,logic,kind,label,parent_address,created_version)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(address) DO UPDATE SET
                 logic=excluded.logic, kind=excluded.kind,
                 label=CASE WHEN excluded.label<>'' THEN excluded.label ELSE dimensions.label END,
                 active=1""",
            (address, logic, kind, label, parent_address, version),
        )
        row = db.execute("SELECT id FROM dimensions WHERE address=?", (address,)).fetchone()
        if connection is None:
            self._connection.commit()
        return int(row[0])

    def set_coordinate(self, object_id: int, address: str, value: Fraction, source: str, version: int,
                       connection: sqlite3.Connection | None = None) -> None:
        if self.read_only:
            raise RuntimeError("set_coordinate est interdit en lecture seule.")
        db = connection or self._connection
        value = positive_fraction(value)
        row = db.execute("SELECT id FROM dimensions WHERE address=?", (address,)).fetchone()
        if row is None:
            raise KeyError(f"Dimension inconnue: {address}")
        db.execute(
            """INSERT INTO coordinates(object_id,dimension_id,value,source,version)
               VALUES(?,?,?,?,?)
               ON CONFLICT(object_id,dimension_id) DO UPDATE SET
                 value=excluded.value, source=excluded.source, version=excluded.version""",
            (object_id, int(row[0]), encode_fraction(value), source, version),
        )
        if connection is None:
            self._connection.commit()

    def coordinates(self, object_id: int, dimensions: list[str] | None = None) -> dict[str, Fraction]:
        params: list[object] = [object_id]
        sql = """SELECT d.address,c.value FROM coordinates c
                 JOIN dimensions d ON d.id=c.dimension_id WHERE c.object_id=?"""
        if dimensions:
            placeholders = ",".join("?" for _ in dimensions)
            sql += f" AND d.address IN ({placeholders})"
            params.extend(dimensions)
        rows = self._connection.execute(sql, params).fetchall()
        return {str(row["address"]): decode_fraction(str(row["value"])) for row in rows}

    def active_dimensions(self, objective: str) -> list[str]:
        rows = self._connection.execute(
            """SELECT address FROM dimensions WHERE active=1 AND
               (logic IN ('fundamental','general',?) OR address LIKE ?)
               ORDER BY CASE WHEN address IN ('x','y','z') THEN 0 ELSE 1 END,address""",
            (objective, f"objective/{objective}/%"),
        ).fetchall()
        return [str(row[0]) for row in rows]

    def inference_dimensions(self, objective: str) -> list[str]:
        """Active d'abord les dimensions de loi explicites.

        Si aucune loi relationnelle n'est disponible pour l'objectif, ANANKÉ
        utilise les dimensions mesurées du corpus. Cette hiérarchie évite qu'une
        statistique générale masque une analogie démontrée dans une logique.
        """
        relation_rows = self._connection.execute(
            """SELECT address FROM dimensions WHERE active=1 AND kind='relation'
               AND logic IN ('general',?) ORDER BY address""",
            (objective,),
        ).fetchall()
        if relation_rows:
            return [str(row[0]) for row in relation_rows]
        return self.active_dimensions(objective)

    def relation_dimensions(self, addresses: list[str]) -> list[str]:
        """Sous-ensemble des adresses dont la dimension est une loi (kind='relation')."""
        if not addresses:
            return []
        placeholders = ",".join("?" for _ in addresses)
        rows = self._connection.execute(
            f"SELECT address FROM dimensions WHERE kind='relation' AND address IN ({placeholders})",
            addresses,
        ).fetchall()
        present = {str(row[0]) for row in rows}
        return [address for address in addresses if address in present]

    def resolve_coordinates(self, target: dict[str, Fraction], required_dimensions: list[str]) -> list[int]:
        if not required_dimensions:
            return []
        candidate_ids: set[int] | None = None
        for address in required_dimensions:
            if address not in target:
                return []
            encoded = encode_fraction(target[address])
            rows = self._connection.execute(
                """SELECT c.object_id FROM coordinates c JOIN dimensions d ON d.id=c.dimension_id
                   WHERE d.address=? AND c.value=?""",
                (address, encoded),
            ).fetchall()
            current = {int(row[0]) for row in rows}
            candidate_ids = current if candidate_ids is None else candidate_ids & current
            if not candidate_ids:
                return []
        return sorted(candidate_ids or [])

    def stats(self) -> dict:
        def count(table: str) -> int:
            return int(self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return {
            "version": self.version(),
            "objects": count("objects"),
            "dimensions": count("dimensions"),
            "coordinates": count("coordinates"),
            "relation_rules": count("relation_rules"),
            "patterns": 0,
            "relations": count("relations"),
            "lines": count("lines"),
            "analyses_pending": int(self._connection.execute("SELECT COUNT(*) FROM learning_analyses WHERE status='analyzed'").fetchone()[0]),
        }

    def journal(self, connection: sqlite3.Connection, version: int, action: str, payload: dict) -> None:
        connection.execute(
            "INSERT INTO journal(version,action,payload_json) VALUES(?,?,?)",
            (version, action, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
        )

    def create_analysis(self, user_id: int, objective: str, filename: str, staging_path: str, payload: dict) -> str:
        analysis_id = uuid.uuid4().hex
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO learning_analyses(id,user_id,objective,filename,staging_path,base_version,status,payload_json)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (analysis_id, user_id, objective, filename, staging_path, self.version(), "analyzed", json.dumps(payload, ensure_ascii=False)),
            )
        return analysis_id

    def analysis(self, analysis_id: str, user_id: int) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM learning_analyses WHERE id=? AND user_id=?", (analysis_id, user_id)
        ).fetchone()

    def close(self) -> None:
        self._connection.close()
