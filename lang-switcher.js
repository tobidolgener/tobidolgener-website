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

  var path      = window.location.pathname;
  var isEnglish = path.indexOf('-en') !== -1;
  /* Always navigate to the home page of the target language */
  var targetPath = isEnglish ? '/index.html' : '/index-en.html';

  var css = [
    /* wrapper – fixed, positioned dynamically via JS */
    '.ls-wrap{position:fixed;z-index:9999;display:flex;align-items:center;}',

    /* trigger button – styled to match .cw-main */
    '.ls-trigger{',
      'display:inline-flex;align-items:center;gap:4px;',
      'background:rgba(255,94,0,0.12);',
      'border:1px solid rgba(255,94,0,0.35);',
      'border-radius:5px;cursor:pointer;',
      'font-size:inherit;line-height:1;',
      'padding:0 8px;height:100%;',
      'color:rgba(255,255,255,0.85);',
      'transition:border-color 0.2s,background 0.2s;',
      'white-space:nowrap;font-family:"Inter",sans-serif;',
    '}',
    '.ls-trigger:hover{border-color:rgba(255,94,0,0.7);background:rgba(255,94,0,0.2);}',
    '.ls-arrow{font-size:0.55em;color:rgba(255,255,255,0.5);transition:transform 0.2s;display:inline-block;margin-top:1px;}',
    '.ls-wrap.open .ls-arrow{transform:rotate(180deg);}',

    /* dropdown panel */
    '.ls-panel{',
      'position:absolute;top:calc(100% + 8px);left:0;',
      'background:rgba(9,22,42,0.98);backdrop-filter:blur(20px);',
      'border:1px solid rgba(0,119,200,0.2);border-radius:10px;',
      'padding:6px;min-width:148px;z-index:9999;',
      'opacity:0;pointer-events:none;transform:translateY(-6px);',
      'transition:opacity 0.18s,transform 0.18s;',
    '}',
    '.ls-wrap.open .ls-panel{opacity:1;pointer-events:all;transform:translateY(0);}',

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

  function positionNext(wrap, cw) {
    var r      = cw.getBoundingClientRect();
    var h      = Math.round(r.height);
    var top    = Math.round(r.top);
    var left   = Math.round(r.left) - 15 - wrap.offsetWidth;
    wrap.style.cssText = [
      'position:fixed',
      'z-index:9999',
      'top:' + top + 'px',
      'left:' + left + 'px',
      'height:' + h + 'px',
      'font-size:' + Math.round(r.height * 0.56) + 'px',
      'display:flex',
      'align-items:center'
    ].join(';') + ';';
  }

  function init() {
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    /* build dropdown */
    var wrap = document.createElement('div');
    wrap.className = 'ls-wrap';

    var trigger = document.createElement('button');
    trigger.className = 'ls-trigger';
    trigger.setAttribute('aria-label', 'Select language');
    trigger.innerHTML = (isEnglish ? '🇦🇺' : '🇩🇪') + '&nbsp;<span class="ls-arrow">▾</span>';

    var panel = document.createElement('div');
    panel.className = 'ls-panel';

    var deOpt = document.createElement('button');
    deOpt.className = 'ls-option' + (!isEnglish ? ' ls-active' : '');
    deOpt.innerHTML = '🇩🇪 <span>Deutsch</span>' + (!isEnglish ? '<span class="ls-check">✓</span>' : '');
    deOpt.addEventListener('click', function (e) {
      e.stopPropagation();
      if (isEnglish) window.location.href = targetPath;
      else closeDD();
    });

    var enOpt = document.createElement('button');
    enOpt.className = 'ls-option' + (isEnglish ? ' ls-active' : '');
    enOpt.innerHTML = '🇦🇺 <span>English</span>' + (isEnglish ? '<span class="ls-check">✓</span>' : '');
    enOpt.addEventListener('click', function (e) {
      e.stopPropagation();
      if (!isEnglish) window.location.href = targetPath;
      else closeDD();
    });

    panel.appendChild(deOpt);
    panel.appendChild(enOpt);
    wrap.appendChild(trigger);
    wrap.appendChild(panel);
    document.body.appendChild(wrap);

    function openDD()  { wrap.classList.add('open'); }
    function closeDD() { wrap.classList.remove('open'); }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      wrap.classList.contains('open') ? closeDD() : openDD();
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) closeDD();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDD();
    });

    /* position next to .cw-main – poll until it appears */
    var tries = 0;
    var timer = setInterval(function () {
      var cw = document.querySelector('.cw-main');
      if (cw || tries > 40) {
        clearInterval(timer);
        if (!cw) return;
        positionNext(wrap, cw);
        /* reposition on resize */
        window.addEventListener('resize', function () { positionNext(wrap, cw); });
      }
      tries++;
    }, 50);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
