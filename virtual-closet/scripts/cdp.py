#!/usr/bin/env python3
"""Drive headless Chrome over DevTools Protocol. Pure stdlib — no pip, no deps.

    python3 scripts/cdp.py shot http://localhost:8765/wear --width 390 --out w.png
    python3 scripts/cdp.py shot file:///tmp/x.html --width 390 --full
    python3 scripts/cdp.py eval  http://localhost:8765/  "innerWidth"

WHY THIS EXISTS. Two traps in this project's own notes need CDP and nothing else:

1. **Chrome CLAMPS `--window-size` to ~500px.** Asking for 390 gives you a 500px
   viewport, verified in BOTH `--headless=new` and `--headless=old` on 07-28. So
   every "tested at 390px" claim made with `--screenshot` alone was actually a
   test at 500px, and a phone breakpoint at 400px never fired. A true phone
   viewport needs `Emulation.setDeviceMetricsOverride`, which is CDP-only.
2. **`--virtual-time-budget` starves rAF**, so `/galaxy`'s load-in reveal and
   any deferred render capture as an empty page. Driving on a REAL CLOCK is the
   documented workaround, and that also needs a live connection.

`/wear` is phone-first and is the page she touches daily, and Phase 4's
acceptance criterion is "all five pages presentable at desktop AND 390px" — none
of which could actually be checked before this.

The websocket client below is deliberately minimal: text frames, client-side
masking, no extensions, no fragmentation on send. That is all CDP needs.
"""
import argparse
import base64
import json
import os
import random
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

