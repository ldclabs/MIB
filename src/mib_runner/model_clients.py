from __future__ import annotations

import json
import os
import subprocess
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class ModelCompletion:
    text: str
    usage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelClient(Protocol):
    def identity(self) -> dict[str, Any]: ...
    def complete(self, *, messages: list[dict[str, str]], parameters: dict[str, Any], request_id: str) -> ModelCompletion: ...
    def close(self) -> None: ...


class HttpJsonModelClient:
    """Provider-neutral stateless HTTP JSON model adapter.

    Request contract:
      {"model": <id>, "messages": [...], "parameters": {...}, "request_id": "..."}

    Response contract:
      {"text": "...", "usage": {...}, "metadata": {...}}

    This intentionally avoids provider-specific conversational state.
    """

    def __init__(self, *, endpoint: str, model_id: str, timeout_s: float = 120.0,
                 headers: dict[str, str] | None = None, api_key_env: str | None = None) -> None:
        self.endpoint = endpoint
        self.model_id = model_id
        self.timeout_s = timeout_s
        self.headers = dict(headers or {})
        if api_key_env:
            token = os.environ.get(api_key_env)
            if not token:
                raise RuntimeError(f"missing model API key environment variable: {api_key_env}")
            self.headers.setdefault("Authorization", f"Bearer {token}")

    def identity(self) -> dict[str, Any]:
        return {"client": "http_json", "model_id": self.model_id, "endpoint": self.endpoint}

    def complete(self, *, messages: list[dict[str, str]], parameters: dict[str, Any], request_id: str) -> ModelCompletion:
        body = json.dumps({
            "model": self.model_id,
            "messages": messages,
            "parameters": parameters,
            "request_id": request_id,
        }, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", **self.headers}
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"model HTTP {exc.code}: {detail}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise RuntimeError("model endpoint must return an object containing string field 'text'")
        return ModelCompletion(
            text=payload["text"],
            usage=dict(payload.get("usage") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )

    def close(self) -> None:
        return None


class OpenAICompatibleChatClient:
    """Minimal OpenAI-compatible chat-completions adapter.

    The endpoint is fully configurable; no provider session is used. The client
    sends independent requests and extracts choices[0].message.content.
    """

    def __init__(self, *, endpoint: str, model_id: str, timeout_s: float = 120.0,
                 api_key_env: str | None = None, headers: dict[str, str] | None = None) -> None:
        self.endpoint = endpoint
        self.model_id = model_id
        self.timeout_s = timeout_s
        self.headers = dict(headers or {})
        if api_key_env:
            token = os.environ.get(api_key_env)
            if not token:
                raise RuntimeError(f"missing model API key environment variable: {api_key_env}")
            self.headers.setdefault("Authorization", f"Bearer {token}")

    def identity(self) -> dict[str, Any]:
        return {"client": "openai_compatible_chat", "model_id": self.model_id, "endpoint": self.endpoint}

    def complete(self, *, messages: list[dict[str, str]], parameters: dict[str, Any], request_id: str) -> ModelCompletion:
        payload: dict[str, Any] = {"model": self.model_id, "messages": messages, **parameters}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "X-MIB-Request-ID": request_id, **self.headers}
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                out = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"model HTTP {exc.code}: {detail}") from exc
        try:
            text = out["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError("invalid OpenAI-compatible response: expected choices[0].message.content") from exc
        if not isinstance(text, str):
            raise RuntimeError("model content is not a string")
        return ModelCompletion(text=text, usage=dict(out.get("usage") or {}), metadata={"response_id": out.get("id")})

    def close(self) -> None:
        return None


class SubprocessJsonlModelClient:
    """Persistent JSONL subprocess model adapter for local servers/wrappers."""

    def __init__(self, *, command: list[str], model_id: str, cwd: str | None = None, env: dict[str, str] | None = None) -> None:
        self.command = list(command)
        self.model_id = model_id
        child_env = os.environ.copy()
        child_env.update(env or {})
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
            env=child_env,
        )
        self._lock = threading.Lock()

    def identity(self) -> dict[str, Any]:
        return {"client": "subprocess_jsonl", "model_id": self.model_id, "command": self.command}

    def complete(self, *, messages: list[dict[str, str]], parameters: dict[str, Any], request_id: str) -> ModelCompletion:
        if not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("model subprocess pipes unavailable")
        req = {"model": self.model_id, "messages": messages, "parameters": parameters, "request_id": request_id}
        with self._lock:
            self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read()[-2000:] if self.proc.stderr else ""
            raise RuntimeError(f"model subprocess exited without response: {err}")
        out = json.loads(line)
        if "error" in out:
            raise RuntimeError(f"model subprocess error: {out['error']}")
        if not isinstance(out.get("text"), str):
            raise RuntimeError("subprocess model response requires string field 'text'")
        return ModelCompletion(out["text"], dict(out.get("usage") or {}), dict(out.get("metadata") or {}))

    def close(self) -> None:
        if self.proc.poll() is None:
            try:
                if self.proc.stdin:
                    self.proc.stdin.write(json.dumps({"operation": "close"}) + "\n")
                    self.proc.stdin.flush()
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                self.proc.kill()


