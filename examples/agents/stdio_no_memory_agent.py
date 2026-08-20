#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from mib_runner.server import serve_stdio
from mib_runner.types import AgentOutput, ActStep

class NoMemoryAgent:
    def describe(self):
        return {
            'protocol':'mib-agent/0.1',
            'implementation':{'name':'MIB No-Memory Fixture','version':'0.5.0','vendor':'MIB'},
            'track_support':['integrated_agent'],
            'capabilities':{'observe':True,'respond':True,'act':True,'spontaneous_emissions':False,'runner_managed_tools':True,'structured_output':False,'virtual_time':True,'seedable':True},
            'state':{'run_isolation':'hard','observe_visibility':'read_after_write','request_idempotency':True},
        }
    def reset(self,*,run_id,seed,virtual_time): return {'reset':True}
    def observe(self,*,run_id,request_id,observation): return {'accepted':True,'emissions':[]}
    def respond(self,*,run_id,request_id,interaction_id,input_data,virtual_time):
        text=(input_data or {}).get('content','')
        # Deliberately memoryless: only answers explicit epistemic unknown prompts; otherwise cannot recover the past.
        if 'Answer exactly one of: yes, no, unknown' in text:
            return AgentOutput(type='message',content='unknown')
        return AgentOutput(type='abstention',content='unknown')
    def act(self,*,run_id,request_id,task_id,goal,constraints,tools,continuation,virtual_time):
        return ActStep(type='final',content='Unable to use prior experience.')

raise SystemExit(serve_stdio(NoMemoryAgent))
