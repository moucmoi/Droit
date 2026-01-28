from __future__ import annotations

import argparse
import socket
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Money Drop - client console")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse serveur")
    parser.add_argument("--port", type=int, default=5050, help="Port serveur")
    args = parser.parse_args()

    with socket.create_connection((args.host, args.port)) as s:
        # Boucle simple : affiche ce que le serveur envoie,
        # et répond dès qu'on détecte un prompt (">" ou ": ").
        buf = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
            text = buf.decode("utf-8", errors="replace")
            # Afficher tout ce qu'on a
            sys.stdout.write(text)
            sys.stdout.flush()
            buf = b""

            # Heuristique : si le texte se termine par un prompt, on lit l'entrée.
            if text.endswith("> ") or text.endswith(": "):
                try:
                    user = input()
                except EOFError:
                    user = ""
                s.sendall((user + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
