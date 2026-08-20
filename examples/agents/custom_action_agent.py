"""Minimal skeleton for integrating an action-capable Agent with MIB Milestone 3."""

from mib_runner.types import ActStep, AgentOutput, Observation


class CustomActionAgent:
    def __init__(self):
        self.memory = []

    def describe(self):
        return {
            "protocol": "mib-agent/0.1",
            "implementation": {"name": "Custom Action Agent", "version": "0.1.0"},
            "capabilities": {
                "observe": True,
                "respond": True,
                "act": True,
                "runner_managed_tools": True,
                "virtual_time": True,
            },
        }

    def reset(self, *, run_id, seed, virtual_time):
        self.memory = []
        return {"accepted": True}

    def observe(self, *, run_id, request_id, observation: Observation):
        self.memory.append(observation)
        return {"accepted": True, "emissions": []}

    def respond(self, *, run_id, request_id, interaction_id, input_data, virtual_time):
        return AgentOutput(type="message", content="unknown")

    def act(self, *, run_id, request_id, task_id, goal, constraints, tools, continuation, virtual_time):
        # Replace with your Agent/planner. A tool call must use one of the supplied names.
        if not continuation and tools:
            first = tools[0]["name"]
            return ActStep(type="tool_call", tool_call_id="call_1", tool=first, arguments={})
        return ActStep(type="final", content="done")
