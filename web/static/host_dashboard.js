(function(){
  const lobbyId = window.LOBBY_ID;
  const playerName = window.PLAYER_NAME || 'Host';
  
  // State management
  let currentState = {
    phase: 'waiting',
    question_index: 0,
    question_total: 0,
    time_remaining: 0,
    question: null,
    players: [],
    correct: null
  };

  // Music
  const countdownMusic = new Audio('/static/musique_décompte.mp3');
  countdownMusic.loop = true;
  countdownMusic.volume = 0.5;
  let musicPlaying = false;

  // Socket connection
  const socket = io(window.location.origin, { transports: ['websocket','polling'] });

  // ========================================
  // SOCKET EVENTS
  // ========================================
  socket.on('connect', () => {
    socket.emit('join_lobby', { lobby_id: lobbyId, role: 'host', player_name: playerName });
  });

  socket.on('error_msg', (p) => setMessage(p?.error || 'Erreur'));
  socket.on('state', (state) => {
    currentState = state;
    render(state);
  });

  socket.on('game_ended', (data) => {
    console.log('🎊 Jeu terminé ! Redirection...');
    setTimeout(() => {
      window.location.href = `/lobby/${lobbyId}/podium?lobby_id=${lobbyId}`;
    }, 1500);
  });

  socket.on('tick', (p) => {
    const timeRemaining = p?.time_remaining ?? 0;
    const el = document.getElementById('timeRemaining');
    if(el) el.textContent = String(timeRemaining);

    // Gestion musique décompte
    if(timeRemaining > 0 && currentState.phase === 'question' && !musicPlaying) {
      countdownMusic.play().catch(e => console.log('Musique non disponible'));
      musicPlaying = true;
    } else if((timeRemaining <= 0 || currentState.phase !== 'question') && musicPlaying) {
      countdownMusic.pause();
      countdownMusic.currentTime = 0;
      musicPlaying = false;
    }
  });

  // ========================================
  // RENDER FUNCTION
  // ========================================
  function render(state) {
    updatePhaseStatus(state.phase);
    updateGameInfo(state);
    updateQuestion(state);
    updateLeaderboard(state.players || []);
    updatePlayersList(state.players || []);
    updateButtonsUI(state);
  }

  function updatePhaseStatus(phase) {
    const badge = document.getElementById('statusBadge');
    const phaseMap = {
      'waiting': { text: '⏳ En attente...', class: 'waiting' },
      'question': { text: '❓ Question en cours', class: 'question' },
      'results': { text: '✓ Résultats', class: 'results' },
      'finished': { text: '🎊 Partie terminée', class: 'finished' }
    };
    const info = phaseMap[phase] || phaseMap['waiting'];
    badge.textContent = info.text;
    badge.className = `host-status-badge ${info.class}`;
  }

  function updateGameInfo(state) {
    document.getElementById('phase').textContent = state.phase;
    document.getElementById('qIndex').textContent = String((state.question_index ?? 0) + 1);
    document.getElementById('qTotal').textContent = String(state.question_total ?? '-');
    
    // Arrêter la musique si pas en question
    if(state.phase !== 'question' && musicPlaying) {
      countdownMusic.pause();
      countdownMusic.currentTime = 0;
      musicPlaying = false;
    }
  }

  function updateQuestion(state) {
    const qBox = document.getElementById('questionBox');
    const answersEl = document.getElementById('answers');
    
    if(!state.question || state.phase === 'waiting') {
      qBox.style.display = 'none';
      return;
    }

    qBox.style.display = 'block';
    document.getElementById('category').textContent = state.question?.category ?? '';
    document.getElementById('prompt').textContent = state.question?.prompt ?? '';

    answersEl.innerHTML = '';
    const answers = state.question?.answers || {};
    
    for(const key of ['A','B','C','D']) {
      if(!answers[key]) continue;

      const div = document.createElement('div');
      div.className = 'answer-card';
      
      // Highlight correct answer
      if(state.phase === 'results' && state.correct === key) {
        div.classList.add('correct');
      }

      // Calculate stats
      const playersBet = currentState.players?.filter(p => p.choice === key) || [];
      const totalBet = playersBet.length;
      const totalMoneyBet = playersBet.reduce((sum, p) => sum + (p.bets?.[key] || 0), 0);

      div.innerHTML = `
        <div class="answer-key">${key}</div>
        <div class="answer-text">${escapeHtml(answers[key])}</div>
        <div class="answer-stats">
          ${totalBet > 0 ? `<span class="answer-stat-badge">👥 ${totalBet} joueur${totalBet > 1 ? 's' : ''}</span>` : '<span style="color: #666;">Aucun pari</span>'}
        </div>
      `;
      answersEl.appendChild(div);
    }
  }

  function updateLeaderboard(players) {
    const lb = document.getElementById('leaderboard');
    lb.innerHTML = '';

    const sorted = [...players].sort((a,b) => b.score - a.score);
    sorted.forEach((p, idx) => {
      const rank = idx + 1;
      const item = document.createElement('div');
      item.className = `leaderboard-item ${idx === 0 ? 'top1' : idx === 1 ? 'top2' : idx === 2 ? 'top3' : ''}`;
      
      let medal = `#${rank}`;
      if(rank === 1) medal = '🥇';
      else if(rank === 2) medal = '🥈';
      else if(rank === 3) medal = '🥉';

      item.innerHTML = `
        <div class="lb-rank">${medal}</div>
        <div class="lb-name">${escapeHtml(p.name)}</div>
        <div class="lb-score">${p.score} €</div>
      `;
      lb.appendChild(item);
    });
  }

  function updatePlayersList(players) {
    const list = document.getElementById('playersList');
    list.innerHTML = '';

    players.forEach(p => {
      const item = document.createElement('div');
      item.className = 'player-item';
      item.innerHTML = `
        <div class="player-info">
          <div class="player-name">${escapeHtml(p.name)}</div>
          <div class="player-score">${p.score} € • ${p.choice ? `Choix: ${p.choice}` : 'En attente'}</div>
        </div>
        <div class="player-actions">
          <button class="btn-kick" data-player="${escapeHtml(p.name)}" title="Exclure ce joueur">⛔</button>
        </div>
      `;
      list.appendChild(item);
    });

    // Attach kick handlers
    document.querySelectorAll('.btn-kick').forEach(btn => {
      btn.onclick = (e) => {
        const playerName = btn.dataset.player;
        if(confirm(`Exclure ${playerName} ?`)) {
          socket.emit('host_kick_player', { lobby_id: lobbyId, player_name: playerName });
          setMessage(`${playerName} a été exclu.`);
        }
      };
    });

    // Update players count
    const header = document.querySelector('.host-players-sidebar h2');
    if(header) {
      header.textContent = `👥 Joueurs (${players.length})`;
    }
  }

  // ========================================
  // BUTTONS LOGIC
  // ========================================
  function updateButtonsUI(state) {
    const container = document.getElementById('buttonContainer');
    container.innerHTML = '';

    const buttons = getButtonsForPhase(state.phase);
    buttons.forEach(btn => {
      const el = document.createElement('button');
      el.className = `host-btn ${btn.className}`;
      el.textContent = btn.label;
      el.disabled = btn.disabled || false;
      el.onclick = btn.onClick;
      container.appendChild(el);
    });
  }

  function getButtonsForPhase(phase) {
    const buttons = [];

    switch(phase) {
      case 'waiting':
        buttons.push({
          label: '▶️ Lancer la partie',
          className: 'host-btn-primary',
          onClick: () => socket.emit('host_start', { lobby_id: lobbyId })
        });
        break;

      case 'question':
        buttons.push({
          label: '⏸️ Pause',
          className: 'host-btn-secondary',
          onClick: () => socket.emit('host_pause', { lobby_id: lobbyId })
        });
        buttons.push({
          label: '🎯 Révéler la réponse',
          className: 'host-btn-primary',
          onClick: () => {
            socket.emit('host_reveal_answer', { lobby_id: lobbyId });
            setMessage('Réponse révélée !');
          }
        });
        break;

      case 'results':
        buttons.push({
          label: '⏸️ Pause',
          className: 'host-btn-secondary',
          onClick: () => socket.emit('host_pause', { lobby_id: lobbyId })
        });
        buttons.push({
          label: '➡️ Question suivante',
          className: 'host-btn-primary',
          onClick: () => {
            socket.emit('host_next_question', { lobby_id: lobbyId });
            setMessage('Question suivante...');
          }
        });
        break;

      case 'paused':
        buttons.push({
          label: '▶️ Reprendre',
          className: 'host-btn-primary',
          onClick: () => socket.emit('host_resume', { lobby_id: lobbyId })
        });
        break;

      case 'finished':
        buttons.push({
          label: '🏁 Partie terminée',
          className: 'host-btn-secondary',
          disabled: true
        });
        break;
    }

    return buttons;
  }

  // ========================================
  // UTILITIES
  // ========================================
  function setMessage(msg) {
    const el = document.getElementById('hostMsg');
    if(el) {
      el.textContent = msg;
      el.style.animation = 'none';
      setTimeout(() => {
        el.style.animation = 'slideInLeft 0.3s ease-out';
      }, 10);
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'",'&#39;');
  }

  // ========================================
  // SETTINGS
  // ========================================
  document.getElementById('maxPlayers').addEventListener('change', (e) => {
    const maxPlayers = parseInt(e.target.value);
    console.log('Max players set to:', maxPlayers);
    // À implémenter côté serveur si nécessaire
  });

  document.getElementById('questionTimer').addEventListener('change', (e) => {
    const timer = parseInt(e.target.value);
    console.log('Question timer set to:', timer);
    // À implémenter côté serveur si nécessaire
  });
})();
