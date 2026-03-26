(function () {
  'use strict';

  var MODAL_ID = 'cwBookingModal';

  function createModal() {
    if (document.getElementById(MODAL_ID)) return;

    var modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:99999;justify-content:center;align-items:center;';

    var inner = document.createElement('div');
    inner.style.cssText = 'background:#111;border-radius:12px;padding:20px;width:90%;max-width:800px;max-height:90vh;position:relative;overflow:hidden;';

    var closeBtn = document.createElement('button');
    closeBtn.id = 'cwBookingClose';
    closeBtn.innerHTML = '&#x2715;';
    closeBtn.style.cssText = 'position:absolute;top:15px;right:15px;background:transparent;border:none;color:white;font-size:24px;cursor:pointer;z-index:1;line-height:1;';
    closeBtn.addEventListener('click', closeBooking);

    var title = document.createElement('h2');
    title.textContent = 'Termin buchen';
    title.style.cssText = 'color:white;margin:0 0 8px;font-size:1.4rem;font-family:"Inter",sans-serif;';

    var sub = document.createElement('p');
    sub.textContent = '30 Minuten. Kein Verkaufsgespräch. Wir schauen gemeinsam ob und wie ich dich weiterbringen kann.';
    sub.style.cssText = 'color:#aaa;margin:0 0 16px;font-size:0.9rem;font-family:"Inter",sans-serif;line-height:1.5;';

    var iframe = document.createElement('iframe');
    iframe.src = 'https://calendar.app.google/LsPEFfuxkZn1TgC26';
    iframe.style.cssText = 'width:100%;height:600px;border:none;border-radius:8px;display:block;';
    iframe.frameBorder = '0';

    inner.appendChild(closeBtn);
    inner.appendChild(title);
    inner.appendChild(sub);
    inner.appendChild(iframe);
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
