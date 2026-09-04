"""Reference Reality Task domains for MIB-R.

A domain supplies real tasks and an upstream-style verifier.  Domains here are
reference implementations used to validate the transfer-intervention
methodology; they are not a claim of ecological validity on their own, and they
are not a redistribution of any external benchmark.
"""

from .ledger_codes import LedgerCodesAdapter

__all__ = ["LedgerCodesAdapter"]
