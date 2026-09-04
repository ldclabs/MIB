"""Scenario generation: programs over the world model (MIB-Specification §4.2, §4.12).

A *program* samples a lived history from a world model, realizes it as natural
language, and derives every Oracle, relevant-memory set, counterfactual and
leak proof by evaluating queries against the model.  Instances are unbounded,
seeded, and reproducible; interference is generated on a distance ladder.
"""

from .registry import PROGRAMS, generate_instance, generate_pack, program_descriptor

__all__ = ["PROGRAMS", "generate_instance", "generate_pack", "program_descriptor"]
