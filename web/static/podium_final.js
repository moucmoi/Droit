(function () {
  function getLobbyIdFromUrl() {
    const qs = new URLSearchParams(window.location.search);
    return qs.get('lobby_id') || null;
  }

  function esc(str) {
    return String(str || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  const lobbyId = getLobbyIdFromUrl();
  const note = document.getElementById('podiumNote');
  const audio = document.getElementById('victoryAudio');

  let played = false;

  function setTop3(players) {
    const sorted = [...(players || [])]
      .filter((p) => p && typeof p.name === 'string')
      .sort((a, b) => (b.score || 0) - (a.score || 0));

    const first = sorted[0];
    const second = sorted[1];
    const third = sorted[2];

    const r1n = document.getElementById('rank1Name');
    const r1s = document.getElementById('rank1Score');
    const r2n = document.getElementById('rank2Name');
    const r2s = document.getElementById('rank2Score');
    const r3n = document.getElementById('rank3Name');
    const r3s = document.getElementById('rank3Score');

    if (r1n) r1n.textContent = first ? first.name : '--';
    if (r1s) r1s.textContent = String(first ? (first.score || 0) : 0);

    if (r2n) r2n.textContent = second ? second.name : '--';
    if (r2s) r2s.textContent = String(second ? (second.score || 0) : 0);

    if (r3n) r3n.textContent = third ? third.name : '--';
    if (r3s) r3s.textContent = String(third ? (third.score || 0) : 0);
  }

  function tryPlayAudio() {
    if (played) return;
    played = true;
    if (!audio) return;
    audio.currentTime = 0;
    audio.play().catch(() => {
      // Autoplay might be blocked; user can still manually start via browser controls.
      if (note) note.textContent = 'Podium affiche. Clique pour activer le son si besoin.';
    });
  }

  if (!lobbyId) {
    if (note) note.textContent = 'Erreur: lobby_id manquant.';
    setTimeout(() => {
      window.location.href = '/';
    }, 1200);
    return;
  }

  const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 800,
    reconnectionDelayMax: 4000,
  });

  socket.on('connect', () => {
    socket.emit('join_lobby', {
      lobby_id: lobbyId,
      role: 'viewer',
      player_name: 'Spectateur',
    });
  });

  socket.on('state', (state) => {
    if (!state || !state.players) return;

    setTop3(state.players);

    if (state.phase === 'finished') {
      if (note) note.textContent = 'Partie terminee.';
      tryPlayAudio();
    } else {
      if (note) note.textContent = 'En attente de la fin de partie...';
    }
  });

  socket.on('error_msg', (p) => {
    if (note) note.textContent = 'Erreur: ' + esc(p && p.error);
  });
})();