class DeterministicStubModelClient:
    """Engineering-only model stub.

    It is deliberately small and never eligible for empirical release. It
    validates prompt construction, stateless calls, JSON parsing, and tool-loop
    plumbing without pretending to be a real LLM.
    """

    def __init__(self, *, model_id: str = "mib-deterministic-stub/0.1") -> None:
        self.model_id = model_id

    def identity(self) -> dict[str, Any]:
        return {"client": "deterministic_stub", "model_id": self.model_id, "empirical": False}

    def complete(self, *, messages: list[dict[str, str]], parameters: dict[str, Any], request_id: str) -> ModelCompletion:
        user = messages[-1]["content"] if messages else ""
        # A deliberately tiny smoke-test vocabulary.
        if "MODE: RESPONSE" in user:
            if "access code" in user.casefold():
                import re
                m = re.findall(r"\b[A-Z][A-Z0-9]{1,12}-\d{1,5}\b", user)
                answer = m[-1] if m else "unknown"
                return ModelCompletion(json.dumps({"type": "message", "content": answer}))
            return ModelCompletion(json.dumps({"type": "abstention", "content": "unknown"}))
        if "MODE: ACTION" in user:
            if "smoke.set_flag" in user and "\"flag\": true" not in user:
                return ModelCompletion(json.dumps({"type": "tool_call", "tool": "smoke.set_flag", "arguments": {"flag": True}}))
            return ModelCompletion(json.dumps({"type": "final", "content": "done"}))
        return ModelCompletion(json.dumps({"type": "abstention", "content": "unknown"}))

    def close(self) -> None:
        return None


def build_model_client(config: dict[str, Any]) -> ModelClient:
    kind = config.get("client")
    model_id = config.get("model_id") or ""
    if not model_id:
        raise ValueError("model.model_id is required")
    if kind == "http_json":
        return HttpJsonModelClient(
            endpoint=config["endpoint"], model_id=model_id,
            timeout_s=float(config.get("timeout_s", 120)),
            headers=dict(config.get("headers") or {}), api_key_env=config.get("api_key_env"),
        )
    if kind == "openai_compatible_chat":
        return OpenAICompatibleChatClient(
            endpoint=config["endpoint"], model_id=model_id,
            timeout_s=float(config.get("timeout_s", 120)),
            api_key_env=config.get("api_key_env"), headers=dict(config.get("headers") or {}),
        )
    if kind == "subprocess_jsonl":
        return SubprocessJsonlModelClient(
            command=list(config["command"]), model_id=model_id,
            cwd=config.get("cwd"), env=dict(config.get("env") or {}),
        )
    if kind == "deterministic_stub":
        return DeterministicStubModelClient(model_id=model_id)
    raise ValueError(f"unsupported model client: {kind!r}")
