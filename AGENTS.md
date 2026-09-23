# Working on MIB

MIB measures how historical information changes an Agent's later answers and
actions. Optimize for truthful, reproducible measurement. A higher fixture score
or a passing test suite is not evidence of general memory intelligence.

## Start here

- Read [README.md](README.md) for scope and entry points, and
  [CONTRIBUTING.md](CONTRIBUTING.md) for development conventions.
- [docs/MIB-Specification.md](docs/MIB-Specification.md), the executable code, and
  [schemas/](schemas/) define the current contract. Keep them consistent.
- Use the English specification as canonical. Respect the user's requested
  scope for `docs/cn/`, `*_CN.md`, and `*_cn.md`; mirrors can lag the current
  implementation. State when a change intentionally leaves mirrors untouched.
- `docs/proposals/`, `docs/archive/`, and historical review reports explain prior
  decisions; they do not override the current specification. Consult
  [the current review resolution](docs/harness/MIB-v0.5-Review-Resolution.md)
  for implemented fixes and remaining empirical work.
- Inspect the worktree before editing. Preserve unrelated changes and respect
  task-specific constraints, including restrictions on subagents.

## Code map

| Area | Location |
| --- | --- |
| World semantics and deterministic generation | `src/mib_runner/worldmodel.py`, `generate/` |
| Program/Instance/rung identity and completeness | `src/mib_runner/episode.py` |
| Observation delivery, lifecycle and tool execution | `src/mib_runner/runner.py`, `world.py`, `adapter_contract.py` |
| Evaluation, aggregation and dependence evidence | `evaluator.py`, `scoring.py`, `aggregation.py`, `dependence.py` in `src/mib_runner/` |
| Reports, verification and comparisons | `report.py`, `benchmark.py`, `leaderboard.py` in `src/mib_runner/` |
| Fixed-model and memory-only experiments | `same_model_agent.py`, `same_model_calibration.py`, `memory_backend.py`, `backend_benchmark.py` in `src/mib_runner/` |
| Longitudinal experiments and optional host bindings | `src/mib_runner/learning/`, `learning/bindings/` |
| Separate experimental result families | `src/mib_runner/experimental/` |
| Pack membership, budgets and measurement policy | `profiles/` |
| Regression coverage and shared paths | `tests/`, `tests/paths.py` |

## Measurement invariants

1. **Protect evaluator boundaries.** Never expose hidden oracles, support sets,
   relevance labels, intervention labels, or future probes during formation.
   Participant-visible IDs and text must not encode those roles (no "held-out" or
   "practice" items). Never commit evaluator
   private packs, secret seeds, credentials, or traces that reveal them. The
   public demo store in `fixtures/private-eval-store-demo/` is synthetic.
2. **Keep comparisons paired.** Hold declared model, prompt, tools, task inputs,
   seeds and budgets constant in Track A. Track B evaluates the integrated Agent.
   Do not mix tracks, Profiles, measurement revisions or source bundles in a rank.
3. **Preserve the experimental unit.** Rungs belong to Instances, not separate
   Programs. Validate complete ladders and reject duplicates. Repetitions do not
   create additional independent Instances or seeds.
4. **Keep denominators fixed.** Wrong, missing, unsupported and failed outcomes
   must retain their declared treatment and coverage semantics. Do not select
   twin admission evidence by full-condition correctness. Missing causal
   evidence is unassessable, not a pass. A policy that remembers nothing must not
   earn structural credit; keep `GrammarOnlyAgent` and `RecoverOnlyAgent` (in-task
   feedback recovery only) at the floor.
5. **Score observable behavior.** Scalar answers require exact normalized aliases;
   negation or candidate enumeration is not correctness. Preserve whole-output
   withdrawal checks, actual world outcomes, first-attempt failures and complete
   commitment lifecycles. Keep signed effects separate from clipped losses. The
   dependence gate measures content following, not accuracy.
6. **Use the shared contracts.** Update execution, aggregation, verification and
   schemas together. New routes must not invent another interpretation of
   identity, weights, lifecycle success, memory budgets or costs.
