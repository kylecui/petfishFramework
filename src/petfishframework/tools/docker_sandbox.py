"""Docker-based sandbox backend (optional extra).

This backend runs a pickled tool inside a disposable container with no network
access, a read-only root filesystem, a writable ``/tmp`` tmpfs, and a memory
limit.

Install the required dependency with::

    pip install "petfishframework[sandbox-docker]"
"""
from __future__ import annotations

import pickle
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from petfishframework.core.types import ToolResult


class DockerSandboxBackend:
    """Docker-based sandbox with network isolation and resource limits.

    Requires the ``docker`` package: ``pip install petfishframework[sandbox-docker]``

    Runs tool execution in a disposable container with:

    - ``--network=none`` (no network access)
    - ``--read-only`` (read-only root filesystem)
    - ``--tmpfs /tmp`` (writable temp directory)
    - ``--memory`` limit
    """

    def __init__(self, image: str = "python:3.12-slim", mem_limit: str = "256m") -> None:
        self._image = image
        self._mem_limit = mem_limit

    def execute(self, tool: Any, args: dict[str, Any]) -> ToolResult:
        """Run ``tool.execute(args)`` inside a disposable Docker container."""
        try:
            import docker
        except ImportError as exc:
            raise ImportError(
                "DockerSandboxBackend requires the 'docker' package. "
                "Install with: pip install petfishframework[sandbox-docker]"
            ) from exc

        host_dir = tempfile.mkdtemp(prefix="pff-docker-sandbox-")
        run_id = uuid.uuid4().hex
        result_path = Path(host_dir) / "result.pkl"

        try:
            # Serialize the tool and its arguments into the shared volume.
            with open(Path(host_dir) / "tool.pkl", "wb") as handle:
                pickle.dump(tool, handle)
            with open(Path(host_dir) / "args.pkl", "wb") as handle:
                pickle.dump(args, handle)

            script = (
                "import pickle\n"
                "from pathlib import Path\n"
                "sandbox = Path('/sandbox')\n"
                f"run_id = {run_id!r}\n"
                "with open(sandbox / 'tool.pkl', 'rb') as handle:\n"
                "    tool = pickle.load(handle)\n"
                "with open(sandbox / 'args.pkl', 'rb') as handle:\n"
                "    args = pickle.load(handle)\n"
                "try:\n"
                "    result = tool.execute(args)\n"
                "    payload = {\n"
                "        'value': result.value,\n"
                "        'error': result.error,\n"
                "        'error_code': result.error_code,\n"
                "        'masked': result.masked,\n"
                "    }\n"
                "except Exception as exc:\n"
                "    payload = {'error': str(exc), 'error_code': 'TOOL_INTERNAL_ERROR'}\n"
                "with open(sandbox / 'result.pkl', 'wb') as handle:\n"
                "    pickle.dump(payload, handle)\n"
            )
            command = ["python", "-c", script]

            client = docker.from_env()
            api = client.api
            host_config = api.create_host_config(
                network_mode="none",
                read_only=True,
                tmpfs={"/tmp": ""},
                mem_limit=self._mem_limit,
                binds={host_dir: {"bind": "/sandbox", "mode": "rw"}},
            )
            container = api.create_container(
                image=self._image,
                command=command,
                host_config=host_config,
                volumes=["/sandbox"],
            )
            container_id = container["Id"]
            api.start(container_id)
            api.wait(container_id)
            api.remove_container(container_id, force=True)

            if not result_path.exists():
                return ToolResult(error="docker sandbox did not produce a result")

            with open(result_path, "rb") as handle:
                payload = pickle.load(handle)

            return ToolResult(**payload)
        except Exception as exc:
            return ToolResult(error=f"docker sandbox failed: {exc}")
        finally:
            shutil.rmtree(host_dir, ignore_errors=True)
