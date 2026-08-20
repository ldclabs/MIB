"""Submission sandbox for untrusted external Agent processes.

Security model
--------------
A submission spec is participant-controlled JSON.  Nothing inside it may relax
containment: the environment allowlist, the network policy, the hidden paths,
and the staging roots are decided by the *evaluator* and passed in as a
``SandboxPolicy``.  A submission may only request softer resource limits, and
even those are clamped to server-side maxima (see ``submission.py``).

Containment relies on Linux user/mount/network namespaces via ``unshare``.
Where those are unavailable the policy decides whether to degrade with a
warning (``disabled_best_effort``) or refuse to run (``disabled_strict``).
"""

from __future__ import annotations

import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import shlex
from dataclasses import dataclass, field
from pathlib import Path

# Environment variables that must never reach a submission process, even if an
# evaluator misconfigures the allowlist.  Evaluator secrets derive every signing
# key in the service, so a leak here forges scores.
ENV_HARD_DENYLIST = frozenset({
    "MIB_SERVICE_ROOT_SECRET",
    "MIB_EVAL_KEY",
    "MIB_OFFICIAL_PACK",
})

DEFAULT_ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL")


class SandboxPolicyError(ValueError):
    """Raised when a sandbox policy or staging request is not containable."""


@dataclass(slots=True)
class SandboxPolicy:
    """Evaluator-controlled containment policy.

    ``memory_mb``/``cpu_seconds``/``file_size_mb``/``nofile``/``nproc`` are
    resource limits a submission may influence (clamped by the caller).  Every
    other field is evaluator-only and must never be taken from a submission.
    """

    memory_mb: int = 1024
    cpu_seconds: int = 120
    file_size_mb: int = 128
    nofile: int = 128
    nproc: int = 64
    # Evaluator-only below this line.
    network: str = "disabled_best_effort"  # inherit | disabled_best_effort | disabled_strict
    env_allowlist: list[str] = field(default_factory=lambda: list(DEFAULT_ENV_ALLOWLIST))
    hide_paths: list[str] = field(default_factory=list)
    # When non-empty, staging sources must resolve inside one of these roots.
    # Empty means "no additional root restriction"; the hide_paths rule and the
    # workdir-containment rule always apply regardless.
    stage_roots: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SandboxProcess:
    process: subprocess.Popen
    workdir: str
    network_isolated: bool
    filesystem_isolated: bool
    warnings: list[str]

    def terminate(self) -> None:
        if self.process.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except Exception:
            try:
                self.process.terminate()
            except Exception:
                pass
        try:
            self.process.wait(timeout=2)
        except Exception:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except Exception:
                pass


def _mb(n) -> int:
    return max(1, int(n)) * 1024 * 1024


