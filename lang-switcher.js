(function () {
  'use strict';

  /* ── PAGE MAP: German ↔ English ── */
  var PAGE_MAP = {
    '/':                  '/index-en.html',
    '/index.html':        '/index-en.html',
    '/ai.html':           '/ai-en.html',
    '/coaching.html':     '/coaching-en.html',
    '/learning.html':     '/learning-en.html',
    '/produkt.html':      '/produkt-en.html',
    '/stufe2.html':       '/stufe2-en.html',
    '/index-en.html':     '/index.html',
    '/ai-en.html':        '/ai.html',
    '/coaching-en.html':  '/coaching.html',
    '/learning-en.html':  '/learning.html',
    '/produkt-en.html':   '/produkt.html',
    '/stufe2-en.html':    '/stufe2.html',
    '/agb.html':          '/agb-en.html',
    '/agb-en.html':       '/agb.html'
  };

  var path       = window.location.pathname;
  var isEnglish  = path.indexOf('-en') !== -1;
  var targetPath = PAGE_MAP[path] || (isEnglish
    ? path.replace('-en.html', '.html')
    : path.replace('.html', '-en.html'));

  var css = [
    /* dropdown wrapper – sits inline in nav */
    '.ls-dropdown{position:relative;display:inline-flex;align-items:center;margin-right:8px;}',

    /* trigger button – matches hamburger style */
    '.ls-trigger{',
      'background:none;border:1px solid rgba(255,255,255,0.15);border-radius:8px;',
      'cursor:pointer;height:32px;padding:0 10px;',
      'display:inline-flex;align-items:center;gap:5px;',
      'font-size:1rem;line-height:1;',
      'transition:border-color 0.2s;',
    '}',
    '.ls-trigger:hover{border-color:rgba(255,255,255,0.4);}',
    '.ls-arrow{',
      'font-size:0.55rem;color:rgba(255,255,255,0.5);',
      'display:inline-block;transition:transform 0.2s;margin-top:1px;',
    '}',
    '.ls-dropdown.open .ls-arrow{transform:rotate(180deg);}',

    /* dropdown panel */
    '.ls-panel{',
      'position:absolute;top:calc(100% + 8px);right:0;',
      'background:rgba(9,22,42,0.98);backdrop-filter:blur(20px);',
      'border:1px solid rgba(0,119,200,0.2);border-radius:10px;',
      'padding:6px;min-width:148px;z-index:9999;',
      'opacity:0;pointer-events:none;transform:translateY(-6px);',
      'transition:opacity 0.18s,transform 0.18s;',
    '}',
    '.ls-dropdown.open .ls-panel{opacity:1;pointer-events:all;transform:translateY(0);}',

    /* option rows */
    '.ls-option{',
      'display:flex;align-items:center;gap:9px;width:100%;',
      'background:none;border:none;cursor:pointer;',
      'padding:9px 12px;border-radius:7px;',
      'font-size:0.84rem;color:rgba(255,255,255,0.5);',
      'font-family:"Inter",sans-serif;letter-spacing:0.02em;',
      'transition:background 0.15s,color 0.15s;text-align:left;',
    '}',
    '.ls-option:hover{background:rgba(255,255,255,0.07);color:#fff;}',
    '.ls-option.ls-active{color:#fff;font-weight:600;}',
    '.ls-check{margin-left:auto;font-size:0.72rem;color:#0077c8;}'
  ].join('');

  function init() {
    var nav = document.querySelector('nav');
    if (!nav) return;

    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    /* dropdown wrapper */
    var dropdown = document.createElement('div');
    dropdown.className = 'ls-dropdown';

    /* trigger: current flag + arrow */
    var trigger = document.createElement('button');
    trigger.className = 'ls-trigger';
    trigger.setAttribute('aria-label', 'Select language');
    trigger.innerHTML = (isEnglish ? '🇦🇺' : '🇩🇪') + '<span class="ls-arrow">▾</span>';

    /* panel */
    var panel = document.createElement('div');
    panel.className = 'ls-panel';
    panel.setAttribute('role', 'menu');

    /* DE option */
    var deOpt = document.createElement('button');
    deOpt.className = 'ls-option' + (!isEnglish ? ' ls-active' : '');
    deOpt.setAttribute('role', 'menuitem');
    deOpt.innerHTML = '🇩🇪 <span>Deutsch</span>' + (!isEnglish ? '<span class="ls-check">✓</span>' : '');
    deOpt.addEventListener('click', function () {
      if (isEnglish) window.location.href = targetPath;
      else closeDropdown();
    });

    /* EN option */
    var enOpt = document.createElement('button');
    enOpt.className = 'ls-option' + (isEnglish ? ' ls-active' : '');
    enOpt.setAttribute('role', 'menuitem');
    enOpt.innerHTML = '🇦🇺 <span>English</span>' + (isEnglish ? '<span class="ls-check">✓</span>' : '');
    enOpt.addEventListener('click', function () {
      if (!isEnglish) window.location.href = targetPath;
      else closeDropdown();
    });

    panel.appendChild(deOpt);
    panel.appendChild(enOpt);
    dropdown.appendChild(trigger);
    dropdown.appendChild(panel);

    /* insert before hamburger button */
    var burger = nav.querySelector('.nav-burger');
    if (burger) {
      nav.insertBefore(dropdown, burger);
    } else {
      nav.appendChild(dropdown);
    }

    function openDropdown()  { dropdown.classList.add('open'); }
    function closeDropdown() { dropdown.classList.remove('open'); }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      dropdown.classList.contains('open') ? closeDropdown() : openDropdown();
    });

    document.addEventListener('click', closeDropdown);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDropdown();
    });
  }

  /* wait for nav.js to finish building the nav (runs before us) */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
