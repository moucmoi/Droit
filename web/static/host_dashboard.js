(function () {
  const lobbyId = window.LOBBY_ID;
  const playerName = window.PLAYER_NAME || 'Host';

  let currentState = {
    phase: 'waiting',
    question_index: 0,
    question_total: 0,
    time_remaining: 0,
    question: null,
    players: [],
    correct: null,
  };

  function el(id) {
    return document.getElementById(id);
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function setMessage(msg) {
    const node = el('hostMsg');
    if (node) node.textContent = msg || '';
  }

  // Tick-tock during the question phase (same audio as the client)
  const countdownMusic = new Audio('/static/musique_d%C3%A9compte.mp3');
  countdownMusic.loop = true;
  countdownMusic.volume = 0.45;
  let musicPlaying = false;
  function musicStart(){
    if(musicPlaying) return;
    countdownMusic.play().catch(() => {});
    musicPlaying = true;
  }
  function musicStop(){
    if(!musicPlaying) return;
    countdownMusic.pause();
    countdownMusic.currentTime = 0;
    musicPlaying = false;
  }

  // Socket
  const socket = io(window.location.origin, { transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    socket.emit('join_lobby', { lobby_id: lobbyId, role: 'host', player_name: playerName });
  });

  socket.on('error_msg', (p) => setMessage((p && p.error) || 'Erreur'));

  socket.on('state', (state) => {
    currentState = state || currentState;
    render(currentState);
    if (currentState.phase === 'question') musicStart();
    else musicStop();
  });

  socket.on('tick', (p) => {
    const t = el('timeRemaining');
    if (t) t.textContent = String((p && p.time_remaining) || 0);
    if (currentState.phase === 'question') musicStart();
    else musicStop();
  });

  socket.on('game_ended', () => {
    setMessage('Partie terminee.');
    musicStop();
    setTimeout(() => {
      window.location.href = `/lobby/${lobbyId}/podium?lobby_id=${encodeURIComponent(lobbyId)}`;
    }, 1200);
  });

  // Copy lobby code
  const copyBtn = el('copyCode');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(String(lobbyId || '').trim());
        setMessage('Code copie.');
      } catch (e) {
        setMessage('Copie impossible.');
      }
    });
  }

  function render(state) {
    updatePhaseStatus(state.phase);
    updateGameInfo(state);
    updateQuestion(state);
    updateLeaderboard(state.players || []);
    updatePlayersList(state.players || []);
    updateButtonsUI(state);
  }

  function updatePhaseStatus(phase) {
    const badge = el('statusBadge');
    if (!badge) return;

    const phaseMap = {
      waiting: { text: 'En attente', cls: 'is-waiting' },
      question: { text: 'Question', cls: 'is-question' },
      results: { text: 'Resultats', cls: 'is-results' },
      paused: { text: 'Pause', cls: 'is-results' },
      finished: { text: 'Terminee', cls: 'is-finished' },
    };

    const info = phaseMap[phase] || phaseMap.waiting;
    badge.textContent = info.text;
    badge.className = `pkd-badge ${info.cls}`;
  }

  function updateGameInfo(state) {
    const phaseEl = el('phase');
    const qIndexEl = el('qIndex');
    const qTotalEl = el('qTotal');

    if (phaseEl) phaseEl.textContent = String(state.phase || 'waiting');
    if (qIndexEl) qIndexEl.textContent = String((state.question_index || 0) + 1);
    if (qTotalEl) qTotalEl.textContent = String(state.question_total || '-');
  }

  function updateQuestion(state) {
    const qBox = el('questionBox');
    const answersEl = el('answers');
    const explEl = el('explanationBox');
    const noQ = el('noQuestion');

    if (!qBox || !answersEl) return;

    if (!state.question || state.phase === 'waiting') {
      qBox.style.display = 'none';
      if (noQ) noQ.style.display = 'block';
      if (explEl) explEl.style.display = 'none';
      return;
    }

    qBox.style.display = 'block';
    if (noQ) noQ.style.display = 'none';

    const category = el('category');
    const prompt = el('prompt');
    if (category) category.textContent = String(state.question.category || '');
    if (prompt) prompt.textContent = String(state.question.prompt || '');

    const players = state.players || [];
    const pot = players.reduce((sum, p) => sum + (p.bet_amount || 0), 0);
    const potEl = el('potTotal');
    if (potEl) potEl.textContent = String(pot);

    answersEl.innerHTML = '';
    const answers = (state.question && state.question.answers) || {};

    for (const key of ['A', 'B', 'C', 'D']) {
      if (!answers[key]) continue;

      const bettors = players.filter((p) => (p.answer === key) && ((p.bet_amount || 0) > 0));
      const bettorsCount = bettors.length;
      const totalMoneyBet = bettors.reduce((sum, p) => sum + (p.bet_amount || 0), 0);

      const card = document.createElement('div');
      card.className = 'pkd-answer' + (state.phase === 'results' && state.correct === key ? ' is-correct' : '');

      card.innerHTML = `
        <div class="pkd-answer-key">
          <div class="pkd-answer-letter">${key}</div>
          <div class="pkd-answer-bet">${totalMoneyBet} jetons</div>
        </div>
        <div class="pkd-answer-text">${escapeHtml(answers[key])}</div>
        <div class="pkd-answer-meta">
          <span class="pkd-pill">${bettorsCount > 0 ? bettorsCount + ' joueur' + (bettorsCount > 1 ? 's' : '') : 'Aucun pari'}</span>
        </div>
      `;

      answersEl.appendChild(card);
    }

    if (explEl) {
      const expl = (state.phase === 'results' && state.explanation) ? String(state.explanation) : '';
      if (expl) {
        explEl.style.display = 'block';
        explEl.innerHTML = `<b>Pourquoi ?</b> ${escapeHtml(expl)}`;
      } else {
        explEl.style.display = 'none';
        explEl.textContent = '';
      }
    }
  }

  function updateLeaderboard(players) {
    const lb = el('leaderboard');
    if (!lb) return;

    lb.innerHTML = '';

    const sorted = [...players].sort((a, b) => (b.score || 0) - (a.score || 0));
    sorted.forEach((p, idx) => {
      const row = document.createElement('div');
      row.className = 'pkd-lb-item';
      row.innerHTML = `
        <div class="pkd-lb-left">
          <div class="pkd-lb-rank">#${idx + 1}</div>
          <div class="pkd-lb-name">${escapeHtml(p.name || '')}</div>
        </div>
        <div class="pkd-lb-score">${p.score || 0} jetons</div>
      `;
      lb.appendChild(row);
    });
  }

  function updatePlayersList(players) {
    const list = el('playersList');
    if (!list) return;

    list.innerHTML = '';

    const header = el('playersHeader');
    if (header) header.textContent = `Joueurs (${players.length})`;

    for (const p of players) {
      const item = document.createElement('div');
      item.className = 'pkd-player';

      const action = p.action || 'check';
      const amount = p.bet_amount || 0;
      const choice = p.answer ? ` · ${p.answer}` : '';
      const betTxt = action === 'check' ? 'check' : `${action} ${amount}`;

      item.innerHTML = `
        <div class="pkd-player-main">
          <div class="pkd-player-name">${escapeHtml(p.name || '')}</div>
          <div class="pkd-player-sub">${p.score || 0} jetons · ${escapeHtml(betTxt)}${escapeHtml(choice)}</div>
        </div>
        <button class="pkd-kick" type="button" data-player="${escapeHtml(p.name || '')}">Kick</button>
      `;

      list.appendChild(item);
    }

    document.querySelectorAll('.pkd-kick').forEach((btn) => {
      btn.addEventListener('click', () => {
        const who = btn.getAttribute('data-player') || '';
        if (!who) return;
        if (!confirm(`Exclure ${who} ?`)) return;
        socket.emit('host_kick_player', { lobby_id: lobbyId, player_name: who });
        setMessage(`${who} exclu.`);
      });
    });
  }

  function updateButtonsUI(state) {
    const container = el('buttonContainer');
    if (!container) return;

    container.innerHTML = '';
    const buttons = getButtonsForPhase(state.phase);

    for (const b of buttons) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `pkd-btn ${b.className || ''}`.trim();
      button.textContent = b.label;
      button.disabled = !!b.disabled;
      button.addEventListener('click', b.onClick);
      container.appendChild(button);
    }
  }

  function getButtonsForPhase(phase) {
    const out = [];

    if (phase === 'waiting') {
      out.push({
        label: 'Lancer la partie',
        className: 'pkd-btn-primary',
        onClick: () => socket.emit('host_start', { lobby_id: lobbyId }),
      });
      return out;
    }

    if (phase === 'question') {
      out.push({
        label: 'Pause',
        className: 'pkd-btn-warn',
        onClick: () => socket.emit('host_pause', { lobby_id: lobbyId }),
      });
      out.push({
        label: 'Reveler la reponse',
        className: 'pkd-btn-primary',
        onClick: () => {
          socket.emit('host_reveal_answer', { lobby_id: lobbyId });
          setMessage('Reponse revelee.');
        },
      });
      return out;
    }

    if (phase === 'results') {
      out.push({
        label: 'Pause',
        className: 'pkd-btn-warn',
        onClick: () => socket.emit('host_pause', { lobby_id: lobbyId }),
      });
      out.push({
        label: 'Question suivante',
        className: 'pkd-btn-primary',
        onClick: () => {
          socket.emit('host_next_question', { lobby_id: lobbyId });
          setMessage('Question suivante...');
        },
      });
      return out;
    }

    if (phase === 'paused') {
      out.push({
        label: 'Reprendre',
        className: 'pkd-btn-primary',
        onClick: () => socket.emit('host_resume', { lobby_id: lobbyId }),
      });
      return out;
    }

    if (phase === 'finished') {
      out.push({ label: 'Partie terminee', className: 'pkd-btn-warn', disabled: true, onClick: () => {} });
      return out;
    }

    out.push({ label: '...', className: 'pkd-btn-warn', disabled: true, onClick: () => {} });
    return out;
  }
})();
