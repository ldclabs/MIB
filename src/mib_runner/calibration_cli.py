from __future__ import annotations

import argparse
import csv
import importlib
import json
from pathlib import Path

from .calibration import calibrate_pack, load_private_templates, write_calibration_markdown
from .validation import load_json


def _parse_seed(x: str):
    try:
        return int(x)
    except ValueError:
        return x


def _parse_seeds(s: str):
    return [_parse_seed(x.strip()) for x in s.split(",") if x.strip()]


def _write_csv(report: dict, path: str) -> None:
    fields = [
        "template_id", "suite", "visibility", "full_context", "no_memory",
        "memory_discriminativeness_index", "simple_retrieval", "structured_agentic",
        "memory_gap_closure_b2", "memory_gap_closure_b3", "baseline_span",
        "structured_over_retrieval", "memory_benefit", "irrelevant_memory_stability",
        "memory_harm", "harm_resistance", "recommendation", "reasons",
    ]
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in report["templates"]:
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
            })


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mib-calibrate", description="MIB v0.1 Calibration Harness")
    p.add_argument("pack", help="Evaluator-only canonical pack root")
    p.add_argument("--schema", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--seeds", default="101,202,303,404")
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--baselines", default="B0,B1,B2,B3")
    p.add_argument("--baseline-override", action="append", default=[], help="Override a baseline factory as ID=module:Class; repeatable")
    p.add_argument("--bootstrap-resamples", type=int, default=2000)
    p.add_argument("--bootstrap-seed", default="mib-calibration-0.1")
    p.add_argument("--causal-baseline", default="B3")
    p.add_argument("--causal-seeds", default="101,202,303,404")
    p.add_argument("--causal-repetitions", type=int, default=1)
    p.add_argument("--output-json", required=True)
    p.add_argument("--output-md")
    p.add_argument("--output-csv")
    args = p.parse_args(argv)

    schema = load_json(args.schema)
    profile = load_json(args.profile)
    templates = load_private_templates(args.pack)
    overrides = {}
    for item in args.baseline_override:
        if "=" not in item or ":" not in item:
            raise SystemExit("--baseline-override must be ID=module:Class")
        bid, target = item.split("=", 1)
        mod, name = target.split(":", 1)
        overrides[bid] = getattr(importlib.import_module(mod), name)
    report = calibrate_pack(
        templates=templates,
        schema=schema,
        profile=profile,
        seeds=_parse_seeds(args.seeds),
        repetitions=args.repetitions,
        baseline_ids=[x.strip() for x in args.baselines.split(",") if x.strip()],
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
        causal_baseline_id=args.causal_baseline,
        causal_seeds=_parse_seeds(args.causal_seeds),
        causal_repetitions=args.causal_repetitions,
        baseline_factories=overrides,
    )
    Path(args.output_json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(write_calibration_markdown(report), encoding="utf-8")
    if args.output_csv:
        _write_csv(report, args.output_csv)
    print(json.dumps({
        "report": args.output_json,
        "markdown": args.output_md,
        "csv": args.output_csv,
        "templates": report["summary"]["template_count"],
        "provisional_pass": report["summary"]["recommendations"].get("provisional_pass", 0),
        "release_calibration_eligible": report["release_calibration_eligible"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
