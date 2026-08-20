from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .sandbox import SandboxPolicy
from .transports import HttpAgentAdapter, StdioAgentAdapter


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


def _sandbox_from_spec(spec: dict[str, Any]) -> SandboxPolicy:
    row = spec.get("sandbox") or {}
    return SandboxPolicy(
        memory_mb=int(row.get("memory_mb", 1024)),
        cpu_seconds=int(row.get("cpu_seconds", 120)),
        file_size_mb=int(row.get("file_size_mb", 128)),
        nofile=int(row.get("nofile", 128)),
        nproc=int(row.get("nproc", 64)),
        network=str(row.get("network", "disabled_best_effort")),
        env_allowlist=list(row.get("env_allowlist") or ["PATH", "HOME", "LANG", "LC_ALL"]),
        hide_paths=list(row.get("hide_paths") or []),
    )


def build_submission_runtime(spec: dict[str, Any], *, persistent_stdio: bool = False) -> SubmissionRuntime:
    transport = spec["transport"]
    timeout = float(spec.get("timeout_seconds", 30.0))
    if transport == "stdio":
        command = spec.get("command")
        if isinstance(command, str): command = shlex.split(command)
        if not command: raise SubmissionSpecError("stdio submission requires command")
        spec_dir = Path(spec.get("_spec_dir") or os.getcwd())
        stage=[]
        for row in spec.get("stage") or []:
            src=Path(row["source"])
            if not src.is_absolute(): src=(spec_dir/src).resolve()
            stage.append({"source":str(src),"dest":str(row["dest"])})
        policy = _sandbox_from_spec(spec)
        env = {str(k): str(v) for k, v in (spec.get("env") or {}).items()}
        def factory():
            return StdioAgentAdapter([str(x) for x in command], timeout_seconds=timeout, sandbox_policy=policy, env=env, stage=stage, persistent=persistent_stdio)
        return SubmissionRuntime(spec, factory, transport)
    if transport == "http":
        base_url = spec.get("base_url")
        if not base_url:
            raise SubmissionSpecError("http submission requires base_url")
        headers = {str(k): str(v) for k, v in (spec.get("headers") or {}).items()}
        def factory():
            return HttpAgentAdapter(base_url, timeout_seconds=timeout, headers=headers)
        return SubmissionRuntime(spec, factory, transport)
    raise SubmissionSpecError(f"unsupported transport: {transport}")
