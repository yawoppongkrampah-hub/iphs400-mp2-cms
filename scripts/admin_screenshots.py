#!/usr/bin/env python3
"""Measure the admin console at phone width and take the six required screenshots.

    uv run python scripts/admin_screenshots.py                 # write docs/screenshots/
    uv run python scripts/admin_screenshots.py --check-only    # only measure, write nothing

It starts the console on a throwaway database (never your own), signs in over HTTP,
and loads each screen in headless Chrome at 390 px and 1280 px. A screen "overflows"
when the page is wider than the viewport. A screenshot is never cropped narrower than
the page, so a page that overflowed shows up as an image wider than its viewport.

Exit codes: 0 all fit, 1 something overflows, 77 Chrome was not found (nothing was run).
Uses `websockets` and `httpx`, which the project already installs (uvicorn[standard], dev group).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import httpx
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
NO_BROWSER = 77
WIDTHS = (1280, 390)
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]
TOKEN = re.compile(r'name="csrf_token" value="([^"]+)"')


def find_chrome() -> str | None:
    for candidate in [os.environ.get("CHROME")] + CHROME_PATHS:
        if candidate and (Path(candidate).exists() or shutil.which(candidate)):
            return candidate
    return None


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Console:
    """The admin console on a throwaway seeded database."""

    def __init__(self, workdir: Path):
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.passwords = {"admin": secrets.token_urlsafe(12), "editor": secrets.token_urlsafe(12)}
        env = {k: v for k, v in os.environ.items() if not k.startswith("CMS_")}
        env.update(CMS_DATABASE=str(workdir / "shots.db"), CMS_SECRET_KEY=secrets.token_urlsafe(32),
                   CMS_ADMIN_PASSWORD=self.passwords["admin"],
                   CMS_EDITOR_PASSWORD=self.passwords["editor"], PYTHONPATH=str(ROOT))
        subprocess.run([sys.executable, str(ROOT / "scripts" / "seed_demo.py")], cwd=ROOT, env=env,
                       check=True, capture_output=True)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(self.port),
             "--log-level", "warning"], cwd=ROOT, env=env, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                httpx.get(self.base + "/login")
                return
            except httpx.TransportError:
                time.sleep(0.2)
        raise RuntimeError("the console did not start")

    def cookie(self, user: str) -> str:
        client = httpx.Client(base_url=self.base)
        token = TOKEN.search(client.get("/login").text).group(1)
        client.post("/login", data={"username": user, "password": self.passwords[user],
                                    "csrf_token": token})
        return client.cookies.get("cms_session")

    def stop(self) -> None:
        os.killpg(self.process.pid, signal.SIGTERM)


class Browser:
    def __init__(self, chrome: str):
        self.profile = tempfile.mkdtemp(prefix="shots-profile-")
        port = free_port()
        self.process = subprocess.Popen(
            [chrome, "--headless=new", f"--remote-debugging-port={port}", "--no-first-run",
             "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--user-data-dir={self.profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Chrome did not start")
        self.socket = connect(next(t for t in tabs if t["type"] == "page")["webSocketDebuggerUrl"],
                              max_size=None)
        self.counter = 0
        self.call("Page.enable")
        self.call("Network.enable")

    def call(self, method: str, **params):
        self.counter += 1
        self.socket.send(json.dumps({"id": self.counter, "method": method, "params": params}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") == self.counter:
                return message.get("result", {})

    def measure(self, url: str, cookie: str | None, base: str, width: int) -> dict:
        """Load `url` and return the page's size, final path and first heading."""
        self.call("Network.clearBrowserCookies")
        if cookie:
            self.call("Network.setCookie", name="cms_session", value=cookie, url=base, httpOnly=True)
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=900,
                  deviceScaleFactor=1, mobile=False)
        self.call("Page.navigate", url=url)
        time.sleep(1.2)
        expression = ("JSON.stringify({w: document.documentElement.scrollWidth, "
                      "h: document.documentElement.scrollHeight, path: location.pathname, "
                      "heading: (document.querySelector('h1') || {}).textContent || ''})")
        return json.loads(self.call("Runtime.evaluate", expression=expression,
                                    returnByValue=True)["result"]["value"])

    def screenshot(self, size: dict, width: int, target: Path) -> None:
        # Never narrower than the page: an overflowing page makes a wider image.
        data = self.call("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                         clip={"x": 0, "y": 0, "width": max(size["w"], width),
                               "height": size["h"], "scale": 1})["data"]
        target.write_bytes(base64.b64decode(data))

    def close(self) -> None:
        self.process.terminate()
        shutil.rmtree(self.profile, ignore_errors=True)


