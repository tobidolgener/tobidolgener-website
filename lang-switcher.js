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
    '/stufe2-en.html':    '/stufe2.html'
  };

  var path       = window.location.pathname;
  var isEnglish  = path.indexOf('-en') !== -1;
  var targetPath = PAGE_MAP[path] || (isEnglish
    ? path.replace('-en.html', '.html')
    : path.replace('.html', '-en.html'));

  /* ── CSS ── */
  var css = [
    '.ls-wrap{position:fixed;top:46px;z-index:9999;',
    'left:48px;',
    'display:flex;align-items:center;gap:3px;}',
    '.ls-btn{background:none;border:none;cursor:pointer;',
    'font-size:1.05rem;padding:1px 2px;border-radius:4px;',
    'line-height:1;transition:opacity 0.2s,transform 0.2s;',
    'opacity:0.35;filter:grayscale(0.4);}',
    '.ls-btn.ls-active{opacity:1;filter:none;transform:scale(1.15);}',
    '.ls-btn:not(.ls-active):hover{opacity:0.75;filter:grayscale(0);}',
    '@media(max-width:640px){',
    '.ls-wrap{left:24px;top:42px;}}'
  ].join('');

  function init() {
    /* inject CSS */
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    /* build widget */
    var wrap = document.createElement('div');
    wrap.className = 'ls-wrap';

    var deBtn = document.createElement('button');
    deBtn.className = 'ls-btn' + (!isEnglish ? ' ls-active' : '');
    deBtn.textContent = '🇩🇪';
    deBtn.title = 'Deutsch';
    deBtn.setAttribute('aria-label', 'Zur deutschen Version wechseln');
    deBtn.addEventListener('click', function () {
      if (isEnglish) window.location.href = targetPath;
    });

    var auBtn = document.createElement('button');
    auBtn.className = 'ls-btn' + (isEnglish ? ' ls-active' : '');
    auBtn.textContent = '🇦🇺';
    auBtn.title = 'English';
    auBtn.setAttribute('aria-label', 'Switch to English version');
    auBtn.addEventListener('click', function () {
      if (!isEnglish) window.location.href = targetPath;
    });

    wrap.appendChild(deBtn);
    wrap.appendChild(auBtn);
    document.body.appendChild(wrap);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
