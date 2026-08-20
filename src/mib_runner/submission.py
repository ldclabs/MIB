"""Submission spec loading and runtime construction.

A submission spec is participant-controlled JSON.  It declares *what* to run
(transport, command or base URL) but never *how strongly* it is contained: the
sandbox policy is supplied by the evaluator through ``SandboxPolicy`` and only
resource limits may be softened, clamped to server-side maxima.
"""

from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .sandbox import DEFAULT_ENV_ALLOWLIST, SandboxPolicy
from .transports import HttpAgentAdapter, StdioAgentAdapter

# Upper bounds a submission may not exceed.  A submission may request less.
MAX_MEMORY_MB = 4096
MAX_CPU_SECONDS = 900
MAX_FILE_SIZE_MB = 512
MAX_NOFILE = 1024
MAX_NPROC = 256

# Hosts a submission's HTTP transport may target when the evaluator has not
# explicitly widened the policy.  Prevents SSRF into cloud metadata services and
# internal networks from an evaluator host.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class SubmissionSpecError(ValueError):
    pass


@dataclass(slots=True)
class SubmissionRuntime:
    spec: dict[str, Any]
    factory: Callable[[], Any]
    transport: str


def load_submission_spec(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    spec = json.loads(p.read_text(encoding="utf-8"))
    if "id" not in spec or "transport" not in spec:
        raise SubmissionSpecError("submission spec requires id and transport")
    spec["_spec_dir"] = str(p.resolve().parent)
    return spec


def _clamp(value: Any, default: int, maximum: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, maximum))


def sandbox_policy_for(
    spec: dict[str, Any],
    *,
    network: str = "disabled_best_effort",
    hide_paths: list[str] | None = None,
    stage_roots: list[str] | None = None,
) -> SandboxPolicy:
    """Build the containment policy for a submission.

    Resource limits are read from the spec but clamped.  ``network``,
    ``env_allowlist``, ``hide_paths`` and ``stage_roots`` are evaluator-only:
    anything the spec says about them is ignored, because a submission must not
    be able to widen its own containment.
    """
    requested = spec.get("sandbox") or {}
    return SandboxPolicy(
        memory_mb=_clamp(requested.get("memory_mb"), 1024, MAX_MEMORY_MB),
        cpu_seconds=_clamp(requested.get("cpu_seconds"), 120, MAX_CPU_SECONDS),
        file_size_mb=_clamp(requested.get("file_size_mb"), 128, MAX_FILE_SIZE_MB),
        nofile=_clamp(requested.get("nofile"), 128, MAX_NOFILE),
        nproc=_clamp(requested.get("nproc"), 64, MAX_NPROC),
        network=network,
        env_allowlist=list(DEFAULT_ENV_ALLOWLIST),
        hide_paths=list(hide_paths or []),
        stage_roots=list(stage_roots or []),
    )


def _validate_base_url(base_url: str, *, allow_remote: bool) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise SubmissionSpecError(f"http submission base_url must be http(s): {base_url!r}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise SubmissionSpecError(f"http submission base_url has no host: {base_url!r}")
    is_local = host in LOCAL_HOSTS
    if not allow_remote and not is_local:
        raise SubmissionSpecError(
            f"http submission targets non-local host {host!r}; the evaluator must opt in via allow_remote_http"
        )
    if not is_local and parsed.scheme != "https":
        raise SubmissionSpecError(f"remote http submission must use https: {base_url!r}")


def build_submission_runtime(
    spec: dict[str, Any],
    *,
    persistent_stdio: bool = False,
    network: str = "disabled_best_effort",
    hide_paths: list[str] | None = None,
    allow_remote_http: bool = False,
    confine_stage_to_spec_dir: bool = False,
) -> SubmissionRuntime:
    transport = spec["transport"]
    timeout = float(spec.get("timeout_seconds", 30.0))
    if transport == "stdio":
        command = spec.get("command")
        if isinstance(command, str):
            command = shlex.split(command)
        if not command:
            raise SubmissionSpecError("stdio submission requires command")
        # Staging may only read from the submission's own directory.  Without
        # this a spec could name the private evaluation store as a source and
        # have the Runner copy it into the sandbox before isolation exists.
        spec_dir = Path(spec.get("_spec_dir") or os.getcwd()).resolve()
        stage = []
        for row in spec.get("stage") or []:
            src = Path(row["source"])
            if not src.is_absolute():
                src = (spec_dir / src).resolve()
            stage.append({"source": str(src), "dest": str(row["dest"])})
        policy = sandbox_policy_for(
            spec,
            network=network,
            hide_paths=hide_paths,
            stage_roots=[str(spec_dir)] if confine_stage_to_spec_dir else [],
        )
        env = {str(k): str(v) for k, v in (spec.get("env") or {}).items()}

        def factory():
            return StdioAgentAdapter(
                [str(x) for x in command],
                timeout_seconds=timeout,
                sandbox_policy=policy,
                env=env,
                stage=stage,
                persistent=persistent_stdio,
            )

        return SubmissionRuntime(spec, factory, transport)
    if transport == "http":
        base_url = spec.get("base_url")
        if not base_url:
            raise SubmissionSpecError("http submission requires base_url")
        _validate_base_url(str(base_url), allow_remote=allow_remote_http)
        headers = {str(k): str(v) for k, v in (spec.get("headers") or {}).items()}

        def factory():
            return HttpAgentAdapter(base_url, timeout_seconds=timeout, headers=headers)

        return SubmissionRuntime(spec, factory, transport)
    raise SubmissionSpecError(f"unsupported transport: {transport}")
