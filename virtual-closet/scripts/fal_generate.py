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

    for _ in range(120):
        st = _req(status_url, key)
        if st["status"] == "COMPLETED":
            break
        if st["status"] in ("FAILED", "CANCELLED"):
            log_generation(model, prompt, purpose, ref_images=list(image_paths),
                           request_id=req_id, outcome="failed", cost_usd=0.0)
            sys.exit(f"Generation {st['status']}: {json.dumps(st)[:500]}")
        time.sleep(2)
    else:
        sys.exit("Timed out waiting for generation")

    result = _req(resp_url, key)
    images = result.get("images") or [result.get("image")] if result.get("image") else result.get("images", [])
    saved = []
    for i, img in enumerate(images or []):
        url = img["url"] if isinstance(img, dict) else img
        dest = Path(out) if out and len(images) == 1 else ROOT / "renders" / f"{req_id}_{i}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dest)
        saved.append(str(dest))

    gen_id = log_generation(model, prompt, purpose, ref_images=list(image_paths),
                            output_path=saved[0] if saved else None,
                            cost_usd=estimate_cost(model), seed=result.get("seed"),
                            request_id=req_id)
    print(json.dumps({"gen_id": gen_id, "request_id": req_id, "saved": saved}, indent=2))
    return saved


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
