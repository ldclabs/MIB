from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from . import __version__
from .evaluation_service import EvaluationService, ServiceConfig

# Mutating endpoints register and execute participant-provided Agent code, so a
# request body must never be read before the caller is authenticated.
MAX_REQUEST_BYTES = 1 * 1024 * 1024


class ServiceAuthError(RuntimeError):
    pass


def make_service_handler(service: EvaluationService):
    token = service.api_token()
    if not token:
        raise ServiceAuthError(
            f"HTTP API requires a bearer token; set ${service.config.api_token_env}. "
            "Mutating endpoints register and run untrusted submissions."
        )

    class Handler(BaseHTTPRequestHandler):
        server_version=f"MIBEvaluationService/{__version__}"
        def _authorized(self):
            header=self.headers.get("Authorization","")
            prefix="Bearer "
            if not header.startswith(prefix) or not hmac.compare_digest(header[len(prefix):],token):
                self._send(401,{"error":"unauthorized"}); return False
            return True
        def _send(self,status,obj):
            data=json.dumps(obj,ensure_ascii=False).encode("utf-8"); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
        def _body(self):
            n=int(self.headers.get("Content-Length","0"))
            if n < 0 or n > MAX_REQUEST_BYTES: raise ValueError("request body too large")
            return json.loads(self.rfile.read(n) or b"{}")
        def log_message(self,*args): return
        def do_GET(self):
            u=urlparse(self.path); path=u.path.rstrip("/")
            try:
                if path=="/health": return self._send(200,{"ok":True,"service":"mib-evaluation-service","version":__version__})
                if path=="/submissions":
                    rows=[]
                    for r in service.db.submissions(): rows.append({k:r.get(k) for k in ["id","display_name","owner","track","status","created_at","updated_at"]})
                    return self._send(200,{"submissions":rows})
                if path=="/cycles":
                    rows=[]
                    for r in service.db.cycles():
                        rows.append({"id":r["id"],"profile_id":r["profile_id"],"status":r["status"],"created_at":r["created_at"],"activated_at":r.get("activated_at"),"public_manifest":json.loads(r["public_manifest_json"])})
                    return self._send(200,{"cycles":rows})
                if path=="/jobs":
                    rows=[]
                    for r in service.db.jobs(): rows.append({k:r.get(k) for k in ["id","submission_id","cycle_id","backend","status","created_at","started_at","completed_at","result_id","error"]})
                    return self._send(200,{"jobs":rows})
                if path=="/leaderboard":
                    q=parse_qs(u.query); return self._send(200,service.leaderboard(cycle_id=(q.get("cycle") or [None])[0],profile_id=(q.get("profile") or [None])[0]))
                if path.startswith("/jobs/"):
                    r=service.get_job(path.split("/")[-1]); return self._send(200,{k:r.get(k) for k in ["id","submission_id","cycle_id","backend","status","created_at","started_at","completed_at","result_id","error","manifest","manifest_signature"]})
                if path.startswith("/results/") and path.endswith("/report"):
                    rid=path.split("/")[2]; row=service.db.result(rid)
                    if not row:return self._send(404,{"error":"unknown_result"})
                    return self._send(200,json.loads(Path(row["public_report_path"]).read_text(encoding="utf-8")))
                if path.startswith("/results/") and path.endswith("/attestation"):
                    rid=path.split("/")[2]; row=service.db.result(rid)
                    if not row:return self._send(404,{"error":"unknown_result"})
                    return self._send(200,{"attestation":json.loads(row["attestation_json"]),"signature":json.loads(row["attestation_signature_json"])})
                return self._send(404,{"error":"not_found"})
            except Exception as e:return self._send(400,{"error":repr(e)})
        def do_POST(self):
            path=urlparse(self.path).path.rstrip("/")
            if not self._authorized(): return
            try:
                b=self._body()
                if path=="/submissions": return self._send(201,service.register_submission(b["spec_path"],display_name=b.get("display_name"),owner=b.get("owner"),track=b.get("track","integrated_agent"),smoke_test=bool(b.get("smoke_test",True))))
                if path=="/jobs": return self._send(201,service.enqueue(b["submission_id"],cycle_id=b.get("cycle_id"),backend=b.get("backend")))
                if path=="/worker/once": return self._send(200,service.worker_once())
                if path=="/compare": return self._send(200,service.compare(b["result_a"],b["result_b"],resamples=max(1,min(int(b.get("resamples",5000)),20000)),seed=b.get("seed",20260819)))
                return self._send(404,{"error":"not_found"})
            except Exception as e:return self._send(400,{"error":repr(e)})
    return Handler


def serve(config_path:str,host:str="127.0.0.1",port:int=8088):
    service=EvaluationService(ServiceConfig.load(config_path))
    handler=make_service_handler(service)
    server=ThreadingHTTPServer((host,port),handler)
    server.serve_forever()
