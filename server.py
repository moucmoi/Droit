from __future__ import annotations

import argparse
import socket
import threading
from typing import Tuple

from moneydrop.engine import IO, MoneyDropEngine
from moneydrop.leaderboard import Leaderboard
from moneydrop.models import GameConfig
from moneydrop.questions import build_question_bank


def _safe_send(conn: socket.socket, text: str) -> None:
    conn.sendall(text.encode("utf-8", errors="replace"))


def _readline(conn: socket.socket, prompt: str) -> str:
    _safe_send(conn, prompt)
    buf = bytearray()
    while True:
        chunk = conn.recv(1)
        if not chunk:
            # Déconnexion
            return ""
        if chunk == b"\n":
            break
        if chunk != b"\r":
            buf.extend(chunk)
    return buf.decode("utf-8", errors="replace").strip()


class PlayerSession(threading.Thread):
    def __init__(
        self,
        conn: socket.socket,
        addr: Tuple[str, int],
        engine: MoneyDropEngine,
        leaderboard: Leaderboard,
        config: GameConfig,
    ):
        super().__init__(daemon=True)
        self._conn = conn
        self._addr = addr
        self._engine = engine
        self._leaderboard = leaderboard
        self._config = config

    def run(self) -> None:
        try:
            _safe_send(self._conn, "Bienvenue sur Money Drop (serveur).\n")
            name = _readline(self._conn, "Entrez votre nom: ")
            if not name:
                return

            io = IO(
                write=lambda s: _safe_send(self._conn, s),
                read_line=lambda p: _readline(self._conn, p),
            )
            result = self._engine.run_game(name, io, self._config)
            self._leaderboard.update(result.player_name, result.final_chips, result.correct_answers)

            _safe_send(self._conn, "\n" + self._leaderboard.render(10) + "\n")
            _safe_send(self._conn, "\nMerci d'avoir joué !\n")
        except Exception as e:
            try:
                _safe_send(self._conn, f"\nErreur serveur: {e}\n")
            except Exception:
                pass
        finally:
            try:
                self._conn.close()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Money Drop - serveur multijoueur")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute")
    parser.add_argument("--port", type=int, default=5050, help="Port d'écoute")
    parser.add_argument("--start", type=int, default=1000, help="Jetons de départ")
    parser.add_argument("--questions", type=int, default=7, help="Nombre de questions")
    parser.add_argument(
        "--leaderboard",
        default="data/leaderboard.json",
        help="Fichier JSON de classement",
    )
    args = parser.parse_args()

    leaderboard = Leaderboard(args.leaderboard)
    engine = MoneyDropEngine(build_question_bank())
    config = GameConfig(starting_chips=args.start, question_count=args.questions)

    print(f"[server] Listening on {args.host}:{args.port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((args.host, args.port))
        s.listen()

        while True:
            conn, addr = s.accept()
            print(f"[server] Connexion: {addr[0]}:{addr[1]}")
            PlayerSession(conn, addr, engine, leaderboard, config).start()


if __name__ == "__main__":
    main()
