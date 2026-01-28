(function(){
  const lobbyId = window.LOBBY_ID;
  const msgEl = document.getElementById('clientMsg');

  let currentState = null;
  let selected = null;

  function setMsg(t){ msgEl.textContent = t || ''; }

  // Connexion SocketIO sur le même host que la page
  const socket = io(window.location.origin, { transports: ['websocket','polling'] });

  socket.on('connect', () => {
    socket.emit('join_lobby', { lobby_id: lobbyId, role: 'player' });
  });

  socket.on('error_msg', (p) => setMsg(p?.error || 'Erreur'));
  socket.on('state', (state) => {
    currentState = state;
    render(state);
  });
  socket.on('tick', (p) => {
    const el = document.getElementById('timerText');
    if(el) el.textContent = String(p?.time_remaining ?? '-');
    updateTimerProgress(p?.time_remaining ?? 0);
  });

  function render(state){
    // Afficher le nombre de joueurs
    document.getElementById('playerCount').textContent = String(state.players?.length || 0);
    document.getElementById('qCounter').textContent = String(state.question_index + 1 || '-');
    document.getElementById('category').textContent = state.question?.category ?? '';
    document.getElementById('prompt').textContent = state.question?.prompt ?? (state.phase === 'waiting' ? 'En attente du démarrage...' : '');
    document.getElementById('timerText').textContent = String(state.time_remaining ?? '-');

    // Afficher les réponses
    const answersKeys = ['A','B','C','D'];
    answersKeys.forEach(k => {
      const ansEl = document.getElementById('ans'+k);
      const textEl = document.getElementById('text'+k);
      if(state.question?.answers?.[k]){
        ansEl.style.display = '';
        textEl.textContent = state.question.answers[k];
        ansEl.classList.remove('correct', 'wrong', 'selected');
        
        if(selected === k) ansEl.classList.add('selected');
        if(state.phase === 'results' && state.correct){
          if(k === state.correct) ansEl.classList.add('correct');
          else if(selected === k) ansEl.classList.add('wrong');
        }
      } else {
        ansEl.style.display = 'none';
      }
    });

    // Afficher les joueurs avec leurs choix
    const players = document.getElementById('players');
    players.innerHTML = '';
    for(const p of (state.players || [])){
      const row = document.createElement('div');
      row.className = 'md-player';
      row.innerHTML = `
        <div class="md-player-name">${escapeHtml(p.name)}</div>
        <div class="md-player-score">${p.score} pts</div>
        ${p.choice ? `<div class="md-player-choice">→ ${p.choice}</div>` : ''}
      `;
      players.appendChild(row);
    }

    // Messages selon la phase
    if(state.phase === 'waiting'){
      setMsg('En attente du démarrage...');
    } else if(state.phase === 'question'){
      setMsg('Cliquez sur une réponse');
    } else if(state.phase === 'results'){
      setMsg(state.correct ? `✓ Réponse correcte: ${state.correct}` : '✗ Résultats');
    } else if(state.phase === 'paused'){
      setMsg('Pause...');
    } else if(state.phase === 'finished'){
      setMsg('Partie terminée !');
    }
  }

  // Click sur une réponse
  document.querySelectorAll('.md-answer').forEach(el => {
    el.onclick = () => {
      if(currentState?.phase !== 'question') return;
      const k = el.dataset.key;
      selected = k;
      socket.emit('player_answer', { lobby_id: lobbyId, choice: k });
      render(currentState);
      setMsg('✓ Choix envoyé');
    };
  });

  function updateTimerProgress(remaining){
    const progress = document.getElementById('timerProgress');
    if(!progress) return;
    const percent = Math.max(0, remaining / 45) * 100;
    const circumference = 2 * Math.PI * 45;
    progress.style.strokeDashoffset = circumference * (1 - percent / 100);
  }

  function escapeHtml(str){
    return String(str)
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'",'&#39;');
  }
})();
