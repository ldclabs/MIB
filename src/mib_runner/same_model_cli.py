from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import jsonschema

from .same_model_calibration import (
    build_experiment_lock,
    estimate_experiment,
    load_experiment,
    run_same_model_calibration,
    write_same_model_markdown,
)


def _write_csv(report: dict, path: str) -> None:
    fields = [
        "template_id", "suite", "visibility", "full_context", "no_memory",
        "memory_discriminativeness_index", "simple_retrieval", "structured_agentic",
        "memory_gap_closure_b2", "memory_gap_closure_b3", "baseline_span",
        "structured_over_retrieval", "memory_benefit", "irrelevant_memory_stability",
        "memory_harm", "harm_resistance", "recommendation", "reasons", "causal_risks",
    ]
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in report["calibration"]["templates"]:
            m = c["metrics"]; cd = c["causal_diagnostics"]
            w.writerow({
                "template_id": c["template_id"], "suite": c["suite"], "visibility": c["visibility"],
                "full_context": m["full_context"], "no_memory": m["no_memory"],
                "memory_discriminativeness_index": m["memory_discriminativeness_index"],
                "simple_retrieval": m["simple_retrieval"], "structured_agentic": m["structured_agentic"],
                "memory_gap_closure_b2": m["memory_gap_closure_b2"], "memory_gap_closure_b3": m["memory_gap_closure_b3"],
                "baseline_span": m["baseline_span"], "structured_over_retrieval": m["structured_over_retrieval"],
                "memory_benefit": cd.get("memory_benefit"), "irrelevant_memory_stability": cd.get("irrelevant_memory_stability"),
                "memory_harm": cd.get("memory_harm"), "harm_resistance": cd.get("harm_resistance"),
                "recommendation": c["recommendation"], "reasons": ";".join(c["reasons"]),
                "causal_risks": ";".join(c.get("causal_risks") or []),
            })


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="mib-same-model-calibrate",
        description="MIB v0.1 Same-Model Empirical Baseline Harness",
    )
    p.add_argument("experiment", help="Same-model experiment JSON")
    p.add_argument("--output-json")
    p.add_argument("--output-md")
    p.add_argument("--output-csv")
    p.add_argument("--output-lock")
    p.add_argument("--experiment-schema")
    p.add_argument("--report-schema")
    p.add_argument("--lock-only", action="store_true")
    p.add_argument("--estimate-only", action="store_true")
    args = p.parse_args(argv)

    cfg, paths = load_experiment(args.experiment)
    if args.experiment_schema:
        schema = json.loads(Path(args.experiment_schema).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(cfg)
    lock = build_experiment_lock(cfg, paths)
    if args.output_lock:
        Path(args.output_lock).write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.lock_only:
        payload = {"experiment_id": cfg["id"], "experiment_lock": lock["digest"]}
        if args.output_json:
            Path(args.output_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0
    if args.estimate_only:
        from .calibration import load_private_templates
        templates = load_private_templates(paths["pack"])
        payload = {"experiment_id": cfg["id"], "experiment_lock": lock["digest"], "estimate": estimate_experiment(cfg, templates)}
        if args.output_json:
            Path(args.output_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    if not args.output_json:
        raise SystemExit("--output-json is required unless --lock-only is used")
    report = run_same_model_calibration(args.experiment)
    if args.report_schema:
        schema = json.loads(Path(args.report_schema).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(report)
    Path(args.output_json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(write_same_model_markdown(report), encoding="utf-8")
    if args.output_csv:
        _write_csv(report, args.output_csv)
    gate = report["empirical_release_gate"]
    print(json.dumps({
        "report": args.output_json,
        "experiment_lock": report["experiment"]["experiment_lock"]["digest"],
        "mode": report["calibration"]["calibration_mode"],
        "fairness_valid": report["fairness_audit"]["valid"],
        "templates_passed": gate["template_full_gate"]["passed"],
        "templates_total": gate["template_full_gate"]["total"],
        "release_calibration_eligible": gate["eligible"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
