"""Real MCP stdio transport using JSON-RPC 2.0 over subprocess pipes.

This module implements the client side of the Model Context Protocol stdio
transport. It spawns a subprocess, speaks newline-delimited JSON-RPC 2.0 over
``stdin``/``stdout``, and exposes a small synchronous API for tool discovery
and invocation.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any


class StdioMCPClient:
    """A synchronous MCP client that uses stdio JSON-RPC.

    The client is designed to be used as a context manager so the subprocess is
    always terminated on exit:

        with StdioMCPClient("uvx", ["mcp-server-time"]) as client:
            tools = client.list_tools()
            result = client.call_tool("get_current_time", {"timezone": "UTC"})

    Outside a context manager, callers must call :meth:`close` explicitly.
    """

    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> None:
        self._command = command
        self._args = args
        self._env = env
        self._process: subprocess.Popen[str] | None = None
        self._next_id = 1
        self._server_capabilities: dict[str, Any] = {}

    def _get_env(self) -> dict[str, str] | None:
        """Return the environment for the subprocess.

        A shallow copy of ``os.environ`` is merged with any user-supplied extra
        variables. ``PATH`` is preserved unless explicitly overridden.
        """
        if self._env is None:
            return None
        merged = dict(os.environ)
        merged.update(self._env)
        return merged

    def _spawn(self) -> subprocess.Popen[str]:
        """Start the MCP server subprocess with text-mode pipes.

        On Windows, commands like 'npx' are .cmd files that Popen can't find
        without shell=True. We resolve the full path via shutil.which instead.
        """
        import shutil

        resolved = shutil.which(self._command)
        cmd = resolved or self._command
        return subprocess.Popen(
            [cmd] + self._args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._get_env(),
        )

    @property
    def _proc(self) -> subprocess.Popen[str]:
        """Return the active subprocess, raising if it has not been started."""
        if self._process is None:
            raise RuntimeError("StdioMCPClient is not initialized")
        return self._process

    def _read_message(self) -> dict[str, Any]:
        """Read and parse one newline-delimited JSON-RPC message."""
        proc = self._proc
        if proc.stdout is None:
            raise RuntimeError("subprocess stdout pipe is closed")
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("subprocess closed stdout before returning a response")
        return json.loads(line)

    def _send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC request and return the ``result`` field."""
        proc = self._proc
        if proc.stdin is None:
            raise RuntimeError("subprocess stdin pipe is closed")

        request_id = self._next_id
        self._next_id += 1

        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params

        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

        while True:
            response = self._read_message()
            # Ignore notifications / unsolicited messages while waiting for
            # the matching response.
            if response.get("id") == request_id:
                break

        if "error" in response:
            error = response["error"]
            raise RuntimeError(
                f"JSON-RPC error for {method}: "
                f"{error.get('code')} {error.get('message')}"
            )

        return response.get("result")

    def _send_notification(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        proc = self._proc
        if proc.stdin is None:
            raise RuntimeError("subprocess stdin pipe is closed")

        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            message["params"] = params

        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    def initialize(self) -> None:
        """Perform the MCP initialization handshake."""
        if self._process is None:
            self._process = self._spawn()

        result = self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "petfishframework", "version": "0.1.0"},
            },
        )
        self._server_capabilities = (result or {}).get("capabilities", {})
        self._send_notification("notifications/initialized")

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the list of tools exposed by the server."""
        result = self._send_request("tools/list", {})
        if not isinstance(result, dict):
            raise RuntimeError(f"unexpected tools/list response: {result!r}")
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise RuntimeError(f"unexpected tools/list tools field: {tools!r}")
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool by name and return the raw result."""
        return self._send_request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )

    def close(self) -> None:
        """Terminate the subprocess and close pipes.

        This method is idempotent: repeated calls are safe.
        """
        proc = self._process
        if proc is None:
            return

        self._process = None

        if proc.stdin is not None:
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass

        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except ProcessLookupError:
            pass

        for pipe in (proc.stdout, proc.stderr):
            if pipe is not None:
                try:
                    pipe.close()
                except BrokenPipeError:
                    pass

    def __enter__(self) -> "StdioMCPClient":
        self.initialize()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
