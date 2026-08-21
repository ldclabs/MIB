from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path

from .agents import ReferenceMemoryAgent
from .benchmark import load_templates, run_benchmark_pack, run_materialized_pack
from .capability import render_capability_card
from .materialize import materialize
from .hidden import HiddenEvalStore, redact_report_for_public
from .submission import build_submission_runtime, load_submission_spec
from .reality import (
    attest_reality_result,
    load_reality_pack,
    redact_reality_report,
    render_reality_card,
    run_reality_benchmark,
)
from .report import build_basic_report, validate_report, verify_score
from .runner import run_scenario
from .transfer import inspect_transfer
from .validation import load_json, validate_scenario


def _load_agent_factory(spec: str | None):
    if not spec or spec == "reference":
        return ReferenceMemoryAgent
    if ":" not in spec:
        raise SystemExit("--agent must be 'reference' or module:Class")
    module_name, class_name = spec.split(":", 1)
    return getattr(importlib.import_module(module_name), class_name)


def _parse_seed(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def _parse_seeds(value: str):
    return [_parse_seed(x.strip()) for x in value.split(",") if x.strip()]


def cmd_validate(args) -> int:
    schema = load_json(args.schema)
    scenario = load_json(args.scenario)
    result = validate_scenario(
        scenario,
        schema,
        transfer_schema=load_json(args.transfer_support_schema) if args.transfer_support_schema else None,
        require_transfer_annotations=args.require_transfer_annotations,
    )
    print(json.dumps({"valid": result.valid, "errors": result.errors, "warnings": result.warnings}, indent=2, ensure_ascii=False))
    return 0 if result.valid else 2


def cmd_inspect_transfer(args) -> int:
    scenario = load_json(args.scenario)
    schema = load_json(args.transfer_support_schema) if args.transfer_support_schema else None
    out = inspect_transfer(scenario, schema=schema)
    text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0 if not out["errors"] else 2


def _load_materialized(path: str, schema_path: str, seed: str | int):
    schema = load_json(schema_path)
    src = load_json(path)
    vr = validate_scenario(src, schema)
    if not vr.valid:
        raise SystemExit("Scenario validation failed:\n" + "\n".join(vr.errors))
    instance = materialize(src, seed)
    vr2 = validate_scenario(instance, schema)
    if not vr2.valid:
        raise SystemExit("Materialized instance validation failed:\n" + "\n".join(vr2.errors))
    return instance


def cmd_run(args) -> int:
    seed = _parse_seed(args.seed)
    scenario = _load_materialized(args.scenario, args.schema, seed)
    factory = _load_agent_factory(args.agent)
    agent_desc = factory().describe()
    runs = run_scenario(scenario=scenario, agent_factory=factory, include_ablations=not args.full_only, repetition=0, agent_seed=seed)
    report = build_basic_report(runs=runs, scenario=scenario, agent_descriptor=agent_desc)
    if args.report_schema:
        validate_report(report, load_json(args.report_schema))
    output = {
        "scenario": scenario["id"],
        "runs": [{"condition": r["condition"], "score": r["scenario_score"], "status": r["status"]} for r in runs],
        "dev_score": report["aggregates"]["mib_score"]["final_score"],
        "report": report,
    }
    text = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


def cmd_run_pack(args) -> int:
    schema = load_json(args.schema)
    report_schema = load_json(args.report_schema) if args.report_schema else None
    factory = _load_agent_factory(args.agent)
    files = sorted(Path(args.path).rglob("MIB-*.json")) if Path(args.path).is_dir() else [Path(args.path)]
    results = []
    for p in files:
        if ".example-" in p.name:
            continue
        scenario = load_json(p)
        vr = validate_scenario(scenario, schema)
        if not vr.valid:
            results.append({"path": str(p), "valid": False, "errors": vr.errors})
            continue
        instance = materialize(scenario, args.seed)
        runs = run_scenario(scenario=instance, agent_factory=factory, include_ablations=not args.full_only, repetition=0, agent_seed=args.seed)
        report = build_basic_report(runs=runs, scenario=instance, agent_descriptor=factory().describe())
        if report_schema:
            validate_report(report, report_schema)
        results.append({
            "path": str(p), "valid": True, "scenario": scenario["id"],
            "full_score": next(r["scenario_score"] for r in runs if r["condition"] == "full"),
            "dev_score": report["aggregates"]["mib_score"]["final_score"],
            "conditions": {r["condition"]: r["scenario_score"] for r in runs},
        })
    valid_rows = [x for x in results if x.get("valid")]
    summary = {
        "count": len(results),
        "passed_validation": len(valid_rows),
        "mean_full_score": sum(x["full_score"] for x in valid_rows) / max(1, len(valid_rows)),
        "results": results,
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


def cmd_benchmark(args) -> int:
    schema = load_json(args.schema)
    report_schema = load_json(args.report_schema) if args.report_schema else None
    profile = load_json(args.profile)
    templates = load_templates(args.path)
    factory = _load_agent_factory(args.agent)
    seeds = _parse_seeds(args.seeds) if args.seeds else list(profile.get("instance_seeds") or [101, 202])
    repetitions = args.repetitions if args.repetitions is not None else int(profile.get("repetitions", 2))
    boot = args.bootstrap_resamples if args.bootstrap_resamples is not None else int((profile.get("statistics") or {}).get("bootstrap_resamples", 0))
    report, summary = run_benchmark_pack(
        templates=templates,
        schema=schema,
        profile=profile,
        agent_factory=factory,
        instance_seeds=seeds,
        repetitions=repetitions,
        include_ablations=not args.full_only,
        bootstrap_resamples=boot,
        bootstrap_seed=args.bootstrap_seed,
        transfer_matrix=args.transfer_diagnostics,
    )
    if report_schema:
        validate_report(report, report_schema)
    if args.output_report:
        Path(args.output_report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.output_summary:
        Path(args.output_summary).write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    card = render_capability_card(report)
    if args.card:
        Path(args.card).write_text(card, encoding="utf-8")
    output = {"summary": summary, "report": args.output_report, "capability_card": args.card}
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def cmd_capability_card(args) -> int:
    report = load_json(args.report)
    text = render_capability_card(report)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


def cmd_verify_score(args) -> int:
    report = load_json(args.report)
    if args.report_schema:
        validate_report(report, load_json(args.report_schema))
    result = verify_score(report, tolerance=args.tolerance)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 3



def cmd_public_eval_manifest(args) -> int:
    store = HiddenEvalStore(args.store)
    manifest = store.public_manifest()
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


def cmd_agent_smoke_test(args) -> int:
    spec = load_submission_spec(args.submission)
    runtime = build_submission_runtime(
        spec,
        network="disabled_best_effort" if args.allow_degraded_sandbox else "disabled_strict",
        allow_remote_http=args.allow_remote_http,
    )
    agent = runtime.factory()
    try:
        descriptor = agent.describe()
        run_id = "smoke_opaque_run"
        agent.reset(run_id=run_id, seed="smoke-seed", virtual_time="2026-01-01T00:00:00Z")
        from .types import Observation
        agent.observe(
            run_id=run_id,
            request_id="req_smoke_observe",
            observation=Observation(
                observation_id="obs_smoke",
                type="user_message",
                virtual_time="2026-01-01T00:00:00Z",
                actor={"id": "user", "kind": "person", "display_name": "Smoke User"},
                content="The access code for my private demo project is ORCHID-91.",
            ),
        )
        output = agent.respond(
            run_id=run_id,
            request_id="req_smoke_respond",
            interaction_id="smoke",
            input_data={"content": "What is the access code for my private demo project? Answer with the code only."},
            virtual_time="2026-01-02T00:00:00Z",
        )
        result = {
            "valid": output.content == "ORCHID-91",
            "submission": spec["id"],
            "transport": runtime.transport,
            "descriptor": descriptor,
            "output": {"type": output.type, "content": output.content, "value": output.value},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["valid"] else 4
    finally:
        close = getattr(agent, "close", None)
        if callable(close):
            try:
                close(run_id="smoke_opaque_run")
            except TypeError:
                close()


def cmd_evaluate_hidden(args) -> int:
    schema = load_json(args.schema)
    report_schema = load_json(args.report_schema) if args.report_schema else None
    profile = load_json(args.profile)
    store = HiddenEvalStore(args.store)
    eval_key = args.eval_key or os.environ.get("MIB_EVAL_KEY")
    if not eval_key:
        raise SystemExit("--eval-key or MIB_EVAL_KEY is required")
    templates, instances, aliases = store.materialize_instances(
        schema=schema,
        evaluation_key=eval_key,
        cycle_id=args.cycle,
    )
    spec = load_submission_spec(args.submission)
    # The evaluator-only store path is masked by the Runner, not by the
    # submission: a spec must not be able to choose what it can see.
    runtime = build_submission_runtime(
        spec,
        network="disabled_best_effort" if args.allow_degraded_sandbox else "disabled_strict",
        hide_paths=[str(Path(args.store).resolve())],
        allow_remote_http=args.allow_remote_http,
    )
    repetitions = args.repetitions if args.repetitions is not None else int(profile.get("repetitions", 1))
    boot = args.bootstrap_resamples if args.bootstrap_resamples is not None else int((profile.get("statistics") or {}).get("bootstrap_resamples", 0))
    report, summary = run_materialized_pack(
        templates=templates,
        instances=instances,
        schema=schema,
        profile=profile,
        agent_factory=runtime.factory,
        repetitions=repetitions,
        include_ablations=not args.full_only,
        bootstrap_resamples=boot,
        bootstrap_seed=args.bootstrap_seed,
    )
    report.setdefault("provenance", {})["notes"] = f"Hidden evaluation cycle {args.cycle}; submission={spec['id']}; transport={runtime.transport}."
    if report_schema:
        validate_report(report, report_schema)
    public = redact_report_for_public(report, aliases=aliases, redaction_key=eval_key)
    if report_schema:
        validate_report(public, report_schema)
    verify = verify_score(public)
    if not verify["valid"]:
        raise SystemExit("redacted public report failed score verification")
    if args.output_internal:
        Path(args.output_internal).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.output_public:
        Path(args.output_public).write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.card:
        Path(args.card).write_text(render_capability_card(public), encoding="utf-8")
    output = {
        "submission": spec["id"],
        "profile": profile["id"],
        "cycle": args.cycle,
        "templates": len(templates),
        "instances": len(instances),
        "summary": summary,
        "public_report_verified": True,
        "internal_report": args.output_internal,
        "public_report": args.output_public,
        "capability_card": args.card,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def cmd_reality_benchmark(args) -> int:
    pack = load_reality_pack(args.pack)
    if args.pack_schema:
        import jsonschema

        jsonschema.Draft202012Validator(load_json(args.pack_schema)).validate(pack)
    profile = load_json(args.profile) if args.profile else None
    if args.submission:
        spec = load_submission_spec(args.submission)
        runtime = build_submission_runtime(
            spec,
            network="disabled_best_effort" if args.allow_degraded_sandbox else "disabled_strict",
            allow_remote_http=args.allow_remote_http,
        )
        factory = runtime.factory
    else:
        factory = _load_agent_factory(args.agent)
    conditions = tuple(x.strip() for x in args.conditions.split(",") if x.strip()) if args.conditions else None
    report, summary = run_reality_benchmark(
        pack=pack,
        pack_path=args.pack,
        agent_factory=factory,
        seeds=_parse_seeds(args.seeds) if args.seeds else None,
        repetitions=args.repetitions if args.repetitions is not None else int(pack.get("repetitions", 1)),
        conditions=conditions,
        bootstrap_resamples=args.bootstrap_resamples or 0,
        bootstrap_seed=args.bootstrap_seed,
        confidence_level=float((profile or {}).get("statistics", {}).get("confidence_level", 0.95)),
    )
    public = redact_reality_report(report)
    if args.output_report:
        Path(args.output_report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.output_public:
        Path(args.output_public).write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.output_attestation:
        secret = os.environ.get(args.attestation_secret_env)
        if not secret:
            raise SystemExit(f"--output-attestation requires {args.attestation_secret_env} in the environment")
        signed = attest_reality_result(report=report, public_report=public, root_secret=secret)
        Path(args.output_attestation).write_text(json.dumps(signed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.card:
        Path(args.card).write_text(render_reality_card(report), encoding="utf-8")
    print(json.dumps({
        "summary": summary,
        "report": args.output_report,
        "public_report": args.output_public,
        "reality_card": args.card,
        "attestation": args.output_attestation,
        "note": "MIB-R-0.1-Dev is a prototype; its results are never ranked against MIB-Core.",
    }, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mib", description="MIB Reference Runner")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="Validate one MIB Scenario")
    v.add_argument("scenario")
    v.add_argument("--schema", required=True)
    v.add_argument("--transfer-support-schema",
                   help="Also validate a mib.transfer_support.v1 annotation against this schema")
    v.add_argument("--require-transfer-annotations", action="store_true",
                   help="Fail when the Scenario carries no Transfer Support Annotation")
    v.set_defaults(func=cmd_validate)

    it = sub.add_parser("inspect-transfer", help="Summarize the Transfer Support Annotation of one Scenario (evaluator-internal)")
    it.add_argument("scenario")
    it.add_argument("--transfer-support-schema")
    it.add_argument("--output")
    it.set_defaults(func=cmd_inspect_transfer)

    r = sub.add_parser("run", help="Run one Scenario/Template")
    r.add_argument("scenario")
    r.add_argument("--schema", required=True)
    r.add_argument("--report-schema")
    r.add_argument("--agent", default="reference")
    r.add_argument("--seed", default="101")
    r.add_argument("--full-only", action="store_true")
    r.add_argument("--output")
    r.set_defaults(func=cmd_run)

    rp = sub.add_parser("run-pack", help="Run Templates independently; legacy development summary")
    rp.add_argument("path")
    rp.add_argument("--schema", required=True)
    rp.add_argument("--report-schema")
    rp.add_argument("--agent", default="reference")
    rp.add_argument("--seed", type=int, default=101)
    rp.add_argument("--full-only", action="store_true")
    rp.add_argument("--output")
    rp.set_defaults(func=cmd_run_pack)

    b = sub.add_parser("benchmark", help="Execute and aggregate a complete MIB Benchmark Pack")
    b.add_argument("path")
    b.add_argument("--profile", required=True)
    b.add_argument("--schema", required=True)
    b.add_argument("--report-schema")
    b.add_argument("--agent", default="reference")
    b.add_argument("--seeds", help="Comma-separated Scenario instance seeds; defaults to Profile")
    b.add_argument("--repetitions", type=int)
    b.add_argument("--bootstrap-resamples", type=int)
    b.add_argument("--bootstrap-seed", default="20260819")
    b.add_argument("--full-only", action="store_true")
    b.add_argument("--transfer-diagnostics", action="store_true",
                   help="Also run the AA/AO/OA/OO transfer diagnostic cells for annotated Templates")
    b.add_argument("--output-report")
    b.add_argument("--output-summary")
    b.add_argument("--card")
    b.set_defaults(func=cmd_benchmark)

    cc = sub.add_parser("capability-card", help="Render a Markdown Capability Card from a MIB Report")
    cc.add_argument("report")
    cc.add_argument("--output")
    cc.set_defaults(func=cmd_capability_card)

    vs = sub.add_parser("verify-score", help="Recompute Template, Dimension, and final report scores")
    vs.add_argument("report")
    vs.add_argument("--report-schema")
    vs.add_argument("--tolerance", type=float, default=1e-9)
    vs.set_defaults(func=cmd_verify_score)


    rb = sub.add_parser("reality-benchmark", help="Execute a MIB-R Reality Pack under paired memory conditions (prototype)")
    rb.add_argument("pack", help="Path to a MIBRealityPack manifest")
    rb.add_argument("--profile")
    rb.add_argument("--pack-schema")
    rb.add_argument("--agent", default="reference")
    rb.add_argument("--submission", help="Run an external Agent submission instead of an in-process factory")
    rb.add_argument("--conditions", help="Comma-separated subset of the pack's declared conditions")
    rb.add_argument("--seeds")
    rb.add_argument("--repetitions", type=int)
    rb.add_argument("--bootstrap-resamples", type=int)
    rb.add_argument("--bootstrap-seed", default="20260819")
    rb.add_argument("--allow-degraded-sandbox", action="store_true",
                    help="Permit running without Linux namespace isolation (development only)")
    rb.add_argument("--allow-remote-http", action="store_true",
                    help="Permit an HTTP submission served from a non-local host (https required)")
    rb.add_argument("--output-report")
    rb.add_argument("--output-public")
    rb.add_argument("--output-attestation")
    rb.add_argument("--attestation-secret-env", default="MIB_SERVICE_ROOT_SECRET",
                    help="Environment variable holding the root secret used to sign the MIB-R attestation")
    rb.add_argument("--card")
    rb.set_defaults(func=cmd_reality_benchmark)

    pm = sub.add_parser("public-eval-manifest", help="Derive a participant-safe manifest from a private evaluation store")
    pm.add_argument("store")
    pm.add_argument("--output")
    pm.set_defaults(func=cmd_public_eval_manifest)

    sm = sub.add_parser("agent-smoke-test", help="Test an external HTTP/stdio Agent submission")
    sm.add_argument("--submission", required=True)
    sm.add_argument("--allow-degraded-sandbox", action="store_true",
                    help="Permit running without Linux namespace isolation (development only)")
    sm.add_argument("--allow-remote-http", action="store_true",
                    help="Permit an HTTP submission served from a non-local host (https required)")
    sm.set_defaults(func=cmd_agent_smoke_test)

    he = sub.add_parser("evaluate-hidden", help="Execute evaluator-only Hidden/Private Scenarios against an external submission")
    he.add_argument("store")
    he.add_argument("--profile", required=True)
    he.add_argument("--submission", required=True)
    he.add_argument("--schema", required=True)
    he.add_argument("--report-schema")
    he.add_argument("--eval-key", help="Evaluator secret; prefer MIB_EVAL_KEY in hosted evaluation")
    he.add_argument("--cycle", default="cycle-1")
    he.add_argument("--repetitions", type=int)
    he.add_argument("--bootstrap-resamples", type=int)
    he.add_argument("--bootstrap-seed", default="20260819")
    he.add_argument("--full-only", action="store_true")
    he.add_argument("--allow-degraded-sandbox", action="store_true",
                    help="Permit running without Linux namespace isolation; hidden content is NOT masked (development only)")
    he.add_argument("--allow-remote-http", action="store_true",
                    help="Permit an HTTP submission served from a non-local host (https required)")
    he.add_argument("--output-internal")
    he.add_argument("--output-public")
    he.add_argument("--card")
    he.set_defaults(func=cmd_evaluate_hidden)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
