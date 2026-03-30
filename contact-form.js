(function () {
  'use strict';

  /* ── LANGUAGE DETECTION ── */
  var path = window.location.pathname;
  var isEN = path.indexOf('-en') !== -1 || path.indexOf('-us') !== -1;

  var T = {
    title:       isEN ? 'Get in touch'                              : 'Schreib mir',
    sub:         isEN ? "I'll get back to you personally."          : 'Ich melde mich persönlich bei dir.',
    vorname:     isEN ? 'First name'                                : 'Vorname',
    nachname:    isEN ? 'Last name'                                 : 'Nachname',
    email:       isEN ? 'Email'                                     : 'E-Mail',
    tel:         isEN ? 'Phone <span style="color:rgba(255,255,255,0.25);font-weight:400;">(optional)</span>'
                      : 'Telefon <span style="color:rgba(255,255,255,0.25);font-weight:400;">(optional)</span>',
    telHint:     isEN ? '📱 WhatsApp-capable number only — I will call you via WhatsApp.'
                      : '📱 Bitte nur WhatsApp-fähige Nummer angeben – ich rufe via WhatsApp an.',
    telPh:       isEN ? '+1 555 123 456'                            : '+49 123 456789',
    bereich:     isEN ? "I'm interested in"                         : 'Ich interessiere mich für',
    selectPh:    isEN ? 'Select area …'                             : 'Bereich auswählen …',
    nachricht:   isEN ? 'Your message'                              : 'Deine Nachricht',
    nachrichtPh: isEN ? 'How can I help you?'                       : 'Wie kann ich dir helfen?',
    privacy:     isEN
      ? 'By submitting your message you agree to the processing of your data in accordance with our <a href="/datenschutz.html" target="_blank">Privacy Policy</a>.'
      : 'Mit dem Absenden deiner Nachricht stimmst du der Verarbeitung deiner Daten gemäß unserer <a href="/datenschutz.html" target="_blank">Datenschutzerklärung</a> zu.',
    submit:      isEN ? 'Send message'                              : 'Nachricht senden',
    sending:     isEN ? 'Sending …'                                 : 'Wird gesendet …',
    successTitle:isEN ? 'Message sent!'                             : 'Nachricht gesendet!',
    successText: isEN ? "Thank you for your message. I'll get back to you as soon as possible."
                      : 'Danke für deine Nachricht. Ich melde mich so schnell wie möglich bei dir.',
    close:       isEN ? 'Close'                                     : 'Schließen',
    ariaLabel:   isEN ? 'Contact form'                              : 'Kontaktformular',
    fallbackSubject: isEN ? 'Enquiry from ' : 'Anfrage von '
  };

  var css = [
    /* overlay */
    '.cf-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:19998;opacity:0;pointer-events:none;transition:opacity 0.3s;}',
    '.cf-overlay.open{opacity:1;pointer-events:all;}',

    /* modal */
    '.cf-modal{',
      'position:fixed;top:50%;left:50%;transform:translate(-50%,-48%);',
      'z-index:19999;width:min(520px,94vw);max-height:90vh;overflow-y:auto;',
      'background:rgba(9,22,42,0.98);backdrop-filter:blur(24px);',
      'border:1px solid rgba(0,119,200,0.2);border-radius:16px;',
      'padding:40px;opacity:0;pointer-events:none;',
      'transition:opacity 0.3s,transform 0.3s;',
    '}',
    '.cf-modal.open{opacity:1;pointer-events:all;transform:translate(-50%,-50%);}',

    /* close */
    '.cf-close{position:absolute;top:18px;right:20px;background:none;border:none;',
      'color:rgba(255,255,255,0.4);font-size:1.1rem;cursor:pointer;padding:4px;',
      'transition:color 0.2s;line-height:1;font-family:inherit;}',
    '.cf-close:hover{color:#fff;}',

    /* heading */
    '.cf-title{font-size:1.3rem;font-weight:800;color:#fff;margin-bottom:6px;letter-spacing:-0.02em;}',
    '.cf-sub{font-size:0.82rem;color:rgba(255,255,255,0.4);margin-bottom:28px;}',

    /* form layout — Nachname column slightly narrower */
    '.cf-row{display:grid;grid-template-columns:1.2fr 0.8fr;gap:14px;margin-bottom:14px;}',
    '.cf-field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px;}',
    '.cf-field label{font-size:0.72rem;font-weight:600;letter-spacing:0.06em;',
      'text-transform:uppercase;color:rgba(255,255,255,0.45);}',
    '.cf-field input,.cf-field select,.cf-field textarea{',
      'background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);',
      'border-radius:8px;padding:11px 14px;color:#fff;',
      'font-family:"Inter",sans-serif;font-size:0.875rem;outline:none;',
      'transition:border-color 0.2s,background 0.2s;',
    '}',
    '.cf-field input:focus,.cf-field select:focus,.cf-field textarea:focus{',
      'border-color:rgba(255,94,0,0.6);background:rgba(255,255,255,0.09);',
    '}',
    '.cf-field input::placeholder,.cf-field textarea::placeholder{color:rgba(255,255,255,0.2);}',
    '.cf-field select{appearance:none;cursor:pointer;}',
    '.cf-field select option{background:#0d2540;color:#fff;}',
    '.cf-field textarea{resize:vertical;min-height:110px;}',

    /* required star */
    '.cf-field .req{color:#ff5e00;}',

    /* phone hint */
    '.cf-tel-hint{font-size:0.7rem;color:rgba(255,255,255,0.3);margin-top:4px;line-height:1.4;}',

    /* submit */
    '.cf-submit{width:100%;padding:13px;border-radius:10px;border:none;',
      'background:#ff5e00;color:#fff;font-family:"Inter",sans-serif;',
      'font-size:0.9rem;font-weight:700;cursor:pointer;letter-spacing:0.02em;',
      'transition:filter 0.2s,transform 0.15s;margin-top:6px;}',
    '.cf-submit:hover{filter:brightness(1.1);}',
    '.cf-submit:active{transform:scale(0.98);}',
    '.cf-submit:disabled{opacity:0.5;cursor:not-allowed;filter:none;}',

    /* success */
    '.cf-success{text-align:center;padding:20px 0;}',
    '.cf-success-icon{font-size:2.5rem;margin-bottom:12px;}',
    '.cf-success h3{color:#fff;font-size:1.1rem;font-weight:700;margin-bottom:8px;}',
    '.cf-success p{color:rgba(255,255,255,0.5);font-size:0.85rem;line-height:1.6;}',

    /* privacy hint */
    '.cf-privacy{font-size:0.72rem;color:rgba(255,255,255,0.35);line-height:1.55;margin-bottom:12px;margin-top:4px;}',
    '.cf-privacy a{color:rgba(255,255,255,0.5);text-decoration:underline;}',
    '.cf-privacy a:hover{color:rgba(255,255,255,0.75);}',

    /* error */
    '.cf-error{font-size:0.75rem;color:#ff5e00;margin-top:4px;}',

    /* mobile */
    '@media(max-width:480px){.cf-modal{padding:28px 20px;}.cf-row{grid-template-columns:1fr;}}'
  ].join('');

  var HTML =
    '<div class="cf-overlay" id="cfOverlay"></div>' +
    '<div class="cf-modal" id="cfModal" role="dialog" aria-modal="true" aria-label="' + T.ariaLabel + '">' +
      '<button class="cf-close" id="cfClose" aria-label="' + T.close + '">&#x2715;</button>' +
      '<div class="cf-title">' + T.title + '</div>' +
      '<div class="cf-sub">' + T.sub + '</div>' +
      '<form id="cfForm" novalidate>' +
        '<input type="hidden" name="form-name" value="kontakt">' +
        '<div class="cf-row">' +
          '<div class="cf-field">' +
            '<label>' + T.vorname + ' <span class="req">*</span></label>' +
            '<input type="text" name="vorname" placeholder="' + (isEN ? 'Jane' : 'Max') + '" required>' +
          '</div>' +
          '<div class="cf-field">' +
            '<label>' + T.nachname + ' <span class="req">*</span></label>' +
            '<input type="text" name="nachname" placeholder="' + (isEN ? 'Doe' : 'Müller') + '" required>' +
          '</div>' +
        '</div>' +
        '<div class="cf-field">' +
          '<label>' + T.email + ' <span class="req">*</span></label>' +
          '<input type="email" name="email" placeholder="' + (isEN ? 'your@email.com' : 'deine@email.de') + '" required>' +
        '</div>' +
        '<div class="cf-field">' +
          '<label>' + T.tel + '</label>' +
          '<input type="tel" name="telefon" placeholder="' + T.telPh + '">' +
          '<span class="cf-tel-hint">' + T.telHint + '</span>' +
        '</div>' +
        '<div class="cf-field">' +
          '<label>' + T.bereich + ' <span class="req">*</span></label>' +
          '<select name="bereich" required>' +
            '<option value="" disabled selected>' + T.selectPh + '</option>' +
            '<option value="Training &amp; Speaking">Training &amp; Speaking</option>' +
            '<option value="Coaching – Pathfinders Berlin">Coaching – Pathfinders Berlin</option>' +
            '<option value="AI Automation">AI Automation</option>' +
          '</select>' +
        '</div>' +
        '<div class="cf-field">' +
          '<label>' + T.nachricht + ' <span class="req">*</span></label>' +
          '<textarea name="nachricht" placeholder="' + T.nachrichtPh + '" required></textarea>' +
        '</div>' +
        '<p class="cf-privacy">' + T.privacy + '</p>' +
        '<button type="submit" class="cf-submit" id="cfSubmit" disabled>' + T.submit + '</button>' +
      '</form>' +
      '<div class="cf-success" id="cfSuccess" style="display:none;">' +
        '<div class="cf-success-icon">✅</div>' +
        '<h3>' + T.successTitle + '</h3>' +
        '<p>' + T.successText + '</p>' +
      '</div>' +
    '</div>';

  function encode(data) {
    return Object.keys(data)
      .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(data[k]); })
      .join('&');
  }

  function openForm() {
    document.getElementById('cfOverlay').classList.add('open');
    document.getElementById('cfModal').classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeForm() {
    document.getElementById('cfOverlay').classList.remove('open');
    document.getElementById('cfModal').classList.remove('open');
    document.body.style.overflow = '';
  }

  function init() {
    /* inject CSS */
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    /* inject HTML */
    var tmp = document.createElement('div');
    tmp.innerHTML = HTML;
    while (tmp.firstChild) document.body.appendChild(tmp.firstChild);

    /* close handlers */
    document.getElementById('cfClose').addEventListener('click', closeForm);
    document.getElementById('cfOverlay').addEventListener('click', closeForm);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeForm();
    });

    /* required-field gate: disable submit until all required fields filled */
    var cfForm   = document.getElementById('cfForm');
    var cfSubmit = document.getElementById('cfSubmit');
    var requiredNames = ['vorname', 'nachname', 'email', 'bereich', 'nachricht'];
    function updateSubmitState() {
      var ok = requiredNames.every(function (n) {
        var el = cfForm.querySelector('[name="' + n + '"]');
        return el && el.value.trim() !== '';
      });
      cfSubmit.disabled = !ok;
    }
    requiredNames.forEach(function (n) {
      var el = cfForm.querySelector('[name="' + n + '"]');
      if (el) {
        el.addEventListener('input', updateSubmitState);
        el.addEventListener('change', updateSubmitState);
      }
    });
    updateSubmitState();

    /* form submit */
    document.getElementById('cfForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target;
      var btn  = document.getElementById('cfSubmit');

      /* collect data */
      var data = { 'form-name': 'kontakt' };
      var els  = form.elements;
      for (var i = 0; i < els.length; i++) {
        if (els[i].name) data[els[i].name] = els[i].value;
      }

      btn.disabled    = true;
      btn.textContent = T.sending;

      fetch('/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body:    encode(data)
      })
      .then(function () {
        form.style.display = 'none';
        document.getElementById('cfSuccess').style.display = 'block';
      })
      .catch(function () {
        /* fallback: mailto */
        var subject = encodeURIComponent(T.fallbackSubject + data['vorname'] + ' ' + data['nachname']);
        var body    = encodeURIComponent(
          (isEN ? 'First name' : 'Vorname')  + ': ' + data['vorname']  + '\n' +
          (isEN ? 'Last name'  : 'Nachname') + ': ' + data['nachname'] + '\n' +
          'E-Mail: '                                 + data['email']    + '\n' +
          (isEN ? 'Phone'      : 'Telefon')  + ': ' + (data['telefon'] || '–') + '\n' +
          (isEN ? 'Area'       : 'Bereich')  + ': ' + data['bereich']  + '\n\n' +
          data['nachricht']
        );
        window.location.href = 'mailto:hallo@tobidolgener.com?subject=' + subject + '&body=' + body;
        btn.disabled    = false;
        btn.textContent = T.submit;
      });
    });

    /* expose globally */
    window.openContactForm = openForm;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
