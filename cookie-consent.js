(function () {
  'use strict';

  var STORAGE_KEY = 'cookie_consent';

  /* ── CSS ── */
  var css = [
    '#cp-popup{',
      'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);',
      'z-index:9999;width:calc(100% - 48px);max-width:700px;',
      'background:rgba(13,37,64,0.97);backdrop-filter:blur(16px);',
      'border:1px solid rgba(0,119,200,0.25);border-radius:14px;',
      'padding:24px 28px;font-family:"Inter",sans-serif;',
      'box-shadow:0 8px 40px rgba(0,0,0,0.5);',
      'transition:opacity 0.3s,transform 0.3s;',
    '}',
    '#cp-popup.cp-hidden{opacity:0;transform:translateX(-50%) translateY(16px);pointer-events:none;}',
    '.cp-text{font-size:0.85rem;color:#8aaec8;line-height:1.6;margin-bottom:10px;}',
    '.cp-links{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;}',
    '.cp-links a{font-size:0.75rem;color:#4a6d8c;text-decoration:none;border-bottom:1px solid rgba(74,109,140,0.4);transition:color 0.2s;}',
    '.cp-links a:hover{color:#8aaec8;}',
    '.cp-buttons{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;}',
    '.cp-btn{padding:9px 18px;border-radius:8px;font-size:0.78rem;font-weight:700;cursor:pointer;font-family:inherit;transition:background 0.2s,transform 0.2s,filter 0.2s;border:none;letter-spacing:0.02em;}',
    '.cp-btn:hover{transform:translateY(-1px);filter:brightness(1.1);}',
    '.cp-btn-accept{background:#ff5e00;color:#fff;}',
    '.cp-btn-save{background:transparent;color:#f0f0f0;border:1px solid rgba(255,255,255,0.25);}',
    '.cp-btn-necessary{background:rgba(255,255,255,0.07);color:#8aaec8;border:1px solid rgba(255,255,255,0.1);}',
    '.cp-toggle-btn{background:none;border:none;color:#4a6d8c;font-size:0.73rem;font-family:inherit;cursor:pointer;padding:0;letter-spacing:0.05em;display:flex;align-items:center;gap:6px;transition:color 0.2s;}',
    '.cp-toggle-btn:hover{color:#8aaec8;}',
    '.cp-toggle-btn .cp-chevron{display:inline-block;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;width:7px;height:7px;transform:rotate(45deg);transition:transform 0.25s;margin-bottom:2px;}',
    '.cp-toggle-btn.open .cp-chevron{transform:rotate(-135deg);margin-bottom:-2px;}',
    '.cp-details{margin-top:16px;display:flex;flex-direction:column;gap:0;border-top:1px solid rgba(0,119,200,0.15);padding-top:16px;}',
    '.cp-cat{display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(0,119,200,0.1);}',
    '.cp-cat:last-child{border-bottom:none;}',
    '.cp-cat-info{}',
    '.cp-cat-name{font-size:0.82rem;font-weight:600;color:#f0f0f0;margin-bottom:2px;}',
    '.cp-cat-desc{font-size:0.72rem;color:#4a6d8c;line-height:1.5;}',
    /* toggle switch */
    '.cp-switch{position:relative;width:40px;height:22px;flex-shrink:0;margin-left:16px;}',
    '.cp-switch input{opacity:0;width:0;height:0;position:absolute;}',
    '.cp-switch-track{',
      'position:absolute;inset:0;border-radius:100px;',
      'background:rgba(255,255,255,0.12);cursor:pointer;transition:background 0.2s;',
    '}',
    '.cp-switch-track::after{',
      'content:"";position:absolute;top:3px;left:3px;',
      'width:16px;height:16px;border-radius:50%;',
      'background:#fff;transition:transform 0.2s;',
    '}',
    '.cp-switch input:checked~.cp-switch-track{background:#ff5e00;}',
    '.cp-switch input:checked~.cp-switch-track::after{transform:translateX(18px);}',
    '.cp-switch input:disabled~.cp-switch-track{opacity:0.45;cursor:not-allowed;}',
    /* footer link */
    '.cp-footer-link{cursor:pointer;background:none;border:none;padding:0;font-family:inherit;font-size:0.78rem;color:#4a6d8c;text-decoration:none;transition:color 0.2s;}',
    '.cp-footer-link:hover{color:#8aaec8;}',
    '@media(max-width:600px){',
      '#cp-popup{bottom:0;left:0;right:0;transform:none;width:100%;border-radius:14px 14px 0 0;}',
      '#cp-popup.cp-hidden{transform:translateY(16px);}',
      '.cp-buttons{flex-direction:column;}',
      '.cp-btn{text-align:center;}',
    '}'
  ].join('');

  /* ── HTML ── */
  function buildHTML(prefs) {
    return [
      '<div id="cp-popup" class="cp-hidden" role="dialog" aria-label="Cookie-Einstellungen">',
        '<p class="cp-text">Diese Website verwendet Cookies. Wählen Sie, welche Cookies Sie zulassen möchten.</p>',
        '<div class="cp-links">',
          '<a href="/impressum.html">Impressum</a>',
          '<a href="/datenschutz.html">Datenschutz</a>',
          '<a href="/cookies.html">Cookie-Richtlinie</a>',
        '</div>',
        '<div class="cp-buttons">',
          '<button class="cp-btn cp-btn-accept" id="cp-accept-all">Alle akzeptieren</button>',
          '<button class="cp-btn cp-btn-save" id="cp-save-sel">Auswahl speichern</button>',
          '<button class="cp-btn cp-btn-necessary" id="cp-necessary">Nur notwendige</button>',
        '</div>',
        '<button class="cp-toggle-btn" id="cp-details-toggle"><span class="cp-chevron"></span>Details anzeigen</button>',
        '<div class="cp-details" id="cp-details" style="display:none">',
          buildCategory('Notwendig', 'Technisch erforderlich für den Betrieb der Website. Kann nicht deaktiviert werden.', 'necessary', true, true),
          buildCategory('Funktional', 'Speichert Ihre Einstellungen und Cookie-Präferenzen.', 'functional', prefs.functional, false),
          buildCategory('Performance', 'Erfassen, wie die Website genutzt wird, um sie zu verbessern.', 'performance', prefs.performance, false),
          buildCategory('Marketing', 'Externe Anbieter für zielgerichtete Inhalte. Derzeit nicht aktiv.', 'marketing', prefs.marketing, false),
        '</div>',
      '</div>'
    ].join('');
  }

  function buildCategory(name, desc, id, checked, disabled) {
    return [
      '<div class="cp-cat">',
        '<div class="cp-cat-info">',
          '<div class="cp-cat-name">' + name + '</div>',
          '<div class="cp-cat-desc">' + desc + '</div>',
        '</div>',
        '<label class="cp-switch">',
          '<input type="checkbox" id="cp-cat-' + id + '"' + (checked ? ' checked' : '') + (disabled ? ' disabled' : '') + '>',
          '<span class="cp-switch-track"></span>',
        '</label>',
      '</div>'
    ].join('');
  }

  /* ── LOGIC ── */
  function getPrefs() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored) return JSON.parse(stored);
    } catch (e) {}
    return { functional: false, performance: false, marketing: false };
  }

  function savePrefs(prefs) {
    prefs.accepted = true;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch (e) {}
  }

  function hide() {
    var el = document.getElementById('cp-popup');
    if (el) {
      el.classList.add('cp-hidden');
      setTimeout(function () { el.style.display = 'none'; }, 350);
    }
  }

  function show() {
    var el = document.getElementById('cp-popup');
    if (el) {
      el.style.display = '';
      setTimeout(function () { el.classList.remove('cp-hidden'); }, 10);
    }
  }

  function currentSelections() {
    return {
      functional:  !!(document.getElementById('cp-cat-functional')  || {}).checked,
      performance: !!(document.getElementById('cp-cat-performance') || {}).checked,
      marketing:   !!(document.getElementById('cp-cat-marketing')   || {}).checked
    };
  }

  function injectFooterLink() {
    var footers = document.querySelectorAll('.footer-inner');
    footers.forEach(function (fi) {
      if (fi.querySelector('.cp-footer-link')) return;
      var btn = document.createElement('button');
      btn.className = 'cp-footer-link';
      btn.textContent = 'Cookie-Einstellungen';
      btn.addEventListener('click', function () { show(); });
      // find last child that holds the links, or append to footer-inner
      var linkDiv = fi.querySelector('div');
      if (linkDiv) linkDiv.appendChild(btn);
      else fi.appendChild(btn);
    });
  }

  function init() {
    /* inject CSS */
    var styleEl = document.createElement('style');
    styleEl.textContent = css;
    document.head.appendChild(styleEl);

    /* inject popup */
    var prefs = getPrefs();
    var wrapper = document.createElement('div');
    wrapper.innerHTML = buildHTML(prefs);
    document.body.appendChild(wrapper.firstElementChild);

    /* buttons */
    document.getElementById('cp-accept-all').addEventListener('click', function () {
      savePrefs({ functional: true, performance: true, marketing: true });
      hide();
    });

    document.getElementById('cp-save-sel').addEventListener('click', function () {
      savePrefs(currentSelections());
      hide();
    });

    document.getElementById('cp-necessary').addEventListener('click', function () {
      savePrefs({ functional: false, performance: false, marketing: false });
      hide();
    });

    /* details toggle */
    var detailsToggle = document.getElementById('cp-details-toggle');
    var detailsPanel  = document.getElementById('cp-details');
    detailsToggle.addEventListener('click', function () {
      var open = detailsPanel.style.display !== 'none';
      detailsPanel.style.display = open ? 'none' : '';
      detailsToggle.classList.toggle('open', !open);
      detailsToggle.querySelector('.cp-chevron').style.display = '';
    });

    /* footer link – disabled: Cookie-Einstellungen ist jetzt in der Nav */
    // injectFooterLink();

    /* show if no consent yet */
    if (!localStorage.getItem(STORAGE_KEY)) {
      setTimeout(function () { show(); }, 400);
    }
  }

  /* expose for external "Cookie-Einstellungen" triggers */
  window.openCookieSettings = function () { show(); };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
