/* Money lock — the reveal side of scripts/lock_money.mjs.
 *
 * The build strips every monetary value out of the deployed payloads and seals
 * them in an AES-256-GCM blob. Nothing here can invent a number: until the
 * passcode derives the right key the figures are simply absent, which is what
 * makes this a lock rather than a curtain.
 *
 * Pages use it in three lines:
 *     MoneyLock.attach(data, render)   // after fetching the payload
 *     MoneyLock.fmt(v)                 // wherever a figure is printed
 *     MoneyLock.mount(el)              // wherever the control belongs
 */
(function () {
  var L = {
    locked: false,
    _blob: null,
    _data: null,
    _render: null,

    /** Wire the payload. No `_locked` (the local server) = nothing to do. */
    attach: function (data, render) {
      this._data = data;
      this._render = render;
      this._blob = data && data._locked;
      this.locked = !!this._blob;
      return this.locked;
    },

    /** Format a figure. `null` while locked means sealed, not missing — the
     *  distinction matters because a garment with no price at all should stay
     *  blank rather than pretend to be hiding something. */
    fmt: function (v, blankIfEmpty) {
      if (this.locked) return '$XXX';
      if (v == null || v === '') return blankIfEmpty ? '' : '$0';
      return '$' + Math.round(v).toLocaleString();
    },

    _b64: function (s) {
      var bin = atob(s), a = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
      return a;
    },

    /** Put the decrypted figures back exactly where the build took them from. */
    _apply: function (entries) {
      for (var i = 0; i < entries.length; i++) {
        var path = entries[i][0], node = this._data;
        for (var j = 0; j < path.length - 1; j++) node = node[path[j]];
        node[path[path.length - 1]] = entries[i][1];
      }
    },

    unlock: async function (passcode) {
      var b = this._blob, enc = new TextEncoder();
      var base = await crypto.subtle.importKey('raw', enc.encode(passcode),
        'PBKDF2', false, ['deriveKey']);
      var key = await crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: this._b64(b.kdf.salt),
          iterations: b.kdf.iterations, hash: b.kdf.hash },
        base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
      // A wrong passcode fails the GCM tag check and throws — there is no
      // comparison here to get subtly wrong, and no way to half-succeed.
      var plain = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: this._b64(b.iv) }, key, this._b64(b.ct));
      this._apply(JSON.parse(new TextDecoder().decode(plain)));
      this.locked = false;
      if (this._render) this._render();
      return true;
    },

    /** The control. Absent entirely when there is nothing locked. */
    mount: function (host) {
      if (!this.locked || !host) return;
      var wrap = document.createElement('span');
      wrap.className = 'moneylock';
      wrap.innerHTML =
        '<button type="button" class="ml-open">figures hidden · reveal</button>'
        + '<span class="ml-form" hidden>'
        + '<input type="password" class="ml-code" placeholder="passcode" '
        + 'autocomplete="off" spellcheck="false">'
        + '<button type="button" class="ml-go">unlock</button>'
        + '<span class="ml-msg"></span></span>';
      host.appendChild(wrap);

      var open = wrap.querySelector('.ml-open'), form = wrap.querySelector('.ml-form');
      var input = wrap.querySelector('.ml-code'), go = wrap.querySelector('.ml-go');
      var msg = wrap.querySelector('.ml-msg'), self = this;

      open.addEventListener('click', function () {
        open.hidden = true; form.hidden = false; input.focus();
      });
      async function submit() {
        msg.textContent = '';
        try {
          await self.unlock(input.value);
          wrap.remove();
        } catch (e) {
          msg.textContent = 'no';
          input.select();
        }
      }
      go.addEventListener('click', submit);
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') submit();
      });
    }
  };
  window.MoneyLock = L;
})();
