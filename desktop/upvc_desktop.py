from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn
import webview


APP_NAME = "UPVC Pro"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


def _user_data_dir() -> Path:
    """Where the database, backups and uploads live.

    Frozen: a `data` folder beside the .exe, matching BROMS - the whole app is
    one folder you can copy or back up. Falls back to the user profile if that
    folder is not writable (e.g. installed under Program Files).
    """
    candidates = [
        Path(sys.executable).resolve().parent / "data" if getattr(sys, "frozen", False) else None,
        Path(os.getenv("LOCALAPPDATA", "")) / APP_NAME if os.getenv("LOCALAPPDATA") else None,
        Path.home() / APP_NAME,
    ]
    for data_dir in candidates:
        if data_dir is None:
            continue
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            # mkdir can succeed where writing cannot (UAC virtualisation under
            # Program Files), so prove the folder really takes a file.
            probe = data_dir / ".write-test"
            probe.write_bytes(b"")
            probe.unlink()
            return data_dir
        except OSError:
            continue
    raise RuntimeError("Could not create a writable UPVC Pro data folder")


def _configure_paths() -> None:
    root = _base_dir()
    backend = root / "backend"
    if backend.exists():
        sys.path.insert(0, str(backend))
    if "UPVC_DATA_DIR" not in os.environ:
        os.environ["UPVC_DATA_DIR"] = str(_user_data_dir())
    os.environ.setdefault("UPVC_FRONTEND_DIST", str(root / "frontend" / "dist"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_app(url: str, timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(f"{url}/api/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, URLError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Application did not start in time: {last_error}")


def main() -> None:
    _configure_paths()
    from app.main import app

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="upvc-api", daemon=True)
    thread.start()
    _wait_for_app(url)

    window = webview.create_window(APP_NAME, url, width=1280, height=820, min_size=(1100, 720))
    webview.start(debug=False)
    server.should_exit = True
    thread.join(timeout=5)


def _self_test() -> int:
    """Prove the packaged build actually runs, not merely that files are present.

    Boots the real API on a free port and exercises the paths that only break
    once frozen: schema creation, seeding, the bundled frontend, and backup.
    Point UPVC_DATA_DIR at a scratch folder to avoid touching live data.
    """
    _configure_paths()
    from app.main import FRONTEND_DIST, app
    from app.database import DEFAULT_DB_PATH
    from app import models

    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        if not condition:
            failures.append(label)
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}{(' - ' + detail) if detail else ''}")

    check("bundled frontend present", FRONTEND_DIST.joinpath("index.html").exists(), str(FRONTEND_DIST))
    check("data folder writable", DEFAULT_DB_PATH.parent.exists(), str(DEFAULT_DB_PATH.parent))
    check("api object built", app.title == "UPVC Pro API")

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="upvc-selftest", daemon=True)
    thread.start()
    try:
        _wait_for_app(url)
        check("server answers /api/health", True)

        import json
        import sqlite3
        from urllib.request import Request

        def get(path: str):
            with urlopen(f"{url}{path}", timeout=10) as r:
                return r.status, json.loads(r.read() or b"null")

        def post(path: str):
            with urlopen(Request(f"{url}{path}", data=b"", method="POST"), timeout=30) as r:
                return r.status, json.loads(r.read() or b"null")

        con = sqlite3.connect(DEFAULT_DB_PATH)
        live = {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
        con.close()
        missing = set(models.Base.metadata.tables) - live
        check(f"all {len(models.Base.metadata.tables)} tables created", not missing, str(sorted(missing)))

        status, accounts = get("/api/accounts")
        check("chart of accounts seeded", status == 200 and len(accounts) > 10, f"{len(accounts)} accounts")
        for path in ("/api/customers", "/api/invoices", "/api/quotations", "/api/trial-balance"):
            status, _ = get(path)
            check(f"GET {path}", status == 200, str(status))

        status, made = post("/api/backup/create")
        check("backup create", status == 200 and made.get("success"), str(made)[:120])
        status, listing = get("/api/backup/list")
        check("backup list", status == 200 and len(listing.get("backups", [])) >= 1,
              f"{len(listing.get('backups', []))} backup(s)")

        with urlopen(f"{url}/", timeout=10) as r:
            body = r.read()
        check("frontend served over http", r.status == 200 and b"<div id=\"root\"" in body, f"{len(body)} bytes")
    except Exception as exc:  # noqa: BLE001 - any failure here is a build failure
        check("self-test completed without error", False, repr(exc))
    finally:
        server.should_exit = True
        thread.join(timeout=5)

    print("SELF-TEST: " + ("PASS" if not failures else f"FAIL ({len(failures)}): {failures}"))
    return 0 if not failures else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    main()
