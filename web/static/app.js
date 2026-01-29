const ANSWER_KEYS = ['A', 'B', 'C', 'D'];
const TOTAL_TIME = 60;

function $(id){
  return document.getElementById(id);
}

async function getState(){
  const r = await fetch('/api/state');
  if(!r.ok) throw new Error('state');
  return await r.json();
}

function setMessage(text){
  const el = $('message');
  if(el) el.textContent = text || '';
}

function escapeHtml(str){
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function clearHighlights(){
  document.querySelectorAll('.pk-answer').forEach(el => {
    el.classList.remove('is-selected', 'is-correct', 'is-wrong');
  });
}

function setTimerValue(seconds){
  const valueEl = $('timerValue');
  if(valueEl) valueEl.textContent = String(seconds);

  const progressEl = $('timerProgress');
  if(progressEl){
    const r = 45;
    const circumference = 2 * Math.PI * r;
    const ratio = Math.max(0, Math.min(1, seconds / TOTAL_TIME));
    const offset = circumference * (1 - ratio);
    progressEl.style.strokeDasharray = String(circumference);
    progressEl.style.strokeDashoffset = String(offset);

    if(seconds <= 5) progressEl.style.stroke = 'var(--md-danger)';
    else if(seconds <= 10) progressEl.style.stroke = 'var(--md-gold)';
    else progressEl.style.stroke = 'var(--md-cyan)';
  }
}

let timerInterval = null;
let timeRemaining = TOTAL_TIME;
let timerQuestionIndex = null;

function stopTimer(){
  if(timerInterval){
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function startTimerForQuestion(progressIndex){
  if(timerQuestionIndex === progressIndex && timerInterval) return;
  timerQuestionIndex = progressIndex;
  timeRemaining = TOTAL_TIME;
  setTimerValue(timeRemaining);
  stopTimer();
  timerInterval = setInterval(() => {
    timeRemaining = Math.max(0, timeRemaining - 1);
    setTimerValue(timeRemaining);
    if(timeRemaining <= 0){
      stopTimer();
    }
  }, 1000);
}

let selectedAnswer = null;
let selectedAction = 'check';

function setAction(action){
  selectedAction = action;
  document.querySelectorAll('.pk-action-btn').forEach(btn => {
    btn.classList.toggle('is-active', btn.dataset.action === action);
  });

  const betInput = $('betAmount');
  if(!betInput) return;

  if(action === 'check'){
    betInput.value = '0';
    betInput.disabled = true;
  } else if(action === 'all-in'){
    const chips = Number($('chips')?.textContent || '0');
    betInput.value = String(chips || 0);
    betInput.disabled = true;
  } else {
    betInput.disabled = false;
    if(Number(betInput.value || '0') <= 0){
      betInput.value = '100';
    }
  }

  updateSelectedInfo();
}

function updateSelectedInfo(){
  const info = $('selectedInfo');
  if(!info) return;

  const answerText = selectedAnswer ? `Reponse ${selectedAnswer}` : 'Choisis une reponse';
  const betInput = $('betAmount');
  const amount = betInput ? Number(betInput.value || '0') : 0;

  if(selectedAction === 'check'){
    info.textContent = `${answerText} · Check`;
  } else if(selectedAction === 'all-in'){
    info.textContent = `${answerText} · All-in`;
  } else {
    info.textContent = `${answerText} · Bet ${amount}`;
  }
}

function bindAnswerClicks(){
  document.querySelectorAll('.pk-answer').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedAnswer = btn.getAttribute('data-key');
      document.querySelectorAll('.pk-answer').forEach(el => el.classList.remove('is-selected'));
      btn.classList.add('is-selected');
      updateSelectedInfo();
    });
  });
}

function bindActionButtons(){
  document.querySelectorAll('.pk-action-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setAction(btn.dataset.action || 'check');
    });
  });

  document.querySelectorAll('.pk-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const pct = Number(btn.dataset.pct || '0');
      const chips = Number($('chips')?.textContent || '0');
      const amount = Math.max(0, Math.floor(chips * pct / 100) * 100);
      const betInput = $('betAmount');
      if(betInput){
        betInput.value = String(amount);
        setAction('bet');
      }
    });
  });

  const betInput = $('betAmount');
  if(betInput){
    betInput.addEventListener('input', () => {
      if(selectedAction !== 'bet') return;
      updateSelectedInfo();
    });
  }
}

