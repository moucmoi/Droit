// Menu navigation logic for Money Drop main menu

document.addEventListener('DOMContentLoaded', function () {

  // Efface lâ€™erreur mot de passe au focus
  const hostPwdInput = document.querySelector('#menu-host input[name="password"]');
  if (hostPwdInput) {
    hostPwdInput.addEventListener('focus', function () {
      const errDiv = document.getElementById('hostPwdError');
      if (errDiv) errDiv.style.display = 'none';
    });
  }

  const menuMain = document.getElementById('menu-main');
  const menuMulti = document.getElementById('menu-multi');
  const menuHost = document.getElementById('menu-host');
  const menuJoin = document.getElementById('menu-join');

    // Solo form back
    document.getElementById('btnBackSolo').onclick = function () {
      document.getElementById('menu-solo').style.display = 'none';
      menuMain.style.display = '';
    };
  document.getElementById('btnMulti').onclick = function () {
    menuMain.style.display = 'none';
    menuMulti.style.display = '';
  };

  // Multi submenu
  document.getElementById('btnHost').onclick = function () {
    menuMulti.style.display = 'none';
    menuHost.style.display = '';
  };
  document.getElementById('btnJoin').onclick = function () {
    menuMulti.style.display = 'none';
    menuJoin.style.display = '';
    loadLobbies();
  };
  document.getElementById('btnBackMulti').onclick = function () {
    menuMulti.style.display = 'none';
    menuMain.style.display = '';
  };

  // Host form back
  document.getElementById('btnBackHost').onclick = function () {
    menuHost.style.display = 'none';
    menuMulti.style.display = '';
  };
  // Join form back
  document.getElementById('btnBackJoin').onclick = function () {
    menuJoin.style.display = 'none';
    menuMulti.style.display = '';
  };

  // Load lobbies periodically
  async function loadLobbies() {
    const list = document.getElementById('lobbiesList');
    try {
      const res = await fetch('/api/lobbies');
      const data = await res.json();
      
      if (!data.ok || !data.lobbies.length) {
        list.innerHTML = '<div style="color: var(--muted); text-align: center; padding: 10px;">Aucun salon disponible</div>';
        setTimeout(loadLobbies, 2000);
        return;
      }

      list.innerHTML = data.lobbies.map(lobby => `
        <div style="background: rgba(33,150,243,0.1); border: 1px solid #2196F3; border-radius: 6px; padding: 10px; cursor: pointer; transition: all 0.2s;" 
             onmouseover="this.style.background='rgba(33,150,243,0.2)'" 
             onmouseout="this.style.background='rgba(33,150,243,0.1)'"
             onclick="joinLobby('${lobby.lobby_id}')">
          <div style="font-weight: bold; color: #2196F3;">${lobby.host_name}</div>
          <div style="font-size: 12px; color: var(--muted);">${lobby.players}/${lobby.max_players} joueurs | ${lobby.time_limit}s/question</div>
        </div>
      `).join('');
      
      setTimeout(loadLobbies, 2000);
    } catch (e) {
      list.innerHTML = '<div style="color: var(--bad); text-align: center; padding: 10px;">Erreur de connexion</div>';
      setTimeout(loadLobbies, 2000);
    }
  }

  window.joinLobby = async function(lobbyId) {
    const name = document.getElementById('joinName').value.trim();
    if (!name) {
      alert('Veuillez entrer votre nom');
      return;
    }

    try {
      const res = await fetch('/lobby/join', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ lobby_id: lobbyId, name })
      });
      const data = await res.json();

      if (data.ok) {
        sessionStorage.setItem('lobby_id', lobbyId);
        window.location.href = `/lobby/${lobbyId}/client`;
      } else {
        alert('Erreur: ' + (data.error || 'Impossible de rejoindre'));
      }
    } catch (e) {
      console.error('Erreur:', e);
      alert('Erreur de connexion: ' + e.message);
    }
  };

  // Host form: create lobby via JSON API then redirect to host dashboard
  const hostForm = document.getElementById('hostForm');
  if(hostForm){
    hostForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();

      const errDiv = document.getElementById('hostPwdError');
      if(errDiv){ errDiv.style.display = 'none'; errDiv.textContent = ''; }

      const fd = new FormData(hostForm);
      const payload = {};
      fd.forEach((v, k) => { payload[k] = String(v); });

      try{
        const r = await fetch('/lobby/create', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await r.json().catch(() => ({}));
        if(!r.ok || !data.ok){
          const msg = (data && data.error === 'invalid password') ? 'Mot de passe incorrect' : (data && data.error) ? data.error : 'Erreur';
          if(errDiv){ errDiv.style.display = ''; errDiv.textContent = msg; }
          return;
        }
        window.location.href = `/lobby/${encodeURIComponent(data.lobby_id)}/host`;
      }catch(e){
        if(errDiv){ errDiv.style.display = ''; errDiv.textContent = 'Erreur de connexion'; }
      }
    });
  }

  // Optionally: prevent double submit, add loading, etc.
});

