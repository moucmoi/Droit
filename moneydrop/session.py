from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional

from .engine import MoneyDropEngine
from .models import AnswerKey, GameConfig, GameResult, Player, Question


@dataclass
class BetResolution:
    correct: AnswerKey
    correct_label: str
    action: str
    bet_amount: int
    delta: int
    bank_after: int
    multiplier: float
    was_correct: bool
    lost: int
    gained: int
    explanation: str


class GameSession:
    """État d'une partie (pilotable question par question)."""

    def __init__(self, engine: MoneyDropEngine, player_name: str, config: GameConfig):
        self.engine = engine
        self.config = config
        self.player = Player(name=player_name, chips=config.starting_chips)

        # Questions figées au démarrage pour la session
        questions = engine._questions[:]  # noqa: SLF001 (accès interne contrôlé pour session)
        engine._rng.shuffle(questions)  # noqa: SLF001
        self.questions = questions[: config.question_count]

        self.index = 0
        self.eliminated = False
        self.finished = False
        self.correct_answers = 0
        self.details: list[str] = []
        self.created_at = time.time()
        self.last_activity = self.created_at

    def current_question(self) -> Optional[Question]:
        if self.finished or self.eliminated:
            return None
        if self.index >= len(self.questions):
            return None
        return self.questions[self.index]

    def submit_action(self, answer: AnswerKey, action: str, amount: int) -> BetResolution:
        self.last_activity = time.time()

        if self.finished or self.eliminated:
            raise ValueError("partie terminée")

        q = self.current_question()
        if q is None:
            self.finished = True
            raise ValueError("plus de question")

        answer = (answer or "").strip().upper()
        if answer not in ("A", "B", "C", "D"):
            raise ValueError("réponse invalide (A/B/C/D)")

        action = (action or "").strip().lower()
        if action not in ("check", "bet", "all-in"):
            raise ValueError("action invalide (check/bet/all-in)")

        bank_before = self.player.chips

        if action == "check":
            amount = 0
        elif action == "all-in":
            amount = bank_before
        else:
            try:
                amount = int(amount)
            except Exception:
                raise ValueError("montant invalide")
            if amount < 0:
                raise ValueError("montant négatif interdit")
            if amount > bank_before:
                raise ValueError("montant > banque disponible")

        correct = answer == q.correct
        delta = 0
        multiplier = 0.0

        if action == "check":
            multiplier = 0.0
            delta = 0
        elif action == "bet":
            multiplier = 1.6
            delta = int(-amount + amount * multiplier) if correct else -amount
        else:  # all-in
            multiplier = 2.25
            delta = int(bank_before * 1.25) if correct else -bank_before

        self.player.chips += delta
        if correct:
            self.correct_answers += 1

        self.details.append(
            f"Q{self.index+1}: action={action} answer={answer} correct={q.correct} delta={delta} bank={self.player.chips}"
        )

        self.index += 1
        if self.player.chips <= 0:
            self.eliminated = True
        if self.index >= len(self.questions):
            self.finished = True

        return BetResolution(
            correct=q.correct,
            correct_label=q.answers[q.correct],
            action=action,
            bet_amount=amount,
            delta=delta,
            bank_after=self.player.chips,
            multiplier=multiplier,
            was_correct=correct,
            lost=max(0, -delta),
            gained=max(0, delta),
            explanation=q.explanation,
        )

    def result(self) -> GameResult:
        return GameResult(
            player_name=self.player.name,
            final_chips=self.player.chips,
            correct_answers=self.correct_answers,
            questions_played=len(self.questions),
            eliminated=self.eliminated,
            details=self.details,
        )


