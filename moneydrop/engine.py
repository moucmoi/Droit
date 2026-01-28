from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .models import AnswerKey, GameConfig, GameResult, Player, Question


@dataclass(frozen=True)
class IO:
    """Abstraction d'I/O (console, socket, tests)."""

    write: Callable[[str], None]
    read_line: Callable[[str], str]


class MoneyDropEngine:
    def __init__(self, questions: List[Question]):
        self._questions = list(questions)

    def run_game(self, player_name: str, io: IO, config: GameConfig) -> GameResult:
        player = Player(name=player_name, chips=config.starting_chips)
        details: List[str] = []

        questions = self._questions[:]
        questions = questions[: config.question_count]

        io.write("\n=== Money Drop ===\n")
        io.write(f"Joueur: {player.name} | Jetons de départ: {player.chips}\n")
        io.write(
            "Règle: vous répartissez vos jetons sur A/B/C/D. "
            "Les jetons sur les mauvaises réponses sont perdus.\n"
        )

        eliminated = False
        for idx, question in enumerate(questions, start=1):
            if player.chips <= 0:
                eliminated = True
                details.append(f"Éliminé avant la question {idx}.")
                break

            io.write("\n" + ("-" * 60) + "\n")
            io.write(f"Question {idx}/{len(questions)} [{question.category}]\n")
            io.write(question.prompt + "\n")
            for key in ["A", "B", "C", "D"]:
                io.write(f"  {key}) {question.answers[key]}\n")
            io.write(f"Jetons disponibles: {player.chips}\n")
            io.write("Format mise: A=200 B=300 C=0 D=50 (espaces ou virgules).\n")

            bets = self._prompt_bets(io, player.chips)
            bet_total = sum(bets.values())
            unbet = player.chips - bet_total
            if unbet > 0 and not config.allow_unbet_chips:
                # Contrat: ici, on force l'utilisation de tous les jetons.
                io.write("Vous devez miser tous vos jetons sur A/B/C/D.\n")
                bets = self._prompt_bets(io, player.chips, must_use_all=True)
                bet_total = sum(bets.values())
                unbet = player.chips - bet_total

            kept = bets[question.correct]
            lost = bet_total - bets[question.correct]
            player.chips = kept
            if bets[question.correct] > 0:
                player.correct_answers += 1

            io.write("\nRésultat :\n")
            io.write(f"Bonne réponse: {question.correct}) {question.answers[question.correct]}\n")
            if question.explanation:
                io.write(f"Explication: {question.explanation}\n")
            io.write(f"Jetons misés: {bet_total} | Non misés: {unbet}\n")
            io.write(f"Perdus: {lost} | Conservés: {kept}\n")

            details.append(
                f"Q{idx}: correct={question.correct} bet={bet_total} kept={kept} lost={lost}"
            )

        io.write("\n" + ("=" * 60) + "\n")
        io.write(f"Fin de partie - {player.name}\n")
        io.write(f"Jetons finaux: {player.chips}\n")
        io.write(f"Bonnes réponses: {player.correct_answers}/{len(questions)}\n")

        return GameResult(
            player_name=player.name,
            final_chips=player.chips,
            correct_answers=player.correct_answers,
            questions_played=len(questions),
            eliminated=eliminated,
            details=details,
        )

    def _prompt_bets(self, io: IO, available: int, must_use_all: bool = False) -> Dict[AnswerKey, int]:
        while True:
            raw = io.read_line(
                "Entrez vos mises (ex: A=200 B=300 C=0 D=50). Vous pouvez mettre 0.\n> "
            )
            try:
                bets = self._parse_bets(raw)
            except ValueError as e:
                io.write(f"Entrée invalide: {e}\n")
                continue

            total = sum(bets.values())
            if total > available:
                io.write(f"Somme des mises {total} > jetons disponibles {available}.\n")
                continue
            if must_use_all and total != available:
                io.write(f"Vous devez miser exactement {available} (actuel: {total}).\n")
                continue
            return bets

    def _parse_bets(self, raw: str) -> Dict[AnswerKey, int]:
        # Accepte: "A=10 B=20" ou "A 10, B 20" etc.
        cleaned = raw.replace(",", " ").replace(";", " ").strip()
        if not cleaned:
            raise ValueError("mise vide")

        tokens = cleaned.split()

        # Cas 1: tokens du type "A=10"
        pairs: List[Tuple[str, str]] = []
        for tok in tokens:
            if "=" in tok:
                left, right = tok.split("=", 1)
                pairs.append((left.strip(), right.strip()))

        # Cas 2: tokens du type "A 10 B 20"
        if not pairs:
            if len(tokens) % 2 != 0:
                raise ValueError("format attendu: A=10 B=20 ... ou A 10 B 20 ...")
            it = iter(tokens)
            pairs = list(zip(it, it))

        bets: Dict[AnswerKey, int] = {"A": 0, "B": 0, "C": 0, "D": 0}

        for key_raw, val_raw in pairs:
            key = key_raw.strip().upper()
            if key not in bets:
                raise ValueError(f"table inconnue '{key_raw}' (utilisez A/B/C/D)")
            try:
                value = int(val_raw)
            except ValueError:
                raise ValueError(f"montant non entier '{val_raw}'")
            if value < 0:
                raise ValueError("montant négatif interdit")
            bets[key] = value  # dernière occurrence gagne

        return bets
