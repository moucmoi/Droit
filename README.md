# Droit – squelette basé sur Money-Drop

Le backend et le frontend du projet *Money-Drop* ont été copiés ici pour servir de base.  
Le front est volontairement neutralisé : logos, titres, sous‑titres et images affichent un `placeholder` afin que vous puissiez injecter vos propres textes/visuels sans reprendre toute la structure.

## Ce qui a été fait
- Backend intact (`server.py`, `web_app.py`, package `moneydrop/`, scripts).  
- Front web copié dans `web/` avec gabarits épurés : les pages HTML utilisent `placeholder.png` (1×1 transparent) et des champs vides pour les titres/sous‑titres.  
- Les boutons, formulaires et flux temps réel restent fonctionnels pour servir de maquette.

## Règles actuelles (mode “poker-quiz”)
- Banque de départ : 1 000 € par joueur.
- À chaque question : choisir une réponse A/B/C/D puis une action :
  - `check` : aucun risque ni gain.
  - `mise` : miser un montant ≤ banque, gain net +25 % de la mise si bon, perte de la mise sinon.
  - `all-in` : miser tout ; banque ×2,25 si bon, banque à 0 sinon.

## Personnaliser le front
1. Remplacez `web/static/placeholder.png` par vos visuels ou changez les `src` des images dans `web/templates/*.html`.  
4. Si vous voulez des sons/vidéos, placez vos fichiers dans `web/static/` et ajustez les références.

## Démarrage rapide (backend inchangé)
```bash
python3 server.py --host 127.0.0.1 --port 5050
```
Puis ouvrez `web_app.py` (Flask/Socket.IO) pour servir le front :
```bash
python3 web_app.py
```
Adaptez les paramètres (questions, timer, jetons) via les options CLI ou le code.

## Organisation
- `moneydrop/` : logique métier (questions, moteur, modèles, sessions).  
- `web/` : templates Jinja + assets statiques (CSS/JS, placeholder).  
- `scripts/` : helpers de démarrage/arrêt.