7. **Bound and account honestly.** Enforce the final rendered context budget,
   including framing. Characters, bytes and tokenizer tokens are distinct.
   Unknown costs stay unknown; cumulative receipts must not be summed repeatedly.
8. **Separate evidence from claims.** Raw history is a valid memory architecture.
   Session acknowledgements do not prove remote storage isolation, withdrawal
   compliance does not prove physical deletion, and host audit data does not
   prove native learning. Keep empirical admission separate from engineering
   validation; do not tune gates or exclude samples to manufacture a pass.

## Implementation and versioning

- Target Python 3.10+. Follow adjacent code: annotations, built-in generic types,
  `pathlib.Path`, narrow exceptions and existing JSON/digest/time helpers. Prefer
  existing dependencies over adding new runtime packages.
- Keep semantic, surface and interference random streams deterministic and
  independent where required. Preserve paired future inputs across rungs and
  interventions. Test observable leakage as well as symbolic non-derivability.
- Add meaningful regressions for changed behavior, especially negative cases,
  denominator preservation, bounds, lifecycle failures and report tampering.
  Use independently specified expectations where generator/oracle agreement
  could otherwise conceal an error.
- Read version constants from `src/mib_runner/__init__.py` and package metadata
  from `pyproject.toml`. Distinguish implementation, measurement, scenario,
  report, protocol and Profile versions. Version incompatible changes explicitly;
  never silently reinterpret old evidence under new scoring rules.
- Preserve source/version identity on historical examples. Regenerate affected
  current evidence or label retained examples as historical. Keep large local
  traces and scratch artifacts out of commits; publish only appropriate evidence.
- Keep Brain-specific requirements in the optional binding; do not impose its
  internal record model on every memory architecture.

## Verification

Use the existing virtual environment when available. Otherwise install the test
extra in an isolated environment:

```bash
python -m pip install -e ".[test]"
PYTHONPATH=src python -m pytest tests -q
```

Run focused tests while iterating and the full suite for behavior changes before
delivery. Documentation-only edits need link/path and diff checks, not a model
experiment. Pytest discovery is restricted to `tests/`; do not collect historical
copies under local `debug/` directories.

Validate changed Scenarios and reports against their schemas. For changes to
generation, scoring, dependence, lifecycle or report contracts, use the relevant
replay and engineering checks:

```bash
python -m mib_runner validate path/to/scenario.json --schema schemas/mib-scenario.schema.json
python -m mib_runner verify path/to/report.json --report-schema schemas/mib-report.schema.json
python tools/validate-review-20260923.py --output-dir /tmp/mib-review-check
python -m mib_runner.same_model_cli examples/same-model/same-model-generated.stub.json \
  --output-json /tmp/mib-smoke.json --report-schema schemas/mib-same-model-report.schema.json
```

The report-schema example above is for ordinary `MIBReport` artifacts. Backend
and longitudinal reports have their own verification paths. Source-bound reports
need the matching executable bundle. Passing verification establishes evidence
consistency, not honest remote execution or scientific validity.

Linux namespace sandbox tests and evaluator-private tests may skip when their
requirements are absent. Record the actual skips; do not weaken containment or
fabricate private data to obtain a green suite. CI tests Python 3.10–3.13 on Linux.

Real-model runs require configured endpoints, immutable identities and an
authorized experiment budget. Start with the estimate-only pilot; do not turn a
routine code or documentation change into an unrequested provider run:

```bash
python -m mib_runner run examples/same-model/same-model-generated.pilot.json --estimate-only
```

## Delivery

- Report what changed, what was verified, relevant skips, and remaining empirical
  or deployment limitations. Do not present fixture results as real-model results.
- Commit and push when requested, using the user's specified branch. Check the
  staged diff, include only intended files, preserve configured Git authorship,
  and add requested AI attribution as a co-author trailer. Avoid force-pushing.
- Follow [SECURITY.md](SECURITY.md) for vulnerability disclosure; do not publish
  sensitive findings or evaluator-private material in ordinary artifacts.
