"""Public product regressions for retired Brain eval goals, using existing tools/evaluators.

The Agent receives explicit user-owned product records and makes a structured
editor/planning decision. The evaluator observes the saved workspace object;
mentioning a keyword or fetching another graph row cannot satisfy that contract.
"""
from __future__ import annotations
import copy
import json
from datetime import timedelta
from .programs import Program
from .interference import other_actors

FACT_FORMAT = 'mib.product-fact/1'
TOOL = {'id':'workspace','version':'1.0.0','visibility':'agent','simulator_binding':'mib.workspace.v1',
    'operations':[
        {'name':'select_workspace','description':'Select the product draft workspace named in the task.',
         'input_schema':{'type':'object','properties':{'workspace':{'type':'string'}},'required':['workspace'],'additionalProperties':False}},
        {'name':'edit_record','description':'Apply the remembered product facts to the draft object. Preserve uncertainty; use null when no facts establish the requested object. This changes a local draft only.',
         'input_schema':{'type':'object','properties':{'value':{}},'required':['value'],'additionalProperties':False}},
        {'name':'save','description':'Save the local draft after editing. Does not send email, book travel, or execute a purchase.',
         'input_schema':{'type':'object','properties':{},'additionalProperties':False}}]}


class ProductProgram(Program):
    VERSION='0.1.0'
    SUITE='cross'
    DIMENSIONS=['retention_retrieval']
    WEIGHTS={'retention_retrieval':1.0}
    CAPABILITIES=['observe','respond','act','tools','maintenance','virtual_time']
    LADDER=[0,20,100]
    CASE=''

    def build(self,b):
        alice=b.actor('alice','Alice'); bob=b.actor('bob','Bob')
        subject='project-'+format(b.rng.getrandbits(32),'08x')
        b.tools=[copy.deepcopy(TOOL)]
        source_ids=[]
        def fact(eid, actor, value, text, **extra):
            source_ids.append(eid)
            return b.event(eid,stage='past',etype='interaction',actor=actor,content=text,
                payload={'format':FACT_FORMAT,'actor_id':actor,'subject':subject,'value':value,**extra})
        expected={}
        if self.CASE=='style':
            expected[alice]={'draft_policy':{'verbosity':'concise','tone':'direct','promotional':False}}
            fact('style',alice,expected[alice],'Please make my technical drafts concise and direct. Avoid promotional hype.')
        elif self.CASE=='budget':
            amount=b.rng.choice([175000,200000,225000])
            expected[alice]={'project':'home renovation','location':'Orange County, CA',
                'budget':{'amount':amount,'currency':'USD','certainty':'approximate'}}
            fact('budget',alice,expected[alice],f'My Orange County home renovation has a rough budget around USD {amount}. Do not present it as an exact commitment.')
            fact('other-budget',bob,{'project':'home renovation','location':'Los Angeles, CA',
                'budget':{'amount':900000,'currency':'USD','certainty':'exact'}},'My separate project has an exact budget; this does not describe Alice.')
        elif self.CASE=='correction':
            fact('old-city',alice,{'shipping_city':'Tokyo'},'Use Tokyo for my shipping city.')
            expected[alice]={'shipping_city':'Berlin'}
            fact('new-city',alice,expected[alice],'Correction: use Berlin for my shipping city now; Tokyo was the older instruction.')
        elif self.CASE=='reversal':
            fact('old-diet',alice,{'restaurant_policy':'meat-heavy','diet':'omnivore'},'I used to enjoy barbecue restaurants.')
            expected[alice]={'restaurant_policy':'vegetarian','diet':'vegetarian'}
            fact('new-diet',alice,expected[alice],'I am vegetarian now. Plan dinner with vegetarian options instead of the previous meat-heavy preference.')
        elif self.CASE=='boundary':
            expected={alice:{'units':'metric','verbosity':'concise'},bob:{'units':'imperial','verbosity':'detailed'}}
            fact('alice-profile',alice,expected[alice],'For my measurement reports use metric units and concise presentation.')
            fact('bob-profile',bob,expected[bob],'For my own reports use imperial units and detailed presentation.')
        elif self.CASE=='travel':
            airport=b.rng.choice(['SFO','SEA','JFK'])
            expected[alice]={'origin_airport':airport,'seat':'aisle','destination':None}
            fact('origin',alice,{'origin_airport':airport},f'My home airport for work travel is {airport}.')
            fact('seat',alice,{'seat':'aisle','destination':None},'I prefer aisle seats. I have not supplied the destination for the next trip.',merge=True)
            fact('other-travel',bob,{'origin_airport':'LAX','seat':'window','destination':'Tokyo'},'These are Bob\'s plans, not Alice\'s.')
        elif self.CASE=='discount':
            live={'discount_code':'SPRING20','pricing_basis':'current'}
            expected[alice]={'discount_code':None,'pricing_basis':'current'}
            expiry=(b._clock+timedelta(days=30)).isoformat().replace('+00:00','Z')
            fact('discount',alice,live,'SPRING20 applies only before the stated expiry. Afterwards use current pricing without this code.',
                 valid_until=expiry,after_expiry=expected[alice])
            b._clock+=timedelta(days=60)
        elif self.CASE=='usage':
            expected[alice]={'drink':'oolong tea','preparation':'strong'}
            fact('drink',alice,expected[alice],'My morning drink is strong oolong tea.')
        else: raise ValueError('unknown product regression')
        b.maintenance_window('maintain')
        b.interfere(subject_id=alice,attribute='city',exclude_values=set(),other_actors=other_actors(b.rng,{'Alice','Bob'}))
        # Generic placebo/questioning injections must precede every product Probe.
        b.checkpoint('cp')
        def probe(actor,index):
            pid=f'p-{index}'
            reset=b.event('reset-'+pid,stage='pre_probe',etype='world_update',actor=None,visibility='harness',extra={
                'world_updates':[{'op':'set','path':'/workspace','value':{'workspace_required':True,'selected_workspace':None,
                    'edited':False,'saved':False,'last_error':None}}]})
            task={'task':'apply_product_memory_to_local_draft','actor_id':actor,'subject':subject,'workspace':subject}
            b.raw_probe({'id':pid,'kind':'implicit','delivery':'act','trigger':{'after_event':reset},
                'input':{'goal':json.dumps(task,sort_keys=True),'available_tools':['workspace.select_workspace','workspace.edit_record','workspace.save'],
                    'constraints':['Use the requested actor and subject only. Save a local draft; do not send messages or book anything.']},
                'oracle':{'world_assertions':[{'path':'/workspace','operator':'eq','value':{'workspace_required':True,
                    'selected_workspace':subject,'edited':True,'saved':True,'last_error':None,'value':expected[actor]}}]},
                'evaluators':['eval-world'],'dimensions':self.DIMENSIONS,'weight':1})
        for index,actor in enumerate(expected):probe(actor,index)
        if self.CASE=='usage':
            boundary_start=len(b.events)
            b.maintenance_window('maintain-after-first-use')
            for event in b.events[boundary_start:]:event['stage']='pre_probe'
            probe(alice,1)
        b.ablation({'id':'a-required-product-history','kind':'relevant_memory','method':'replay_excluding_events',
            'probes':[p['id'] for p in b.probes],'targets':{'event_ids':source_ids},'expected_effect':'degrade'})
        # These are product instances, not eight independent cognitive abilities.
        b.parameters['legacy_goal']=self.CASE


