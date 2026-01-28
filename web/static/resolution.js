// Money Drop resolution animation: focus bets, drop wrong money simultaneously.

(function(){
  function q(sel){ return document.querySelector(sel); }
  function qa(sel){ return Array.from(document.querySelectorAll(sel)); }

  function byKey(baseSelector, key){
    return document.querySelector(`${baseSelector}[data-key="${key}"]`);
  }

  function setControlsDisabled(disabled){
    const ids = ['submit','btn5050'];
    for(const id of ids){
      const el = document.getElementById(id);
      if(el) el.disabled = !!disabled;
    }
    qa('button[data-action][data-key]').forEach(b => b.disabled = !!disabled);
  }

  function cleanup(){
    document.body.classList.remove('resolving');
    document.body.classList.remove('drone-view');
    qa('.md-answer').forEach(el => el.classList.remove('res-dim','res-focus','res-win','res-lose','res-drop'));
    qa('.md-zone').forEach(el => el.classList.remove('res-zone-lose','res-drop'));
    setControlsDisabled(false);
  }

  async function play(opts){
    const correct = String(opts?.correct ?? '');
    const bets = opts?.bets ?? {};

    if(!correct) return;

    setControlsDisabled(true);

    // Drone view 3D perspective
    document.body.classList.add('resolving');
    document.body.classList.add('drone-view');

    const keys = ['A','B','C','D'];
    const betKeys = keys.filter(k => Number(bets[k] || 0) > 0);

    for(const k of keys){
      const ans = byKey('.md-answer', k);
      if(!ans) continue;

      // Highlight les réponses misées
      if(betKeys.includes(k)) ans.classList.add('res-focus');
      else ans.classList.add('res-dim');

      // La bonne réponse verte, les mauvaises rouges
      if(k === correct) {
        ans.classList.add('res-win');
      } else {
        ans.classList.add('res-lose');
      }
    }

    // Dramatic pause for 3D perspective
    await new Promise(r => setTimeout(r, 900));

    // Tables drop for wrong answers
    for(const k of keys){
      if(k === correct) continue;
      
      const ans = byKey('.md-answer', k);
      const zone = byKey('.md-zone', k);
      
      if(ans){
        ans.classList.add('res-drop');
      }
      if(zone){
        zone.classList.add('res-zone-lose');
        zone.classList.add('res-drop');
      }
    }

    // Correct answer gets shine
    const winAns = byKey('.md-answer', correct);
    if(winAns) winAns.classList.add('res-drop');

    // Animation complète + winner visible
    await new Promise(r => setTimeout(r, 1300));

    cleanup();
  }

  window.MD_RESOLUTION = { play, cleanup };
})();
