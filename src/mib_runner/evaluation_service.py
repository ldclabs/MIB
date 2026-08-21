from __future__ import annotations

import json
import os
import secrets
import shutil
import traceback
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from . import __version__
from .benchmark import run_materialized_pack
from .capability import render_capability_card
from .hidden import HiddenEvalStore, redact_report_for_public
from .leaderboard import compare_results, leaderboard as build_leaderboard, result_family
from .report import validate_report, verify_score
from .service_db import ServiceDB, utc_now
from .service_signing import derive_key, derive_ed25519_private_key, digest_json, sha256_hex, sign_json_ed25519, verify_json_ed25519, public_key_b64, key_id_from_public_b64
from .submission import build_submission_runtime, load_submission_spec
from .validation import load_json


class ServiceConfigError(ValueError): pass


# Upper bound for client-supplied bootstrap work on the comparison endpoint.
MAX_COMPARE_RESAMPLES = 50_000


def file_digest(path: str | Path) -> str:
    return "sha256:" + sha256_hex(Path(path).read_bytes())


def tree_digest(path: str | Path) -> str:
    root=Path(path)
    rows=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        rows.append({"path":str(p.relative_to(root)),"sha256":sha256_hex(p.read_bytes())})
    return digest_json(rows)


@dataclass(slots=True)
class ServiceConfig:
    db_path: Path
    artifact_root: Path
    scenario_schema: Path
    report_schema: Path
    submission_schema: Path
    job_manifest_schema: Path
    result_attestation_schema: Path
    service_root_secret_env: str = "MIB_SERVICE_ROOT_SECRET"
    backend: str = "local_namespace"
    # Submission specs may only be loaded from inside this directory.  Without
    # it, an API client could name any path on the evaluator host.
    submission_root: Path | None = None
    # Environment variable holding the bearer token required by mutating HTTP
    # endpoints.  The HTTP API refuses to start when it is unset.
    api_token_env: str = "MIB_SERVICE_API_TOKEN"
    # Untrusted submissions require real namespace isolation.  Evaluators may
    # relax this only for local development against trusted agents.
    sandbox_network: str = "disabled_strict"
    allow_remote_http_submissions: bool = False

    @classmethod
    def load(cls, path: str | Path) -> "ServiceConfig":
        p=Path(path).resolve(); raw=json.loads(p.read_text(encoding="utf-8")); base=p.parent
        def rp(v):
            x=Path(v); return x if x.is_absolute() else (base/x).resolve()
        return cls(
            db_path=rp(raw["db_path"]), artifact_root=rp(raw["artifact_root"]),
            scenario_schema=rp(raw["scenario_schema"]), report_schema=rp(raw["report_schema"]),
            submission_schema=rp(raw["submission_schema"]), job_manifest_schema=rp(raw["job_manifest_schema"]),
            result_attestation_schema=rp(raw["result_attestation_schema"]),
            service_root_secret_env=raw.get("service_root_secret_env","MIB_SERVICE_ROOT_SECRET"),
            backend=raw.get("backend","local_namespace"),
            submission_root=rp(raw["submission_root"]) if raw.get("submission_root") else None,
            api_token_env=raw.get("api_token_env","MIB_SERVICE_API_TOKEN"),
            sandbox_network=raw.get("sandbox_network","disabled_strict"),
            allow_remote_http_submissions=bool(raw.get("allow_remote_http_submissions",False)),
        )


