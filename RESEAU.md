# Configuration pour jeu en réseau local

## Pour jouer entre plusieurs PC

### Sur le PC serveur (celui qui lance le jeu)

1. Lancez l'application:
```bash
bash scripts/start.sh
```

2. Vous verrez l'IP locale s'afficher:
```
🌐 Accédez au serveur via: http://192.168.x.x:8001
💡 Partagez cette adresse IP avec vos amis pour qu'ils se connectent à distance!
```

3. Partagez cette adresse avec vos amis (ex: `http://192.168.1.100:8001`)

### Sur les PC clients (les amis)

1. Clonez le dépôt git:
```bash
git clone <repo-url> Money-Drop
cd Money-Drop
```

2. Ouvrez votre navigateur et accédez à l'adresse du serveur:
```
http://192.168.1.100:8001
```
(remplacez par l'IP réelle donnée par le serveur)

3. Créez un salon ou rejoignez celui créé par l'hôte

## Configuration personnalisée

### Changer le port

```bash
MONEYDROP_PORT=9000 bash scripts/start.sh
```

### Changer l'adresse d'écoute (avancé)

```bash
MONEYDROP_HOST=192.168.1.100 MONEYDROP_PORT=8001 bash scripts/start.sh
```

## Dépannage

### Je ne vois pas les salons créés sur un autre PC

- Vérifiez que les deux PC sont sur le **même réseau**
- Vérifiez que le **pare-feu** ne bloque pas le port 8001
- Vérifiez l'adresse IP affichée au démarrage du serveur

### Impossible de se connecter

1. Vérifiez que le serveur est bien lancé (il devrait dire "Started")
2. Testez: `ping <IP-DU-SERVEUR>`
3. Testez dans le navigateur: `http://<IP>:8001/menu`
4. Vérifiez les logs: `tail -f /tmp/md_web.log`

### Les salons ne se synchronisent pas

C'est peut-être un problème de réseau local. Essayez:
- Redémarrez le routeur WiFi
- Utilisez une connexion Ethernet si possible
- Vérifiez que les PC ne sont pas en VPN
