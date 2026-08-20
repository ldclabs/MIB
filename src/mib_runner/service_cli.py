from __future__ import annotations

import argparse,json
from pathlib import Path

from .evaluation_service import EvaluationService,ServiceConfig
from .service_api import serve
from .service_signing import verify_json_ed25519
from .evaluation_service import file_digest


def svc(args): return EvaluationService(ServiceConfig.load(args.config))
def emit(x): print(json.dumps(x,indent=2,ensure_ascii=False,default=str))

def main(argv=None):
    p=argparse.ArgumentParser(prog="mib-service",description="MIB Leaderboard / Evaluation Service Milestone 5")
    p.add_argument("--config",default="service/service-config.json")
    sp=p.add_subparsers(dest="cmd",required=True)
    sp.add_parser("init")
    r=sp.add_parser("register-submission"); r.add_argument("spec"); r.add_argument("--name"); r.add_argument("--owner"); r.add_argument("--track",default="integrated_agent"); r.add_argument("--no-smoke",action="store_true")
    c=sp.add_parser("register-cycle"); c.add_argument("cycle"); c.add_argument("--store",required=True); c.add_argument("--profile",required=True); c.add_argument("--activate",action="store_true")
    a=sp.add_parser("activate-cycle"); a.add_argument("cycle")
    e=sp.add_parser("enqueue"); e.add_argument("submission"); e.add_argument("--cycle"); e.add_argument("--backend")
    w=sp.add_parser("worker-once"); w.add_argument("--backend")
    sp.add_parser("recover-running")
    j=sp.add_parser("job"); j.add_argument("job")
    sp.add_parser("jobs")
    l=sp.add_parser("leaderboard"); l.add_argument("--cycle"); l.add_argument("--profile")
    v=sp.add_parser("verify-result"); v.add_argument("result")
    vf=sp.add_parser("verify-attestation-file"); vf.add_argument("attestation_file"); vf.add_argument("--public-report"); vf.add_argument("--expected-key-id")
    q=sp.add_parser("compare"); q.add_argument("result_a"); q.add_argument("result_b"); q.add_argument("--resamples",type=int,default=5000); q.add_argument("--seed",default="20260819")
    h=sp.add_parser("serve"); h.add_argument("--host",default="127.0.0.1"); h.add_argument("--port",type=int,default=8088)
    args=p.parse_args(argv)
    if args.cmd=="serve": return serve(args.config,args.host,args.port)
    if args.cmd=="verify-attestation-file":
        obj=json.loads(Path(args.attestation_file).read_text(encoding="utf-8")); att=obj["attestation"]; sig=obj["signature"]
        signature_valid=verify_json_ed25519(att,sig,expected_context="mib-service-result-attestation/v1")
        key_ok=(args.expected_key_id is None or sig.get("key_id")==args.expected_key_id)
        report_ok=True
        if args.public_report: report_ok=file_digest(args.public_report)==att.get("public_report_digest")
        emit({"valid":bool(signature_valid and key_ok and report_ok),"signature_valid":signature_valid,"expected_key_id_valid":key_ok,"public_report_digest_valid":report_ok,"key_id":sig.get("key_id"),"public_key":sig.get("public_key")})
        return 0 if signature_valid and key_ok and report_ok else 5
    s=svc(args)
    if args.cmd=="init": emit(s.init())
    elif args.cmd=="register-submission": emit(s.register_submission(args.spec,display_name=args.name,owner=args.owner,track=args.track,smoke_test=not args.no_smoke))
    elif args.cmd=="register-cycle": emit(s.register_cycle(args.cycle,store_path=args.store,profile_path=args.profile,activate=args.activate))
    elif args.cmd=="activate-cycle": emit(s.activate_cycle(args.cycle))
    elif args.cmd=="enqueue": emit(s.enqueue(args.submission,cycle_id=args.cycle,backend=args.backend))
    elif args.cmd=="worker-once": emit(s.worker_once(backend=args.backend))
    elif args.cmd=="recover-running": emit({"requeued":s.db.requeue_running_jobs()})
    elif args.cmd=="job": emit(s.get_job(args.job))
    elif args.cmd=="jobs": emit({"jobs":s.db.jobs()})
    elif args.cmd=="leaderboard": emit(s.leaderboard(cycle_id=args.cycle,profile_id=args.profile))
    elif args.cmd=="verify-result": emit(s.verify_result_attestation(args.result))
    elif args.cmd=="compare": emit(s.compare(args.result_a,args.result_b,resamples=args.resamples,seed=args.seed))
    return 0

if __name__=="__main__": raise SystemExit(main())
