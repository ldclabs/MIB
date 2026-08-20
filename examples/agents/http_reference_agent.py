#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mib_runner.agents import ReferenceMemoryAgent
from mib_runner.server import serve_http
p=argparse.ArgumentParser()
p.add_argument('--host',default='127.0.0.1')
p.add_argument('--port',type=int,default=8765)
a=p.parse_args()
serve_http(ReferenceMemoryAgent,a.host,a.port)
