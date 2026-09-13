"""No-model product fixture over explicit public records, never an empirical baseline."""
from __future__ import annotations
import copy
import json
from .v2 import StructuredMemoryAgent
from ..generate.products import FACT_FORMAT
from ..types import ActStep

class ProductMemoryFixture(StructuredMemoryAgent):
    NAME='MIB Product Record Fixture (not a language model)'

    def describe(self):
        result=super().describe()
        result['capabilities']['spontaneous_emissions']=False
        return result

    def act(self,*,run_id,request_id,task_id,goal,constraints,tools,continuation,virtual_time):
        if not continuation:
            task=json.loads(goal)
            current=None
            for observation in self._memory():
                data=observation.payload
                if not isinstance(data,dict) or data.get('format')!=FACT_FORMAT:continue
                if data['actor_id']!=(observation.actor or {}).get('id'):continue
                if data['actor_id']!=task['actor_id'] or data['subject']!=task['subject']:continue
                value=copy.deepcopy(data.get('after_expiry') if data.get('valid_until') and virtual_time>=data['valid_until'] else data['value'])
                if data.get('merge') and isinstance(current,dict):current.update(value)
                else:current=value
            self.task_states[task_id]={'step':0,'workspace':task['workspace'],'value':current}
        state=self.task_states[task_id]
        actions=[('workspace.select_workspace',{'workspace':state['workspace']}),
                 ('workspace.edit_record',{'value':state['value']}),('workspace.save',{})]
        if state['step']==len(actions):return ActStep(type='final',content='Local draft saved.')
        name,args=actions[state['step']];state['step']+=1
        return self._call(name,args)
