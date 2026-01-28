// ========================================
// PODIUM FINAL - Money Drop
// Gestion de l'affichage du podium
// ========================================

let socket = null;
let lobbyId = null;

/**
 * Récupère l'ID du lobby depuis l'URL
 */
function getLobbyIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('lobby_id');
}

/**
 * Crée des confettis animés
 */
function createConfetti() {
  const container = document.getElementById('confettiContainer');
  if (!container) return;

  const confettiCount = 60;
  const colors = ['#ffd700', '#ffed4e', '#ff6b6b', '#4ade80', '#60a5fa', '#a855f7', '#ff85c0'];

  for (let i = 0; i < confettiCount; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';

    const left = Math.random() * 100;
    const delay = Math.random() * 0.5;
    const duration = 2.5 + Math.random() * 1.5;
    const color = colors[Math.floor(Math.random() * colors.length)];

    piece.style.left = left + '%';
    piece.style.top = '-20px';
    piece.style.backgroundColor = color;
    piece.style.animation = `confettiFall ${duration}s ease-out ${delay}s forwards`;

    container.appendChild(piece);
  }
}

/**
 * Joue un son de victoire
 */
function playVictorySound() {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const notes = [800, 1000, 1200, 1400];
    let time = audioContext.currentTime;

    for (const freq of notes) {
      const osc = audioContext.createOscillator();
      const gain = audioContext.createGain();

      osc.connect(gain);
      gain.connect(audioContext.destination);

      osc.frequency.setValueAtTime(freq, time);
      gain.gain.setValueAtTime(0.2, time);
      gain.gain.setValueAtTime(0, time + 0.15);

      osc.start(time);
      osc.stop(time + 0.15);

      time += 0.15;
    }
  } catch (e) {
    // Audio context might not work
  }
}

/**
 * Met à jour le podium avec les données des joueurs
 */
function updatePodium(players) {
  // Trier par score (jetons)
  // Filtrer les joueurs valides (nom non vide)
  const filtered = (players || []).filter(p => p && typeof p.name === 'string');
  // Trier par score décroissant
  const sorted = [...filtered].sort((a, b) => (b.score || 0) - (a.score || 0));

  // Top 3 podium
  const first = sorted[0];
  const second = sorted[1];
  const third = sorted[2];

  // Avatar dynamique (initiale du nom)
  function avatarHtml(player) {
    if (!player || !player.name) return '👤';
    return `<span class="player-avatar-circle">${player.name[0].toUpperCase()}</span>`;
  }

  // 1er
  document.getElementById('rank1Name').textContent = first ? first.name : '--';
  document.getElementById('rank1Score').textContent = first ? (first.score || 0).toLocaleString('fr-FR') + ' €' : '0 €';
  document.querySelector('.pos-1 .player-avatar').innerHTML = first ? avatarHtml(first) : '👤';
  // 2e
  document.getElementById('rank2Name').textContent = second ? second.name : '--';
  document.getElementById('rank2Score').textContent = second ? (second.score || 0).toLocaleString('fr-FR') + ' €' : '0 €';
  document.querySelector('.pos-2 .player-avatar').innerHTML = second ? avatarHtml(second) : '👤';
  // 3e
  document.getElementById('rank3Name').textContent = third ? third.name : '--';
  document.getElementById('rank3Score').textContent = third ? (third.score || 0).toLocaleString('fr-FR') + ' €' : '0 €';
  document.querySelector('.pos-3 .player-avatar').innerHTML = third ? avatarHtml(third) : '👤';

  // Classement complet
  updateFullRanking(sorted);
}

/**
 * Met à jour le classement complet
 */
function updateFullRanking(players) {
  const container = document.getElementById('rankingList');
  if (!container) return;

  container.innerHTML = '';

  players.forEach((player, index) => {
    const item = document.createElement('div');
    item.className = 'ranking-item';
    item.style.setProperty('--index', index);

    const rank = index + 1;
    let medal = '⭐';
    if (rank === 1) medal = '🥇';
    else if (rank === 2) medal = '🥈';
    else if (rank === 3) medal = '🥉';
    else medal = `#${rank}`;

    item.innerHTML = `
      <div class="ranking-pos">${medal}</div>
      <div class="ranking-avatar">${player && player.name ? player.name[0].toUpperCase() : '👤'}</div>
      <div class="ranking-name">${escapeHtml(player.name || 'Joueur')}</div>
      <div class="ranking-score">${(player.score || 0).toLocaleString('fr-FR')} €</div>
    `;

    container.appendChild(item);
  });
}

/**
 * Échappe les caractères HTML
 */
function escapeHtml(str) {
  return str
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/**
 * Initialise la page du podium
 */
function initPodium() {
  lobbyId = getLobbyIdFromUrl();

  if (!lobbyId) {
    console.error('Pas de lobby_id dans l\'URL');
    setTimeout(() => {
      window.location.href = '/menu';
    }, 2000);
    return;
  }

  // Créer le socket avec les bonnes options
  if (!socket) {
    socket = io({
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5
    });
  }

  socket.on('connect', () => {
    console.log('WebSocket connecté, socket id:', socket.id);

    socket.emit('join_lobby', {
      lobby_id: lobbyId,
      role: 'viewer',
      player_name: 'Spectateur',
    });
  });

  socket.on('state', (state) => {
    console.log('État reçu:', state);

    // Afficher toujours les joueurs et leurs scores, peu importe la phase
    if (state && state.players && state.players.length > 0) {
      updatePodium(state.players);

      // Déclencher les effets seulement si la partie est finie
      if (state.phase === 'finished' && !window.podiumShown) {
        window.podiumShown = true;
        setTimeout(() => {
          createConfetti();
          playVictorySound();
        }, 500);
      }
    }
  });

  socket.on('error_msg', (data) => {
    console.error('Erreur:', data.error);
  });

  socket.on('disconnect', () => {
    console.log('WebSocket déconnecté');
  });

  socket.on('connect_error', (error) => {
    console.error('Erreur de connexion WebSocket:', error);
  });
}

// Initialiser quand la page est prête
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPodium);
} else {
  initPodium();
}
