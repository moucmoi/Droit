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
        self._rng = random.Random()
        self._questions = list(questions)

    def run_game(self, player_name: str, io: IO, config: GameConfig) -> GameResult:
        """Boucle console inspirée du poker-quiz (check/mise/all-in)."""

        player = Player(name=player_name, chips=config.starting_chips)
        details: List[str] = []

        questions = self._questions[: config.question_count]
        self._rng.shuffle(questions)

        io.write("\n=== Quiz Poker ===\n")
        io.write(f"Joueur: {player.name} | Banque de départ: {player.chips}€\n")
        io.write(
            "À chaque question, choisissez une réponse (A/B/C/D) puis une action :\n"
            "- check : vous passez, aucun risque ni gain ;\n"
            "- mise <montant> : si bonne réponse, vous gagnez 1,25× votre mise ; sinon vous perdez la mise ;\n"
            "- all-in : vous engagez tout. Si bonne réponse, votre banque passe à 2,25× ; sinon vous perdez tout.\n"
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
            io.write(f"Banque actuelle: {player.chips}€\n")

            answer = self._prompt_answer(io)
            action, amount = self._prompt_action(io, player.chips)

            correct = answer == question.correct
            delta = 0
            if action == "check":
                delta = 0
            elif action == "bet":
                if correct:
                    delta = int(-amount + amount * 1.25)  # net gain +25% sur la mise
                else:
                    delta = -amount
            elif action == "all-in":
                delta = int(player.chips * 1.25) if correct else -player.chips

            player.chips += delta
            if correct:
                player.correct_answers += 1

            io.write("\nRésultat :\n")
            io.write(f"Bonne réponse: {question.correct}) {question.answers[question.correct]}\n")
            if question.explanation:
                io.write(f"Explication: {question.explanation}\n")
            if action == "check":
                io.write("Action: check — aucun changement.\n")
            else:
                io.write(f"Action: {action} | Montant: {amount}\n")
                if delta >= 0:
                    io.write(f"Gagné: +{delta} | Nouvelle banque: {player.chips}\n")
                else:
                    io.write(f"Perdu: {abs(delta)} | Nouvelle banque: {player.chips}\n")

            details.append(
                f"Q{idx}: action={action} answer={answer} correct={question.correct} delta={delta} bank={player.chips}"
            )

        io.write("\n" + ("=" * 60) + "\n")
        io.write(f"Fin de partie - {player.name}\n")
        io.write(f"Banque finale: {player.chips}€\n")
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

    def _prompt_answer(self, io: IO) -> AnswerKey:
        while True:
            ans = io.read_line("Votre réponse (A/B/C/D): ").strip().upper()
            if ans in ("A", "B", "C", "D"):
                return ans  # type: ignore[return-value]
            io.write("Réponse invalide. Choisissez A, B, C ou D.\n")

    def _prompt_action(self, io: IO, bank: int) -> Tuple[str, int]:
        while True:
            raw = io.read_line("Action (check | mise <montant> | all-in): ").strip().lower()
            if raw == "check":
                return "check", 0
            if raw == "all-in":
                return "all-in", bank
            if raw.startswith("mise"):
                parts = raw.split()
                if len(parts) != 2:
                    io.write("Format attendu: mise 200\n")
                    continue
                try:
                    amt = int(parts[1])
                except ValueError:
                    io.write("Montant invalide.\n")
                    continue
                if amt < 0:
                    io.write("Montant négatif interdit.\n")
                    continue
                if amt > bank:
                    io.write(f"Montant supérieur à la banque ({bank}).\n")
                    continue
                return "bet", amt
            io.write("Choisissez: check, mise <montant> ou all-in.\n")
