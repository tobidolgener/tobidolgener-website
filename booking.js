(function () {
  'use strict';

  var MODAL_ID = 'cwBookingModal';
  var CALENDAR_URL = 'https://calendar.app.google/LsPEFfuxkZn1TgC26';

  function createModal() {
    if (document.getElementById(MODAL_ID)) return;

    var modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.style.cssText = [
      'display:none;position:fixed;top:0;left:0;width:100%;height:100%;',
      'background:rgba(0,0,0,0.88);z-index:99999;',
      'justify-content:center;align-items:center;',
      'padding:20px;box-sizing:border-box;'
    ].join('');

    var inner = document.createElement('div');
    inner.style.cssText = [
      'background:#111;border-radius:16px;padding:36px 32px 40px;',
      'width:100%;max-width:520px;position:relative;',
      'text-align:center;'
    ].join('');

    var closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&#x2715;';
    closeBtn.style.cssText = [
      'position:absolute;top:16px;right:18px;background:transparent;',
      'border:none;color:rgba(255,255,255,0.5);font-size:22px;cursor:pointer;',
      'line-height:1;transition:color 0.2s;'
    ].join('');
    closeBtn.addEventListener('mouseover', function(){ this.style.color='#fff'; });
    closeBtn.addEventListener('mouseout',  function(){ this.style.color='rgba(255,255,255,0.5)'; });
    closeBtn.addEventListener('click', closeBooking);

    // Calendar icon
    var iconWrap = document.createElement('div');
    iconWrap.style.cssText = 'margin:0 auto 20px;width:64px;height:64px;border-radius:50%;background:#FF6600;display:flex;align-items:center;justify-content:center;';
    iconWrap.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>';

    var title = document.createElement('h2');
    title.textContent = 'Termin buchen';
    title.style.cssText = 'color:#fff;margin:0 0 12px;font-size:1.7rem;font-family:"Inter",sans-serif;font-weight:800;letter-spacing:-0.02em;';

    var sub = document.createElement('p');
    sub.textContent = '30 Minuten. Kein Verkaufsgespräch. Wir schauen gemeinsam ob und wie ich dich weiterbringen kann.';
    sub.style.cssText = 'color:rgba(255,255,255,0.55);margin:0 0 32px;font-size:1rem;font-family:"Inter",sans-serif;line-height:1.6;';

    var ctaBtn = document.createElement('a');
    ctaBtn.href = CALENDAR_URL;
    ctaBtn.target = '_blank';
    ctaBtn.rel = 'noopener';
    ctaBtn.textContent = 'Jetzt Termin wählen →';
    ctaBtn.style.cssText = [
      'display:inline-block;background:#FF6600;color:#fff;',
      'padding:16px 36px;border-radius:10px;font-size:1.05rem;',
      'font-weight:700;font-family:"Inter",sans-serif;letter-spacing:0.02em;',
      'text-decoration:none;transition:filter 0.2s;'
    ].join('');
    ctaBtn.addEventListener('mouseover', function(){ this.style.filter='brightness(1.15)'; });
    ctaBtn.addEventListener('mouseout',  function(){ this.style.filter=''; });

    var note = document.createElement('p');
    note.textContent = 'Öffnet Google Calendar in einem neuen Tab';
    note.style.cssText = 'color:rgba(255,255,255,0.25);margin:16px 0 0;font-size:0.75rem;font-family:"Inter",sans-serif;';

    inner.appendChild(closeBtn);
    inner.appendChild(iconWrap);
    inner.appendChild(title);
    inner.appendChild(sub);
    inner.appendChild(ctaBtn);
    inner.appendChild(note);
    modal.appendChild(inner);
    document.body.appendChild(modal);

    modal.addEventListener('click', function (e) {
      if (e.target === modal) closeBooking();
    });
  }

  function openBooking() {
    createModal();
    var modal = document.getElementById(MODAL_ID);
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeBooking() {
    var modal = document.getElementById(MODAL_ID);
    if (modal) {
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeBooking();
  });

  window.openBooking = openBooking;
  window.closeBooking = closeBooking;
})();
