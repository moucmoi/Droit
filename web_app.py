from __future__ import annotations

import eventlet
eventlet.monkey_patch()

import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, emit, join_room

from moneydrop.engine import MoneyDropEngine
from moneydrop.leaderboard import Leaderboard
from moneydrop.models import GameConfig
from moneydrop.questions import build_question_bank
from moneydrop.session import GameSession, SessionManager, LobbyManager, LobbyPlayer


BASE_DIR = Path(__file__).resolve().parent


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "web" / "templates"),
        static_folder=str(BASE_DIR / "web" / "static"),
    )
    app.secret_key = os.environ.get("MONEYDROP_SECRET", "dev-secret-change-me")

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="eventlet",
        engineio_logger=False,
        socketio_logger=False,
        ping_timeout=60,
        ping_interval=25
    )

    leaderboard = Leaderboard(str(BASE_DIR / "data" / "leaderboard.json"))
    engine = MoneyDropEngine(build_question_bank())
    sessions = SessionManager()
    lobbies = LobbyManager()
    config = GameConfig(starting_chips=10000, question_count=7, allow_unbet_chips=True)

    create_lobby_password = os.environ.get("MONEYDROP_CREATE_PASSWORD", "Droit_Terrasse2026")

    # --- Realtime multiplayer (server-authoritative) ---
    def _ensure_sid() -> str:
        sid = session.get("sid")
        if not sid:
            sid = secrets.token_urlsafe(18)
            session["sid"] = sid
        return sid

    @dataclass
    class RTPlayer:
        sid: str
        name: str
        score: int = 10000  # capital à miser (jetons)
        choice: Optional[str] = None
        is_correct: Optional[bool] = None
        eliminated: bool = False  # Défaite totale (capital=0)
        bets: Dict[str, int] = field(default_factory=lambda: {"A": 0, "B": 0, "C": 0, "D": 0})
        socket_id: Optional[str] = None  # SocketIO session ID
        ip: Optional[str] = None  # last known IP address

    @dataclass
    class RealtimeLobby:
        lobby_id: str
        host_sid: str
        host_name: str
        max_players: int = 50
        time_limit: int = 30
        question_total: int = 10
        created_at: float = field(default_factory=time.time)
        lock: threading.Lock = field(default_factory=threading.Lock)

        phase: str = "waiting"  # waiting|question|paused|results|finished
        question_index: int = 0
        question_started_at: Optional[float] = None
        paused_remaining: Optional[int] = None

        questions: list = field(default_factory=list)
        correct: Optional[str] = None
        players: Dict[str, RTPlayer] = field(default_factory=dict)
        # SIDs of players who were eliminated and must not rejoin as active players
        banned_sids: set = field(default_factory=set)

        # Durée de la cinématique côté client avant affichage du plateau (voir web/static/cinematic.js)
        CINEMATIC_DELAY_SECONDS = 4.5  # 4s animation + 0.5s transition

        def add_player(self, sid: str, name: str, socket_sid: str = None, ip: Optional[str] = None) -> None:
            with self.lock:
                if sid in self.players:
                    self.players[sid].name = name
                    if socket_sid:
                        self.players[sid].socket_id = socket_sid
                    if ip:
                        self.players[sid].ip = ip
                    return
                if len(self.players) >= self.max_players:
                    raise ValueError("Lobby plein")
                self.players[sid] = RTPlayer(sid=sid, name=name, score=10000, socket_id=socket_sid, ip=ip)

        def time_remaining(self) -> Optional[int]:
            if self.phase == "question" and self.question_started_at is not None:
                elapsed = max(0.0, time.time() - self.question_started_at)
                return max(0, int(self.time_limit - elapsed))
            if self.phase == "paused" and self.paused_remaining is not None:
                return int(self.paused_remaining)
            return None

        def current_question(self) -> Optional[Dict[str, Any]]:
            if not self.questions or self.question_index >= len(self.questions):
                return None
            q = self.questions[self.question_index]
            return {
                "category": q.category,
                "prompt": q.prompt,
                "answers": q.answers,
            }

        def start_game(self, questions: list) -> None:
            with self.lock:
                if self.phase != "waiting":
                    # idempotent: on n'écrase pas une partie en cours
                    return
                self.questions = list(questions)[: self.question_total]
                self.question_index = 0
                self.correct = None
                self.question_started_at = None
                self.paused_remaining = None
                for p in self.players.values():
                    p.score = 10000  # Reset jetons
                    p.eliminated = False  # Reset statut éliminé
                    p.choice = None
                    p.is_correct = None
                    p.bets = {"A": 0, "B": 0, "C": 0, "D": 0}
                # Le host déclenche explicitement le lancement de question
                self.phase = "waiting"

        def launch_question(self) -> None:
            with self.lock:
                if self.phase not in ("waiting", "results"):
                    return
                if self.question_index >= len(self.questions):
                    self.phase = "finished"
                    return
                self.correct = None
                for p in self.players.values():
                    p.choice = None
                    p.is_correct = None
                    # Ne réinitialiser les mises que si le joueur n'est pas éliminé
                    if not p.eliminated:
                        p.bets = {"A": 0, "B": 0, "C": 0, "D": 0}
                self.phase = "question"
                # Le chrono démarre après la cinématique (plateau visible)
                self.question_started_at = time.time() + self.CINEMATIC_DELAY_SECONDS
                self.paused_remaining = None

        def pause(self) -> None:
            with self.lock:
                if self.phase != "question":
                    return
                self.paused_remaining = self.time_remaining()
                self.phase = "paused"

        def resume(self) -> None:
            with self.lock:
                if self.phase != "paused":
                    return
                remaining = int(self.paused_remaining or 0)
                self.question_started_at = time.time() - (self.time_limit - remaining)
                self.paused_remaining = None
                self.phase = "question"

        def answer(self, sid: str, choice: str) -> None:
            with self.lock:
                if self.phase != "question":
                    return
                if sid not in self.players:
                    return
                c = (choice or "").strip().upper()[:1]
                if c not in ("A", "B", "C", "D"):
                    return
                self.players[sid].choice = c

        def place_bets(self, sid: str, bets: Dict[str, int]) -> None:
            """Place les mises d'un joueur"""
            with self.lock:
                if self.phase != "question":
                    return
                if sid not in self.players:
                    return
                p = self.players[sid]
                # Valider les mises jetons
                total_bet = sum(bets.get(k, 0) for k in ["A", "B", "C", "D"])
                if total_bet > p.score:
                    return  # Mise invalide
                
                p.bets = {k: bets.get(k, 0) for k in ["A", "B", "C", "D"]} 


        def all_players_bet(self) -> bool:
            """Vérifie si tous les joueurs ont misé"""
            with self.lock:
                if self.phase != "question":
                    return False
                for p in self.players.values():
                    # Si p.bets est vide ou toutes les mises sont à 0, le joueur n'a pas misé
                    if not p.bets or sum(p.bets.values()) == 0:
                        return False
                return len(self.players) > 0  # Au moins un joueur et tous ont misé

        def validate(self) -> None:
            with self.lock:
                if self.phase not in ("question", "paused"):
                    return
                if self.question_index >= len(self.questions):
                    self.phase = "finished"
                    return
                q = self.questions[self.question_index]
                self.correct = q.correct

                # Calculer les gains/pertes pour chaque joueur
                for p in self.players.values():
                    # Ignorer les joueurs déjà éliminés
                    if p.eliminated:
                        p.is_correct = None
                        continue
                    
                    # Si le joueur n'a pas misé (p.bets vide ou tout à 0), il perd tout son capital
                    if not p.bets or sum(p.bets.values()) == 0:
                        p.score = 0
                        p.is_correct = False
                    else:
                        correct_bet = p.bets.get(self.correct, 0)
                        # Le joueur garde UNIQUEMENT sa mise correcte (les jetons non misés sont perdus)
                        p.score = correct_bet
                        p.is_correct = correct_bet > 0

                    # Si capital = 0 → défaite totale
                    if p.score <= 0:
                        p.eliminated = True
                        p.score = 0
                        p.bets = {"A": 0, "B": 0, "C": 0, "D": 0}
                                # Prevent the eliminated player from re-joining as an active player (ban sid and ip if available)
                        try:
                            if p.sid:
                                self.banned_sids.add(p.sid)
                            if getattr(p, 'ip', None):
                                self.banned_sids.add(p.ip)
                        except Exception:
                            pass 

                self.phase = "results"

        def next_question(self) -> None:
            with self.lock:
                if self.phase != "results":
                    return
                self.question_index += 1
                if self.question_index >= len(self.questions):
                    self.phase = "finished"
                    return
                self.correct = None
                self.question_started_at = None
                self.paused_remaining = None
                for p in self.players.values():
                    p.choice = None
                    p.is_correct = None
                    # Ne réinitialiser les mises que si le joueur n'est pas éliminé
                    if not p.eliminated:
                        p.bets = {"A": 0, "B": 0, "C": 0, "D": 0}
                self.phase = "waiting"

        def snapshot(self) -> Dict[str, Any]:
            with self.lock:
                return {
                    "lobby_id": self.lobby_id,
                    "phase": self.phase,
                    "time_remaining": self.time_remaining(),
                    "question_index": self.question_index,
                    "question_total": len(self.questions) if self.questions else self.question_total,
                    "question": self.current_question() if self.phase in ("question", "paused", "results") else None,
                    "correct": self.correct if self.phase == "results" else None,
                    "host_sid": self.host_sid,
                    "host_name": self.host_name,
                    "players": [
                        {
                            "sid": p.sid,
                            "name": p.name,
                            "score": p.score,
                            "eliminated": p.eliminated,
                            "choice": p.choice,
                            "is_correct": p.is_correct if self.phase == "results" else None,
                            "socket_id": p.socket_id,
                        }
                        for p in self.players.values()
                    ],
                }

    class RealtimeLobbyManager:
        def __init__(self):
            self._lock = threading.Lock()
            self._lobbies: Dict[str, RealtimeLobby] = {}

        def create(self, host_sid: str, host_name: str, max_players: int, time_limit: int) -> RealtimeLobby:
            lobby_id = secrets.token_urlsafe(8)
            lobby = RealtimeLobby(
                lobby_id=lobby_id,
                host_sid=host_sid,
                host_name=host_name,
                max_players=max(2, min(int(max_players), 50)),
                time_limit=max(5, min(int(time_limit), 120)),
                question_total=10,
            )
            # Ne pas ajouter automatiquement le host comme joueur
            # lobby.add_player(host_sid, host_name)
            with self._lock:
                self._lobbies[lobby_id] = lobby
            return lobby

        def get(self, lobby_id: str) -> Optional[RealtimeLobby]:
            with self._lock:
                return self._lobbies.get(lobby_id)

        def all(self) -> Dict[str, RealtimeLobby]:
            with self._lock:
                return dict(self._lobbies)

    rt_lobbies = RealtimeLobbyManager()

    def _require_session() -> tuple[str, GameSession]:
        sid = session.get("sid")
        if not sid:
            raise ValueError("no-session")
        game = sessions.get(sid)
        if not game:
            raise ValueError("unknown-session")
        return sid, game


    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/menu")
    def menu():
        return render_template("menu.html")

    @app.get("/api/lobbies")
    def list_lobbies():
        """Liste tous les salons disponibles (en attente de joueurs)"""
        available = []
        for lobby_id, lobby in rt_lobbies._lobbies.items():
            if lobby.phase == "waiting" and len(lobby.players) < lobby.max_players:
                available.append({
                    "lobby_id": lobby_id,
                    "host_name": lobby.host_name,
                    "players": len(lobby.players),
                    "max_players": lobby.max_players,
                    "time_limit": lobby.time_limit,
                    "question_total": lobby.question_total,
                })
        return jsonify({"ok": True, "lobbies": available})

    @app.post("/start")
    def start():
        name = (request.form.get("name") or "").strip()
        if not name:
            return render_template("index.html", error="Veuillez entrer un nom."), 400

        game = GameSession(engine=engine, player_name=name, config=config)
        sid = sessions.create(game)
        session["sid"] = sid
        return redirect(url_for("play"))

    @app.get("/play")
    def play():
        try:
            _require_session()
        except Exception:
            return redirect(url_for("index"))
        return render_template("play.html")

    # --- Lobby endpoints ---
    @app.post("/lobby/create")
    def lobby_create():
        data = request.form or request.get_json() or {}
        sid = _ensure_sid()
        name = (data.get("name") or "Host").strip()[:24]
        password = (data.get("password") or "").strip()
        size = int(data.get("size", 2))
        time_limit = int(data.get("time_limit", 30))

        if password != create_lobby_password:
            if request.is_json:
                return jsonify({"ok": False, "error": "invalid password"}), 403
            # On renvoie une erreur pour affichage sous le champ
            return render_template("menu.html", host_error="MTP incorrect", host_name=name, host_size=size, host_time_limit=time_limit)

        lobby = rt_lobbies.create(host_sid=sid, host_name=name, max_players=size, time_limit=time_limit)
        # Stocker le nom de l'hôte en session
        session[f"player_name_{lobby.lobby_id}"] = name
        return redirect(url_for("lobby_host", lobby_id=lobby.lobby_id))

    @app.post("/lobby/join")
    def lobby_join():
        data = request.form or request.get_json() or {}
        sid = _ensure_sid()
        lobby_id = (data.get("lobby_id") or "").strip()
        if not lobby_id:
            if request.is_json:
                return jsonify({"ok": False, "error": "missing lobby_id"}), 400
            return redirect(url_for("menu", error="missing lobby_id"))
        name = (data.get("name") or "Joueur").strip()[:24]

        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            if request.is_json:
                return jsonify({"ok": False, "error": "unknown-lobby"}), 404
            return redirect(url_for("menu", error="unknown-lobby"))
        
        # Stocker le nom en session pour le passer au template
        session[f"player_name_{lobby_id}"] = name
        
        # NE PAS ajouter le joueur ici - il sera ajouté via websocket
        # pour éviter la duplication
        
        if request.is_json:
            return jsonify({"ok": True, "lobby_id": lobby_id})
        return redirect(url_for("lobby_client", lobby_id=lobby_id))

    @app.get("/lobby/<lobby_id>/host")
    def lobby_host(lobby_id: str):
        _ensure_sid()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            return redirect(url_for("menu", error="unknown-lobby"))
        if session.get("sid") != lobby.host_sid:
            return redirect(url_for("lobby_client", lobby_id=lobby_id))
        # Récupérer le nom de l'hôte depuis la session
        player_name = session.get(f"player_name_{lobby_id}", lobby.host_name)
        return render_template("host_dashboard.html", lobby_id=lobby_id, player_name=player_name)

    @app.get("/lobby/<lobby_id>/client")
    def lobby_client(lobby_id: str):
        _ensure_sid()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            return redirect(url_for("menu", error="unknown-lobby"))
        # Récupérer le nom du joueur depuis la session
        player_name = session.get(f"player_name_{lobby_id}", "Joueur")
        return render_template("lobby_client.html", lobby_id=lobby_id, player_name=player_name)

    @app.get("/lobby/<lobby_id>/podium")
    def lobby_podium(lobby_id: str):
        """Page du podium final"""
        _ensure_sid()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            return redirect(url_for("menu", error="unknown-lobby"))
        if lobby.phase != "finished":
            # Si pas fini, rediriger vers la page appropriée
            if session.get("sid") == lobby.host_sid:
                return redirect(url_for("lobby_host", lobby_id=lobby_id))
            else:
                return redirect(url_for("lobby_client", lobby_id=lobby_id))
        return render_template("podium_final.html", lobby_id=lobby_id)

    # Socket.IO events
    def _emit_state(lobby: RealtimeLobby) -> None:
        socketio.emit("state", lobby.snapshot(), room=lobby.lobby_id)

    def _is_host(lobby: RealtimeLobby) -> bool:
        return session.get("sid") == lobby.host_sid

    @socketio.on("join_lobby")
    def _ws_join(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        role = (data.get("role") or "player").strip()
        player_name = (data.get("player_name") or "Joueur").strip()[:24]
        socket_sid = request.sid  # SocketIO session ID unique
        
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "Lobby invalide"})
            return
        
        # Pour les joueurs : utiliser le SID de session si possible pour éviter les ré-entrées frauduleuses
        # (fallback sur socket id si pas de session). Pour l'host : utiliser le SID de session Flask
        if role == "player":
            session_sid = session.get("sid")
            sid = session_sid or socket_sid

            # Si ce SID est banni (éliminé), forcer le spectateur
            # Check if the player is banned by sid or IP
            banned_ip = request.remote_addr
            if sid in lobby.banned_sids or (banned_ip and banned_ip in lobby.banned_sids):
                # Joindre la room mais ne pas ajouter comme joueur actif
                join_room(lobby_id)
                emit("force_spectator", {"message": "Vous êtes éliminé — mode spectateur"})
                # Envoyer l'état courant
                emit("state", lobby.snapshot())
                # Ne pas ajouter le joueur
                return

            try:
                lobby.add_player(sid, player_name, socket_sid)
            except ValueError as e:
                emit("error_msg", {"error": str(e)})
                return
        else:
            # Host
            sid = session.get("sid")
            if not sid or sid != lobby.host_sid:
                emit("error_msg", {"error": "Host uniquement"})
                return
            # Mettre à jour le socket_id du host
            if sid in lobby.players:
                lobby.players[sid].socket_id = socket_sid
            
        join_room(lobby_id)
        # Envoyer l'état actuel du lobby au client
        emit("state", lobby.snapshot())
        # Notifier tous les autres clients du lobby
        socketio.emit("state", lobby.snapshot(), room=lobby_id, skip_sid=request.sid)

    @socketio.on("player_answer")
    def _ws_player_answer(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        choice = data.get("choice")
        sid = request.sid  # Utiliser socket_sid
        lobby = rt_lobbies.get(lobby_id)
        if not sid or not lobby:
            emit("error_msg", {"error": "Lobby ou session invalide"})
            return
        lobby.answer(sid, choice)
        _emit_state(lobby)

    @socketio.on("player_bets")
    def _ws_player_bets(payload):
        """Handler pour les mises des joueurs"""
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        bets = data.get("bets", {})
        sid = request.sid  # Utiliser socket_sid
        lobby = rt_lobbies.get(lobby_id)
        if not sid or not lobby:
            emit("error_msg", {"error": "Lobby ou session invalide"})
            return
            
        # Trouver le joueur par son socket_id dans lobby.players (clé peut être autre chose que socket_id)
        target_sid = None
        for pid, p in lobby.players.items():
            if p.socket_id == sid:
                target_sid = pid
                break
        
        if target_sid:
            lobby.place_bets(target_sid, bets)
        else:
            # Fallback (devrait pas arriver si logique de connection OK)
            lobby.place_bets(sid, bets)

        # Ne pas valider automatiquement pour laisser le temps aux joueurs de modifier leurs mises
        # La validation se fera à la fin du timer (_ticker) ou par forcage hote
        
        _emit_state(lobby)

    @socketio.on("host_start")
    def _ws_host_start(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        
        # Initialiser le jeu ET lancer automatiquement la première question
        lobby.start_game(list(engine._questions)[:lobby.question_total])
        lobby.launch_question()
        
        # Émettre les événements dans le bon ordre : 1. game_started, 2. state, 3. new_question
        socketio.emit("game_started", {}, room=lobby_id)
        _emit_state(lobby)  # Envoyer l'état AVANT l'animation
        socketio.emit("new_question", {}, room=lobby_id)

    @socketio.on("host_launch_question")
    def _ws_host_launch(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        lobby.launch_question()
        # Émettre dans le bon ordre : état puis animation
        _emit_state(lobby)
        socketio.emit("new_question", {}, room=lobby_id)

    @socketio.on("host_pause")
    def _ws_host_pause(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        lobby.pause()
        _emit_state(lobby)

    @socketio.on("host_resume")
    def _ws_host_resume(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        lobby.resume()
        _emit_state(lobby)

    @socketio.on("host_force_validate")
    def _ws_host_validate(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        lobby.validate()
        # Émettre l'événement de révélation de la réponse
        socketio.emit(
            "reveal_answer",
            {"correct": lobby.correct, "question_index": lobby.question_index},
            room=lobby_id,
        )
        _emit_state(lobby)

    @socketio.on("host_reveal_answer")
    def _ws_host_reveal(payload):
        """Révéler la réponse (alias pour host_force_validate)"""
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        # Si le jeu est toujours en cours, valider et révéler
        if lobby.phase == "question":
            lobby.validate()
            socketio.emit(
                "reveal_answer",
                {"correct": lobby.correct, "question_index": lobby.question_index},
                room=lobby_id,
            )
            _emit_state(lobby)

    @socketio.on("host_next_question")
    def _ws_host_next(payload):
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        
        lobby.next_question()
        
        # Si on a une nouvelle question, la lancer automatiquement avec animation
        if lobby.phase != "finished":
            lobby.launch_question()
            _emit_state(lobby)
            socketio.emit("new_question", {}, room=lobby_id)
        else:
            # Jeu terminé - émettre l'événement de fin
            _emit_state(lobby)
            socketio.emit("game_ended", {"lobby_id": lobby_id}, room=lobby_id)

    @socketio.on("host_kick_player")
    def _ws_host_kick(payload):
        """Exclure un joueur du lobby"""
        data = payload or {}
        lobby_id = (data.get("lobby_id") or "").strip()
        player_name = (data.get("player_name") or "").strip()
        
        lobby = rt_lobbies.get(lobby_id)
        if not lobby:
            emit("error_msg", {"error": "unknown-lobby"})
            return
        if not _is_host(lobby):
            emit("error_msg", {"error": "Host uniquement"})
            return
        
        # Trouver et supprimer le joueur
        player_to_kick = None
        for sid, player in list(lobby.players.items()):
            if player.name == player_name:
                player_to_kick = sid
                break
        
        if player_to_kick:
            del lobby.players[player_to_kick]
            _emit_state(lobby)
            socketio.emit("player_kicked", {"player_name": player_name}, room=lobby_id)

    def _ticker() -> None:
        while True:
            try:
                for lobby in rt_lobbies.all().values():
                    if lobby.phase == "question" and (lobby.time_remaining() or 0) <= 0:
                        lobby.validate()
                        # Émettre l'événement de révélation de la réponse
                        socketio.emit(
                            "reveal_answer",
                            {"correct": lobby.correct, "question_index": lobby.question_index},
                            room=lobby.lobby_id,
                        )
                        _emit_state(lobby)
                    socketio.emit("tick", {"time_remaining": lobby.time_remaining()}, room=lobby.lobby_id)
            except Exception:
                pass
            socketio.sleep(1)

    socketio.start_background_task(_ticker)

    @app.post("/lobby/start")
    def lobby_start():
        sid = session.get("sid")
        data = request.form or request.get_json() or {}
        lobby_id = data.get("lobby_id")
        if not lobby_id:
            return jsonify({"ok": False, "error": "missing lobby_id"}), 400
        lobby = lobbies.get(lobby_id)
        if not lobby:
            return jsonify({"ok": False, "error": "unknown-lobby"}), 404

        try:
            lobby.start()
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        return jsonify({"ok": True})

    @app.get("/lobby/state")
    def lobby_state():
        sid = session.get("sid")
        lobby_id = request.args.get("lobby_id")
        if not sid or not lobby_id:
            return jsonify({"ok": False, "error": "missing"}), 400
        lobby = lobbies.get(lobby_id)
        if not lobby:
            return jsonify({"ok": False, "error": "unknown-lobby"}), 404
        return jsonify({"ok": True, "state": lobby.player_view(sid)})

    @app.post("/lobby/bet")
    def lobby_bet():
        sid = session.get("sid")
        data = request.get_json(force=True, silent=True) or {}
        lobby_id = data.get("lobby_id")
        if not sid or not lobby_id:
            return jsonify({"ok": False, "error": "missing"}), 400
        lobby = lobbies.get(lobby_id)
        if not lobby:
            return jsonify({"ok": False, "error": "unknown-lobby"}), 404

        bets = {k: int(data.get(k, 0)) for k in ["A", "B", "C", "D"]}
        try:
            lobby.submit(sid, bets)
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400

        return jsonify({"ok": True, "state": lobby.player_view(sid)})

    @app.post("/reset")
    def reset():
        sid = session.get("sid")
        if sid:
            sessions.delete(sid)
        session.pop("sid", None)
        return redirect(url_for("index"))

    @app.get("/api/state")
    def api_state():
        sid, game = _require_session()
        q = game.current_question()

        payload = {
            "player": {"name": game.player.name, "chips": game.player.chips},
            "progress": {"index": game.index, "total": len(game.questions)},
            "finished": bool(game.finished),
            "eliminated": bool(game.eliminated),
            "leaderboard": leaderboard.top(10),
        }

        if q is None:
            result = game.result()
            leaderboard.update(result.player_name, result.final_chips, result.correct_answers)
            payload["result"] = {
                "final_chips": result.final_chips,
                "correct_answers": result.correct_answers,
                "questions_played": result.questions_played,
            }
            payload["leaderboard_text"] = leaderboard.render(10)
            return jsonify(payload)

        payload["question"] = {
            "category": q.category,
            "prompt": q.prompt,
            "answers": q.answers,
        }
        return jsonify(payload)

    @app.post("/api/bet")
    def api_bet():
        sid, game = _require_session()
        data = request.get_json(force=True, silent=True) or {}

        def _to_int(x):
            try:
                return int(x)
            except Exception:
                return 0

        bets = {
            "A": _to_int(data.get("A", 0)),
            "B": _to_int(data.get("B", 0)),
            "C": _to_int(data.get("C", 0)),
            "D": _to_int(data.get("D", 0)),
        }

        try:
            resolution = game.submit_bets(bets)
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400

        # Si fin après cette réponse : mise à jour classement
        if game.finished or game.eliminated:
            result = game.result()
            leaderboard.update(result.player_name, result.final_chips, result.correct_answers)

        return jsonify(
            {
                "ok": True,
                "resolution": {
                    "correct": resolution.correct,
                    "correct_label": resolution.correct_label,
                    "kept": resolution.kept,
                    "lost": resolution.lost,
                    "bet_total": resolution.bet_total,
                    "unbet": resolution.unbet,
                    "explanation": resolution.explanation,
                    "correct_bet": resolution.correct_bet,
                },
                "player": {"chips": game.player.chips},
                "finished": bool(game.finished),
                "eliminated": bool(game.eliminated),
                "leaderboard_text": leaderboard.render(10),
            }
        )

    @app.get("/api/leaderboard")
    def api_leaderboard():
        return jsonify({"text": leaderboard.render(10)})

    # Expose socketio for __main__
    app.socketio = socketio  # type: ignore[attr-defined]
    return app


if __name__ == "__main__":
    app = create_app()
    host = os.environ.get("MONEYDROP_HOST", "127.0.0.1")
    port = int(os.environ.get("MONEYDROP_PORT", "8000"))
    # Socket.IO must run the server (use the instance that registered handlers)
    app.socketio.run(app, host=host, port=port, debug=True, use_reloader=False)  # type: ignore[attr-defined]