def _preexec(policy: SandboxPolicy):
    # RLIMIT_AS is unusable on macOS: the child is killed before it can exec.
    # The sandbox is only *containing* on Linux anyway, so elsewhere we set the
    # portable limits and let spawn_sandboxed_stdio warn about the rest.
    apply_address_space = sys.platform.startswith("linux")

    def fn() -> None:
        os.setsid()
        if apply_address_space:
            resource.setrlimit(resource.RLIMIT_AS, (_mb(policy.memory_mb), _mb(policy.memory_mb)))
        resource.setrlimit(resource.RLIMIT_CPU, (policy.cpu_seconds, policy.cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (_mb(policy.file_size_mb), _mb(policy.file_size_mb)))
        resource.setrlimit(resource.RLIMIT_NOFILE, (policy.nofile, policy.nofile))
        if hasattr(resource, "RLIMIT_NPROC"):
            resource.setrlimit(resource.RLIMIT_NPROC, (policy.nproc, policy.nproc))

    return fn


def _namespace_supported() -> bool:
    if os.name != "posix" or not shutil.which("unshare"):
        return False
    try:
        r = subprocess.run(
            ["unshare", "--user", "--map-root-user", "--mount", "--net", "true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return r.returncode == 0
    except Exception:
        return False


def _clean_env(policy: SandboxPolicy, extra: dict[str, str] | None) -> dict[str, str]:
    allow = {k for k in policy.env_allowlist if k not in ENV_HARD_DENYLIST}
    env = {k: v for k, v in os.environ.items() if k in allow}
    for k, v in (extra or {}).items():
        key = str(k)
        if key in ENV_HARD_DENYLIST:
            raise SandboxPolicyError(f"submission may not set protected environment variable: {key}")
        env[key] = str(v)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _resolved_under(path: Path, roots: list[str]) -> bool:
    target = path.resolve()
    for root in roots:
        r = Path(root).resolve()
        if target == r or r in target.parents:
            return True
    return False


def _overlaps_hidden(src: Path, hide_paths: list[str]) -> str | None:
    """Return the hidden path a staging source would expose, if any.

    Both directions matter: staging the evaluation store itself exposes it, and
    so does staging any ancestor directory that contains it.  Staging runs on the
    host before the mount namespace exists, so the tmpfs mask cannot help here.
    """
    target = src.resolve()
    for hidden in hide_paths:
        h = Path(hidden).resolve()
        if target == h or h in target.parents or target in h.parents:
            return str(h)
    return None


def _stage(workdir: str, stage: list[dict] | None, policy: SandboxPolicy) -> None:
    """Copy declared files into the sandbox workdir.

    This runs in the *parent* process before any namespace exists, so both ends
    are validated here: ``source`` may not escape the evaluator-approved staging
    roots (otherwise a submission could copy the private evaluation store into
    its own workdir), and ``dest`` may not escape the workdir.
    """
    rows = list(stage or [])
    if not rows:
        return
    work = Path(workdir).resolve()
    for row in rows:
        raw_dest = str(row["dest"])
        if os.path.isabs(raw_dest) or Path(raw_dest).is_absolute():
            raise SandboxPolicyError(f"staging dest must be relative to the sandbox workdir: {raw_dest!r}")
        dst = (work / raw_dest).resolve()
        if dst != work and work not in dst.parents:
            raise SandboxPolicyError(f"staging dest escapes the sandbox workdir: {raw_dest!r}")
        src = Path(row["source"]).resolve()
        # Hidden evaluator content may never be staged, under any policy.
        exposed = _overlaps_hidden(src, policy.hide_paths)
        if exposed is not None:
            raise SandboxPolicyError(
                f"staging source {src} would expose evaluator-only path {exposed}"
            )
        # An explicit root list further confines staging; the evaluation service
        # sets it so an untrusted submission bundle must be self-contained.
        if policy.stage_roots and not _resolved_under(src, policy.stage_roots):
            raise SandboxPolicyError(f"staging source is outside the approved staging roots: {src}")
        if not src.exists():
            raise SandboxPolicyError(f"staging source does not exist: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=False)
        else:
            shutil.copy2(src, dst, follow_symlinks=True)


def spawn_sandboxed_stdio(
    command: list[str],
    *,
    policy: SandboxPolicy | None = None,
    env: dict[str, str] | None = None,
    stage: list[dict] | None = None,
) -> SandboxProcess:
    policy = policy or SandboxPolicy()
    warnings: list[str] = []
    workdir = tempfile.mkdtemp(prefix="mib-submission-")
    _stage(workdir, stage, policy)

    use_ns = policy.network in {"disabled_best_effort", "disabled_strict"} and _namespace_supported()
    if policy.network == "disabled_strict" and not use_ns:
        raise SandboxPolicyError("strict user/mount/network namespace isolation unavailable")
    if policy.network == "inherit":
        warnings.append(
            "Sandbox policy inherits host network and filesystem visibility; "
            "this must never be used for untrusted submissions."
        )

    cmd = list(command)
    fs_isolated = False
    if use_ns:
        hides = [p for p in policy.hide_paths if Path(p).exists()]
        mount_cmds = "; ".join(
            f"mount -t tmpfs tmpfs {shlex.quote(str(Path(p).resolve()))}" for p in hides
        )
        script = "mount --make-rprivate /"
        if mount_cmds:
            script += "; " + mount_cmds
        script += '; exec "$@"'
        cmd = ["unshare", "--user", "--map-root-user", "--mount", "--net", "sh", "-c", script, "mib-sandbox", *cmd]
        fs_isolated = bool(hides)
        if policy.hide_paths and not hides:
            warnings.append("No hide_paths existed on disk; no evaluator path was masked.")
    elif policy.network == "disabled_best_effort":
        warnings.append("User/mount/network namespace unavailable; using resource/environment isolation only.")
    if not sys.platform.startswith("linux"):
        warnings.append(f"Address-space limit not enforced on {sys.platform}; memory_mb is advisory.")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=workdir,
        env=_clean_env(policy, env),
        preexec_fn=_preexec(policy) if os.name == "posix" else None,
    )
    return SandboxProcess(proc, workdir, use_ns, fs_isolated, warnings)