class StyleProductProgram(ProductProgram):
    ID='mib.product_style.v1'; CASE='style'; TITLE='Apply writing policy, with and without interference'
class BudgetProductProgram(ProductProgram):
    ID='mib.product_budget.v1'; CASE='budget'; TITLE='Approximate renovation budget and project attribution'
class CorrectionProductProgram(ProductProgram):
    ID='mib.product_correction.v1'; CASE='correction'; TITLE='Use the corrected shipping city'
class ReversalProductProgram(ProductProgram):
    ID='mib.product_reversal.v1'; CASE='reversal'; TITLE='Apply current dietary preference'
class BoundaryProductProgram(ProductProgram):
    ID='mib.product_boundary.v1'; CASE='boundary'; TITLE='Keep counterparties separate in applied report settings'
class TravelProductProgram(ProductProgram):
    ID='mib.product_travel.v1'; CASE='travel'; TITLE='Combine origin and seat without inventing destination'
class DiscountProductProgram(ProductProgram):
    ID='mib.product_discount.v1'; CASE='discount'; TITLE='Expired code must not enter the current pricing draft'
class UsageProductProgram(ProductProgram):
    ID='mib.product_usage.v1'; CASE='usage'; TITLE='Repeated application across maintenance, without reinforcement assumptions'

PRODUCT_PROGRAM_CLASSES=[StyleProductProgram,BudgetProductProgram,CorrectionProductProgram,ReversalProductProgram,
    BoundaryProductProgram,TravelProductProgram,DiscountProductProgram,UsageProductProgram]
