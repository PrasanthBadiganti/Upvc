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
    candidates = [
        Path(os.getenv("LOCALAPPDATA", "")) / APP_NAME if os.getenv("LOCALAPPDATA") else None,
        Path.home() / APP_NAME,
    ]
    for data_dir in candidates:
        if data_dir is None:
            continue
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
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


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _configure_paths()
        from app.main import FRONTEND_DIST, app
        from app.database import DEFAULT_DB_PATH

        assert FRONTEND_DIST.joinpath("index.html").exists(), f"Missing frontend at {FRONTEND_DIST}"
        assert DEFAULT_DB_PATH.parent.exists(), f"Missing data folder at {DEFAULT_DB_PATH.parent}"
        assert app.title == "UPVC Pro API"
        raise SystemExit(0)
    main()
