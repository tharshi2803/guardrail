"""Rules file watcher using watchdog."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import GuardrailConfig

_observer: Observer | None = None


class _ReloadHandler(FileSystemEventHandler):
    """Re-validate and swap config on file change."""

    def __init__(self, path: str, callback: Callable[[GuardrailConfig], None]) -> None:
        self._path = path
        self._callback = callback

    def on_modified(self, event):  # type: ignore[override]
        if event.src_path.endswith(Path(self._path).name):
            try:
                new_config = GuardrailConfig.from_yaml(self._path)
                self._callback(new_config)
            except Exception:
                pass  # Keep previous valid config


def start(path: str | Path, callback: Callable[[GuardrailConfig], None]) -> None:
    """Start watching *path* for changes."""
    global _observer
    path = str(path)
    _observer = Observer()
    _observer.schedule(
        _ReloadHandler(path, callback),
        str(Path(path).parent),
        recursive=False,
    )
    _observer.daemon = True
    _observer.start()


def stop() -> None:
    """Stop the file watcher."""
    global _observer
    if _observer:
        _observer.stop()
        _observer = None
