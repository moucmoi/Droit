(function(){
  const lobbyId = window.LOBBY_ID;
  const playerName = window.PLAYER_NAME || 'Joueur';
  const msgEl = document.getElementById('message');

  let currentState = null;
  let myPlayerName = '';
  let myChipsBank = 0; // server score
  let gameStarted = false;
  let timerActive = false;
  let resolving = false;
  let lastResolvedQuestionIndex = null;
  let hasShownGameOver = false;
  let isSpectator = false;

  let selectedAnswer = null;
  let selectedAction = 'check';
  let hasBet = false;

  // Tick-tock during question
  const countdownMusic = new Audio('/static/musique_d%C3%A9compte.mp3');
  countdownMusic.loop = true;
  countdownMusic.volume = 0.5;
  let musicPlaying = false;

  function musicStart(){
    if(musicPlaying) return;
    countdownMusic.play().catch(()=>{});
    musicPlaying = true;
  }
  function musicStop(){
    if(!musicPlaying) return;
    countdownMusic.pause();
    countdownMusic.currentTime = 0;
    musicPlaying = false;
  }

  function setMsg(text, type){
    if(!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'md-message';
    if(type === 'error') msgEl.classList.add('md-message-error');
    else if(type === 'success') msgEl.classList.add('md-message-success');
  }

  function updateTimerProgress(remaining){
    const progress = document.getElementById('timerProgress');
    if(!progress) return;
    const maxTime = 60;
    const percent = Math.max(0, remaining / maxTime);
    const circumference = 2 * Math.PI * 45;
    progress.style.strokeDashoffset = circumference * (1 - percent);
  }

  function setAction(action){
    selectedAction = action;
    document.querySelectorAll('.pk-action-btn').forEach(btn => {
      btn.classList.toggle('is-active', btn.dataset.action === action);
    });

    const betInput = document.getElementById('betAmount');
    if(!betInput) return;

    if(action === 'check'){
      betInput.value = '0';
      betInput.disabled = true;
    } else if(action === 'all-in'){
      betInput.value = String(myChipsBank || 0);
      betInput.disabled = true;
    } else {
      betInput.disabled = false;
      if(Number(betInput.value || '0') <= 0) betInput.value = '100';
    }

    updateSelectedInfo();
  }

  function updateSelectedInfo(){
    const info = document.getElementById('selectedInfo');
    if(!info) return;

    const answerTxt = selectedAnswer ? `Reponse: ${selectedAnswer}` : 'Reponse: aucune';
    if(selectedAction === 'check'){
      info.textContent = `${answerTxt} · Check`;
      return;
    }
    if(selectedAction === 'all-in'){
      info.textContent = `${answerTxt} · All-in`;
      return;
    }
    const betInput = document.getElementById('betAmount');
    const amt = betInput ? (parseInt(betInput.value || '0', 10) || 0) : 0;
    info.textContent = `${answerTxt} · Miser ${amt}`;
  }

  function enableBetting(){
    if(isSpectator || myChipsBank <= 0) return;
    document.querySelectorAll('.pk-action-btn').forEach(btn => btn.disabled = false);

    const betInput = document.getElementById('betAmount');
    if(betInput) betInput.disabled = (selectedAction !== 'bet');

    const submitBtn = document.getElementById('submit');
    if(submitBtn) submitBtn.disabled = false;
  }

  function disableBetting(){
    document.querySelectorAll('.pk-action-btn').forEach(btn => btn.disabled = true);
    const betInput = document.getElementById('betAmount');
    if(betInput) betInput.disabled = true;

    const submitBtn = document.getElementById('submit');
    if(submitBtn) submitBtn.disabled = true;
  }

  function showLobbyWaiting(state){
    document.getElementById('lobbyWaiting').style.display = 'flex';
    document.getElementById('gameBoard').style.display = 'none';
    document.getElementById('chipsDisplay').style.display = 'none';

    const playersList = document.getElementById('lobbyPlayersList');
    const playerCount = document.getElementById('lobbyPlayerCount');
    const baseCount = state.players?.length || 0;
    const hostCount = state.host_sid ? 1 : 0;
    playerCount.textContent = baseCount + hostCount;
    playersList.innerHTML = '';

    const hostSid = state.host_sid || null;
    (state.players || []).forEach((p) => {
      const item = document.createElement('div');
      item.className = 'md-lobby-player-item';

      const avatar = document.createElement('div');
      avatar.className = 'md-lobby-player-avatar';
      avatar.textContent = (p.name || '?')[0].toUpperCase();

      const name = document.createElement('div');
      name.className = 'md-lobby-player-name';
      name.textContent = p.name || 'Joueur';

      item.appendChild(avatar);
      item.appendChild(name);

      if(hostSid && p.sid === hostSid){
        const badge = document.createElement('div');
        badge.className = 'md-lobby-player-badge';
        badge.textContent = 'Hote';
        item.appendChild(badge);
      }

      playersList.appendChild(item);
    });
  }

  function showGameBoard(){
    document.getElementById('lobbyWaiting').style.display = 'none';
    document.getElementById('gameOver').style.display = 'none';
    document.getElementById('gameBoard').style.display = 'flex';
    document.getElementById('chipsDisplay').style.display = '';
  }

  function showGameOver(){
    document.getElementById('lobbyWaiting').style.display = 'none';
    document.getElementById('gameBoard').style.display = 'none';
    document.getElementById('gameOver').style.display = 'flex';
    document.getElementById('finalScore').textContent = myChipsBank + ' jetons';

    timerActive = false;
    musicStop();
    disableBetting();

    const msgDiv = document.querySelector('.md-game-over-message p');
    msgDiv.textContent = myChipsBank > 0
      ? `Bravo ! Vous avez sauve ${myChipsBank} jetons !`
      : 'Dommage, vous avez perdu tous vos jetons.';

    setTimeout(() => {
      window.location.href = `/lobby/${lobbyId}/podium?lobby_id=${encodeURIComponent(lobbyId)}`;
    }, 3000);
  }

  function renderAnswers(state){
    const keys = ['A','B','C','D'];
    keys.forEach(k => {
      const textEl = document.getElementById('ans'+k);
      const card = textEl?.parentElement;
      if(state.question?.answers?.[k]){
        textEl.textContent = state.question.answers[k];
        if(card) card.style.display = '';
      } else {
        if(card) card.style.display = 'none';
      }
    });
  }

  async function playResolutionOnce(correct, questionIndex){
    if(!window.MD_RESOLUTION || !correct) return;
    if(resolving) return;
    if(questionIndex != null && lastResolvedQuestionIndex === questionIndex) return;

    resolving = true;
    timerActive = false;
    musicStop();

    if(questionIndex != null) lastResolvedQuestionIndex = questionIndex;
    try{
      await window.MD_RESOLUTION.play({ correct, bets: { A: 0, B: 0, C: 0, D: 0 } });
    } finally {
      resolving = false;
    }
  }

  function render(state){
    const qIndex = (state.question_index || 0) + 1;
    document.getElementById('qCounter').textContent = String(qIndex);
    document.getElementById('category').textContent = state.question?.category ?? '';
    document.getElementById('prompt').textContent = state.question?.prompt ?? '';
    document.getElementById('timerValue').textContent = String(state.time_remaining ?? 60);

    renderAnswers(state);

    if(state.phase === 'waiting'){
      musicStop();
      setMsg('En attente du lancement de la partie...', 'info');
      disableBetting();
      timerActive = false;
    } else if(state.phase === 'question'){
      if(myChipsBank <= 0){
        musicStop();
        setMsg('Mode spectateur - elimine', 'info');
        disableBetting();
        timerActive = false;
      } else {
        setMsg(hasBet ? 'Mise envoyee.' : 'Choisis une reponse et une action.', 'info');
        timerActive = !!state.question && !resolving;
        if(!hasBet) enableBetting();
      }
    } else if(state.phase === 'results'){
      musicStop();
      setMsg('Resultats...', 'info');
      disableBetting();
      timerActive = false;
      if(state.correct){
        playResolutionOnce(state.correct, state.question_index);
      }
    } else if(state.phase === 'paused'){
      musicStop();
      setMsg('Pause...', 'info');
      disableBetting();
      timerActive = false;
    } else if(state.phase === 'finished'){
      musicStop();
      setMsg('Partie terminee !', 'success');
      disableBetting();
      timerActive = false;
    }
  }

  function bindUI(){
    document.querySelectorAll('.pk-answer').forEach(btn => {
      btn.addEventListener('click', () => {
        if(hasBet || isSpectator || myChipsBank <= 0) return;
        selectedAnswer = btn.getAttribute('data-key');
        document.querySelectorAll('.pk-answer').forEach(el => el.classList.remove('is-selected'));
        btn.classList.add('is-selected');
        updateSelectedInfo();
      });
    });

    document.querySelectorAll('.pk-action-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if(hasBet || isSpectator || myChipsBank <= 0) return;
        setAction(btn.dataset.action || 'check');
        const betInput = document.getElementById('betAmount');
        if((btn.dataset.action || '') === 'bet' && betInput && !betInput.disabled){
          betInput.focus();
          betInput.select();
        }
      });
    });

    const betInput = document.getElementById('betAmount');
    if(betInput){
      betInput.addEventListener('input', () => {
        if(selectedAction !== 'bet') return;
        updateSelectedInfo();
      });
    }

    const submitBtn = document.getElementById('submit');
    if(submitBtn){
      submitBtn.addEventListener('click', () => {
        if(hasBet || isSpectator || myChipsBank <= 0) return;
        let action = selectedAction;
        let amount = 0;

        if(action === 'check'){
          amount = 0;
        } else if(action === 'all-in'){
          if(!selectedAnswer){
            setMsg('Choisis une reponse.', 'error');
            return;
          }
          amount = myChipsBank;
        } else {
          if(!selectedAnswer){
            setMsg('Choisis une reponse.', 'error');
            return;
          }
          const raw = betInput?.value || '0';
          amount = Math.max(0, parseInt(raw, 10) || 0);
          if(amount <= 0){
            setMsg('Mise invalide.', 'error');
            return;
          }
          if(amount > myChipsBank){
            amount = myChipsBank;
          }
          if(amount >= myChipsBank){
            action = 'all-in';
          }
        }

        socket.emit('player_bets', {
          lobby_id: lobbyId,
          action,
          answer: selectedAnswer || null,
          amount
        });

        hasBet = true;
        disableBetting();
        updateSelectedInfo();
        setMsg('Mise envoyee.', 'info');
      });
    }

    const btnSpectator = document.getElementById('btnSpectator');
    if(btnSpectator){
      btnSpectator.addEventListener('click', () => {
        isSpectator = true;
        showGameBoard();
        if(currentState) render(currentState);
      });
    }
  }

  // Socket
  const socket = io(window.location.origin, { transports: ['websocket','polling'] });

  socket.on('connect', () => {
    socket.emit('join_lobby', { lobby_id: lobbyId, role: 'player', player_name: playerName });
  });

  socket.on('game_ended', () => {
    musicStop();
    setTimeout(() => {
      window.location.href = `/lobby/${lobbyId}/podium?lobby_id=${encodeURIComponent(lobbyId)}`;
    }, 1000);
  });

  socket.on('game_started', () => {
    if(!gameStarted){
      gameStarted = true;
      showGameBoard();
    }
  });

  socket.on('new_question', () => {
    if(myChipsBank <= 0 && hasShownGameOver){
      return;
    }
    hasBet = false;
    selectedAnswer = null;
    setAction('check');
    updateSelectedInfo();
    enableBetting();
  });

  socket.on('state', (state) => {
    currentState = state;

    const me = state.players?.find(p => p.socket_id === socket.id);
    if(me){
      const prev = myChipsBank;
      myPlayerName = me.name;
      myChipsBank = me.score || 0;

      const committed = me.bet_amount || 0;
      const shown = (state.phase === 'question') ? Math.max(0, myChipsBank - committed) : myChipsBank;

      document.getElementById('playerName').textContent = myPlayerName;
      document.getElementById('chips').textContent = shown;

      const isNowEliminated = me.eliminated || false;
      const wasAlreadyEliminated = prev <= 0;
      if(gameStarted && isNowEliminated && !wasAlreadyEliminated && !hasShownGameOver){
        hasShownGameOver = true;
        showGameOver();
        return;
      }
    }

    const inLobbyWaitingRoom = !gameStarted && state.phase === 'waiting' && state.question_index === 0 && !state.question;
    if(inLobbyWaitingRoom){
      showLobbyWaiting(state);
    } else {
      if(!gameStarted){
        gameStarted = true;
        showGameBoard();
      }
      render(state);
    }
  });

  socket.on('reveal_answer', (data) => {
    playResolutionOnce(data?.correct, data?.question_index);
  });

  socket.on('tick', (p) => {
    const remaining = p?.time_remaining ?? 0;
    document.getElementById('timerValue').textContent = Math.max(0, remaining);
    updateTimerProgress(remaining);

    if(!timerActive){
      musicStop();
      return;
    }

    if(currentState && currentState.phase === 'question' && myChipsBank > 0 && !resolving) musicStart();
    else musicStop();
  });

  socket.on('force_spectator', (p) => {
    isSpectator = true;
    showGameBoard();
    disableBetting();
    setMsg(p?.message || 'Mode spectateur', 'info');
    if(currentState) render(currentState);
  });

  socket.on('error_msg', (p) => setMsg(p?.error || 'Erreur', 'error'));

  // Init
  bindUI();
  setAction('check');
  updateSelectedInfo();
  disableBetting();
  musicStop();
})();
