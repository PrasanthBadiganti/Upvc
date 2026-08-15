"""Scheduled backup functionality"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .backup import create_backup
from .database import DEFAULT_DB_PATH


CONFIG_FILE = DEFAULT_DB_PATH.parent / "backup_config.json"
DEFAULT_CONFIG = {
    "enabled": True,
    "interval_hours": 6,  # Every 6 hours
    "last_backup": None,
    "next_backup": None
}


class BackupScheduler:
    """Handles scheduled automatic backups"""

    _instance = None
    _lock = threading.Lock()
    _scheduler_thread = None
    _should_stop = False

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.config = self._load_config()
        self.running = False

    @staticmethod
    def _load_config() -> dict:
        """Load backup configuration"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def _save_config(self) -> None:
        """Save backup configuration"""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            pass

    def start(self) -> None:
        """Start the backup scheduler"""
        if self.running:
            return

        self.running = True
        BackupScheduler._should_stop = False

        def scheduler_loop():
            while not BackupScheduler._should_stop:
                try:
                    self._check_and_backup()
                except Exception:
                    pass
                # Check every minute
                for _ in range(60):
                    if BackupScheduler._should_stop:
                        break
                    threading.Event().wait(1)

        BackupScheduler._scheduler_thread = threading.Thread(
            target=scheduler_loop,
            name="backup-scheduler",
            daemon=True
        )
        BackupScheduler._scheduler_thread.start()

    def stop(self) -> None:
        """Stop the backup scheduler"""
        self.running = False
        BackupScheduler._should_stop = True
        if BackupScheduler._scheduler_thread:
            BackupScheduler._scheduler_thread.join(timeout=5)

    def _check_and_backup(self) -> None:
        """Check if backup is due and perform it"""
        if not self.config.get("enabled", True):
            return

        last_backup_str = self.config.get("last_backup")
        interval_hours = self.config.get("interval_hours", 6)

        if last_backup_str:
            try:
                last_backup = datetime.fromisoformat(last_backup_str)
                next_backup_time = last_backup + timedelta(hours=interval_hours)
                if datetime.now() < next_backup_time:
                    return
            except (ValueError, TypeError):
                pass

        # Perform backup
        result = create_backup(backup_name="auto_backup")
        if result.get("success"):
            self.config["last_backup"] = datetime.now().isoformat()
            next_time = datetime.now() + timedelta(hours=interval_hours)
            self.config["next_backup"] = next_time.isoformat()
            self._save_config()

    def get_config(self) -> dict:
        """Get current backup configuration"""
        self.config = self._load_config()
        return self.config.copy()

    def update_config(self, enabled: Optional[bool] = None, interval_hours: Optional[int] = None) -> dict:
        """
        Update backup configuration

        Args:
            enabled: Enable/disable auto-backup
            interval_hours: Interval between backups in hours

        Returns:
            Updated configuration
        """
        if enabled is not None:
            self.config["enabled"] = enabled

        if interval_hours is not None:
            if interval_hours < 1:
                interval_hours = 1
            self.config["interval_hours"] = interval_hours

        self._save_config()
        return self.config.copy()

    def force_backup(self) -> dict:
        """Force an immediate backup"""
        result = create_backup(backup_name="manual_backup")
        if result.get("success"):
            self.config["last_backup"] = datetime.now().isoformat()
            interval_hours = self.config.get("interval_hours", 6)
            next_time = datetime.now() + timedelta(hours=interval_hours)
            self.config["next_backup"] = next_time.isoformat()
            self._save_config()
        return result


# Global scheduler instance
_scheduler = BackupScheduler()


def get_scheduler() -> BackupScheduler:
    """Get the global backup scheduler instance"""
    return _scheduler
