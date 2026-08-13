"""Rules loader — YAML config with watchdog hot-reload."""

from __future__ import annotations

import os
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

_current_rules: dict[str, Any] = {}
_rules_lock = threading.Lock()
_observer: Observer | None = None # type: ignore


def load_rules(path: str | Path) -> dict[str, Any]:
    """Load guardrails.yaml and return the parsed dict."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data or {}


def reload_rules(path: str | Path) -> None:
    """Reload rules from disk into the module-level cache."""
    global _current_rules
    try:
        new_rules = load_rules(path)
        with _rules_lock:
            _current_rules = new_rules
    except Exception:
        pass  # Keep previous valid config on error


def save_rules(
    path: str | Path,
    data: dict[str, Any],
    validator: Callable[[str], None] | None = None,
) -> None:
    """Validate, back up, and atomically write the rules file, then reload.

    `data` must be the full config dict with a top-level ``guardrails`` key
    (the same shape ``load_rules`` returns). ``validator``, if given, is called
    with the path of the candidate file *before* it replaces the live one; it
    should raise on an invalid config so the live file is never clobbered.
    """
    if not isinstance(data, dict) or "guardrails" not in data:
        raise ValueError("Payload must be an object with a top-level 'guardrails' key.")

    path = Path(path)
    text = yaml.safe_dump(
        data, sort_keys=False, default_flow_style=False, allow_unicode=True
    )

    # Write candidate to a temp file in the same dir so os.replace is atomic.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    try:
        if validator is not None:
            validator(str(tmp))
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    if path.exists():
        backup = path.with_name(f"{path.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(path, backup)

    try:
        os.replace(tmp, path)
    except OSError:
        # Docker bind-mounted files don't allow rename(); copy content instead.
        shutil.copy2(tmp, path)
        tmp.unlink(missing_ok=True)

    reload_rules(path)


def get_rules() -> dict[str, Any]:
    """Return the currently active rules."""
    with _rules_lock:
        return dict(_current_rules)


class _RulesHandler(FileSystemEventHandler):
    """Watchdog handler that reloads on file write."""

    def __init__(self, path: str):
        self._path = path

    def on_modified(self, event):  # type: ignore[override]
        if event.src_path.endswith(Path(self._path).name):
            reload_rules(self._path)


def start_watcher(path: str | Path) -> None:
    """Start a background file watcher on the rules file."""
    global _observer
    path = str(path)
    reload_rules(path)  # Initial load
    _observer = Observer()
    _observer.schedule(_RulesHandler(path), str(Path(path).parent), recursive=False)
    _observer.daemon = True
    _observer.start()


def stop_watcher() -> None:
    """Stop the background file watcher."""
    global _observer
    if _observer:
        _observer.stop()
        _observer = None
