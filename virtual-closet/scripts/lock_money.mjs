#!/usr/bin/env node
/**
 * Encrypt every monetary value in the exported payloads.
 *
 * Why this exists: a static site has no server to check a passcode against, so
 * a click-to-reveal built the obvious way is a curtain — the numbers still ship
 * in the JSON and anyone can curl them. This strips the values out of the
 * payloads entirely and puts them in an AES-256-GCM blob keyed by a passcode,
 * so the numbers are genuinely absent until someone types it.
 *
 * Node rather than Python because export_static.py is stdlib-only by design and
 * the stdlib has no AEAD cipher — while node:crypto is guaranteed present in
 * Vercel's build image and needs no dependency.
 *
 * Usage: node lock_money.mjs <site-dir>        (passcode from INSIGHTS_PASSCODE)
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { pbkdf2Sync, randomBytes, createCipheriv } from 'node:crypto';

const SITE = process.argv[2];
const PASSCODE = process.env.INSIGHTS_PASSCODE || '';
const ITERATIONS = 210000;

// Exact key names, not substrings: `wears`, `count` and `priced` are counts that
// sit right beside the money and must stay readable, or the charts lose shape.
const MONEY_KEYS = new Set(['price', 'cpw', 'value', 'idle_value', 'median_cpw', 'idle_usd']);

const TARGETS = ['api/insights.json', 'api/galaxy.json', 'api/stylist/suggest.json'];

/** Collect [path, value] for every monetary leaf, nulling it as we go. */
function strip(node, path, out) {
  if (Array.isArray(node)) {
    node.forEach((v, i) => strip(v, path.concat(i), out));
  } else if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (MONEY_KEYS.has(k) && typeof v === 'number') {
        out.push([path.concat(k), v]);
        node[k] = null;
      } else {
        strip(v, path.concat(k), out);
      }
    }
  }
}

function seal(plaintext, passcode) {
  const salt = randomBytes(16);
  const iv = randomBytes(12);
  const key = pbkdf2Sync(passcode, salt, ITERATIONS, 32, 'sha256');
  const c = createCipheriv('aes-256-gcm', key, iv);
  const ct = Buffer.concat([c.update(plaintext, 'utf8'), c.final(), c.getAuthTag()]);
  return {
    v: 1,
    kdf: { name: 'PBKDF2', hash: 'SHA-256', iterations: ITERATIONS,
           salt: salt.toString('base64') },
    iv: iv.toString('base64'),
    ct: ct.toString('base64'),   // ciphertext||tag, the layout WebCrypto expects
  };
}

if (!PASSCODE) {
  // Failing loudly on Vercel is the whole point: a silent skip there would
  // publish the real numbers, which is the exact thing this script prevents.
  if (process.env.VERCEL) {
    console.error('lock_money: INSIGHTS_PASSCODE is not set on Vercel — refusing to '
                  + 'publish unlocked figures. Set it in Project Settings > Environment '
                  + 'Variables, or remove this step from buildCommand deliberately.');
    process.exit(1);
  }
  console.warn('lock_money: no INSIGHTS_PASSCODE — leaving figures in the clear '
               + '(local build only).');
  process.exit(0);
}

let totalLocked = 0;
for (const rel of TARGETS) {
  const p = join(SITE, rel);
  if (!existsSync(p)) continue;
  const data = JSON.parse(readFileSync(p, 'utf8'));
  const found = [];
  strip(data, [], found);
  if (!found.length) continue;
  data._locked = seal(JSON.stringify(found), PASSCODE);
  writeFileSync(p, JSON.stringify(data));
  totalLocked += found.length;
  console.log(`lock_money: ${rel} — ${found.length} figures sealed`);
}
console.log(`lock_money: ${totalLocked} figures total`);
