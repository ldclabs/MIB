from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _parts(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {pointer}")
    return [_decode_pointer_token(x) for x in pointer[1:].split("/")]


def _resolve_parent(root: Any, pointer: str, create: bool = False):
    parts = _parts(pointer)
    if not parts:
        return None, None
    cur = root
    for token in parts[:-1]:
        if isinstance(cur, dict):
            if token not in cur:
                if not create:
                    raise KeyError(pointer)
                cur[token] = {}
            cur = cur[token]
        elif isinstance(cur, list):
            cur = cur[int(token)]
        else:
            raise KeyError(pointer)
    return cur, parts[-1]


def get_pointer(root: Any, pointer: str, default: Any = None) -> Any:
    parts = _parts(pointer)
    cur = root
    try:
        for token in parts:
            if isinstance(cur, dict):
                cur = cur[token]
            elif isinstance(cur, list):
                cur = cur[int(token)]
            else:
                return default
        return cur
    except (KeyError, IndexError, ValueError, TypeError):
        return default


@dataclass(slots=True)
class ToolExecution:
    tool: str
    arguments: dict[str, Any]
    result: dict[str, Any]


@dataclass(slots=True)
class WorldState:
    state: dict[str, Any]
    hidden_ground_truth: dict[str, Any]
    tools: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_scenario(cls, world: dict[str, Any]) -> "WorldState":
        return cls(
            copy.deepcopy(world.get("state") or {}),
            copy.deepcopy(world.get("hidden_ground_truth") or {}),
            copy.deepcopy(world.get("tools") or []),
        )

    def apply(self, update: dict[str, Any]) -> None:
        op = update["op"]
        pointer = update["path"]
        value = copy.deepcopy(update.get("value"))
        parent, key = _resolve_parent(self.state, pointer, create=(op in {"set", "append", "increment"}))
        if parent is None:
            if op == "set":
                if not isinstance(value, dict):
                    raise ValueError("only object root replacement is supported")
                self.state = value
                return
            raise ValueError(f"unsupported root operation: {op}")

        if isinstance(parent, dict):
            if op == "set":
                parent[key] = value
            elif op == "unset":
                parent.pop(key, None)
            elif op == "increment":
                parent[key] = parent.get(key, 0) + value
            elif op == "append":
                parent.setdefault(key, []).append(value)
            elif op == "remove":
                target = parent.get(key)
                if isinstance(target, list):
                    try:
                        target.remove(value)
                    except ValueError:
                        pass
                else:
                    parent.pop(key, None)
            else:
                raise ValueError(op)
        elif isinstance(parent, list):
            index = int(key)
            if op == "set":
                parent[index] = value
            elif op == "unset":
                parent.pop(index)
            elif op == "increment":
                parent[index] += value
            elif op == "append":
                parent[index].append(value)
            elif op == "remove":
                if value is None:
                    parent.pop(index)
                else:
                    try:
                        parent[index].remove(value)
                    except ValueError:
                        pass
            else:
                raise ValueError(op)

    def get(self, pointer: str, default: Any = None) -> Any:
        return get_pointer(self.state, pointer, default)

    def exposed_tools(self, allowed: list[str] | None = None) -> list[dict[str, Any]]:
        names = set(allowed or [])
        out: list[dict[str, Any]] = []
        for tool in self.tools:
            tid = tool["id"]
            for op in tool.get("operations", []):
                name = f"{tid}.{op['name']}"
                if names and name not in names:
                    continue
                out.append({
                    "name": name,
                    "description": op.get("description", ""),
                    "input_schema": copy.deepcopy(op.get("input_schema") or {"type": "object", "properties": {}}),
                })
        return out

    def _lookup_tool(self, full_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
        if "." not in full_name:
            raise KeyError(f"tool operation must be <tool>.<operation>: {full_name}")
        tid, opname = full_name.split(".", 1)
        for tool in self.tools:
            if tool["id"] != tid:
                continue
            for op in tool.get("operations", []):
                if op["name"] == opname:
                    return tool, op
        raise KeyError(f"unknown benchmark tool: {full_name}")

    def execute_tool(self, full_name: str, arguments: dict[str, Any] | None = None) -> ToolExecution:
        arguments = copy.deepcopy(arguments or {})
        tool, op = self._lookup_tool(full_name)
        binding = tool.get("simulator_binding")
        opname = op["name"]
        if binding == "mib.deployment.v1":
            result = self._exec_deployment(opname, arguments)
        elif binding == "mib.workspace.v1":
            result = self._exec_workspace(opname, arguments)
        elif binding == "mib.contextual_save.v1":
            result = self._exec_contextual_save(opname, arguments)
        else:
            raise NotImplementedError(f"unsupported simulator binding: {binding!r}")
        return ToolExecution(full_name, arguments, result)

    def _exec_deployment(self, op: str, args: dict[str, Any]) -> dict[str, Any]:
        s = self.state.setdefault("deployment", {})
        if op == "inspect_target":
            return {
                "actual_target": s.get("actual_target"),
                "selected_target": s.get("selected_target"),
            }
        if op == "select_target":
            target = args.get("target")
            if not target:
                return {"success": False, "error": "target_required"}
            s["selected_target"] = target
            return {"success": True, "selected_target": target}
        if op == "run_migration":
            if s.get("selected_target") == s.get("actual_target"):
                s["migration_applied"] = True
                s["last_error"] = None
                return {"success": True, "target": s.get("selected_target")}
            s["migration_applied"] = False
            s["last_error"] = "wrong_target"
            return {
                "success": False,
                "error": "wrong_target",
                "selected_target": s.get("selected_target"),
            }
        if op == "restart_service":
            if s.get("migration_applied"):
                s["service_running"] = True
                s["last_error"] = None
                return {"success": True, "service_running": True}
            s["service_running"] = False
            s["last_error"] = "missing_column"
            return {"success": False, "error": "missing_column", "service_running": False}
        if op == "read_error":
            return {"error": s.get("last_error")}
        if op == "status":
            return copy.deepcopy(s)
        raise KeyError(op)

    def _exec_workspace(self, op: str, args: dict[str, Any]) -> dict[str, Any]:
        s = self.state.setdefault("workspace", {})
        if op == "select_workspace":
            ws = args.get("workspace")
            if not ws:
                return {"success": False, "error": "workspace_required"}
            s["selected_workspace"] = ws
            return {"success": True, "selected_workspace": ws}
        if op == "edit_record":
            s["edited"] = True
            s["value"] = args.get("value", "updated")
            return {"success": True, "edited": True}
        if op == "save":
            if s.get("workspace_required", True) and not s.get("selected_workspace"):
                s["saved"] = False
                s["last_error"] = "workspace_required"
                return {"success": False, "error": "workspace_required"}
            if not s.get("edited"):
                s["saved"] = False
                s["last_error"] = "nothing_to_save"
                return {"success": False, "error": "nothing_to_save"}
            s["saved"] = True
            s["last_error"] = None
            return {"success": True, "saved": True}
        if op == "inspect_status":
            return copy.deepcopy(s)
        raise KeyError(op)

    def _exec_contextual_save(self, op: str, args: dict[str, Any]) -> dict[str, Any]:
        s = self.state.setdefault("contextual_save", {})
        if op == "activate_context":
            if not s.get("context_required", True):
                s["policy_violation"] = True
                return {"success": False, "error": "unnecessary_context_activation"}
            # The Agent must name the context; the simulator never fills in the
            # expected answer for it.
            ctx = args.get("context")
            if not ctx:
                return {"success": False, "error": "context_required"}
            s["active_context"] = ctx
            return {"success": True, "active_context": ctx}
        if op == "edit_item":
            s["edited"] = True
            s["value"] = args.get("value", "updated")
            return {"success": True, "edited": True}
        if op == "commit":
            if s.get("context_required", True) and not s.get("active_context"):
                s["committed"] = False
                s["last_error"] = "context_required"
                return {"success": False, "error": "context_required"}
            if not s.get("edited"):
                s["committed"] = False
                s["last_error"] = "nothing_to_commit"
                return {"success": False, "error": "nothing_to_commit"}
            s["committed"] = True
            s["last_error"] = None
            return {"success": True, "committed": True}
        if op == "inspect_status":
            return copy.deepcopy(s)
        raise KeyError(op)
