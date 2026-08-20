from mib_runner.types import AgentOutput


class MyAgent:
    def __init__(self):
        self.memory = []

    def describe(self):
        return {
            "protocol": "mib-agent/0.1",
            "implementation": {"name": "My Agent", "version": "0.1.0"},
            "capabilities": {"observe": True, "respond": True},
        }

    def reset(self, *, run_id, seed, virtual_time):
        self.memory = []
        return {"accepted": True}

    def observe(self, *, run_id, request_id, observation):
        self.memory.append(observation)
        return {"accepted": True, "emissions": []}

    def respond(self, *, run_id, request_id, interaction_id, input_data, virtual_time):
        # Replace with your normal Agent + memory implementation.
        return AgentOutput(type="message", content="unknown")
