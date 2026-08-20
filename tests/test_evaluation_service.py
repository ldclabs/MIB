from __future__ import annotations

import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from mib_runner import __version__
from mib_runner.evaluation_service import EvaluationService, ServiceConfig
from mib_runner.leaderboard import paired_compare_reports
from mib_runner.service_api import ServiceAuthError, make_service_handler
from mib_runner.service_signing import derive_ed25519_private_key, sign_json_ed25519, verify_json_ed25519

import pytest

from paths import SANDBOX_AVAILABLE, SANDBOX_REASON, EXAMPLES, PRIVATE_EVAL_STORE_DEMO, REPORT_SCHEMA_PATH, SCENARIO_SCHEMA_PATH, SCHEMAS


def make_service(tmp_path: Path) -> EvaluationService:
    cfg=ServiceConfig(
        db_path=tmp_path/'service.sqlite3', artifact_root=tmp_path/'artifacts',
        scenario_schema=SCENARIO_SCHEMA_PATH, report_schema=REPORT_SCHEMA_PATH,
        submission_schema=SCHEMAS/'mib-submission.schema.json',
        job_manifest_schema=SCHEMAS/'mib-evaluation-job-manifest.schema.json',
        result_attestation_schema=SCHEMAS/'mib-service-result-attestation.schema.json',
    )
    return EvaluationService(cfg,root_secret='unit-test-root-secret')


def tiny_store(tmp_path: Path):
    store=tmp_path/'store'; (store/'templates'/'hidden').mkdir(parents=True)
    src=PRIVATE_EVAL_STORE_DEMO/'templates'/'hidden'/'MIB-RET-901.json'
    shutil.copy2(src,store/'templates'/'hidden'/'MIB-RET-901.json')
    manifest={
      'mib':'0.1','kind':'MIBPrivateEvaluationStore','id':'MIB-M5-Test-Store','version':'0.1.0','profile':'MIB-M5-Test-Profile',
      'templates':[{'path':'templates/hidden/MIB-RET-901.json','visibility':'hidden_eval','public_id':'hidden-recall-test','instances':1,'title_public':'Hidden recall test'}]
    }
    (store/'manifest.private.json').write_text(json.dumps(manifest),encoding='utf-8')
    profile={
      'id':'MIB-M5-Test-Profile','version':'0.1.0','official':True,'track':'integrated_agent','scale':'MIB-S','required_coverage':1.0,'repetitions':1,
      'scenario_pack':{'id':'MIB-M5-Test-Store','version':'0.1.0'},'required_templates':['MIB-RET-901'],
      'dimensions':{'retention_retrieval':{'weight':0.8},'causal_memory_impact':{'weight':0.2}},
      'statistics':{'confidence_level':0.95,'bootstrap_resamples':5}
    }
    pp=tmp_path/'profile.json'; pp.write_text(json.dumps(profile),encoding='utf-8')
    return store,pp


def test_job_manifest_signature_rejects_tamper():
    obj={'job':'j1','score':1}
    key=derive_ed25519_private_key('k','test')
    sig=sign_json_ed25519(obj,key,context='ctx')
    assert verify_json_ed25519(obj,sig,expected_context='ctx')
    assert not verify_json_ed25519({'job':'j1','score':2},sig,expected_context='ctx')


@pytest.mark.skipif(not SANDBOX_AVAILABLE, reason=SANDBOX_REASON)
def test_service_job_result_attestation_and_leaderboard(tmp_path):
    svc=make_service(tmp_path); store,profile=tiny_store(tmp_path)
    svc.register_submission(EXAMPLES/'submissions/reference-stdio.json',display_name='Reference',owner='MIB',smoke_test=False)
    svc.register_cycle('cycle-test',store_path=store,profile_path=profile,activate=True)
    job=svc.enqueue('mib-reference-fixture-stdio')
    assert svc.verify_job_manifest(job['id'])
    result=svc.worker_once()
    assert result['status']=='succeeded'
    checked=svc.verify_result_attestation(result['result_id'])
    assert checked['valid']
    board=svc.leaderboard()
    assert board['entries'][0]['score']==100.0
    assert board['entries'][0]['submission_id']=='mib-reference-fixture-stdio'


def test_recover_running_jobs(tmp_path):
    svc=make_service(tmp_path); store,profile=tiny_store(tmp_path)
    svc.register_submission(EXAMPLES/'submissions/reference-stdio.json',smoke_test=False)
    svc.register_cycle('cycle-test',store_path=store,profile_path=profile,activate=True)
    job=svc.enqueue('mib-reference-fixture-stdio')
    claimed=svc.db.claim_next_job('local_namespace')
    assert claimed and svc.db.job(job['id'])['status']=='running'
    assert svc.db.requeue_running_jobs()==1
    assert svc.db.job(job['id'])['status']=='queued'


def test_service_http_requires_api_token(tmp_path, monkeypatch):
    """Mutating endpoints run participant code, so the API must not start open."""
    svc=make_service(tmp_path)
    monkeypatch.delenv(svc.config.api_token_env, raising=False)
    with pytest.raises(ServiceAuthError):
        make_service_handler(svc)


def test_service_http_health(tmp_path, monkeypatch):
    svc=make_service(tmp_path)
    monkeypatch.setenv(svc.config.api_token_env,'test-token')
    server=ThreadingHTTPServer(('127.0.0.1',0),make_service_handler(svc)); th=threading.Thread(target=server.serve_forever,daemon=True); th.start()
    try:
        import urllib.request,urllib.error
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/health') as r:
            body=json.loads(r.read())
        assert body['ok'] is True and body['version']==__version__

        # An unauthenticated POST must be refused before the body is parsed.
        req=urllib.request.Request(
            f'http://127.0.0.1:{server.server_port}/jobs',
            data=json.dumps({'submission_id':'x'}).encode(),
            headers={'Content-Type':'application/json'},method='POST')
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.code==401

        # A wrong token is refused too.
        req.add_header('Authorization','Bearer wrong-token')
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.code==401
    finally:
        server.shutdown(); server.server_close(); th.join(timeout=2)


def test_paired_compare_public_reports():
    reports=[]
    for p in (EXAMPLES/'service').glob('MIB-M5-*.public.report.json'):
        r=json.loads(p.read_text()); reports.append((r['aggregates']['mib_score']['final_score'],r))
    assert len(reports)>=2
    reports.sort(key=lambda x:x[0],reverse=True)
    a,b=reports[0][1],reports[-1][1]
    out=paired_compare_reports(a,b,resamples=100,seed=7)
    assert out['paired_instance_count']==12
    assert out['mib_score_delta_a_minus_b']>50
    assert out['statistically_distinguishable_95'] is True
