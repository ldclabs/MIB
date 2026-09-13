"""Track A runtime memory seam. Independent of experimental AO MemoryAdapter.

The evaluator owns the business model, prompt, tools and action loop. A backend
only stores lived observations, returns memory context and manages its lifecycle.
"""
from __future__ import annotations

import copy
import json
import os
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict
from typing import Any, Protocol

from .adapter_contract import AdapterLifecycleError, digest, require_accepted
from .transports import (AgentTransportError, MAX_HTTP_RESPONSE_BYTES, _NoRedirectHandler,
                         _check_response, PROTOCOL_IDENTITY_FIELDS)
from .types import Observation

PROTOCOL = "mib-memory-backend/0.1"
PREFIX = "/mib-memory/v0.1"
CAPABILITIES = ("observe", "retrieve", "maintenance", "session_boundary", "virtual_time", "run_isolation")


class MemoryBackend(Protocol):
    def describe(self) -> dict[str, Any]: ...
    def reset(self, *, seed, virtual_time) -> dict[str, Any]: ...
    def observe(self, observation: Observation) -> dict[str, Any]: ...
    def retrieve(self, *, query: str, limit_chars: int, virtual_time) -> dict[str, Any]: ...
    def maintain(self, *, budget, virtual_time) -> dict[str, Any]: ...
    def session_boundary(self, *, virtual_time) -> dict[str, Any]: ...
    def close(self) -> dict[str, Any]: ...


def check_backend_descriptor(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict) or body.get("protocol") != PROTOCOL:
        raise AgentTransportError(f"memory backend must declare {PROTOCOL}")
    if any(body.get("capabilities", {}).get(c) is not True for c in CAPABILITIES):
        raise AgentTransportError("memory backend lacks explicit required capabilities")
    impl = body.get("implementation", {})
    if not isinstance(impl, dict) or any(not impl.get(k) for k in ("name", "version")):
        raise AgentTransportError("memory backend lacks implementation identity")
    if not isinstance(body.get("identity"), dict) or not body["identity"]:
        raise AgentTransportError("memory backend lacks configuration identity")
    return body


