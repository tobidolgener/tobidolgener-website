(function () {
  'use strict';

  /* ── SVG ICONS ── */
  var SVG = {
    chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    whatsapp: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>',
    instagram: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>',
    tiktok: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.27 6.27 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.18 8.18 0 004.79 1.54V6.78a4.85 4.85 0 01-1.02-.09z"/></svg>',
    facebook: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>',
    linkedin: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>',
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'
  };

  /* ── BUTTON CONFIG (bottom → top) ── */
  var BTNS = [
    { label: 'Schreib mir', href: 'mailto:hallo@tobidolgener.com', color: '#ff5e00', icon: 'chat',      target: '_self'  },
    { label: 'WhatsApp',    href: 'https://wa.me/4915225210226',                      color: '#25D366', icon: 'whatsapp',  target: '_blank' },
    { label: 'Instagram',   href: 'https://www.instagram.com/pathfindersberlin/',     color: '#E1306C', icon: 'instagram', target: '_blank' },
    { label: 'TikTok',      href: 'https://www.tiktok.com/@pathfinders_denkfabrik',  color: '#010101', icon: 'tiktok',    target: '_blank' },
    { label: 'Facebook',    href: 'https://www.facebook.com/profile.php?id=61588410167429', color: '#1877F2', icon: 'facebook', target: '_blank' },
    { label: 'LinkedIn',    href: 'https://www.linkedin.com/in/tobias-dolgener/',    color: '#0A66C2', icon: 'linkedin',  target: '_blank' }
  ];

  /* ── SOCIAL FOOTER CONFIG ── */
  var SOCIAL = [
    { label: 'LinkedIn',  href: 'https://www.linkedin.com/in/tobias-dolgener/',    icon: 'linkedin'  },
    { label: 'Instagram', href: 'https://www.instagram.com/pathfindersberlin/',     icon: 'instagram' },
    { label: 'TikTok',    href: 'https://www.tiktok.com/@pathfinders_denkfabrik',  icon: 'tiktok'    },
    { label: 'Facebook',  href: 'https://www.facebook.com/profile.php?id=61588410167429', icon: 'facebook' },
    { label: 'WhatsApp',  href: 'https://wa.me/4915225210226',                      icon: 'whatsapp'  }
  ];

  /* ── CSS ── */
  var css = [
    /* wrap */
    '.cw-wrap{position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:9999;display:flex;flex-direction:column;align-items:center;gap:8px;}',
    /* option items */
    '.cw-item{display:flex;align-items:center;gap:10px;opacity:0;transform:translateY(-8px) scale(0.85);transition:opacity 0.25s ease,transform 0.25s ease;pointer-events:none;}',
    '.cw-wrap.cw-open .cw-item{opacity:1;transform:translateY(0) scale(1);pointer-events:all;}',
    /* stagger delays when opening (bottom first) */
    '.cw-wrap.cw-open .cw-item:nth-child(6){transition-delay:0s;}',
    '.cw-wrap.cw-open .cw-item:nth-child(5){transition-delay:.05s;}',
    '.cw-wrap.cw-open .cw-item:nth-child(4){transition-delay:.1s;}',
    '.cw-wrap.cw-open .cw-item:nth-child(3){transition-delay:.15s;}',
    '.cw-wrap.cw-open .cw-item:nth-child(2){transition-delay:.2s;}',
    '.cw-wrap.cw-open .cw-item:nth-child(1){transition-delay:.25s;}',
    /* action buttons */
    '.cw-btn{width:36px;height:36px;border-radius:50%;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#fff;transition:transform 0.2s,box-shadow 0.2s;box-shadow:0 2px 10px rgba(0,0,0,0.3);}',
    '.cw-btn svg{width:16px;height:16px;flex-shrink:0;}',
    '.cw-btn:hover{transform:scale(1.12);}',
    /* label */
    '.cw-label{background:rgba(10,20,40,0.92);backdrop-filter:blur(8px);color:#f0f0f0;padding:5px 11px;border-radius:6px;font-size:0.72rem;font-weight:600;white-space:nowrap;letter-spacing:0.03em;opacity:0;transition:opacity 0.15s;pointer-events:none;font-family:"Inter",sans-serif;}',
    '.cw-item:hover .cw-label{opacity:1;}',
    /* main button */
    '.cw-main{height:22px;padding:0 8px;border-radius:5px;background:#ff5e00;border:none;cursor:pointer;display:flex;align-items:center;gap:5px;color:#fff;box-shadow:0 2px 6px rgba(255,94,0,0.35);transition:transform 0.3s,filter 0.2s;flex-shrink:0;font-family:"Inter",sans-serif;font-size:0.61rem;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;}',
    '.cw-main svg{width:10px;height:10px;flex-shrink:0;transition:transform 0.35s;}',
    '.cw-main:hover{filter:brightness(1.12);}',
    '.cw-wrap.cw-open .cw-main svg{transform:rotate(45deg);}',
    /* footer social row */
    '.cw-footer-social{border-top:1px solid rgba(0,119,200,0.15);margin-top:16px;padding-top:14px;display:flex;gap:18px;align-items:center;justify-content:center;flex-wrap:wrap;width:100%;}',
    '.cw-footer-social a{display:flex;align-items:center;gap:6px;color:rgba(74,109,140,0.8);text-decoration:none;font-size:0.72rem;font-family:"Inter",sans-serif;transition:color 0.2s;}',
    '.cw-footer-social a:hover{color:#8aaec8;}',
    '.cw-footer-social svg{width:14px;height:14px;flex-shrink:0;}',
    '@media(max-width:480px){.cw-wrap{top:16px;}.cw-btn{width:40px;height:40px;}}'
  ].join('');

  /* ── BUILD WIDGET HTML ── */
  function buildWidget() {
    var items = '';
    // reversed so DOM order is top→bottom but visually bottom→top via flex-col
    for (var i = BTNS.length - 1; i >= 0; i--) {
      var b = BTNS[i];
      items += '<div class="cw-item">'
        + '<a class="cw-btn" href="' + b.href + '" target="' + b.target + '" rel="noopener" style="background:' + b.color + '" aria-label="' + b.label + '">'
        + SVG[b.icon]
        + '</a>'
        + '<span class="cw-label">' + b.label + '</span>'
        + '</div>';
    }
    return '<div class="cw-wrap" id="cwWrap">'
      + '<button class="cw-main" id="cwMain" aria-label="Kontakt öffnen">' + SVG.plus + 'Kontakt</button>'
      + '<div class="cw-options" id="cwOptions">' + items + '</div>'
      + '</div>';
  }

  /* ── INJECT FOOTER SOCIAL ── */
  function injectFooterSocial() {
    document.querySelectorAll('footer').forEach(function (footer) {
      if (footer.querySelector('.cw-footer-social')) return;
      var row = document.createElement('div');
      row.className = 'cw-footer-social';
      var links = SOCIAL.map(function (s) {
        return '<a href="' + s.href + '" target="_blank" rel="noopener" aria-label="' + s.label + '">'
          + SVG[s.icon] + s.label + '</a>';
      }).join('');
      row.innerHTML = links;

      // append inside footer-inner if it exists, otherwise directly in footer
      var fi = footer.querySelector('.footer-inner');
      if (fi) {
        fi.style.flexWrap = 'wrap';
        fi.appendChild(row);
      } else {
        footer.appendChild(row);
      }
    });
  }

  /* ── INIT ── */
  function init() {
    // inject CSS
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    // inject widget
    var tmp = document.createElement('div');
    tmp.innerHTML = buildWidget();
    document.body.appendChild(tmp.firstElementChild);

    // toggle
    var wrap = document.getElementById('cwWrap');
    document.getElementById('cwMain').addEventListener('click', function () {
      wrap.classList.toggle('cw-open');
    });

    // close on outside click
    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) wrap.classList.remove('cw-open');
    });

    // footer
    injectFooterSocial();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
