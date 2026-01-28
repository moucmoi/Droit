from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

AnswerKey = Literal["A", "B", "C", "D"]


@dataclass(frozen=True)
class Question:
    """Question à 4 choix, avec une seule bonne réponse."""

    category: str
    prompt: str
    answers: Dict[AnswerKey, str]
    correct: AnswerKey
    explanation: str = ""


@dataclass
class Player:
    name: str
    chips: int
    correct_answers: int = 0


@dataclass(frozen=True)
class GameConfig:
    starting_chips: int = 1000
    question_count: int = 7
    allow_unbet_chips: bool = True


@dataclass(frozen=True)
class GameResult:
    player_name: str
    final_chips: int
    correct_answers: int
    questions_played: int
    eliminated: bool
    details: List[str] = field(default_factory=list)
