#!/usr/bin/env python3
"""fal.ai client: submit a generation via the queue API, poll, download outputs.

Stdlib-only (urllib). Reads FAL_KEY from environment or ../.env.
Budget-gated: refuses to run if the call would exceed the cap in logs/budget.json.

Usage:
    python3 scripts/fal_generate.py --smoke-test
    python3 scripts/fal_generate.py --model fal-ai/nano-banana-pro \
        --prompt "..." --image ref1.jpg --image ref2.jpg \
        --purpose avatar-candidate --out renders/foo.png
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from genlog import check_budget, log_generation, estimate_cost

ROOT = Path(__file__).resolve().parent.parent
QUEUE = "https://queue.fal.run"


def load_key():
    key = os.environ.get("FAL_KEY")
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith("FAL_KEY="):
                    val = line.split("=", 1)[1].split("#", 1)[0].strip()
                    key = val.strip('"').strip("'") or None
    if not key:
        sys.exit("FAL_KEY not found in environment or .env — see .env.example")
    return key


def _req(url, key, data=None, method=None, retries=3):
    body = json.dumps(data).encode() if data is not None else None
    last_err = None
    for attempt in range(retries):
        r = urllib.request.Request(url, data=body, method=method or ("POST" if body else "GET"))
        r.add_header("Authorization", f"Key {key}")
        r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            # fal intermittently 403s valid requests; a locked account 403 won't recover
            if e.code == 403 and "locked" not in detail.lower() and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                last_err = f"HTTP {e.code}: {detail}"
                continue
            raise SystemExit(f"HTTP {e.code} from {url}: {detail}")
    raise SystemExit(f"Retries exhausted: {last_err}")


def image_to_data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def generate(model, prompt, image_paths=(), purpose="tryon", out=None, extra_args=None):
    key = load_key()
    check_budget(model)  # raises BudgetExceeded before spending

    payload = {"prompt": prompt}
    if image_paths:
        payload["image_urls"] = [image_to_data_uri(p) for p in image_paths]
    if extra_args:
        payload.update(extra_args)

    sub = _req(f"{QUEUE}/{model}", key, payload)
    req_id = sub["request_id"]
    status_url = sub.get("status_url", f"{QUEUE}/{model}/requests/{req_id}/status")
    resp_url = sub.get("response_url", f"{QUEUE}/{model}/requests/{req_id}")

    # slow-queue nights (2026-07-22) put nb2 jobs well past the old ~4-minute
    # window; abandoning a submitted job loses billed work, so poll up to 15 min
    # and log the request_id if we still give up
    for _ in range(300):
        st = _req(status_url, key)
        if st["status"] == "COMPLETED":
            break
        if st["status"] in ("FAILED", "CANCELLED"):
            log_generation(model, prompt, purpose, ref_images=list(image_paths),
                           request_id=req_id, outcome="failed", cost_usd=0.0)
            sys.exit(f"Generation {st['status']}: {json.dumps(st)[:500]}")
        time.sleep(3)
    else:
        log_generation(model, prompt, purpose, ref_images=list(image_paths),
                       request_id=req_id, outcome=f"timeout-abandoned: {resp_url}",
                       cost_usd=0.0)
        sys.exit(f"Timed out waiting for generation; request logged: {req_id}")

    result = _req(resp_url, key)
    images = result.get("images") or [result.get("image")] if result.get("image") else result.get("images", [])
    saved = []
    for i, img in enumerate(images or []):
        url = img["url"] if isinstance(img, dict) else img
        dest = Path(out) if out and len(images) == 1 else ROOT / "renders" / f"{req_id}_{i}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(4):  # transient DNS/network failures happen after billing
            try:
                urllib.request.urlretrieve(url, dest)
                saved.append(str(dest))
                break
            except OSError as e:
                if attempt == 3:
                    # already billed: log it with the URL so the image is recoverable
                    log_generation(model, prompt, purpose, ref_images=list(image_paths),
                                   request_id=req_id, cost_usd=estimate_cost(model),
                                   outcome=f"completed-download-failed: {url}")
                    sys.exit(f"Download failed after retries ({e}); result URL logged: {url}")
                time.sleep(3 * (attempt + 1))

    gen_id = log_generation(model, prompt, purpose, ref_images=list(image_paths),
                            output_path=saved[0] if saved else None,
                            cost_usd=estimate_cost(model), seed=result.get("seed"),
                            request_id=req_id)
    print(json.dumps({"gen_id": gen_id, "request_id": req_id, "saved": saved}, indent=2))
    return saved


def generate_flf2v(first_path, last_path, prompt, out, resolution="720p",
                   purpose="spin-video", model="fal-ai/wan-flf2v"):
    """First-last-frame video: bridge two real spin frames into rotation motion.
    Reuses the budget gate, queue poll, and genlog of generate(). Output is one
    video file at `out`; result JSON is {"video": {"url": ...}}."""
    key = load_key()
    cost = 0.20 if resolution == "480p" else 0.40
    check_budget(model)  # gate uses the 720p worst case in COST_TABLE

    payload = {"prompt": prompt, "resolution": resolution,
               "first_frame_url": image_to_data_uri(first_path),
               "last_frame_url": image_to_data_uri(last_path)}
    sub = _req(f"{QUEUE}/{model}", key, payload)
    req_id = sub["request_id"]
    status_url = sub.get("status_url", f"{QUEUE}/{model}/requests/{req_id}/status")
    resp_url = sub.get("response_url", f"{QUEUE}/{model}/requests/{req_id}")

    for _ in range(300):
        st = _req(status_url, key)
        if st["status"] == "COMPLETED":
            break
        if st["status"] in ("FAILED", "CANCELLED"):
            log_generation(model, prompt, purpose, ref_images=[first_path, last_path],
                           request_id=req_id, outcome="failed", cost_usd=0.0)
            sys.exit(f"Video {st['status']}: {json.dumps(st)[:400]}")
        time.sleep(3)
    else:
        log_generation(model, prompt, purpose, ref_images=[first_path, last_path],
                       request_id=req_id, outcome=f"timeout-abandoned: {resp_url}",
                       cost_usd=0.0)
        sys.exit(f"Timed out; request logged: {req_id}")

    result = _req(resp_url, key)
    url = (result.get("video") or {}).get("url")
    if not url:
        sys.exit(f"No video in result: {json.dumps(result)[:400]}")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(url, out)
            break
        except OSError as e:
            if attempt == 3:
                log_generation(model, prompt, purpose, ref_images=[first_path, last_path],
                               request_id=req_id, cost_usd=cost,
                               outcome=f"completed-download-failed: {url}")
                sys.exit(f"Download failed ({e}); URL logged: {url}")
            time.sleep(3 * (attempt + 1))
    log_generation(model, prompt, purpose, ref_images=[first_path, last_path],
                   output_path=out, cost_usd=cost, request_id=req_id)
    print(f"video saved {out} (${cost})")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-test", action="store_true",
                    help="one cheapest-possible generation to verify auth + download (Phase 0.2)")
    ap.add_argument("--model", default="fal-ai/nano-banana-2")
    ap.add_argument("--prompt")
    ap.add_argument("--image", action="append", default=[])
    ap.add_argument("--purpose", default="tryon")
    ap.add_argument("--out")
    args = ap.parse_args()

    if args.smoke_test:
        generate("fal-ai/nano-banana-2",
                 "A single red apple on a plain white background, studio photograph.",
                 purpose="smoke-test", out=str(ROOT / "renders" / "smoke_test.png"))
    else:
        if not args.prompt:
            ap.error("--prompt required unless --smoke-test")
        generate(args.model, args.prompt, args.image, args.purpose, args.out)


if __name__ == "__main__":
    main()
