/* AKTE: Push-Abo, Installationshinweis, Unterschrift, Foto-Vorschau */
(function () {
  const A = window.AKTE || {};
  const istStandalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const istIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  // Installationshinweis (nur Kunde, nur wenn nicht installiert)
  const inst = document.getElementById('installation');
  let aufforderung = null;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); aufforderung = e; if (inst) inst.classList.remove('versteckt'); });
  if (inst && A.rolle === 'kunde' && !istStandalone) {
    const knopf = document.getElementById('install-knopf');
    if (istIOS) { inst.classList.remove('versteckt'); knopf.classList.add('versteckt'); }
    else { document.getElementById('install-text').textContent = 'Damit du Nachrichten bekommst, installiere die App auf deinem Handy.'; }
    knopf.addEventListener('click', async () => { if (aufforderung) { aufforderung.prompt(); await aufforderung.userChoice; } });
  }
  if (istStandalone && A.rolle === 'kunde') {
    fetch('/app/installiert', { method: 'POST' }).catch(() => {});
  }

  // Push
  function b64zuArray(b64) {
    const pad = '='.repeat((4 - b64.length % 4) % 4);
    const roh = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from([...roh].map(c => c.charCodeAt(0)));
  }
  const pushKnopf = document.getElementById('push-knopf');
  const pushHinweis = document.getElementById('push-hinweis');
  if (pushKnopf) {
    pushKnopf.addEventListener('click', async () => {
      try {
        if (!A.pushOeffentlich) { pushHinweis.textContent = 'Push ist auf dem Server noch nicht eingerichtet (VAPID-Schluessel fehlen).'; return; }
        if (!('Notification' in window) || !('PushManager' in window)) {
          pushHinweis.textContent = istIOS ? 'Bitte zuerst die App auf den Homebildschirm legen, dann hier erlauben.' : 'Dieser Browser unterstuetzt keine Mitteilungen.';
          return;
        }
        const erlaubnis = await Notification.requestPermission();
        if (erlaubnis !== 'granted') { pushHinweis.textContent = 'Mitteilungen wurden nicht erlaubt.'; return; }
        const reg = await navigator.serviceWorker.ready;
        const abo = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64zuArray(A.pushOeffentlich) });
        const ziel = A.rolle === 'berater' ? '/berater/push' : '/app/push';
        const r = await fetch(ziel, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(abo.toJSON()) });
        if (r.ok) { pushHinweis.textContent = 'Mitteilungen sind aktiv.'; pushKnopf.classList.add('versteckt'); const k = document.getElementById('push-karte'); if (k) k.classList.add('versteckt'); }
        else pushHinweis.textContent = 'Speichern fehlgeschlagen.';
      } catch (e) { pushHinweis.textContent = 'Fehler: ' + e.message; }
    });
  }

  // Unterschrift
  const pad = document.getElementById('pad');
  if (pad) {
    const ctx = pad.getContext('2d');
    ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.strokeStyle = '#1b2a30';
    let zeichnet = false, gezeichnet = false;
    const pos = (e) => { const r = pad.getBoundingClientRect(); const p = e.touches ? e.touches[0] : e; return [(p.clientX - r.left) * pad.width / r.width, (p.clientY - r.top) * pad.height / r.height]; };
    const start = (e) => { zeichnet = true; const [x, y] = pos(e); ctx.beginPath(); ctx.moveTo(x, y); e.preventDefault(); };
    const zieh = (e) => { if (!zeichnet) return; const [x, y] = pos(e); ctx.lineTo(x, y); ctx.stroke(); gezeichnet = true; e.preventDefault(); };
    const ende = () => { zeichnet = false; };
    pad.addEventListener('mousedown', start); pad.addEventListener('mousemove', zieh); window.addEventListener('mouseup', ende);
    pad.addEventListener('touchstart', start, { passive: false }); pad.addEventListener('touchmove', zieh, { passive: false }); pad.addEventListener('touchend', ende);
    document.getElementById('pad-leeren').addEventListener('click', () => { ctx.clearRect(0, 0, pad.width, pad.height); gezeichnet = false; });
    const form = document.getElementById('auftrag');
    form.addEventListener('submit', (e) => {
      if (!gezeichnet) { e.preventDefault(); alert('Bitte unterschreibe im Feld.'); return; }
      if (!form.querySelector('input[name=unterlage]:checked')) { e.preventDefault(); alert('Bitte mindestens eine Unterlage waehlen.'); return; }
      document.getElementById('unterschrift').value = pad.toDataURL('image/png');
    });
    const summe = () => { let s = 0; form.querySelectorAll('input[name=unterlage]:checked').forEach(c => s += parseFloat(c.dataset.preis || 0)); document.getElementById('summe').textContent = s.toFixed(2).replace('.', ',') + ' EUR'; };
    form.querySelectorAll('input[name=unterlage]').forEach(c => c.addEventListener('change', summe)); summe();
  }

  // Foto-Vorschau und Upload-Status
  const upload = document.getElementById('upload');
  if (upload) {
    const vorschau = document.getElementById('vorschau');
    const zeige = (input) => { vorschau.innerHTML = ''; [...input.files].forEach(f => { if (f.type.startsWith('image/')) { const img = document.createElement('img'); img.src = URL.createObjectURL(f); vorschau.appendChild(img); } else { const s = document.createElement('span'); s.className = 'klein'; s.textContent = f.name; vorschau.appendChild(s); } }); };
    const pdf = document.getElementById('pdf-datei'), foto = document.getElementById('foto-datei');
    pdf.addEventListener('change', () => { foto.value = ''; zeige(pdf); });
    foto.addEventListener('change', () => { pdf.value = ''; zeige(foto); });
    upload.addEventListener('submit', (e) => {
      if (!pdf.files.length && !foto.files.length) { e.preventDefault(); alert('Bitte ein PDF waehlen oder fotografieren.'); return; }
      document.getElementById('upload-knopf').disabled = true; document.getElementById('upload-lauf').classList.remove('versteckt');
    });
  }
})();
