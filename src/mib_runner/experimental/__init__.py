"""Experimental layers: Transfer Intelligence diagnostics, the Memory Adapter, and the MIB-R Reality Track.

Nothing in this package enters the MIB Score, the Causal Score, or Coverage.  The
core Runner depends on it only through explicit, optional hooks (transfer
diagnostics attached to a report, the 2x2 transfer matrix, the reality
benchmark CLI), and a pack whose Templates carry no transfer annotation produces
a report byte-identical to one built without this package.  Interfaces here may
change without a benchmark version bump.
"""
