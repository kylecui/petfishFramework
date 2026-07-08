"""Hot-reload support for YAML policy files.

Polls the policy file mtime on a daemon thread and reloads the YamlPolicy
whenever a change is detected. Cross-platform: uses ``os.stat`` mtime polling
so no extra dependencies such as watchdog or watchfiles are required.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from petfishframework.policies.engine import YamlPolicy

Callback = Callable[[YamlPolicy], None]


@dataclass
class PolicyHotReloader:
    """Watches a YAML policy file for changes and hot-reloads.

    Checks file mtime periodically. When changed, reloads the policy
    and notifies registered callbacks. Runs watcher in a daemon thread.

    Cross-platform: uses os.stat mtime polling (no watchdog dependency).
    """

    policy_path: str
    check_interval_s: float = 2.0
    _last_mtime: float = field(default=0.0, init=False)
    _watcher_thread: threading.Thread | None = field(default=None, init=False)
    _running: bool = field(default=False, init=False)
    _callbacks: list[Callback] = field(default_factory=list, init=False)
    _policy: YamlPolicy | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def start(self) -> None:
        """Start watching in a daemon thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._reload_if_changed()
            self._watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._watcher_thread.start()

    def stop(self) -> None:
        """Stop the watcher thread."""
        with self._lock:
            self._running = False
            thread = self._watcher_thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=self.check_interval_s + 1.0)

    def reload_now(self) -> bool:
        """Force a reload check. Returns True if file changed and reloaded."""
        with self._lock:
            return self._reload_if_changed()

    def on_reload(self, callback: Callback) -> None:
        """Register a callback called when policy file changes.

        The callback receives the newly loaded YamlPolicy.
        """
        with self._lock:
            self._callbacks.append(callback)

    def current_policy(self) -> YamlPolicy | None:
        """Return the currently loaded policy."""
        with self._lock:
            return self._policy

    def _watch_loop(self) -> None:
        """Background loop that polls for file changes."""
        while True:
            with self._lock:
                if not self._running:
                    break
            time.sleep(self.check_interval_s)
            with self._lock:
                if not self._running:
                    break
            self.reload_now()

    def _reload_if_changed(self) -> bool:
        """Check mtime and reload if needed.

        Must be called while holding ``_lock``.
        """
        path = Path(self.policy_path)
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            return False

        if self._last_mtime != 0.0 and mtime == self._last_mtime:
            return False

        try:
            new_policy = YamlPolicy.from_file(str(path))
        except Exception:  # noqa: BLE001
            return False

        self._policy = new_policy
        self._last_mtime = mtime
        callbacks = list(self._callbacks)
        for callback in callbacks:
            callback(new_policy)
        return True