class EvaluationService:
    def __init__(self, config: ServiceConfig, *, root_secret: str | None = None) -> None:
        self.config=config; self.db=ServiceDB(config.db_path)
        config.artifact_root.mkdir(parents=True,exist_ok=True)
        self.root_secret=root_secret or os.environ.get(config.service_root_secret_env)
        if not self.root_secret: raise ServiceConfigError(f"missing service root secret: env {config.service_root_secret_env}")
        # Every signing key in the service derives from this secret.  Remove it
        # from the process environment so it cannot reach a submission process
        # through environment inheritance, however the sandbox is configured.
        os.environ.pop(config.service_root_secret_env, None)
        self.eval_key=derive_key(self.root_secret,"evaluation")
        self.job_key=derive_ed25519_private_key(self.root_secret,"job-manifest")
        self.result_key=derive_ed25519_private_key(self.root_secret,"result-attestation")
        self.redaction_key=derive_key(self.root_secret,"public-redaction")

    def api_token(self) -> str | None:
        """Bearer token required by mutating HTTP endpoints, if configured."""
        return os.environ.get(self.config.api_token_env) or None

    def _resolve_spec_path(self, spec_path: str | Path) -> Path:
        p=Path(spec_path).resolve()
        root=self.config.submission_root
        if root is not None:
            root=Path(root).resolve()
            if p != root and root not in p.parents:
                raise ValueError(f"submission spec must live under {root}")
        return p

    def init(self) -> dict[str,Any]:
        job_pub=public_key_b64(self.job_key); result_pub=public_key_b64(self.result_key)
        return {"mib":"0.1","kind":"MIBEvaluationServiceIdentity","version":__version__,"db":str(self.config.db_path),"artifact_root":str(self.config.artifact_root),"backend":self.config.backend,
                "job_signing":{"scheme":"ed25519","public_key":job_pub,"key_id":key_id_from_public_b64(job_pub)},
                "result_signing":{"scheme":"ed25519","public_key":result_pub,"key_id":key_id_from_public_b64(result_pub)}}

    def register_submission(self, spec_path: str | Path, *, display_name: str | None=None, owner: str|None=None, track: str="integrated_agent", smoke_test: bool=True) -> dict[str,Any]:
        p=self._resolve_spec_path(spec_path); spec=load_submission_spec(p)
        schema=load_json(self.config.submission_schema); clean={k:v for k,v in spec.items() if not k.startswith("_")}
        jsonschema.Draft202012Validator(schema).validate(clean)
        desc=None
        if smoke_test:
            runtime=build_submission_runtime(
                spec,
                network=self.config.sandbox_network,
                allow_remote_http=self.config.allow_remote_http_submissions,
                confine_stage_to_spec_dir=True,
            )
            agent=runtime.factory()
            try: desc=agent.describe()
            finally:
                close=getattr(agent,"close",None)
                if callable(close):
                    try: close(run_id=None)
                    except TypeError: close()
        row={"id":spec["id"],"display_name":display_name or spec.get("display_name") or spec["id"],"owner":owner,"track":track,
             "spec_path":str(p),"spec_digest":digest_json(clean),"status":"accepted","descriptor":desc}
        self.db.upsert_submission(row); return self.db.submission(spec["id"])

    def register_cycle(self, cycle_id: str, *, store_path: str|Path, profile_path: str|Path, activate: bool=False) -> dict[str,Any]:
        store_path=Path(store_path).resolve(); profile_path=Path(profile_path).resolve(); store=HiddenEvalStore(store_path); profile=load_json(profile_path)
        row={"id":cycle_id,"profile_id":profile["id"],"store_path":str(store_path),"profile_path":str(profile_path),
             "store_digest":tree_digest(store_path),"profile_digest":file_digest(profile_path),"public_manifest":store.public_manifest(),"status":"registered",
             "transfer_digest":store.transfer_digest()}
        self.db.upsert_cycle(row)
        if activate:self.db.activate_cycle(cycle_id)
        return self.db.cycle(cycle_id)

    def activate_cycle(self, cycle_id:str)->dict[str,Any]: self.db.activate_cycle(cycle_id); return self.db.cycle(cycle_id)

    def _job_manifest(self, *, job_id:str, submission:dict[str,Any], cycle:dict[str,Any], backend:str)->dict[str,Any]:
        manifest={"mib":"0.1","kind":"MIBEvaluationJobManifest","version":"0.1.0","job_id":job_id,"submission_id":submission["id"],
                "submission_spec_digest":submission["spec_digest"],"cycle_id":cycle["id"],"profile_id":cycle["profile_id"],
                "private_store_digest":cycle["store_digest"],"profile_digest":cycle["profile_digest"],"scenario_schema_digest":file_digest(self.config.scenario_schema),
                "report_schema_digest":file_digest(self.config.report_schema),"backend":backend,"runner_version":__version__,"created_at":utc_now(),
                "nonce":secrets.token_hex(16)}
        # Result family is never inferred at read time: it is signed into the
        # manifest, so a job can never be re-filed under a family it did not run.
        # The key matches `benchmark.result_family` in every report and
        # attestation; `diagnostic_mode` means something else entirely in
        # `mib.transfer_diagnostics.v1`.
        manifest["result_family"]=result_family(cycle["profile_id"])
        # Bind the evaluator-private transfer metadata by digest, never by value.
        # A silent post-enqueue edit to Ability support, an oracle artifact, or a
        # transfer relation then breaks manifest verification.
        transfer=cycle.get("transfer_digest")
        if transfer:
            manifest["transfer_support_digest"]=transfer
        return manifest

    def enqueue(self, submission_id:str, *, cycle_id:str|None=None, backend:str|None=None)->dict[str,Any]:
        sub=self.db.submission(submission_id)
        if not sub or sub["status"]!="accepted": raise ValueError("submission is not accepted")
        cycle=self.db.cycle(cycle_id) if cycle_id else self.db.active_cycle()
        if not cycle: raise ValueError("no active evaluation cycle")
        jid="job_"+uuid.uuid4().hex[:20]; backend=backend or self.config.backend
        manifest=self._job_manifest(job_id=jid,submission=sub,cycle=cycle,backend=backend)
        jsonschema.Draft202012Validator(load_json(self.config.job_manifest_schema)).validate(manifest)
        sig=sign_json_ed25519(manifest,self.job_key,context="mib-evaluation-job-manifest/v1")
        self.db.create_job({"id":jid,"submission_id":submission_id,"cycle_id":cycle["id"],"backend":backend,"manifest":manifest,"manifest_signature":sig})
        return self.get_job(jid)

    def get_job(self,jid:str)->dict[str,Any]:
        row=self.db.job(jid)
        if not row: raise KeyError(jid)
        row["manifest"]=json.loads(row.pop("manifest_json")); row["manifest_signature"]=json.loads(row.pop("manifest_signature_json")); return row

    def verify_job_manifest(self,jid:str)->bool:
        job=self.get_job(jid); return verify_json_ed25519(job["manifest"],job["manifest_signature"],expected_context="mib-evaluation-job-manifest/v1",expected_public_key=public_key_b64(self.job_key))

    def _execute_local_namespace(self, job:dict[str,Any])->dict[str,Any]:
        manifest=json.loads(job["manifest_json"]); sig=json.loads(job["manifest_signature_json"])
        if not verify_json_ed25519(manifest,sig,expected_context="mib-evaluation-job-manifest/v1",expected_public_key=public_key_b64(self.job_key)): raise RuntimeError("job manifest signature invalid")
        sub=self.db.submission(job["submission_id"]); cycle=self.db.cycle(job["cycle_id"])
        if digest_json({k:v for k,v in load_submission_spec(sub["spec_path"]).items() if not k.startswith("_")}) != manifest["submission_spec_digest"]: raise RuntimeError("submission spec changed after job enqueue")
        if tree_digest(cycle["store_path"]) != manifest["private_store_digest"]: raise RuntimeError("private evaluation store changed after job enqueue")
        if file_digest(cycle["profile_path"]) != manifest["profile_digest"]: raise RuntimeError("profile changed after job enqueue")

        schema=load_json(self.config.scenario_schema); report_schema=load_json(self.config.report_schema); profile=load_json(cycle["profile_path"]); store=HiddenEvalStore(cycle["store_path"])
        templates,instances,aliases=store.materialize_instances(schema=schema,evaluation_key=self.eval_key,cycle_id=cycle["id"])
        spec=load_submission_spec(sub["spec_path"])
        # Hidden-store masking is an evaluator decision, never a submission one.
        runtime=build_submission_runtime(
            spec,
            persistent_stdio=False,
            network=self.config.sandbox_network,
            hide_paths=[str(Path(cycle["store_path"]).resolve())],
            allow_remote_http=self.config.allow_remote_http_submissions,
            confine_stage_to_spec_dir=True,
        )
        # Each causal condition gets its own Agent process.  Sharing one process
        # across Full and its Ablations would let a submission diff conditions
        # and infer which events were removed.
        probe_agent=runtime.factory()
        try:
            descriptor=probe_agent.describe()
        finally:
            shutdown=getattr(probe_agent,"shutdown",None)
            if callable(shutdown): shutdown()
        report,summary=run_materialized_pack(templates=templates,instances=instances,schema=schema,profile=profile,agent_factory=runtime.factory,
            repetitions=int(profile.get("repetitions",1)),include_ablations=True,
            bootstrap_resamples=int((profile.get("statistics") or {}).get("bootstrap_resamples",0)),bootstrap_seed=f"{cycle['id']}|{sub['id']}")
        report.setdefault("provenance",{})["notes"]=f"MIB Evaluation Service job={job['id']}; cycle={cycle['id']}; submission={sub['id']}; backend=local_namespace."
        validate_report(report,report_schema)
        public=redact_report_for_public(report,aliases=aliases,redaction_key=self.redaction_key)
        validate_report(public,report_schema)
        checked=verify_score(public)
        if not checked["valid"]: raise RuntimeError("public report score verification failed")
        return {"internal_report":report,"public_report":public,"summary":summary,"backend_evidence":{"kind":"local_namespace","submission_transport":runtime.transport,"agent_descriptor":descriptor,"persistent_stdio_process":False,"process_per_condition":runtime.transport=="stdio"}}

    def execute_claimed_job(self, job:dict[str,Any])->dict[str,Any]:
        if job["backend"] != "local_namespace":
            raise RuntimeError(f"backend {job['backend']} is declared but not executable in the M5 reference environment")
        return self._execute_local_namespace(job)

    def worker_once(self, *, backend: str | None = None)->dict[str,Any]:
        worker_backend=backend or self.config.backend
        job=self.db.claim_next_job(worker_backend)
        if not job:return {"status":"idle","backend":worker_backend}
        started=utc_now()
        try:
            execution=self.execute_claimed_job(job); rid="result_"+uuid.uuid4().hex[:20]; outdir=self.config.artifact_root/job["id"]; outdir.mkdir(parents=True,exist_ok=True)
            internal_path=outdir/"internal.report.json"; public_path=outdir/"public.report.json"; card_path=outdir/"capability-card.md"
            internal_path.write_text(json.dumps(execution["internal_report"],indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            public_path.write_text(json.dumps(execution["public_report"],indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            card_path.write_text(render_capability_card(execution["public_report"]),encoding="utf-8")
            pub_digest=file_digest(public_path); int_digest=file_digest(internal_path); score=float(execution["public_report"]["aggregates"]["mib_score"]["final_score"])
            cirow=(execution["public_report"].get("statistics") or {}).get("mib_score",{}).get("ci") or {}
            manifest=json.loads(job["manifest_json"])
            att={"mib":"0.1","kind":"MIBServiceResultAttestation","version":"0.1.0","result_id":rid,"job_id":job["id"],"job_manifest_digest":digest_json(manifest),
                 "submission_id":job["submission_id"],"cycle_id":job["cycle_id"],"profile_id":execution["public_report"]["benchmark"]["profile"]["id"],"score":score,
                 "public_report_digest":pub_digest,"internal_report_digest":int_digest,"backend":job["backend"],"backend_evidence":execution["backend_evidence"],
                 "started_at":started,"completed_at":utc_now(),"attestation_type":"service_attestation","statement":"This is a MIB service-level cryptographic attestation, not hardware or confidential-computing attestation."}
            jsonschema.Draft202012Validator(load_json(self.config.result_attestation_schema)).validate(att)
            attsig=sign_json_ed25519(att,self.result_key,context="mib-service-result-attestation/v1")
            (outdir/"result-attestation.json").write_text(json.dumps({"attestation":att,"signature":attsig},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            self.db.insert_result({"id":rid,"job_id":job["id"],"submission_id":job["submission_id"],"cycle_id":job["cycle_id"],"profile_id":att["profile_id"],"score":score,
                "ci_lower":cirow.get("lower"),"ci_upper":cirow.get("upper"),"public_report_path":str(public_path),"internal_report_path":str(internal_path),
                "public_report_digest":pub_digest,"internal_report_digest":int_digest,"attestation":att,"attestation_signature":attsig})
            self.db.finish_job(job["id"],result_id=rid)
            return {"status":"succeeded","job_id":job["id"],"result_id":rid,"score":score,"public_report":str(public_path),"capability_card":str(card_path)}
        except Exception as exc:
            self.db.finish_job(job["id"],error="".join(traceback.format_exception_only(type(exc),exc)).strip())
            return {"status":"failed","job_id":job["id"],"error":repr(exc)}

    def verify_result_attestation(self,result_id:str)->dict[str,Any]:
        row=self.db.result(result_id)
        if not row: raise KeyError(result_id)
        att=json.loads(row["attestation_json"]); sig=json.loads(row["attestation_signature_json"])
        sig_ok=verify_json_ed25519(att,sig,expected_context="mib-service-result-attestation/v1",expected_public_key=public_key_b64(self.result_key))
        pub_ok=file_digest(row["public_report_path"])==att["public_report_digest"]; int_ok=file_digest(row["internal_report_path"])==att["internal_report_digest"]
        job_ok=self.verify_job_manifest(row["job_id"])
        return {"valid":bool(sig_ok and pub_ok and int_ok and job_ok),"signature_valid":sig_ok,"public_report_digest_valid":pub_ok,"internal_report_digest_valid":int_ok,"job_manifest_valid":job_ok,"result_id":result_id}

    def leaderboard(self,*,cycle_id:str|None=None,profile_id:str|None=None)->dict[str,Any]: return build_leaderboard(self.db,cycle_id=cycle_id,profile_id=profile_id)
    def compare(self,result_a:str,result_b:str,*,resamples:int=5000,seed:int|str=20260819)->dict[str,Any]:
        # Bounded: resamples is client-supplied over HTTP and drives a loop.
        resamples=max(1,min(int(resamples),MAX_COMPARE_RESAMPLES))
        return compare_results(self.db,result_a,result_b,resamples=resamples,seed=seed)
