# Phase 0 Report — Environment Verification

**Date:** 2026-07-11
**Environment:** Claude Code on Janice's Mac (Darwin 24.6.0) — this is the plan's **Fallback C** environment, which turns out to be the *best* case: unrestricted network + persistent filesystem.

## 0.1 Network probes (all domains from §2.1)

| Domain | HTTP status | Verdict |
|---|---|---|
| `api.anthropic.com` | 404 (root) | ✅ Reachable |
| `fal.run` | 404 (root) | ✅ Reachable |
| `queue.fal.run` | 404 (root) | ✅ Reachable |
| `fal.ai` | 200 | ✅ Reachable |
| `v3.fal.media` | 404 (root) | ✅ Reachable |
| `generativelanguage.googleapis.com` | 404 (root) | ✅ Reachable |
| `api.replicate.com` | 200 | ✅ Reachable |
| `api.fashn.ai` | 401 (needs auth) | ✅ Reachable |
| `github.com` | 200 | ✅ Reachable |
| `registry.npmjs.org` / `pypi.org` | 200 | ✅ Reachable |

> A 404/401 on a bare domain root means the request traversed the network and the API server answered — the route is open. The sandbox's 403 egress-proxy blocks do **not** exist here.

## 0.2 Test generation

⏸ **Pending `FAL_KEY`.** Script is ready: `scripts/fal_generate.py --smoke-test` runs one cheapest-possible generation and logs it.

## 0.3 Anthropic API

CLI environment has Claude access by construction (this session). Direct `api.anthropic.com` reachable for the auto-QA judge; `scripts/qa_judge.py` will use it in Phase 2 (needs `ANTHROPIC_API_KEY` in `.env`, or QA can run through Claude Code itself at $0 marginal cost).

## 0.4 Artifact CSP test

**Obsolete.** Fallback A (client-side generation from an artifact) is unnecessary — the primary route (direct API calls from this machine) is live.

## 0.5 Persistence

**Solved by environment.** Local filesystem persists; repo initialized with git at `~/wardrobe-v3/virtual-closet`. Optional: add a private GitHub remote for off-machine backup (§2.4 Option A).

## Verdict

**Live route: sandbox-direct (local-direct).** All three pipelines can run from this machine as soon as keys + personal assets are provided. No fallbacks needed.

Revised §0 ground-truth table:

| Capability | Sandbox (old) | This machine |
|---|---|---|
| fal.ai / Gemini / Replicate / FASHN | ❌ Blocked | ✅ Open |
| Filesystem persistence | ❌ Resets | ✅ Persists |
| Python / Node | ✅ | ✅ Python 3.9.6, Node 25.9.0 |
| Image generation possible | ❌ | ✅ (pending key only) |