class SessionManager:
    """Gestionnaire thread-safe de sessions de jeu."""

    def __init__(self):
        self._lock = Lock()
        self._sessions: Dict[str, GameSession] = {}

    def create(self, session: GameSession) -> str:
        session_id = secrets.token_urlsafe(24)
        with self._lock:
            self._sessions[session_id] = session
        return session_id

    def get(self, session_id: str) -> Optional[GameSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def cleanup_inactive(self, ttl_seconds: int = 3600) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            to_delete = [sid for sid, s in self._sessions.items() if now - s.last_activity > ttl_seconds]
            for sid in to_delete:
                self._sessions.pop(sid, None)
                removed += 1
        return removed


@dataclass
class LobbyPlayer:
    session_id: str
    name: str
    chips: int
    correct_answers: int = 0


class Lobby:
    """Salon multi-joueurs synchronisé par question.

    - Tous les joueurs partagent la même liste de questions (mélangée selon le moteur).
    - Pour chaque question, on collecte les mises dans `submissions`.
    - Quand tous ont soumis ou que le timeout est dépassé, on résout la manche.
    """

    def __init__(self, lobby_id: str, engine: MoneyDropEngine, config: GameConfig, size: int, creator: LobbyPlayer, time_limit: int = 30):
        self.id = lobby_id
        self.engine = engine
        self.config = config
        self.size = int(size)
        self.time_limit = int(time_limit)

        # players: list of LobbyPlayer
        self.players: list[LobbyPlayer] = [creator]
        self.creator = creator.session_id

        # prepare questions once per lobby
        qs = engine._questions[:]  # noqa: SLF001
        engine._rng.shuffle(qs)  # noqa: SLF001
        self.questions = qs[: config.question_count]

        self.index = 0
        self.started = False

        # submissions: session_id -> {"answer": ..., "action": ..., "amount": ...}
        self.submissions: Dict[str, Dict[str, object]] = {}

        # last round results: session_id -> resolution dict (compat front)
        self.last_results: Dict[str, dict] = {}

        self.question_start = 0.0

    def join(self, player: LobbyPlayer) -> None:
        if any(p.session_id == player.session_id for p in self.players):
            return
        if len(self.players) >= self.size:
            raise ValueError("lobby plein")
        self.players.append(player)

    def start(self) -> None:
        if self.started:
            return
        if len(self.players) != self.size:
            raise ValueError("attente d'autres joueurs")
        self.started = True
        self.index = 0
        self.submissions = {}
        self.last_results = {}
        self.question_start = time.time()

    def current_question(self) -> Optional[Question]:
        if not self.started:
            return None
        if self.index >= len(self.questions):
            return None
        return self.questions[self.index]

    def submit(self, session_id: str, bet_payload: Dict[AnswerKey, int] | Dict[str, object]) -> None:
        if not self.started:
            raise ValueError("partie non démarrée")
        if session_id in self.submissions:
            # override allowed
            pass

        action = "check"
        amount = 0
        answer: AnswerKey = "A"
        player = next((pl for pl in self.players if pl.session_id == session_id), None)
        bank = player.chips if player else self.config.starting_chips

        if isinstance(bet_payload, dict) and ("action" in bet_payload or "answer" in bet_payload):
            action = str(bet_payload.get("action", "check")).lower()
            answer = str(bet_payload.get("answer", "A")).upper()[:1] or "A"  # type: ignore[assignment]
            try:
                amount = int(bet_payload.get("amount", 0))
            except Exception:
                amount = 0
        else:
            bets = {k: int(bet_payload.get(k, 0)) for k in ["A", "B", "C", "D"]} if isinstance(bet_payload, dict) else {}
            amount = sum(bets.values())
            answer = max(bets.items(), key=lambda kv: kv[1])[0] if bets else "A"  # type: ignore[index]
            if amount <= 0:
                action = "check"
            elif amount >= bank:
                action = "all-in"
                amount = bank
            else:
                action = "bet"

        self.submissions[session_id] = {"action": action, "amount": amount, "answer": answer}

        # maybe resolve
        if self._should_resolve():
            self._resolve_round()

    def _should_resolve(self) -> bool:
        if not self.started:
            return False
        if len(self.submissions) >= len(self.players):
            return True
        if time.time() - self.question_start >= self.time_limit:
            return True
        return False

    def _resolve_round(self) -> None:
        q = self.current_question()
        if q is None:
            return

        for p in self.players:
            submission = self.submissions.get(p.session_id, {"action": "check", "amount": 0, "answer": None})
            action = str(submission.get("action", "check") or "check").lower()
            amount = int(submission.get("amount", 0) or 0)
            answer = str(submission.get("answer", "") or "").upper()[:1]

            bank_before = p.chips
            if action == "all-in":
                amount = bank_before
            amount = max(0, min(amount, bank_before))
            correct = answer == q.correct

            if action == "check":
                delta = 0
            elif action == "bet":
                delta = int(-amount + amount * 1.6) if correct else -amount
            elif action == "all-in":
                delta = int(bank_before * 1.25) if correct else -bank_before
            else:
                delta = 0

            p.chips += delta
            if correct:
                p.correct_answers += 1
            if p.chips <= 0:
                p.chips = 0

            self.last_results[p.session_id] = {
                "correct": q.correct,
                "correct_label": q.answers[q.correct],
                "kept": p.chips,
                "lost": max(0, -delta),
                "bet_total": amount,
                "unbet": max(0, bank_before - amount),
                "explanation": q.explanation,
                "correct_bet": amount if correct else 0,
                "action": action,
                "gained": max(0, delta),
            }

        # advance
        self.index += 1
        self.submissions = {}
        self.question_start = time.time()

    def is_finished(self) -> bool:
        return self.index >= len(self.questions)

    def player_view(self, session_id: str) -> dict:
        # returns view for a player
        q = self.current_question()
        now = time.time()
        remaining = max(0, int(self.time_limit - (now - self.question_start)))

        players_list = [
            {"name": p.name, "chips": p.chips, "session_id": p.session_id, "correct_answers": p.correct_answers}
            for p in self.players
        ]

        return {
            "lobby_id": self.id,
            "started": self.started,
            "players": players_list,
            "question_index": self.index,
            "question_total": len(self.questions),
            "question": None if q is None else {"category": q.category, "prompt": q.prompt, "answers": q.answers},
            "time_remaining": remaining,
            "you_submitted": session_id in self.submissions,
            "last_results": self.last_results,
            "finished": self.is_finished(),
        }


class LobbyManager:
    def __init__(self):
        self._lock = Lock()
        self._lobbies: Dict[str, Lobby] = {}

    def create(self, lobby_id: str, engine: MoneyDropEngine, config: GameConfig, size: int, creator: LobbyPlayer, time_limit: int = 30) -> Lobby:
        with self._lock:
            if lobby_id in self._lobbies:
                raise ValueError("lobby exists")
            l = Lobby(lobby_id, engine, config, size, creator, time_limit=time_limit)
            self._lobbies[lobby_id] = l
            return l

    def get(self, lobby_id: str) -> Optional[Lobby]:
        with self._lock:
            return self._lobbies.get(lobby_id)

    def delete(self, lobby_id: str) -> None:
        with self._lock:
            self._lobbies.pop(lobby_id, None)
