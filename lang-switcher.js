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

  /* ── CSS (desktop only – mobile handled via JS) ── */
  var css = [
    '.ls-wrap{position:fixed;top:60px;left:48px;z-index:9999;',
    'display:flex;align-items:center;gap:3px;}',
    '.ls-btn{background:none;border:none;cursor:pointer;',
    'font-size:1.05rem;padding:1px 2px;border-radius:4px;',
    'line-height:1;transition:opacity 0.2s,transform 0.2s;',
    'opacity:0.35;filter:grayscale(0.4);}',
    '.ls-btn.ls-active{opacity:1;filter:none;transform:scale(1.15);}',
    '.ls-btn:not(.ls-active):hover{opacity:0.75;filter:grayscale(0);}',
    '@media(max-width:640px){.ls-wrap{display:none;}}'
  ].join('');

  function makeBtn(flag, title, active, onClick) {
    var btn = document.createElement('button');
    btn.className = 'ls-btn' + (active ? ' ls-active' : '');
    btn.textContent = flag;
    btn.title = title;
    btn.addEventListener('click', onClick);
    return btn;
  }

  function placeMobileFlags(deBtn, auBtn) {
    /* wait for contact widget (.cw-main) to exist */
    var tries = 0;
    var timer = setInterval(function () {
      var cw = document.querySelector('.cw-main');
      if (cw || tries > 30) {
        clearInterval(timer);
        if (!cw) return;
        var r    = cw.getBoundingClientRect();
        var top  = Math.round((r.top + r.bottom) / 2 - 11);
        var base = 'position:fixed;z-index:9999;top:' + top + 'px;'
                 + 'background:none;border:none;cursor:pointer;'
                 + 'font-size:1.1rem;line-height:1;padding:0;'
                 + 'opacity:' + (isEnglish ? '0.35' : '1') + ';'
                 + 'filter:' + (isEnglish ? 'grayscale(0.4)' : 'none') + ';'
                 + 'transition:opacity 0.2s;';
        /* 🇩🇪 – 10 px LEFT of widget */
        deBtn.style.cssText = base
          + 'right:' + Math.round(window.innerWidth - r.left + 10) + 'px;';
        /* 🇦🇺 – 10 px RIGHT of widget */
        auBtn.style.cssText = base
          + 'left:' + Math.round(r.right + 10) + 'px;'
          + 'opacity:' + (isEnglish ? '1' : '0.35') + ';'
          + 'filter:' + (isEnglish ? 'none' : 'grayscale(0.4)') + ';';
        document.body.appendChild(deBtn);
        document.body.appendChild(auBtn);
      }
      tries++;
    }, 50);
  }

  function init() {
    /* inject CSS */
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    var deBtn = makeBtn('🇩🇪', 'Deutsch', !isEnglish, function () {
      if (isEnglish) window.location.href = targetPath;
    });
    var auBtn = makeBtn('🇦🇺', 'English', isEnglish, function () {
      if (!isEnglish) window.location.href = targetPath;
    });

    if (window.innerWidth <= 640) {
      /* mobile: flanking the contact widget */
      placeMobileFlags(deBtn, auBtn);
    } else {
      /* desktop: below logo */
      var wrap = document.createElement('div');
      wrap.className = 'ls-wrap';
      wrap.appendChild(deBtn);
      wrap.appendChild(auBtn);
      document.body.appendChild(wrap);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
