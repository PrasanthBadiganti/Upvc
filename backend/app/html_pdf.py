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

    with tempfile.TemporaryDirectory(prefix="upvc-pdf-") as workdir:
        work = Path(workdir)
        source = work / "document.html"
        target = work / "document.pdf"
        # utf-8 so the rupee sign and any regional text survive the round trip.
        source.write_text(html, encoding="utf-8")

        base_args = [
            browser,
            "--disable-gpu",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            # A throwaway profile keeps this from attaching to the user's open browser.
            f"--user-data-dir={work / 'profile'}",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=5000",
            "--no-pdf-header-footer",
            f"--print-to-pdf={target}",
            source.as_uri(),
        ]

        # --headless=new is the modern flag; older builds only understand --headless.
        for headless_flag in ("--headless=new", "--headless"):
            if target.exists():
                break
            subprocess.run(
                [base_args[0], headless_flag, *base_args[1:]],
                capture_output=True,
                timeout=60,
                check=False,
            )

        if not target.exists():
            raise RuntimeError(f"Headless browser did not produce a PDF (browser: {browser})")
        return target.read_bytes()
