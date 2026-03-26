(function () {
  'use strict';

  var css = [
    /* nav-left: logo + legal links */
    'nav .nav-left{display:flex;align-items:center;gap:20px;min-width:0;}',
    'nav .nav-logo{white-space:nowrap!important;}',
    'nav .nav-legal{display:flex;gap:14px;align-items:center;}',
    'nav .nav-legal a, nav .nav-legal button{',
      'font-size:0.62rem;color:rgba(255,255,255,0.3);text-decoration:none;',
      'background:none;border:none;cursor:pointer;font-family:"Inter",sans-serif;',
      'padding:0;transition:color 0.2s;letter-spacing:0.03em;',
    '}',
    'nav .nav-legal a:hover, nav .nav-legal button:hover{color:rgba(255,255,255,0.6);}',

    /* hamburger button */
    '.nav-burger{',
      'background:none;border:1px solid rgba(255,255,255,0.15);border-radius:8px;',
      'cursor:pointer;width:38px;height:32px;',
      'display:flex;flex-direction:column;justify-content:center;align-items:center;gap:5px;',
      'padding:0;transition:border-color 0.2s;flex-shrink:0;',
    '}',
    '.nav-burger:hover{border-color:rgba(255,255,255,0.4);}',
    '.nav-burger span{',
      'display:block;width:16px;height:1.5px;',
      'background:rgba(255,255,255,0.8);',
      'transition:transform 0.3s ease,opacity 0.3s ease;',
      'transform-origin:center;',
    '}',
    '.nav-burger.open span:nth-child(1){transform:translateY(6.5px) rotate(45deg);}',
    '.nav-burger.open span:nth-child(2){opacity:0;}',
    '.nav-burger.open span:nth-child(3){transform:translateY(-6.5px) rotate(-45deg);}',

    /* overlay */
    '.nav-overlay{',
      'position:fixed;inset:0;background:rgba(0,0,0,0.45);',
      'z-index:198;opacity:0;pointer-events:none;',
      'transition:opacity 0.35s;',
    '}',
    '.nav-overlay.open{opacity:1;pointer-events:all;}',

    /* slide panel */
    '.nav-panel{',
      'position:fixed;top:0;right:0;height:100vh;width:300px;',
      'background:rgba(9,22,42,0.98);backdrop-filter:blur(24px);',
      'border-left:1px solid rgba(0,119,200,0.15);',
      'z-index:199;display:flex;flex-direction:column;',
      'justify-content:center;padding:60px 44px;',
      'transform:translateX(100%);',
      'transition:transform 0.4s cubic-bezier(0.4,0,0.2,1);',
    '}',
    '.nav-panel.open{transform:translateX(0);}',

    /* menu items inside panel */
    '.nav-panel .nav-menu{',
      'display:flex!important;flex-direction:column;gap:0;list-style:none;',
    '}',
    '.nav-panel .nav-menu li a{',
      'display:block;padding:15px 0;',
      'font-size:1.35rem;font-weight:800;letter-spacing:-0.02em;',
      'color:rgba(255,255,255,0.45);text-decoration:none;',
      'border:none!important;background:none!important;border-radius:0!important;',
      'backdrop-filter:none!important;',
      'border-bottom:1px solid rgba(255,255,255,0.06)!important;',
      'transition:color 0.2s;',
    '}',
    '.nav-panel .nav-menu li:last-child a{border-bottom:none!important;}',
    '.nav-panel .nav-menu li a:hover,.nav-panel .nav-menu li a.active{color:#fff;}',

    /* panel close btn */
    '.nav-panel-close{',
      'position:absolute;top:24px;right:24px;',
      'background:none;border:none;cursor:pointer;',
      'color:rgba(255,255,255,0.4);font-size:1.2rem;',
      'transition:color 0.2s;line-height:1;padding:4px;',
    '}',
    '.nav-panel-close:hover{color:#fff;}',

    /* panel label */
    '.nav-panel-label{',
      'font-size:0.62rem;font-weight:600;letter-spacing:0.16em;',
      'text-transform:uppercase;color:rgba(255,255,255,0.2);',
      'margin-bottom:28px;',
    '}',
    '.nav-panel-legal{',
      'margin-top:40px;padding-top:24px;',
      'border-top:1px solid rgba(255,255,255,0.08);',
      'display:flex;flex-direction:column;gap:12px;',
    '}',
    '.nav-panel-legal a,.nav-panel-legal button{',
      'font-size:0.75rem;color:rgba(255,255,255,0.35);text-decoration:none;',
      'background:none;border:none;cursor:pointer;font-family:"Inter",sans-serif;',
      'padding:0;text-align:left;letter-spacing:0.03em;transition:color 0.2s;',
    '}',
    '.nav-panel-legal a:hover,.nav-panel-legal button:hover{color:rgba(255,255,255,0.7);}',
    '@media(max-width:640px){nav .nav-legal{display:none;}}',

    /* Termin buchen button in panel */
    '.nav-panel-booking{',
      'display:inline-flex;align-items:center;gap:8px;',
      'background:#FF6600;color:#fff;border:none;cursor:pointer;',
      'padding:10px 20px;border-radius:8px;',
      'font-size:0.85rem;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;',
      'font-family:"Inter",sans-serif;transition:filter 0.2s;margin-bottom:32px;',
    '}',
    '.nav-panel-booking:hover{filter:brightness(1.12);}',
    '.nav-panel-booking svg{width:16px;height:16px;flex-shrink:0;}',
    '@media(max-width:640px){.nav-panel-booking{display:none!important;}}'
  ].join('');

  function init() {
    /* inject CSS */
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    var nav = document.querySelector('nav');
    if (!nav) return;

    var logo = nav.querySelector('.nav-logo');
    var menu = nav.querySelector('.nav-menu');

    /* ── 1. Wrap logo + inject legal links ── */
    if (logo && !nav.querySelector('.nav-left')) {
      var navLeft = document.createElement('div');
      navLeft.className = 'nav-left';
      nav.insertBefore(navLeft, logo);
      navLeft.appendChild(logo);
    }

    /* ── 2. Hamburger button ── */
    var burger = document.createElement('button');
    burger.className = 'nav-burger';
    burger.setAttribute('aria-label', 'Menü öffnen');
    burger.innerHTML = '<span></span><span></span><span></span>';
    nav.appendChild(burger);

    /* ── 3. Slide panel ── */
    var overlay = document.createElement('div');
    overlay.className = 'nav-overlay';
    document.body.appendChild(overlay);

    var panel = document.createElement('div');
    panel.className = 'nav-panel';

    var closeBtn = document.createElement('button');
    closeBtn.className = 'nav-panel-close';
    closeBtn.setAttribute('aria-label', 'Menü schließen');
    closeBtn.innerHTML = '&#x2715;';
    panel.appendChild(closeBtn);

    /* Termin buchen button at top */
    var bookingBtn = document.createElement('button');
    bookingBtn.className = 'nav-panel-booking';
    bookingBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>Termin buchen';
    function triggerBooking(e) {
      e.preventDefault();
      e.stopPropagation();
      closePanel();
      setTimeout(function () { if (window.openBooking) openBooking(); }, 350);
    }
    bookingBtn.addEventListener('click', triggerBooking);
    bookingBtn.addEventListener('touchend', triggerBooking);
    panel.appendChild(bookingBtn);

    var panelLabel = document.createElement('div');
    panelLabel.className = 'nav-panel-label';
    panelLabel.textContent = 'Navigation';
    panel.appendChild(panelLabel);

    /* move nav-menu into panel */
    if (menu) {
      panel.appendChild(menu);
    }

    /* legal links at bottom of panel */
    var legalDiv = document.createElement('div');
    legalDiv.className = 'nav-panel-legal';
    legalDiv.innerHTML =
      '<a href="/impressum.html">Impressum</a>' +
      '<a href="/datenschutz.html">Datenschutz</a>' +
      '<button onclick="if(window.openCookieSettings)openCookieSettings()">Cookies</button>';
    panel.appendChild(legalDiv);

    document.body.appendChild(panel);

    /* ── 4. Toggle ── */
    function openPanel() {
      panel.classList.add('open');
      overlay.classList.add('open');
      burger.classList.add('open');
    }
    function closePanel() {
      panel.classList.remove('open');
      overlay.classList.remove('open');
      burger.classList.remove('open');
    }

    burger.addEventListener('click', function () {
      panel.classList.contains('open') ? closePanel() : openPanel();
    });
    closeBtn.addEventListener('click', closePanel);
    overlay.addEventListener('click', closePanel);

    /* close on nav link click; intercept Kontakt → contact form */
    panel.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function (e) {
        if (a.href.indexOf('mailto:') !== -1 && a.textContent.trim() === 'Kontakt') {
          e.preventDefault();
          closePanel();
          setTimeout(function () {
            if (window.openContactForm) openContactForm();
          }, 350);
        } else {
          closePanel();
        }
      });
    });

    /* ESC key */
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closePanel();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