def validate_retrieval(result: Any, limit_chars: int) -> dict[str, Any]:
    if not isinstance(result, dict) or not isinstance(result.get("items"), list) or type(result.get("truncated")) is not bool:
        raise AgentTransportError("retrieve requires items and boolean truncated")
    ids = set()
    for item in result["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or not isinstance(item.get("content"), str):
            raise AgentTransportError("retrieve items require nonempty id and string content")
        if item["id"] in ids:
            raise AgentTransportError("retrieve returned duplicate receipt ids")
        ids.add(item["id"])
    # The final prompt rendering is bounded separately, including [n] prefixes.
    if sum(len(i["content"]) for i in result["items"]) > limit_chars:
        raise AgentTransportError("retrieve exceeded its requested content budget")
    return result


class NullMemoryBackend:
    """B0: current-task working state is owned by SameModelAgent; nothing persists."""
    def __init__(self):
        self.run_id = None
        self.operations = []

    def describe(self):
        return {"protocol": PROTOCOL, "implementation": {"name": "MIB NullBackend", "version": "0.1.0"},
                "capabilities": dict.fromkeys(CAPABILITIES, True), "identity": {"memory": "none"}}

    def _result(self, operation, **body):
        costs = {"receipts": [], "unreported_stages": [], "accounting_complete": True}
        result = {"accepted": True, "cost_scope": "cumulative_run", "costs": costs, **body}
        self.operations.append({"operation": operation, "run_id": self.run_id, "outcome": "success", "costs": costs,
                                "cost_scope": "cumulative_run", "accepted": True,
                                **({"closed": True} if operation == "close" else {})})
        return result

    def reset(self, *, seed, virtual_time):
        if self.run_id is not None:
            raise AdapterLifecycleError("backend reset requires a fresh instance")
        self.run_id = "memory_" + uuid.uuid4().hex
        return self._result("reset")

    def observe(self, observation): return self._result("observe")
    def retrieve(self, *, query, limit_chars, virtual_time): return self._result("retrieve", items=[], truncated=False, accounting_complete=True)
    def maintain(self, *, budget, virtual_time): return self._result("maintain")
    def session_boundary(self, *, virtual_time): return self._result("session_boundary")
    def close(self): return self._result("close")


class HttpMemoryBackend:
    """Bounded, correlated HTTP; no automatic retry of uncertain mutations."""
    def __init__(self, base_url: str, *, timeout_seconds: float = 120.0,
                 api_key_env: str | None = None, allow_remote_http: bool = False):
        parsed = urllib.parse.urlparse(base_url)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("backend URL must be an HTTP(S) origin without credentials/query/fragment")
        if not local and (not allow_remote_http or parsed.scheme != "https"):
            raise ValueError("remote backend requires explicit allow_remote_http and HTTPS")
        if timeout_seconds <= 0:
            raise ValueError("backend timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.headers = {"Content-Type": "application/json"}
        if api_key_env:
            token = os.environ.get(api_key_env)
            if not token:
                raise ValueError(f"missing backend token environment variable {api_key_env}")
            self.headers["Authorization"] = "Bearer " + token
        self.opener = urllib.request.build_opener(_NoRedirectHandler)
        self.run_id = None
        self.operations: list[dict[str, Any]] = []
        self.last_costs = None
        self._descriptor = None
        self._closed = False

    def _call(self, operation, *, body=None, virtual_time=None, describe=False):
        request = {"mib": "0.1", "protocol": PROTOCOL, "operation": operation,
                   "run_id": self.run_id, "request_id": "memory_req_" + uuid.uuid4().hex,
                   "virtual_time": virtual_time, "body": body or {}}
        evidence = {"operation": operation, "run_id": self.run_id, "request_id": request["request_id"],
                    "request_digest": digest(request)}
        req = urllib.request.Request(self.base_url + PREFIX + "/" + operation,
            data=None if describe else json.dumps(request, ensure_ascii=False).encode(),
            headers=self.headers, method="GET" if describe else "POST")
        try:
            with self.opener.open(req, timeout=self.timeout_seconds) as response:
                raw = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
            if len(raw) > MAX_HTTP_RESPONSE_BYTES:
                raise AgentTransportError("memory backend response exceeded size bound")
            envelope = json.loads(raw)
            # Preserve cumulative accounting even when the operation itself fails.
            sources = [envelope.get("body"), envelope.get("extensions")]
            cost_source = next((source for source in sources if isinstance(source, dict) and "costs" in source), {})
            costs = cost_source.get("costs")
            cost_scope = cost_source.get("cost_scope")
            correlated = all(envelope.get(k) == request.get(k) for k in ("mib", "protocol", "run_id", "request_id"))
            if costs is not None and correlated:
                evidence["costs"] = copy.deepcopy(costs)
                evidence["cost_scope"] = cost_scope
                if cost_scope == "cumulative_run":
                    self.last_costs = copy.deepcopy(costs)
            result = _check_response(envelope, request, PROTOCOL_IDENTITY_FIELDS if describe else ("mib", "protocol", "request_id", "run_id"))
            if not isinstance(result, dict):
                raise AgentTransportError("memory backend body must be an object")
            if not describe:
                if result.get("cost_scope") != "cumulative_run" or not isinstance(result.get("costs"), dict):
                    raise AgentTransportError("backend must return cumulative_run costs (unknown values remain null)")
                costs = result["costs"]
                if type(costs.get("accounting_complete")) is not bool or not isinstance(costs.get("receipts"), list) or not isinstance(costs.get("unreported_stages"), list):
                    raise AgentTransportError("invalid backend CostSummary")
                if operation == "close":
                    if result.get("closed") is not True:
                        raise AgentTransportError("close must return closed=true")
                elif operation != "retrieve":
                    require_accepted(operation, result)
            evidence.update(outcome="success", response_digest=digest(result), cost_scope=result.get("cost_scope"))
            if operation in {"reset", "observe", "maintain", "session_boundary"}:
                evidence["accepted"] = result.get("accepted")
            if operation == "close":
                evidence["closed"] = result.get("closed")
            if operation == "retrieve":
                evidence["retrieval"] = {"items": result.get("items"), "truncated": result.get("truncated"),
                                         "limit_chars": request["body"].get("limit_chars")}
            return result
        except Exception as exc:
            evidence.update(outcome="failure", error=repr(exc))
            raise AdapterLifecycleError(f"memory backend {operation}: {exc}") from exc
        finally:
            if not describe:
                self.operations.append(evidence)

    def describe(self):
        if self._descriptor is None:
            self._descriptor = check_backend_descriptor(self._call("describe", describe=True))
        expected = getattr(self, "expected_descriptor_digest", None)
        if expected is not None and digest(self._descriptor) != expected:
            raise AdapterLifecycleError("backend descriptor changed after experiment lock")
        return copy.deepcopy(self._descriptor)

    def reset(self, *, seed, virtual_time):
        if self.run_id is not None:
            raise AdapterLifecycleError("backend reset requires a fresh instance and run id")
        self.describe()
        self.run_id = "memory_" + uuid.uuid4().hex
        return self._call("reset", body={"mode": "fresh", "seed": seed, "virtual_time": virtual_time}, virtual_time=virtual_time)

    def observe(self, observation: Observation):
        return self._call("observe", body={"observation": asdict(observation)}, virtual_time=observation.virtual_time)

    def retrieve(self, *, query, limit_chars, virtual_time):
        result = self._call("retrieve", body={"query": query, "limit_chars": limit_chars}, virtual_time=virtual_time)
        try:
            return validate_retrieval(result, limit_chars)
        except Exception as exc:
            self.operations[-1].update(outcome="failure", error=repr(exc))
            raise AdapterLifecycleError(f"memory backend retrieve: {exc}") from exc

    def maintain(self, *, budget, virtual_time):
        return self._call("maintain", body={"budget": budget}, virtual_time=virtual_time)

    def session_boundary(self, *, virtual_time):
        return self._call("session_boundary", virtual_time=virtual_time)

    def close(self):
        if not self.run_id or self._closed:
            return {"accepted": True}
        result = self._call("close", body={"reason": "run_complete"})
        self._closed = True
        return result

    def evidence(self):
        return {"descriptor": self._descriptor, "operations": copy.deepcopy(self.operations),
                "cost_scope": "cumulative_run", "costs": copy.deepcopy(self.last_costs),
                "accounting_complete": bool(self.last_costs and self.last_costs.get("accounting_complete"))}
