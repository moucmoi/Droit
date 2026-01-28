# Money Drop - Interface Web

## Installation

```bash
cd "/home/iut45/Etudiants/o22300674/Documents/BUT3/Money Drop"
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Lancer

```bash
. .venv/bin/activate
python3 web_app.py
```

Ouvre ensuite : http://127.0.0.1:8000

## Multijoueur

- Ouvre plusieurs onglets / navigateurs
- Chaque onglet démarre une session (partie) indépendante
- Le classement global est partagé et persistant (`data/leaderboard.json`)