function renderLeaderboard(state){
  const container = $('leaderboard');
  if(!container) return;
  container.innerHTML = '';

  const entries = state?.leaderboard || [];
  for(const e of entries){
    const row = document.createElement('div');
    row.className = 'md-lb-item';
    const correct = Number(e.best_correct ?? 0);
    const chips = Number(e.best_chips ?? 0);
    row.innerHTML = `
      <div class="md-lb-top">
        <div class="md-lb-rank">#</div>
        <div style="flex:1; min-width:0;">
          <div class="md-lb-name">${escapeHtml(String(e.name ?? ''))}</div>
          <div class="md-lb-sub">${correct} bonne${correct !== 1 ? 's' : ''} reponse${correct !== 1 ? 's' : ''}</div>
        </div>
        <div class="md-lb-score">${chips.toLocaleString('fr-FR')}<small>jetons</small></div>
      </div>
    `;
    container.appendChild(row);
  }

  const footer = $('leaderboardFooter');
  if(footer) footer.textContent = `${entries.length} joueurs connectes`;
}

function renderState(state){
  clearHighlights();
  setMessage('');

  const playerNameEl = $('playerName');
  if(playerNameEl) playerNameEl.textContent = state?.player?.name ?? '...';

  const chipsEl = $('chips');
  if(chipsEl) chipsEl.textContent = String(state?.player?.chips ?? '0');

  const qCounterEl = $('qCounter');
  if(qCounterEl) qCounterEl.textContent = String((state?.progress?.index ?? 0) + 1);

  const categoryEl = $('category');
  if(categoryEl) categoryEl.textContent = state?.question?.category ?? (state?.eliminated ? 'Elimine' : '');

  const promptEl = $('prompt');
  if(promptEl){
    if(state?.finished || state?.eliminated || !state?.question){
      promptEl.textContent = `Partie terminee. Jetons finaux: ${state?.result?.final_chips ?? state?.player?.chips ?? 0}`;
    } else {
      promptEl.textContent = state.question.prompt;
    }
  }

  for(const k of ANSWER_KEYS){
    const ansEl = $('ans'+k);
    if(ansEl) ansEl.textContent = state?.question?.answers?.[k] ?? '';
  }

  renderLeaderboard(state);

  if(state?.question && !state?.finished && !state?.eliminated){
    const idx = Number(state?.progress?.index ?? 0);
    startTimerForQuestion(idx);
  } else {
    stopTimer();
    setTimerValue(0);
  }
}

async function refresh(){
  const state = await getState();
  renderState(state);
}

async function submit(){
  setMessage('');
  clearHighlights();

  const state = await getState();
  const chips = state?.player?.chips ?? 0;

  if(!selectedAnswer){
    setMessage('Choisis une reponse.');
    return;
  }

  let action = selectedAction;
  let amount = 0;

  if(action === 'check'){
    amount = 0;
  } else if(action === 'all-in'){
    amount = chips;
  } else {
    const raw = $('betAmount')?.value || '0';
    amount = Math.max(0, parseInt(raw, 10) || 0);
    if(amount <= 0){
      setMessage('Mise invalide.');
      return;
    }
    amount = Math.min(amount, chips);
  }

  const payload = { answer: selectedAnswer, action, amount };

  const r = await fetch('/api/bet', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await r.json().catch(() => ({ ok:false, error:'erreur' }));

  if(!r.ok || !data.ok){
    setMessage(`Erreur: ${data.error || 'inconnue'}`);
    return;
  }

  stopTimer();

  const res = data.resolution;
  document.querySelector(`.pk-answer[data-key="${res.correct}"]`)?.classList.add('is-correct');
  for(const k of ANSWER_KEYS){
    if(k === res.correct) continue;
    document.querySelector(`.pk-answer[data-key="${k}"]`)?.classList.add('is-wrong');
  }

  setMessage(`Bonne reponse: ${res.correct}) ${res.correct_label} | Action: ${res.action} | Gain: ${res.gained} | Perte: ${res.lost}${res.explanation ? ' — ' + res.explanation : ''}`);

  setTimeout(() => { refresh().catch(() => {}); }, 650);
}

function bind(){
  bindAnswerClicks();
  bindActionButtons();
  setAction('check');

  const submitBtn = $('submit');
  if(submitBtn){
    submitBtn.addEventListener('click', () => { submit().catch(() => {}); });
  }

  refresh().catch(() => { window.location.href = '/'; });
}

bind();
