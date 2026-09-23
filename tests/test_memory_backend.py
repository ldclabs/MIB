from mib_runner import PACK_REPORT_VERSION
import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from mib_runner.adapter_contract import AdapterLifecycleError, digest
from mib_runner.backend_benchmark import run_backend_benchmark, verify_backend_report
from mib_runner.memory_backend import HttpMemoryBackend, NullMemoryBackend, PROTOCOL
from mib_runner.model_clients import ModelCompletion
from mib_runner.same_model_agent import InvocationRecorder, SameModelAgent
from mib_runner.types import Observation
from mib_runner.report import verify_score
from paths import BASE, DEV_PACK, SCENARIO_SCHEMA_PATH


@pytest.fixture
def server():
    state = {'requests': [], 'runs': {}, 'reject': None, 'mismatch': False, 'oversize': False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def send(self, body, request=None):
            response = {'mib': '0.1', 'protocol': PROTOCOL, 'status': 'ok', 'body': body}
            if request:
                response.update(run_id=request['run_id'], request_id='wrong' if state['mismatch'] else request['request_id'])
            data = json.dumps(response).encode()
            self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            assert self.path == '/mib-memory/v0.1/describe'
            self.send(NullMemoryBackend().describe() | {'implementation': {'name': 'HTTP fixture backend', 'version': '0.1.0'}, 'identity': {'fixture': True}})
        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert req['protocol'] == PROTOCOL
            assert self.path == '/mib-memory/v0.1/' + req['operation']
            state['requests'].append(req)
            op, rid = req['operation'], req['run_id']
            if op == 'reset':
                assert rid not in state['runs']
                state['runs'][rid] = []
            observations = state['runs'][rid]
            body = {'accepted': op != state['reject'], 'cost_scope': 'cumulative_run',
                    'costs': {'receipts': [{'stage': 'formation', 'input_tokens': None, 'accounting_complete': False}],
                              'unreported_stages': ['provider_retries'], 'accounting_complete': False}}
            if op == 'observe': observations.append(req['body']['observation'])
            if op == 'retrieve':
                content = '\n'.join(o.get('content') or json.dumps(o.get('payload')) for o in observations)
                limit = req['body']['limit_chars']
                body.update(items=[{'id': 'receipt:' + req['request_id'], 'content': content[:limit] + ('x' if state['oversize'] else '')}] if content else [],
                            truncated=len(content) > limit, accounting_complete=False)
            if op == 'close': body['closed'] = True
            self.send(body, req)
    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
    yield f'http://127.0.0.1:{http.server_port}', state
    http.shutdown(); http.server_close(); thread.join()


class Model:
    def __init__(self): self.calls = []
    def identity(self): return {'client': 'test', 'model_id': 'fixed'}
    def complete(self, *, messages, parameters, request_id):
        self.calls.append({'messages': copy.deepcopy(messages), 'parameters': parameters})
        prompt = messages[-1]['content']
        if prompt.startswith('MODE: ACTION'):
            output = {'type': 'tool_call', 'tool': 'check', 'arguments': {}} if 'continuation": false' in prompt else {'type': 'final', 'content': 'done'}
        elif prompt.startswith('MODE: OBSERVE'): output = {'emissions': []}
        elif prompt.startswith('MODE: MAINTENANCE'): output = {}
        else: output = {'type': 'message', 'content': 'unknown'}
        return ModelCompletion(json.dumps(output))
    def close(self): pass


def agent(backend, model):
    return SameModelAgent(condition='B0' if isinstance(backend, NullMemoryBackend) else 'MIB_BACKEND_CANDIDATE',
        model_client=model, system_prompt='fixed system', reasoning_policy='fixed reasoning',
        model_parameters={'temperature': 0, 'max_tokens': 100}, recorder=InvocationRecorder(),
        memory_backend=backend, memory_config={'max_memory_chars': 1000, 'parse_retries': 0}, seed_policy='paired_per_call')


def test_http_backend_is_the_only_persistent_memory_and_business_contract_is_fixed(server):
    url, state = server
    models = [Model(), Model()]
    agents = [agent(NullMemoryBackend(), models[0]), agent(HttpMemoryBackend(url), models[1])]
    for a in agents:
        a.reset(run_id='evaluator-run', seed=7, virtual_time='2026-01-01T00:00:00Z')
        a.observe(run_id='evaluator-run', request_id='observe', observation=Observation('o1', 'user_message', content='The code is orchid.'))
        a.session_boundary(run_id='evaluator-run', request_id='boundary', virtual_time='2026-01-02T00:00:00Z')
        a.respond(run_id='evaluator-run', request_id='r1', interaction_id='i', input_data={'content': 'What is the code?'}, virtual_time='2026-01-02T00:00:00Z')
        assert not a.long_term and not a.transient
        a.close()
    p0, p1 = [m.calls[0] for m in models]
    assert p0['messages'][0] == p1['messages'][0]
    assert p0['parameters'] == p1['parameters']
    def remove_memory(call):
        user = call['messages'][-1]['content']
        return user.split('LONG_TERM_MEMORY_CONTEXT:')[0] + user.split('CURRENT_TASK_TRANSIENT_STATE:')[1]
    assert remove_memory(p0) == remove_memory(p1)
    assert 'orchid' not in p0['messages'][-1]['content'] and 'orchid' in p1['messages'][-1]['content']
    assert all(req['run_id'] != 'evaluator-run' for req in state['requests'])
    assert set(req['operation'] for req in state['requests']) == {'reset', 'observe', 'session_boundary', 'retrieve', 'close'}
    assert 'MIB_BACKEND_CANDIDATE' not in json.dumps(state['requests'])


def test_task_tool_feedback_is_transient_until_completion_and_boundary_clears_state(server):
    url, state = server
    a = agent(HttpMemoryBackend(url), Model()); a.reset(run_id='r', seed=1, virtual_time=None)
    step = a.act(run_id='r', request_id='a1', task_id='t', goal='Check state', constraints=[], tools=[{'name':'check'}], continuation=False, virtual_time=None)
    a.observe(run_id='r', request_id='o', observation=Observation('o', 'tool_result', payload={'ok':True}, tool_call_id=step.tool_call_id))
    assert not state['runs'][a.backend.run_id]
    a.act(run_id='r', request_id='a2', task_id='t', goal=None, constraints=[], tools=[], continuation=True, virtual_time=None)
    assert any(o['type'] == 'tool_result' for o in state['runs'][a.backend.run_id])
    a.session_boundary(run_id='r', request_id='s', virtual_time=None)
    assert not a.transient and a.active_task is None and not a._active_tools
    a.close()


@pytest.mark.parametrize('failure', ['mismatch', 'reject', 'oversize'])
def test_http_backend_never_turns_transport_or_contract_failure_into_empty_memory(server, failure):
    url, state = server
    backend = HttpMemoryBackend(url); backend.reset(seed=1, virtual_time=None)
    backend.observe(Observation('o', 'user_message', content='x'*20))
    if failure == 'reject':
        state['reject'] = 'maintain'
        call = lambda: backend.maintain(budget='PT1H', virtual_time=None)
    else:
        state[failure] = True
        call = lambda: backend.retrieve(query='q', limit_chars=10, virtual_time=None)
    with pytest.raises(AdapterLifecycleError): call()
    assert backend.operations[-1]['outcome'] == 'failure'
    if failure != 'mismatch':
        assert backend.operations[-1]['cost_scope'] == 'cumulative_run'
    assert backend.last_costs['receipts'][0]['input_tokens'] is None
    state.update(mismatch=False, reject=None, oversize=False); backend.close()


def config(tmp_path, url):
    pack = tmp_path/'pack'; pack.mkdir(); (pack/'templates').mkdir()
    template = json.loads((DEV_PACK/'epistemic/MIB-EPI-002.json').read_text())
    template['timeline'].append({'id':'last-maintenance','type':'maintenance_window','stage':'consolidation','visibility':'agent','at':{'sequence':999},'payload':{'budget':'PT1H'}})
    (pack/'templates'/'MIB-EPI-002.json').write_text(json.dumps(template))
    profile = {'id':'backend-fixture','version':'0.1.0','track':'memory_system','scenario_pack':{'id':'fixture','version':'0.1.0'},
        'required_templates':[template['id']], 'dimensions':{d:{'weight':1/len(template['dimensions'])} for d in template['dimensions']}}
    (tmp_path/'profile.json').write_text(json.dumps(profile))
    value = {'id':'backend-fixture','pack':str(pack),'scenario_schema':str(SCENARIO_SCHEMA_PATH), 'profile':str(tmp_path/'profile.json'),
        'model':{'client':'deterministic_stub','model_id':'fixture','parameters':{'temperature':0,'max_tokens':100}},
        'agent':{'system_prompt':str(BASE/'prompts/same-model-agent-v0.1.txt'),'reasoning_policy':str(BASE/'prompts/reasoning-policy-v0.1.txt'),
                 'max_memory_chars':1000,'parse_retries':0},
        'memory_backend':{'base_url':url},'execution':{'instance_seeds':[101],'repetitions':1,'include_ablations':True}}
    path=tmp_path/'experiment.json';path.write_text(json.dumps(value));return path


def test_generated_backend_execution_preserves_each_rung_in_frozen_schedule(server, tmp_path):
    url, _ = server
    path = config(tmp_path, url)
    cfg = json.loads(path.read_text())
    profile = json.loads((BASE / 'profiles/MIB-Core-0.2-Dev.json').read_text())
    profile['programs'] = [{'id': 'mib.recall.v1'}]
    profile['dimensions'] = {'retention_retrieval': {'weight': 1}}
    Path(cfg['profile']).write_text(json.dumps(profile))
    cfg['execution']['include_ablations'] = False
    path.write_text(json.dumps(cfg))
    report = run_backend_benchmark(path, model_client=Model())
    assert verify_backend_report(report)['valid']
    assert len(report['experiment_lock']['episode_plan']) == len(report['schedule']) == 3
    for child in report['reports'].values():
        assert child['coverage']['overall'] == 1
        assert len(child['retention']) == 1 and len(child['retention'][0]['rungs']) == 3
    report['schedule'].pop()
    assert not verify_backend_report(report)['valid']


@pytest.mark.parametrize('reject_maintenance', [False, True])
def test_executable_backend_experiment_verifies_and_preserves_failed_maintenance(server, tmp_path, reject_maintenance):
    url,state=server
    if reject_maintenance: state['reject']='maintain'
    report=run_backend_benchmark(config(tmp_path,url),model_client=Model())
    result=verify_score(report)
    assert result['valid'],result
    assert report['reports']['candidate']['report_version']==PACK_REPORT_VERSION
    assert report['total_cost'] is None and report['accounting_complete'] is False
    if not reject_maintenance:
        assert report['fairness_audit']['valid'], report['fairness_audit']
    if reject_maintenance:
        assert not report['fairness_audit']['valid']
        assert report['reports']['candidate']['execution']['execution_failure_rate']>0
    changed=copy.deepcopy(report)
    changed['fairness_audit']['valid']=not changed['fairness_audit']['valid']
    assert not verify_backend_report(changed)['valid']
    changed=copy.deepcopy(report)
    changed['backend_runs']['candidate'][0]['costs']['receipts'][0]['input_tokens']=0
    assert not verify_backend_report(changed)['valid']


def test_model_and_operation_tampering_rejected_even_with_recomputed_evidence_digest(server, tmp_path):
    url, _ = server
    report = run_backend_benchmark(config(tmp_path, url), model_client=Model())
    for field in ['model_identity', 'decoding_fingerprint']:
        changed = copy.deepcopy(report)
        for rows in changed['business_calls'].values():
            for row in rows:
                row[field] = {'model_id': 'other'} if field == 'model_identity' else 'wrong'
        changed['evidence_digest'] = digest({'calls': changed['business_calls'], 'backends': changed['backend_runs']})
        assert not verify_backend_report(changed)['valid']
    changed = copy.deepcopy(report)
    changed['backend_runs']['candidate'][0]['operations'][0]['accepted'] = False
    changed['evidence_digest'] = digest({'calls': changed['business_calls'], 'backends': changed['backend_runs']})
    assert not verify_backend_report(changed)['valid']


def test_failed_statelessness_preflight_cannot_pass_fairness(server, tmp_path):
    class Stateful(Model):
        def complete(self, **kwargs):
            if kwargs['request_id'].startswith('preflight-test-'):
                return ModelCompletion(kwargs['request_id'])
            return super().complete(**kwargs)
    url, _ = server
    report = run_backend_benchmark(config(tmp_path, url), model_client=Stateful())
    assert report['preflight']['passed'] is False
    assert report['fairness_audit']['checks']['statelessness_preflight'] is False
    assert report['fairness_audit']['valid'] is False
    assert verify_backend_report(report)['valid']
    changed = copy.deepcopy(report)
    changed['preflight']['passed'] = True
    changed['fairness_audit']['checks']['statelessness_preflight'] = True
    changed['fairness_audit']['valid'] = True
    assert not verify_backend_report(changed)['valid']


@pytest.mark.parametrize('extra_budget, expected_selected', [(0, 0), (4, 1)])
def test_rendering_overhead_never_slices_a_complete_backend_packet(extra_budget, expected_selected):
    packet = json.dumps({'facts': ['记忆'], 'uncertainty': 'insufficient', 'warnings': ['not execution permission']}, ensure_ascii=False)
    class PacketBackend(NullMemoryBackend):
        def retrieve(self, **kwargs):
            return {'items': [{'id': 'packet', 'content': packet}], 'truncated': False}
    a = agent(PacketBackend(), Model())
    a.max_memory_chars = len(packet) + extra_budget
    text, truncated, selected = a._memory_context('query')
    assert len(text) <= a.max_memory_chars
    assert selected == expected_selected
    assert truncated is (not expected_selected)
    assert a.recorder.memory_selection[-1]['selected'] == expected_selected
    if expected_selected:
        assert json.loads(text.removeprefix('[1] ')) == json.loads(packet)
    else:
        assert text == '<empty>' and packet not in text


def test_backend_rendering_accounts_for_separators_and_handles_tiny_empty_budgets():
    class Packets(NullMemoryBackend):
        def retrieve(self, **kwargs):
            return {'items': [{'id': 'first', 'content': '{"a":1}'}, {'id': 'second', 'content': '{"b":2}'}], 'truncated': False}
    a = agent(Packets(), Model())
    a.max_memory_chars = 22  # Both 11-character lines fit only without their separator.
    text, truncated, selected = a._memory_context('query')
    assert text == '[1] {"a":1}' and truncated and selected == 1
    a.max_memory_chars = 1
    assert a._memory_context('query') == ('', True, 0)
