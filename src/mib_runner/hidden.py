from __future__ import annotations

import copy
import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .materialize import materialize
from .experimental.transfer import TRANSFER_DIAGNOSTICS_EXTENSION, TRANSFER_EXTENSION, transfer_support_digest
from .experimental.transfer_diagnostics import redact_transfer_diagnostics
from .validation import validate_scenario


class HiddenStoreError(ValueError):
    pass


def _hmac_hex(key: str | bytes, message: str) -> str:
    kb = key.encode("utf-8") if isinstance(key, str) else key
    return hmac.new(kb, message.encode("utf-8"), hashlib.sha256).hexdigest()


def _derived_seed(key: str | bytes, *, cycle: str, template_id: str, index: int) -> tuple[int, str]:
    digest = _hmac_hex(key, f"mib-hidden-seed-v1|{cycle}|{template_id}|{index}")
    seed_int = int(digest[:16], 16)
    alias = f"hs_{digest[16:32]}"
    return seed_int, alias


@dataclass(slots=True)
class HiddenTemplateEntry:
    path: Path
    visibility: str
    public_id: str
    instances: int
    title_public: str | None = None


class HiddenEvalStore:
    """Evaluator-only Scenario store.

    The private manifest identifies exact Template files.  A public manifest is
    derived from it without exposing private paths, exact holdout titles, seeds,
    Oracle, or Probe variants.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.manifest_path = self.root / "manifest.private.json"
        if not self.manifest_path.exists():
            raise HiddenStoreError(f"missing private manifest: {self.manifest_path}")
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def entries(self) -> list[HiddenTemplateEntry]:
        out = []
        for row in self.manifest.get("templates", []):
            path = (self.root / row["path"]).resolve()
            if self.root.resolve() not in path.parents:
                raise HiddenStoreError("private Template path escapes store root")
            out.append(HiddenTemplateEntry(
                path=path,
                visibility=row["visibility"],
                public_id=row["public_id"],
                instances=int(row.get("instances", 1)),
                title_public=row.get("title_public"),
            ))
        return out

    def load_templates(self, schema: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
        templates = []
        aliases = {}
        for entry in self.entries():
            template = json.loads(entry.path.read_text(encoding="utf-8"))
            vr = validate_scenario(template, schema)
            if not vr.valid:
                raise HiddenStoreError(f"private Template {entry.path.name} invalid: {vr.errors}")
            template = copy.deepcopy(template)
            template.setdefault("metadata", {})["visibility"] = entry.visibility
            template.setdefault("extensions", {})["mib.hidden_store"] = {
                "public_id": entry.public_id,
                "visibility": entry.visibility,
            }
            templates.append(template)
            aliases[template["id"]] = entry.public_id
        return templates, aliases

    def materialize_instances(
        self,
        *,
        schema: dict[str, Any],
        evaluation_key: str,
        cycle_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
        templates, aliases = self.load_templates(schema)
        by_id = {t["id"]: t for t in templates}
        instances: list[dict[str, Any]] = []
        entries_by_path = {e.path.resolve(): e for e in self.entries()}
        entries_by_id: dict[str, HiddenTemplateEntry] = {}
        for entry in self.entries():
            raw = json.loads(entry.path.read_text(encoding="utf-8"))
            entries_by_id[raw["id"]] = entry

        for tid, template in by_id.items():
            entry = entries_by_id[tid]
            for index in range(entry.instances):
                real_seed, alias = _derived_seed(evaluation_key, cycle=cycle_id, template_id=tid, index=index)
                inst = materialize(template, real_seed)
                # Replace the secret deterministic seed with a non-invertible public alias.
                inst.setdefault("instantiation", {})["seed"] = alias
                inst["instantiation"]["generator_version"] = "mib-hidden-hmac-materializer/0.1.0"
                inst.setdefault("metadata", {})["hidden_instance_index"] = index
                inst["metadata"]["visibility"] = entry.visibility
                vr = validate_scenario(inst, schema)
                if not vr.valid:
                    raise HiddenStoreError(f"hidden instance {tid}[{index}] invalid: {vr.errors}")
                instances.append(inst)
        return templates, instances, aliases

    def transfer_digest(self) -> str | None:
        """Digest binding every private Transfer Support Annotation in the store.

        Changing Ability support, an oracle artifact, or a transfer relation
        changes this digest and therefore invalidates a signed evaluation
        cycle, so an evaluator-side edit after job creation cannot pass
        unnoticed.  ``None`` when no Template in the store is annotated.
        """
        rows: list[dict[str, str]] = []
        for entry in self.entries():
            raw = json.loads(entry.path.read_text(encoding="utf-8"))
            annotation = (raw.get("extensions") or {}).get(TRANSFER_EXTENSION)
            if annotation is None:
                continue
            rows.append({"public_id": entry.public_id, "digest": transfer_support_digest(annotation)})
        if not rows:
            return None
        payload = json.dumps(sorted(rows, key=lambda r: r["public_id"]), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def public_manifest(self) -> dict[str, Any]:
        suites: dict[str, int] = {}
        hidden = []
        holdout_count = 0
        for entry in self.entries():
            raw = json.loads(entry.path.read_text(encoding="utf-8"))
            suite = raw.get("suite", "unknown")
            if entry.visibility == "private_holdout":
                holdout_count += 1
                continue
            suites[suite] = suites.get(suite, 0) + 1
            hidden.append({
                "public_id": entry.public_id,
                "visibility": "hidden_eval",
                "suite": suite,
                "dimensions": list(raw.get("dimensions") or []),
                "title": entry.title_public or "Hidden evaluation family",
            })
        return {
            "mib": "0.1",
            "kind": "MIBPublicEvaluationManifest",
            "id": self.manifest.get("id"),
            "version": self.manifest.get("version"),
            "profile": self.manifest.get("profile"),
            "hidden_eval": hidden,
            "private_holdout": {
                "count": holdout_count,
                "statement": "Exact Private Holdout Template composition, generators, Oracle data, and Probe variants are evaluator-only."
            },
            "suite_counts": suites,
        }


def redact_report_for_public(report: dict[str, Any], *, aliases: dict[str, str], redaction_key: str) -> dict[str, Any]:
    """Create a score-verifiable public report without private evaluator identifiers."""
    out = copy.deepcopy(report)
    out["scope"] = "public"
    out.setdefault("results", {})["redacted"] = True
    out["results"]["raw_output_policy"] = "digest_only"

    def alias_value(prefix: str, value: Any) -> str:
        return f"{prefix}_{_hmac_hex(redaction_key, str(value))[:16]}"

    # Public score reports intentionally omit per-run/per-Probe evidence.  The
    # evaluator keeps the internal report.  Template/Dimension aggregates remain
    # sufficient for score recomputation without revealing private Probe shape,
    # ablation IDs, or holdout execution structure.
    out.get("results", {})["runs"] = []

    # Aggregates.  Build an old instance -> public instance map first.
    inst_map: dict[str, str] = {}
    for i in out.get("aggregates", {}).get("scenario_instances", []):
        old = i["scenario_instance_id"]
        pub = alias_value("inst", old)
        inst_map[old] = pub
        i["scenario_instance_id"] = pub
        if i.get("template_id") in aliases:
            i["template_id"] = aliases[i["template_id"]]
        i.pop("instance_seed", None)
        # Pair IDs can reveal private ablation names; replace them with opaque aliases.
        i["causal_pair_ids"] = [alias_value("pair", x) for x in i.get("causal_pair_ids", [])]
    for t in out.get("aggregates", {}).get("templates", []):
        if t.get("template_id") in aliases:
            t["template_id"] = aliases[t["template_id"]]

    # Causal metric scoped identifiers.
    for m in out.get("causal_metrics", []):
        if m.get("template_id") in aliases:
            m["template_id"] = aliases[m["template_id"]]
        if m.get("scenario_instance_id"):
            m["scenario_instance_id"] = alias_value("inst", m["scenario_instance_id"])

    # Transfer diagnostics: aggregates and aliases only.  A public surface must
    # never let a participant reconstruct which hidden past supports which
    # hidden future, or repeated submissions become an oracle-probing channel.
    extensions = out.get("extensions") or {}
    body = extensions.get(TRANSFER_DIAGNOSTICS_EXTENSION)
    if body is not None:
        extensions[TRANSFER_DIAGNOSTICS_EXTENSION] = redact_transfer_diagnostics(
            body, aliases=aliases, redaction_key=redaction_key
        )
    extensions.pop(TRANSFER_EXTENSION, None)
    if extensions:
        out["extensions"] = extensions

    out.setdefault("provenance", {})["verification_status"] = "verified"
    out["provenance"]["notes"] = "Evaluator-only Scenario identifiers and seeds were redacted; aggregate score evidence remains recomputable."
    return out
