"""Tests for the YAML policy hot-reloader."""
from __future__ import annotations

import time

from petfishframework.policies import PolicyHotReloader

_POLICY_V1 = """\
version: "1.0"
name: test-policy
rules:
  - name: allow-calculator
    priority: 10
    effect: ALLOW
    when:
      action.tool_name: calculator
"""

_POLICY_V2 = """\
version: "1.1"
name: test-policy
rules:
  - name: deny-calculator
    priority: 10
    effect: DENY
    when:
      action.tool_name: calculator
"""


def test_hot_reloader_loads_policy(tmp_path):
    """Initial load reads the YAML file correctly."""
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(_POLICY_V1, encoding="utf-8")
    reloader = PolicyHotReloader(policy_path=str(policy_file))
    reloader.start()
    try:
        policy = reloader.current_policy()
        assert policy is not None
        assert policy._version == "1.0"  # noqa: SLF001
    finally:
        reloader.stop()


def test_reload_detects_file_change(tmp_path):
    """File modified -> reload_now() returns True, new policy loaded."""
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(_POLICY_V1, encoding="utf-8")
    reloader = PolicyHotReloader(policy_path=str(policy_file))
    reloader.start()
    try:
        time.sleep(0.05)
        policy_file.write_text(_POLICY_V2, encoding="utf-8")
        reloaded = reloader.reload_now()
        assert reloaded is True
        policy = reloader.current_policy()
        assert policy is not None
        assert policy._version == "1.1"  # noqa: SLF001
    finally:
        reloader.stop()


def test_callback_called_on_reload(tmp_path):
    """Registered callback called when file changes."""
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(_POLICY_V1, encoding="utf-8")
    reloader = PolicyHotReloader(policy_path=str(policy_file))
    seen = []

    def callback(policy):
        seen.append(policy._version)  # noqa: SLF001

    reloader.on_reload(callback)
    reloader.start()
    try:
        time.sleep(0.05)
        policy_file.write_text(_POLICY_V2, encoding="utf-8")
        reloader.reload_now()
        assert "1.1" in seen
    finally:
        reloader.stop()


def test_no_reload_when_unchanged(tmp_path):
    """reload_now() returns False when file mtime unchanged."""
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(_POLICY_V1, encoding="utf-8")
    reloader = PolicyHotReloader(policy_path=str(policy_file))
    reloader.start()
    try:
        reloaded = reloader.reload_now()
        assert reloaded is False
    finally:
        reloader.stop()
