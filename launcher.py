#!/usr/bin/env python3
"""
UPVC Pro Launcher - Starts the FastAPI backend and opens the app in browser
"""
import os
import sys
import webbrowser
import subprocess
import time
import requests
from pathlib import Path

def get_app_dir():
    """Get application directory"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def start_backend():
    """Start FastAPI backend"""
    app_dir = get_app_dir()
    backend_dir = app_dir / "backend"

    if not backend_dir.exists():
        print(f"Error: Backend directory not found at {backend_dir}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Change to backend directory
    os.chdir(backend_dir)

    # Start uvicorn server
    print("Starting UPVC Pro backend server...")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

def wait_for_backend(max_retries=30):
    """Wait for backend to be ready"""
    for i in range(max_retries):
        try:
            response = requests.get("http://127.0.0.1:8000/docs")
            if response.status_code == 200:
                print("Backend is ready!")
                return True
        except requests.exceptions.ConnectionError:
            print(f"Waiting for backend... ({i+1}/{max_retries})")
            time.sleep(1)

    return False

def open_app():
    """Open app in default browser"""
    url = "http://localhost:5173"
    print(f"Opening {url} in your browser...")
    webbrowser.open(url)

def main():
    print("=" * 60)
    print("UPVC Pro - Professional UPVC Business Management System")
    print("=" * 60)
    print()

    # Start backend
    backend_process = start_backend()

    # Wait for backend to be ready
    if not wait_for_backend():
        print("Error: Backend failed to start")
        input("Press Enter to exit...")
        sys.exit(1)

    # Open app in browser
    time.sleep(2)
    open_app()

    print()
    print("Backend is running at: http://127.0.0.1:8000")
    print("App is running at: http://localhost:5173")
    print()
    print("Close this window to stop the application.")
    print()

    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        backend_process.terminate()
        backend_process.wait()

if __name__ == "__main__":
    main()
