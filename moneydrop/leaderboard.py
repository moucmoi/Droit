from __future__ import annotations

import json
import os
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Tuple


@dataclass
class LeaderboardEntry:
    name: str
    best_chips: int
    best_correct: int


class Leaderboard:
    """Classement global thread-safe, persistant (JSON)."""

    def __init__(self, path: str):
        self._path = path
        self._lock = Lock()
        self._scores: Dict[str, LeaderboardEntry] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, payload in data.items():
                self._scores[name] = LeaderboardEntry(
                    name=name,
                    best_chips=int(payload.get("best_chips", 0)),
                    best_correct=int(payload.get("best_correct", 0)),
                )
        except Exception:
            # En cas de fichier corrompu, on repart proprement.
            self._scores = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {
            name: {"best_chips": e.best_chips, "best_correct": e.best_correct}
            for name, e in self._scores.items()
        }
        tmp = f"{self._path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def update(self, name: str, final_chips: int, correct_answers: int) -> None:
        with self._lock:
            current = self._scores.get(name)
            if current is None:
                self._scores[name] = LeaderboardEntry(
                    name=name, best_chips=final_chips, best_correct=correct_answers
                )
            else:
                # On conserve la meilleure perf en jetons, et à égalité, les bonnes réponses.
                if (final_chips > current.best_chips) or (
                    final_chips == current.best_chips
                    and correct_answers > current.best_correct
                ):
                    current.best_chips = final_chips
                    current.best_correct = correct_answers
            self._save()

    def top(self, n: int = 10) -> List[LeaderboardEntry]:
        with self._lock:
            entries = list(self._scores.values())
        entries.sort(key=lambda e: (e.best_chips, e.best_correct, e.name.lower()), reverse=True)
        return entries[:n]

    def render(self, n: int = 10) -> str:
        entries = self.top(n)
        if not entries:
            return "(Classement vide)"
        lines = ["=== Classement global ==="]
        for i, e in enumerate(entries, start=1):
            lines.append(f"{i:>2}. {e.name:<16} | Jetons: {e.best_chips:<5} | Bonnes réponses: {e.best_correct}")
        return "\n".join(lines)