def screens() -> list[tuple[str, str, str | None, str, bool]]:
    """(name, path, who, expected heading, required) for every admin screen worth measuring.

    The heading proves the intended screen loaded: a redirect to sign-in or a 404 page
    would be narrow too, and must not pass for the screen it replaced.
    """
    return [
        ("login", "/login", None, "Sign in", True),
        ("dashboard", "/admin", "admin", "Dashboard", True),
        ("content-list", "/admin/content", "admin", "Content", True),
        ("editor", "/admin/posts/1/edit", "editor", "Edit Post", True),
        ("users", "/admin/users", "admin", "Accounts", True),
        ("editor-denied", "/admin/users", "editor", "You don't have permission", True),
        ("new-post", "/admin/posts/new", "editor", "New Post", False),
        ("posts-list", "/admin/posts", "editor", "Posts", False),
        ("page-editor", "/admin/pages/1/edit", "editor", "Edit Page", False),
        ("page-editor-admin", "/admin/pages/1/edit", "admin", "Edit Page", False),
        ("pages-list", "/admin/pages", "admin", "Pages", False),
        ("new-page", "/admin/pages/new", "admin", "New Page", False),
        ("new-account", "/admin/users/new", "admin", "Create an account", False),
        ("account", "/admin/users/1", "admin", "ASA Leadership", False),
        ("not-found", "/admin/posts/9999/edit", "editor", "Not found", False),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="measure; write no files")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "screenshots")
    args = parser.parse_args()

    chrome = find_chrome()
    if chrome is None:
        print("Chrome was not found (set CHROME to its path). Nothing was measured.")
        return NO_BROWSER

    workdir = Path(tempfile.mkdtemp(prefix="admin-shots-"))
    console = browser = None
    overflowing = []
    try:
        console = Console(workdir)
        browser = Browser(chrome)
        cookies = {None: None, "admin": console.cookie("admin"), "editor": console.cookie("editor")}
        if not args.check_only:
            args.out.mkdir(parents=True, exist_ok=True)
        for width in WIDTHS:
            for name, path, who, heading, required in screens():
                size = browser.measure(console.base + path, cookies[who], console.base, width)
                loaded = size["path"] == path and size["heading"].strip() == heading
                fits = size["w"] <= width
                status = "ok      " if fits and loaded else ("OVERFLOW" if loaded else "WRONG   ")
                print(f"{status} {width} px {name}: page is {size['w']} px wide"
                      + ("" if loaded else f" (expected '{heading}' at {path}, got "
                                           f"'{size['heading'].strip()}' at {size['path']})"))
                if not (fits and loaded):
                    overflowing.append((width, name))
                if required and not args.check_only:
                    browser.screenshot(size, width, args.out / f"{name}-{width}.png")
    finally:
        if browser:
            browser.close()
        if console:
            console.stop()
        shutil.rmtree(workdir, ignore_errors=True)

    if overflowing:
        print(f"\n{len(overflowing)} screen(s) overflow or did not load as expected: {overflowing}")
        return 1
    print(f"\nEvery screen fits at {' and '.join(f'{w} px' for w in WIDTHS)}."
          + ("" if args.check_only else f" Screenshots are in {args.out}."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
