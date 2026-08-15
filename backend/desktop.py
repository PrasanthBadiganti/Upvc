"""
UPVC Pro desktop launcher (BROMS-style).

Starts the FastAPI server on an auto-detected free port in a background thread,
then opens a native Windows window with pywebview. Business data stays in local
SQLite database.

Dev run:   python desktop.py
Bundled:   UPVC Pro.exe  (PyInstaller one-folder)
"""
import threading
import time
import socket
import uvicorn
import webview

from app.main import app

HOST = "127.0.0.1"

# Enable downloads (CSV exports, PDF downloads)
webview.settings["ALLOW_DOWNLOADS"] = True


def _enable_dpi_awareness():
    """Windows: make the process per-monitor DPI-aware so the embedded WebView
    renders crisply on any monitor (14"/24"/27", any display-scaling) instead of
    being bitmap-stretched by the OS."""
    try:
        import ctypes
    except Exception:
        return

    # Per-Monitor v2 (Win10 1703+) → Per-Monitor → System, best-effort.
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()  # system-aware (Vista+)
    except Exception:
        pass


def _free_port() -> int:
    """Find a free local port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _run_server(port: int):
    """Run uvicorn and auto-restart if it exits/crashes."""
    while True:
        try:
            uvicorn.run(
                app,
                host=HOST,
                port=port,
                log_level="warning",
                access_log=False,
                use_colors=False
            )
        except Exception as e:
            print(f"[server] crashed: {e!r} — restarting in 2s")
        else:
            print("[server] exited — restarting in 2s")
        time.sleep(2)


def main():
    """Launch desktop app: start server in background, open native window."""
    _enable_dpi_awareness()

    # Find free port (auto-detects, no conflicts)
    port = _free_port()
    print(f"[startup] Starting server on port {port}...")

    # Start server in background thread (daemon so it stops when window closes)
    t = threading.Thread(target=_run_server, args=(port,), daemon=True)
    t.start()

    # Wait until server is ready
    url = f"http://{HOST}:{port}"
    for attempt in range(50):
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.1)

    print(f"[startup] Opening window at {url}")

    # Open native window and start event loop
    webview.create_window(
        "UPVC Pro",
        url,
        width=1280,
        height=800,
        min_size=(1024, 600),
        background_color="#ffffff",
    )
    webview.start()


if __name__ == "__main__":
    main()
