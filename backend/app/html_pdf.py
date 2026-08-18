"""Render HTML to PDF using a headless Chromium browser (Edge or Chrome).

Chromium is the same engine that renders the reference HTML template, so the
generated PDF is pixel-identical to opening that template in a browser and
choosing "Save as PDF". Edge ships with Windows 10/11, so nothing extra needs
to be installed on customer machines.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_CANDIDATE_BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


class BrowserNotFound(RuntimeError):
    """Raised when no Chromium-based browser is available for rendering."""


def find_browser() -> str | None:
    """Locate a Chromium-based browser, preferring Edge (always on Windows)."""
    override = os.getenv("UPVC_PDF_BROWSER")
    if override and Path(override).exists():
        return override
    for path in _CANDIDATE_BROWSERS:
        if Path(path).exists():
            return path
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def render_pdf(html: str) -> bytes:
    """Convert an HTML string to PDF bytes via headless Chromium."""
    browser = find_browser()
    if not browser:
        raise BrowserNotFound(
            "No Chromium-based browser found for PDF rendering. Install Microsoft Edge "
            "or Google Chrome, or set UPVC_PDF_BROWSER to a browser executable."
        )

    # --headless=new is the modern flag; older builds only understand --headless.
    # A browser instance is usually already running on the user's machine, and a
    # cold spawn under that contention sometimes exits without rendering, so each
    # attempt gets a fresh working directory and we retry before giving up.
    # Two attempts only: a healthy machine succeeds on the first in ~2s, and a
    # machine too short of RAM to start Chromium will not recover on a third try,
    # so extra attempts just delay the caller's fallback.
    attempts = ("--headless=new", "--headless")
    last_detail = ""
    for attempt, headless_flag in enumerate(attempts, 1):
        # ignore_cleanup_errors: on Windows the browser can still hold a handle on
        # its profile directory a moment after exit, and a PermissionError raised
        # during cleanup would discard an already-good PDF.
        with tempfile.TemporaryDirectory(prefix="upvc-pdf-", ignore_cleanup_errors=True) as workdir:
            work = Path(workdir)
            source = work / "document.html"
            target = work / "document.pdf"
            # utf-8 so the rupee sign and any regional text survive the round trip.
            source.write_text(html, encoding="utf-8")

            args = [
                browser,
                headless_flag,
                "--disable-gpu",
                "--disable-extensions",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-dev-shm-usage",
                # A throwaway profile keeps this from attaching to the user's open browser.
                f"--user-data-dir={work / 'profile'}",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=10000",
                "--no-pdf-header-footer",
                f"--print-to-pdf={target}",
                source.as_uri(),
            ]
            try:
                proc = subprocess.run(args, capture_output=True, timeout=120, check=False)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                last_detail = f"attempt {attempt} ({headless_flag}) timed out"
                continue

            if target.exists():
                data = target.read_bytes()
                if data.startswith(b"%PDF"):
                    return data
                last_detail = f"attempt {attempt} wrote {len(data)} bytes that are not a PDF"
            else:
                last_detail = f"attempt {attempt} ({headless_flag}) exited rc={rc} without writing a PDF"

    raise RuntimeError(
        f"Headless browser did not produce a PDF after {len(attempts)} attempts "
        f"(browser: {browser}; last: {last_detail})"
    )
