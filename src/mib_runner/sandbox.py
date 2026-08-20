from __future__ import annotations

import os, resource, shutil, signal, subprocess, tempfile, shlex
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(slots=True)
class SandboxPolicy:
    memory_mb:int=1024; cpu_seconds:int=120; file_size_mb:int=128; nofile:int=128; nproc:int=64
    network:str="disabled_best_effort"  # inherit | disabled_best_effort | disabled_strict
    env_allowlist:list[str]=field(default_factory=lambda:["PATH","HOME","LANG","LC_ALL"])
    hide_paths:list[str]=field(default_factory=list)

@dataclass(slots=True)
class SandboxProcess:
    process:subprocess.Popen; workdir:str; network_isolated:bool; filesystem_isolated:bool; warnings:list[str]
    def terminate(self):
        if self.process.poll() is not None: return
        try: os.killpg(self.process.pid, signal.SIGTERM)
        except Exception:
            try:self.process.terminate()
            except Exception:pass
        try:self.process.wait(timeout=2)
        except Exception:
            try:os.killpg(self.process.pid, signal.SIGKILL)
            except Exception:pass

def _mb(n): return max(1,int(n))*1024*1024

def _preexec(policy):
    def fn():
        os.setsid()
        resource.setrlimit(resource.RLIMIT_AS,(_mb(policy.memory_mb),_mb(policy.memory_mb)))
        resource.setrlimit(resource.RLIMIT_CPU,(policy.cpu_seconds,policy.cpu_seconds+1))
        resource.setrlimit(resource.RLIMIT_FSIZE,(_mb(policy.file_size_mb),_mb(policy.file_size_mb)))
        resource.setrlimit(resource.RLIMIT_NOFILE,(policy.nofile,policy.nofile))
        if hasattr(resource,"RLIMIT_NPROC"): resource.setrlimit(resource.RLIMIT_NPROC,(policy.nproc,policy.nproc))
    return fn

def _namespace_supported()->bool:
    if os.name!="posix" or not shutil.which("unshare"): return False
    try:
        r=subprocess.run(["unshare","--user","--map-root-user","--mount","--net","true"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
        return r.returncode==0
    except Exception:return False

def _clean_env(policy,extra):
    env={k:v for k,v in os.environ.items() if k in set(policy.env_allowlist)}
    if extra: env.update({str(k):str(v) for k,v in extra.items()})
    env["PYTHONUNBUFFERED"]="1"; return env

def _stage(workdir:str, stage:list[dict]|None):
    for row in stage or []:
        src=Path(row["source"]).resolve(); dst=Path(workdir)/row["dest"]
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True)
        else: shutil.copy2(src,dst)

def spawn_sandboxed_stdio(command:list[str],*,policy:SandboxPolicy|None=None,env:dict[str,str]|None=None,stage:list[dict]|None=None)->SandboxProcess:
    policy=policy or SandboxPolicy(); warnings=[]; workdir=tempfile.mkdtemp(prefix="mib-submission-")
    _stage(workdir,stage)
    use_ns=policy.network in {"disabled_best_effort","disabled_strict"} and _namespace_supported()
    if policy.network=="disabled_strict" and not use_ns: raise RuntimeError("strict user/mount/network namespace isolation unavailable")
    cmd=list(command); fs_isolated=False
    if use_ns:
        hides=[p for p in policy.hide_paths if Path(p).exists()]
        mount_cmds="; ".join(f"mount -t tmpfs tmpfs {shlex.quote(str(Path(p).resolve()))}" for p in hides)
        script="mount --make-rprivate /"
        if mount_cmds: script += "; " + mount_cmds
        script += '; exec "$@"'
        cmd=["unshare","--user","--map-root-user","--mount","--net","sh","-c",script,"mib-sandbox",*cmd]
        fs_isolated=bool(hides)
    elif policy.network=="disabled_best_effort":
        warnings.append("User/mount/network namespace unavailable; using resource/environment isolation only.")
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,cwd=workdir,env=_clean_env(policy,env),preexec_fn=_preexec(policy) if os.name=="posix" else None)
    return SandboxProcess(proc,workdir,use_ns,fs_isolated,warnings)
