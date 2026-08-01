from __future__ import annotations

from pathlib import Path

from .inference import ReferentialInference
from .learning import LearningCycle
from .store import AnankeStore
from .trainer import AnankeTrainer


class AnankeEngine:
    def __init__(self, state_path: str | Path, read_only: bool = False, max_context: int = 18):
        self.store = AnankeStore(state_path, read_only=read_only)
        self.read_only = read_only
        self.inference = ReferentialInference(self.store, max_context=max_context)
        self.trainer = None if read_only else AnankeTrainer(self.store, max_context=max_context)
        self.learning = None if read_only else LearningCycle(self.store, self.trainer)

    def infer(self, prompt: str, objective: str = "general", max_characters: int = 512,
              include_trace: bool = False) -> dict:
        result = self.inference.generate(prompt, objective, max_characters, include_trace)
        result["version"] = self.store.version()
        result["model"] = "ANANKÉ · génératrice relationnelle v3.3"
        return result

    def stats(self) -> dict:
        return self.store.stats()

    def analyze_file(self, **kwargs) -> dict:
        if self.learning is None:
            raise RuntimeError("Analyse indisponible en lecture seule.")
        return self.learning.analyze_file(**kwargs)

    def commit_analysis(self, analysis_id: str, user_id: int) -> dict:
        if self.learning is None:
            raise RuntimeError("Apprentissage indisponible en lecture seule.")
        return self.learning.commit(analysis_id, user_id)

    def discard_analysis(self, analysis_id: str, user_id: int) -> dict:
        if self.learning is None:
            raise RuntimeError("Apprentissage indisponible en lecture seule.")
        return self.learning.discard(analysis_id, user_id)

    def referential_view(self, query: str = "", object_limit: int = 80, dimension_limit: int = 80) -> dict:
        object_limit = min(max(1, int(object_limit)), 500)
        dimension_limit = min(max(3, int(dimension_limit)), 500)
        params: list[object] = []
        where = ""
        if query:
            where = "WHERE o.value LIKE ? OR o.label LIKE ?"
            params.extend([f"%{query}%", f"%{query}%"])
        params.append(object_limit)
        objects = self.store._connection.execute(
            f"SELECT o.id,o.value,o.kind,o.label FROM objects o {where} ORDER BY o.id DESC LIMIT ?", params
        ).fetchall()
        dimensions = self.store._connection.execute(
            """SELECT address,logic,kind,label,parent_address FROM dimensions WHERE active=1
               ORDER BY CASE WHEN address IN ('x','y','z') THEN 0 ELSE 1 END,address LIMIT ?""",
            (dimension_limit,),
        ).fetchall()
        addresses = [str(row["address"]) for row in dimensions]
        result_objects = []
        for row in objects:
            coordinates = self.store.coordinates(int(row["id"]), addresses)
            result_objects.append({
                "id": int(row["id"]), "value": str(row["value"]), "kind": str(row["kind"]),
                "label": str(row["label"]),
                "coordinates": {key: f"{value.numerator}/{value.denominator}" for key, value in coordinates.items()},
            })
        return {
            "stats": self.stats(),
            "dimensions": [dict(row) for row in dimensions],
            "objects": result_objects,
        }

    def close(self) -> None:
        self.store.close()
