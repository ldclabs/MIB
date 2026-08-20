#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.server import serve_stdio
raise SystemExit(serve_stdio(ReferenceMemoryAgent))
