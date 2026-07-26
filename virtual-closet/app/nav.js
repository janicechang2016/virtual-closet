/* Shared navigation — a hamburger that rolls open top-to-bottom and resolves
   its labels out of noise.
   -------------------------------------------------------------------------
   Why one file: the page links were duplicated inline across five pages, and
   every new page meant editing all of them. This is injected, so a new route is
   one line here.

   The reveal is the ASCII entrance run backwards. The entrance dispels glyphs
   under a DECAYING envelope with noise-clustered per-glyph delays
   (`0.5 + 0.5*sin(x*0.011 + y*0.017)`); this resolves them under a SETTLING one,
   delays clustered by row so the menu materialises roughly downward while
   individual characters still land out of order. Same monospace face, same
   black-on-white, so it reads as the same hand.

   Respects `body.demo`: routes that need the local server are omitted from the
   static export, exactly as the inline links were. */
(function () {
  'use strict';

  var ROUTES = [
    { href: '/',             label: 'Archive' },
    { href: '/fitting-room', label: 'Fitting room' },
    { href: '/stylist',      label: 'Stylist',  local: true },
    { href: '/insights',     label: 'Insights', local: true },
    { href: '/galaxy',       label: 'Galaxy',   local: true },
    { href: '/sourcing',     label: 'Sourcing', local: true }
  ];

  // Glyph pool: the menu's own letters plus technical punctuation, the same
  // trick the entrance uses (it scrambles with the passage it is drawing).
  var POOL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ/·—+=<>[]{}|0123456789'.split('');
  var SETTLE = 620;   // ms for one label to resolve once it starts
  var ROW_STEP = 90;  // ms between rows — the downward roll
  var JITTER = 220;   // ms of per-character disorder inside a label

  function css() {
    return [
      // No box: three hairlines, the same weight as every other rule on the
      // site. The hit area stays 34px via padding, not a visible border.
      '#navburger{z-index:120;width:34px;height:34px;border:0;background:none;',
      '  cursor:pointer;padding:0;display:flex;flex-direction:column;',
      '  align-items:center;justify-content:center;gap:5px;}',
      // Mounted into a page header it sits in the flow and aligns with its
      // neighbours; only pages without a mount point get the floating fallback,
      // which is what was covering their content.
      '#navburger.floating{position:fixed;top:6px;right:12px;}',
      '#navburger:not(.floating){margin-left:16px;flex:none;align-self:center;}',
      '#navburger span{display:block;width:18px;height:1px;background:#000;',
      '  transition:transform .28s ease,opacity .2s ease;}',
      '#navburger.open span:nth-child(1){transform:translateY(5px) rotate(45deg);}',
      '#navburger.open span:nth-child(2){opacity:0;}',
      '#navburger.open span:nth-child(3){transform:translateY(-5px) rotate(-45deg);}',
      '#navsheet{position:fixed;inset:0;z-index:110;background:#fff;',
      // the roll: revealed top-to-bottom, not faded in
      '  clip-path:inset(0 0 100% 0);transition:clip-path .52s cubic-bezier(.22,.61,.36,1);',
      '  pointer-events:none;display:flex;align-items:center;justify-content:center;}',
      '#navsheet.open{clip-path:inset(0 0 0 0);pointer-events:auto;}',
      '#navsheet ul{list-style:none;margin:0;padding:0;text-align:center;}',
      '#navsheet li{margin:0 0 18px;}',
      '#navsheet li:last-child{margin-bottom:0;}',
      // routes that need the local server are absent from the static export
      'body.demo #navsheet li[data-local]{display:none;}',
      'body.demo #navsheet li[data-local] + li{margin-top:0;}',
      '#navsheet a{display:inline-block;text-decoration:none;color:#000;',
      "  font:italic 400 26px/1.2 'IBM Plex Mono','Spline Sans Mono',ui-monospace,Menlo,monospace;",
      '  letter-spacing:.06em;text-transform:uppercase;white-space:pre;}',
      '#navsheet a:hover{background:linear-gradient(180deg,#f6f7f9,#e9ebef 55%,#dee1e6);}',
      // keyboard focus stays visible but in the brand's ink, not the browser blue
      '#navsheet a:focus-visible{outline:1px solid #000;outline-offset:5px;}',
      '#navsheet a:focus:not(:focus-visible){outline:none;}',
      '#navburger:focus-visible{outline:1px solid #000;outline-offset:3px;}',
      '#navsheet a[aria-current="page"]{text-decoration:underline;text-underline-offset:6px;}',
      '@media (max-width:760px){#navsheet a{font-size:19px;}}',
      '@media (prefers-reduced-motion:reduce){',
      '  #navsheet{transition:none;}}'
    ].join('');
  }

  function build() {
    if (document.getElementById('navburger')) return;

    var style = document.createElement('style');
    style.textContent = css();
    document.head.appendChild(style);

    var burger = document.createElement('button');
    burger.id = 'navburger';
    burger.setAttribute('aria-label', 'Menu');
    burger.setAttribute('aria-expanded', 'false');
    for (var i = 0; i < 3; i++) burger.appendChild(document.createElement('span'));

    var sheet = document.createElement('div');
    sheet.id = 'navsheet';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    sheet.hidden = false;

    var here = location.pathname.replace(/\/$/, '') || '/';

    var wrap = document.createElement('div');
    var ul = document.createElement('ul');
    ROUTES.forEach(function (r) {
      var li = document.createElement('li');
      // Marked, not omitted. `body.demo` is applied AFTER an async manifest
      // fetch, so reading it at build time raced and the static export offered
      // three links that 404. CSS has no timing to lose.
      if (r.local) li.setAttribute('data-local', '');
      var a = document.createElement('a');
      a.href = r.href;
      a.dataset.text = r.label;
      a.textContent = r.label;                    // untrusted-safe, and the
                                                  // no-JS/reduced-motion state
      if ((r.href.replace(/\/$/, '') || '/') === here) a.setAttribute('aria-current', 'page');
      li.appendChild(a); ul.appendChild(li);
    });
    wrap.appendChild(ul);
    sheet.appendChild(wrap);

    document.body.appendChild(sheet);
    // Mount into the page's own header so the button aligns with what is
    // already there — but only where that actually works. A column stack would
    // put it under the readout, and a space-between row would shove the
    // readout to the middle. Both were observed; both are worse than floating.
    var mount = document.querySelector('[data-nav-mount]');
    var mounted = false;
    if (mount) {
      var cs = getComputedStyle(mount);
      var column = cs.display.indexOf('flex') >= 0 && cs.flexDirection.indexOf('column') === 0;
      if (!column) {
        var last = mount.lastElementChild;
        mount.appendChild(burger);
        // In a space-between row the new last child would redistribute the
        // others; pinning the previous item keeps them exactly where they were.
        if (last && cs.justifyContent === 'space-between') last.style.marginLeft = 'auto';
        mounted = true;
      }
    }
    if (!mounted) {
      burger.classList.add('floating');
      document.body.appendChild(burger);
    }

    var open = false, raf = null;

    function scramble() {
      var links = [].slice.call(sheet.querySelectorAll('a'));
      var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reduced) {                              // resolve immediately
        links.forEach(function (a) { a.textContent = a.dataset.text; });
        return;
      }
      var start = performance.now();
      var plan = links.map(function (a, row) {
        var text = a.dataset.text;
        return {
          el: a,
          text: text,
          // Row sets the downward roll; the sine gives the same clustered
          // disorder the entrance uses, so characters do not land in reading
          // order.
          delays: text.split('').map(function (_, i) {
            var cluster = 0.5 + 0.5 * Math.sin(i * 0.9 + row * 1.7);
            return row * ROW_STEP + cluster * JITTER + Math.random() * JITTER;
          })
        };
      });

      cancelAnimationFrame(raf);
      (function tick(now) {
        var t = now - start, done = true;
        plan.forEach(function (p) {
          var out = '';
          for (var i = 0; i < p.text.length; i++) {
            var ch = p.text[i];
            if (ch === ' ') { out += ' '; continue; }
            var e = t - p.delays[i];
            if (e >= SETTLE) { out += ch; continue; }
            done = false;
            if (e < 0) { out += ' '; continue; }
            // settle: the closer to resolved, the likelier the true glyph
            out += (Math.random() < e / SETTLE) ? ch
                 : POOL[(Math.random() * POOL.length) | 0];
          }
          p.el.textContent = out;
        });
        if (!done) raf = requestAnimationFrame(tick);
      })(performance.now());
    }

    function setOpen(v) {
      open = v;
      sheet.classList.toggle('open', v);
      burger.classList.toggle('open', v);
      burger.setAttribute('aria-expanded', String(v));
      document.documentElement.style.overflow = v ? 'hidden' : '';
      if (v) {
        // let the roll get underway before the labels resolve
        setTimeout(scramble, 160);
        var first = sheet.querySelector('a');
        if (first) setTimeout(function () { first.focus(); }, 220);
      } else {
        cancelAnimationFrame(raf);
        [].forEach.call(sheet.querySelectorAll('a'), function (a) {
          a.textContent = a.dataset.text;
        });
        burger.focus();
      }
    }

    burger.addEventListener('click', function () { setOpen(!open); });
    sheet.addEventListener('click', function (e) {
      if (e.target === sheet || e.target === wrap) setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && open) setOpen(false);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }
})();
