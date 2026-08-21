from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


DDL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    owner TEXT,
    track TEXT NOT NULL,
    spec_path TEXT NOT NULL,
    spec_digest TEXT NOT NULL,
    status TEXT NOT NULL,
    descriptor_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cycles (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    store_path TEXT NOT NULL,
    profile_path TEXT NOT NULL,
    store_digest TEXT NOT NULL,
    profile_digest TEXT NOT NULL,
    public_manifest_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    activated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_cycles_profile_status ON cycles(profile_id, status);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    backend TEXT NOT NULL,
    status TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    manifest_signature_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    result_id TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_submission_cycle ON jobs(submission_id, cycle_id);
CREATE TABLE IF NOT EXISTS results (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    profile_id TEXT NOT NULL,
    score REAL NOT NULL,
    ci_lower REAL,
    ci_upper REAL,
    public_report_path TEXT NOT NULL,
    internal_report_path TEXT NOT NULL,
    public_report_digest TEXT NOT NULL,
    internal_report_digest TEXT NOT NULL,
    attestation_json TEXT NOT NULL,
    attestation_signature_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_results_cycle_score ON results(cycle_id, score DESC);
"""


class ServiceDB:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(DDL)
            # Additive migration: a store registered before transfer diagnostics
            # existed keeps working, and gains the column on next open.
            columns = {r["name"] for r in con.execute("PRAGMA table_info(cycles)")}
            if "transfer_digest" not in columns:
                con.execute("ALTER TABLE cycles ADD COLUMN transfer_digest TEXT")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA foreign_keys=ON")
            yield con
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def upsert_submission(self, row: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as con:
            con.execute(
                """INSERT INTO submissions(id,display_name,owner,track,spec_path,spec_digest,status,descriptor_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name, owner=excluded.owner,
                   track=excluded.track, spec_path=excluded.spec_path, spec_digest=excluded.spec_digest,
                   status=excluded.status, descriptor_json=excluded.descriptor_json, updated_at=excluded.updated_at""",
                (row["id"], row["display_name"], row.get("owner"), row["track"], row["spec_path"], row["spec_digest"],
                 row.get("status", "accepted"), json.dumps(row.get("descriptor"), separators=(",", ":")) if row.get("descriptor") else None,
                 row.get("created_at", now), now),
            )

    def submission(self, sid: str) -> dict[str, Any] | None:
        with self.connect() as con:
            return self._dict(con.execute("SELECT * FROM submissions WHERE id=?", (sid,)).fetchone())

    def submissions(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM submissions ORDER BY created_at,id")]

    def upsert_cycle(self, row: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as con:
            con.execute(
                """INSERT INTO cycles(id,profile_id,store_path,profile_path,store_digest,profile_digest,public_manifest_json,status,created_at,activated_at,transfer_digest)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET profile_id=excluded.profile_id,store_path=excluded.store_path,
                   profile_path=excluded.profile_path,store_digest=excluded.store_digest,profile_digest=excluded.profile_digest,
                   public_manifest_json=excluded.public_manifest_json,status=excluded.status,activated_at=excluded.activated_at,
                   transfer_digest=excluded.transfer_digest""",
                (row["id"], row["profile_id"], row["store_path"], row["profile_path"], row["store_digest"], row["profile_digest"],
                 json.dumps(row["public_manifest"], separators=(",", ":"), ensure_ascii=False), row.get("status", "registered"),
                 row.get("created_at", now), row.get("activated_at"), row.get("transfer_digest")),
            )

    def activate_cycle(self, cycle_id: str) -> None:
        with self.connect() as con:
            row = con.execute("SELECT profile_id FROM cycles WHERE id=?", (cycle_id,)).fetchone()
            if not row:
                raise KeyError(f"unknown cycle: {cycle_id}")
            con.execute("UPDATE cycles SET status='retired' WHERE profile_id=? AND status='active'", (row["profile_id"],))
            con.execute("UPDATE cycles SET status='active', activated_at=? WHERE id=?", (utc_now(), cycle_id))

    def cycle(self, cycle_id: str) -> dict[str, Any] | None:
        with self.connect() as con:
            return self._dict(con.execute("SELECT * FROM cycles WHERE id=?", (cycle_id,)).fetchone())

    def active_cycle(self, profile_id: str | None = None) -> dict[str, Any] | None:
        with self.connect() as con:
            if profile_id:
                row = con.execute("SELECT * FROM cycles WHERE profile_id=? AND status='active' ORDER BY activated_at DESC LIMIT 1", (profile_id,)).fetchone()
            else:
                row = con.execute("SELECT * FROM cycles WHERE status='active' ORDER BY activated_at DESC LIMIT 1").fetchone()
            return self._dict(row)

    def cycles(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM cycles ORDER BY created_at,id")]

    def create_job(self, row: dict[str, Any]) -> None:
        with self.connect() as con:
            con.execute(
                """INSERT INTO jobs(id,submission_id,cycle_id,backend,status,manifest_json,manifest_signature_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (row["id"], row["submission_id"], row["cycle_id"], row["backend"], row.get("status", "queued"),
                 json.dumps(row["manifest"], separators=(",", ":"), ensure_ascii=False),
                 json.dumps(row["manifest_signature"], separators=(",", ":"), ensure_ascii=False), row.get("created_at", utc_now())),
            )

    def job(self, jid: str) -> dict[str, Any] | None:
        with self.connect() as con:
            return self._dict(con.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone())

    def jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))]

    def claim_next_job(self, backend: str | None = None) -> dict[str, Any] | None:
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if backend:
                row = con.execute("SELECT * FROM jobs WHERE status='queued' AND backend=? ORDER BY created_at LIMIT 1", (backend,)).fetchone()
            else:
                row = con.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                return None
            con.execute("UPDATE jobs SET status='running', started_at=? WHERE id=? AND status='queued'", (utc_now(), row["id"]))
            return dict(con.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())


    def requeue_running_jobs(self) -> int:
        """Administrative recovery for workers that died after claiming jobs.

        M5 has no distributed lease/heartbeat yet; a service restart may call this
        before starting workers. Production backends should replace this with a
        lease expiry / heartbeat protocol.
        """
        with self.connect() as con:
            cur=con.execute("UPDATE jobs SET status='queued', started_at=NULL, error=NULL WHERE status='running'")
            return int(cur.rowcount)

    def finish_job(self, jid: str, *, result_id: str | None = None, error: str | None = None) -> None:
        status = "succeeded" if result_id else "failed"
        with self.connect() as con:
            con.execute("UPDATE jobs SET status=?,completed_at=?,result_id=?,error=? WHERE id=?", (status, utc_now(), result_id, error, jid))

    def insert_result(self, row: dict[str, Any]) -> None:
        with self.connect() as con:
            con.execute(
                """INSERT INTO results(id,job_id,submission_id,cycle_id,profile_id,score,ci_lower,ci_upper,
                   public_report_path,internal_report_path,public_report_digest,internal_report_digest,
                   attestation_json,attestation_signature_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (row["id"], row["job_id"], row["submission_id"], row["cycle_id"], row["profile_id"], row["score"],
                 row.get("ci_lower"), row.get("ci_upper"), row["public_report_path"], row["internal_report_path"],
                 row["public_report_digest"], row["internal_report_digest"],
                 json.dumps(row["attestation"], separators=(",", ":"), ensure_ascii=False),
                 json.dumps(row["attestation_signature"], separators=(",", ":"), ensure_ascii=False), row.get("created_at", utc_now())),
            )

    def result(self, rid: str) -> dict[str, Any] | None:
        with self.connect() as con:
            return self._dict(con.execute("SELECT * FROM results WHERE id=?", (rid,)).fetchone())

    def latest_results_for_cycle(self, cycle_id: str) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                """SELECT r.*, s.display_name, s.owner, s.track FROM results r
                   JOIN submissions s ON s.id=r.submission_id
                   JOIN (SELECT submission_id, MAX(created_at) AS max_created FROM results WHERE cycle_id=? GROUP BY submission_id) x
                     ON x.submission_id=r.submission_id AND x.max_created=r.created_at
                   WHERE r.cycle_id=? ORDER BY r.score DESC, r.created_at ASC""", (cycle_id, cycle_id)
            ).fetchall()
            return [dict(r) for r in rows]
