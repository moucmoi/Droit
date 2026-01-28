// Cinematic intro for quiz questions (question-only -> suspense -> reveal UI -> answers one by one)

(function(){
  let lastPlayedIndex = null;
  let running = false;

  const SUSPENSE_MS = 4000; // 4 secondes pour l'animation de question

  function qs(sel){ return document.querySelector(sel); }
  function qsa(sel){ return Array.from(document.querySelectorAll(sel)); }

  function ensureOverlay(){
    let overlay = document.getElementById('cineOverlay');
    if(!overlay){
      overlay = document.createElement('div');
      overlay.id = 'cineOverlay';
      overlay.className = 'cine-overlay';
      document.body.appendChild(overlay);
    }

    // Si le conteneur existe déjà dans le HTML mais est vide, on construit le contenu.
    if(!overlay.querySelector('#cineQuestionText')){
      overlay.innerHTML = `
        <div class="cine-card">
          <div class="cine-title">QUESTION</div>
          <div class="cine-question" id="cineQuestionText"></div>
        </div>
      `;
    }

    return overlay;
  }

  function prepareAnswersForReveal(){
    const cards = qsa('.md-answer');
    for(const c of cards){
      c.classList.add('cine-answer');
      c.classList.remove('is-visible');
    }
  }

  function revealAnswersSequential(){
    const cards = qsa('.md-answer.cine-answer');
    cards.forEach((c, idx) => {
      setTimeout(() => c.classList.add('is-visible'), 250 + idx * 320);
    });
  }

  function fadeOutOverlay(overlay){
    overlay.classList.remove('is-visible');
    // keep display:flex briefly to allow opacity transition
    setTimeout(() => {
      overlay.style.display = 'none';
    }, 750);
  }

  function playOnce(opts){
    const index = Number(opts?.index);
    const prompt = String(opts?.prompt ?? '');
    const onAfterReveal = typeof opts?.onAfterReveal === 'function' ? opts.onAfterReveal : null;

    if(!Number.isFinite(index) || !prompt) return false;
    if(lastPlayedIndex === index) return false;
    if(running) return false;

    running = true;
    lastPlayedIndex = index;

    const overlay = ensureOverlay();
    const textEl = document.getElementById('cineQuestionText');
    if(textEl) textEl.textContent = prompt;

    // Step 1: show only the question
    overlay.style.display = 'flex';
    // force reflow for transition reliability
    void overlay.offsetHeight;
    overlay.classList.add('is-visible');

    document.body.classList.add('cine-active');
    document.body.classList.remove('cine-reveal');

    // Prepare answers hidden for later
    prepareAnswersForReveal();

    // Step 2: suspense
    setTimeout(() => {
      // Step 3: reveal board (camera zoom-out)
      document.body.classList.remove('cine-active');
      document.body.classList.add('cine-reveal');
      fadeOutOverlay(overlay);

      // Step 4: answers one by one
      setTimeout(() => {
        revealAnswersSequential();
        if(onAfterReveal) onAfterReveal();
        // end
        setTimeout(() => { running = false; }, 1200);
      }, 350);
    }, SUSPENSE_MS);

    return true;
  }

  window.MD_CINEMATIC = {
    playOnce
  };
})();