CHROME = os.environ.get("CHROME_BIN") or (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


# ------------------------------------------------------------ websocket (RFC 6455)

class WS:
    """Just enough websocket to speak CDP. Text frames only."""

    def __init__(self, url, timeout=30):
        if not url.startswith("ws://"):
            raise ValueError("only ws:// (Chrome is local)")
        rest = url[len("ws://"):]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET /%s HTTP/1.1\r\n"
            "Host: %s\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n" % (path, hostport, key)
        )
        self.sock.sendall(req.encode())
        self._buf = b""
        # drain the handshake response
        while b"\r\n\r\n" not in self._buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise IOError("chrome closed during handshake")
            self._buf += chunk
        head, _, self._buf = self._buf.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise IOError("handshake refused: %s" % head.split(b"\r\n")[0])

    def _recv_exactly(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise IOError("chrome closed the connection")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def send(self, text):
        payload = text.encode()
        # Client frames MUST be masked. FIN + opcode 1 (text).
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < (1 << 16):
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def recv(self):
        """One complete message; reassembles continuation frames."""
        chunks = []
        while True:
            b0, b1 = self._recv_exactly(2)
            fin = b0 & 0x80
            opcode = b0 & 0x0F
            length = b1 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exactly(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exactly(8))[0]
            data = self._recv_exactly(length) if length else b""
            if opcode == 0x8:                      # close
                raise IOError("chrome closed the socket")
            if opcode == 0x9:                      # ping -> pong
                self.sock.sendall(b"\x8a\x80" + os.urandom(4))
                continue
            if opcode == 0xA:
                continue
            chunks.append(data)
            if fin:
                return b"".join(chunks).decode("utf-8", "replace")

    def close(self):
        try:
            self.sock.close()
        except Exception:                          # noqa: BLE001
            pass


# ------------------------------------------------------------------- chrome

class Chrome:
    def __init__(self, width=390, height=844, scale=2, headless=True, quiet=True,
                 touch=False):
        self.profile = tempfile.mkdtemp(prefix="cdp-profile-")
        self.port = self._free_port()
        args = [
            CHROME,
            "--remote-debugging-port=%d" % self.port,
            # Newer Chrome refuses websocket upgrades without this.
            "--remote-allow-origins=*",
            "--user-data-dir=" + self.profile,
            "--no-first-run", "--no-default-browser-check",
            "--disable-gpu", "--hide-scrollbars",
            # NOT --virtual-time-budget: it starves rAF and captures blank pages.
            "--window-size=%d,%d" % (max(width, 500), height),
        ]
        if headless:
            args.insert(1, "--headless=new")
        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None)
        self.ws = None
        self._id = 0
        self._connect()
        # THE WHOLE POINT: a real 390px viewport, which --window-size cannot give.
        self.call("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height,
            "deviceScaleFactor": scale, "mobile": bool(touch) or scale > 1,
        })
        if touch:
            # Layout is only half of "does this work on a phone". Without this,
            # `(hover: hover)` and `(pointer: fine)` still match, so hover-gated
            # affordances look reachable in a screenshot and are not on a thumb.
            self.call("Emulation.setTouchEmulationEnabled",
                      {"enabled": True, "maxTouchPoints": 5})
            self.call("Emulation.setEmitTouchEventsForMouse",
                      {"enabled": True, "configuration": "mobile"})
        self.call("Page.enable")

    @staticmethod
    def _free_port():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def _connect(self, timeout=25):
        deadline = time.time() + timeout
        target = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:%d/json/list" % self.port, timeout=2) as fh:
                    tabs = json.load(fh)
                target = next((t for t in tabs if t.get("type") == "page"), None)
                if target:
                    break
            except Exception:                      # noqa: BLE001
                pass
            time.sleep(0.2)
        if not target:
            raise IOError("chrome never exposed a page target on :%d" % self.port)
        self.ws = WS(target["webSocketDebuggerUrl"])

    def call(self, method, params=None, timeout=60):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})
            # events are ignored here; wait_for_load consumes them deliberately
        raise TimeoutError(method)

    def navigate(self, url, settle=1.2):
        """Navigate and let the page actually run.

        `settle` is wall-clock on purpose. Load alone is not enough for this
        project's pages — /galaxy reveals itself through rAF, and a screenshot
        taken at load fires captures an empty field.
        """
        self.call("Page.navigate", {"url": url})
        time.sleep(settle)

    def eval(self, expr):
        r = self.call("Runtime.evaluate",
                      {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return (r.get("result") or {}).get("value")

    def screenshot(self, path, full=False):
        """`full=True` captures the DOCUMENT, which is not the same as "the whole
        page": a container with its own `overflow-y:auto` scrolls internally, and
        everything below its fold is silently absent from the image. The fitting
        room is exactly this — `main` scrolls, `body` does not — so a full-page
        shot of it shows the mirror and nothing else, and reads as a broken
        layout. Check `el.scrollHeight > el.clientHeight` before believing it.
        """
        params = {"format": "png", "captureBeyondViewport": bool(full)}
        if full:
            m = self.call("Page.getLayoutMetrics")
            css = m.get("cssContentSize") or m.get("contentSize") or {}
            if css:
                params["clip"] = {"x": 0, "y": 0, "width": css["width"],
                                  "height": css["height"], "scale": 1}
        data = self.call("Page.captureScreenshot", params)["data"]
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(data))
        return path

    def close(self):
        try:
            if self.ws:
                self.ws.close()
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:                      # noqa: BLE001
                self.proc.kill()
            shutil.rmtree(self.profile, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("shot", "eval"))
    ap.add_argument("url")
    ap.add_argument("expr", nargs="?", default="innerWidth")
    ap.add_argument("--width", type=int, default=390)
    ap.add_argument("--height", type=int, default=844)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--settle", type=float, default=1.2)
    ap.add_argument("--touch", action="store_true",
                    help="emulate a touchscreen: (hover:none), (pointer:coarse), touch events")
    ap.add_argument("--full", action="store_true", help="full-page, not just viewport")
    ap.add_argument("--out", default="shot.png")
    args = ap.parse_args()

    with Chrome(width=args.width, height=args.height, scale=args.scale,
                touch=args.touch) as c:
        c.navigate(args.url, settle=args.settle)
        if args.cmd == "eval":
            print(json.dumps(c.eval(args.expr)))
        else:
            c.screenshot(args.out, full=args.full)
            real = c.eval("innerWidth")
            print("%s  (viewport %spx, requested %d)" % (args.out, real, args.width))
            if real != args.width:
                print("WARNING: viewport is not the requested width", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
