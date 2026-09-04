# Contributing to MIB

MIB is a benchmark, so a contribution is judged by one question: does it make the
measurement more truthful? A Scenario that is easy to pass, a metric that cannot be
recomputed from a published report, or a document that promises a number the code
does not emit all make MIB worse, however much work went into them.

Please read [README.md](README.md) first for what MIB measures and why.

---

## Development setup

Python 3.10 or newer. Install the package in editable mode with the test extra:

```bash
python -m pip install -e ".[test]"
```

Run the suite:

```bash
PYTHONPATH=src python -m pytest tests -q
```

`PYTHONPATH=src` is required because `tests/` imports `mib_runner` and the local
helper module `tests/paths.py` directly rather than through the installed
distribution.

Two groups of tests skip rather than fail:

- **Submission-sandbox tests** skip off Linux. Containment relies on Linux
  unprivileged user, mount, and network namespaces via `unshare`; nothing equivalent
  exists on macOS or Windows.
- **Calibration tests** (`tests/test_calibration.py`) skip unless `MIB_OFFICIAL_PACK`
  points at the evaluator-only Scenario pack, which is not published here.

Everything else must pass on every supported Python version before a pull request is
merged. CI runs the suite on Ubuntu across Python 3.10–3.13 and additionally
validates every Scenario against the Scenario schema.

Anything that launches a participant-supplied stdio submission — `mib
agent-smoke-test` on a stdio spec, `mib evaluate-hidden`, `mib-service
register-submission` / `worker-once` — is Linux-only for the same reason. The rest of
the CLI (`validate`, `run`, `run-pack`, `benchmark`, `capability-card`,
`verify-score`, `public-eval-manifest`) is cross-platform.

---

## Repository layout

Every artifact has exactly one canonical location. A Scenario body, a schema, or a
profile is never stored twice; milestone slices are expressed as family subsets of
the one public pack.

```text
docs/                   normative specifications; docs/cn/ mirrors them in Chinese
docs/harness/           calibration, same-model, hidden-eval, evaluation-service notes
schemas/                JSON Schemas — the contract for every artifact MIB emits
scenarios/dev/          the 24 public dev Templates, by Scenario family
profiles/               benchmark profiles (dimension weights, coverage rules)
baselines/              B0–B3 memory-condition definitions
prompts/                fixed same-model prompts
fixtures/               synthetic demo private eval store
src/mib_runner/         reference Runner, evaluators, adapters, service, leaderboard
tests/                  regression suite; tests/paths.py holds canonical paths
tools/                  operational scripts
examples/               reference agents, submissions, and committed run artifacts
```

Two directories are gitignored runtime state and never committed: `service/state/`
and `service/artifacts/`. The evaluator-only `private/` directory is gitignored for a
stronger reason — see below.

---

## The one rule that is not negotiable

**Hidden Eval and Private Holdout Scenario bodies must never be committed to this
repository.**

That includes Template definitions, generators, Oracle data, evaluator rubrics,
Probe input variants, and any fixture derived closely enough from them to leak
composition. A leaked Hidden Eval body is not a bug that can be reverted: git history
is public, and the affected Templates are permanently burned.

What may live here:

- the 24 **public dev** Templates under `scenarios/dev/`;
- the synthetic demo store under `fixtures/private-eval-store-demo/`, which is an
  infrastructure fixture with no relationship to the official hidden set;
- **redacted** public reports and Capability Cards, which by construction carry
  opaque aliases instead of private Template IDs, seeds, and paths.

Evaluator-only content is resolved at runtime through `MIB_OFFICIAL_PACK`, and the
tests that need it skip when it is absent. If you are unsure whether something you
want to add is derived from hidden content, do not commit it — open an issue and ask.

---

## Proposing a new Scenario

Start from the framing question in the README:

> **What part of the past should matter now, what part should not, and how can we
> prove the difference?**

A Scenario that cannot answer the third clause is not yet a MIB Scenario. Concretely,
a proposal should state:

1. **Which Dimension** it targets — retention/retrieval, temporal, epistemic,
   experience, skill learning and transfer, or causal memory impact — and why an
   existing family does not already cover it.
2. **The memory dependency.** What in the past must be carried forward, and what
   makes the future Probe unanswerable without it.
3. **The relevant ablation.** Removing the critical information must remove the
   complete critical set, never a redundant subset, or the paired intervention proves
   nothing.
4. **The irrelevant ablation.** Removing unrelated history must leave performance
   approximately stable.
5. **What must not leak.** Future Probes may not be visible during memory formation,
   and goals may not disclose applicability labels that let a memoryless agent guess.
6. **The Oracle.** How a correct answer or a correct world outcome is decided
   mechanically, without a human in the loop.

Draft it as a public dev Template under the appropriate `scenarios/dev/<family>/`
directory, give it the next free `MIB-<FAMILY>-NNN` ID, and validate it:

```bash
mib validate scenarios/dev/<family>/MIB-<FAMILY>-NNN.json \
  --schema schemas/mib-scenario.schema.json

mib run scenarios/dev/<family>/MIB-<FAMILY>-NNN.json \
  --schema schemas/mib-scenario.schema.json
```

Static Templates are v0.1 material. New MIB-Core evidence is a **Program**
(`src/mib_runner/generate/programs.py`): register it in `generate/registry.py`, give it a
test in `tests/test_v02.py` proving that its Instances are schema-valid, deterministic,
and leak-free at every rung, and add its id to the Profile's `programs`
(`profiles/MIB-Core-0.2-Dev.json`).

If the Template is added to the pack, add its id to the Profile's
`required_templates` (`profiles/*.json`); the Profile is the only definition of
pack membership, and `mib benchmark` refuses a directory whose Templates do not
match it exactly. Calibration decides whether a Scenario is admitted:
`docs/harness/calibration-harness-notes.md` describes the gates a Template has to
clear (full-context solvability, no-memory ceiling, memory discriminativeness,
baseline span, causal sensitivity, irrelevant stability).

---

## Coding conventions

These are observed throughout `src/mib_runner/`; follow them rather than importing a
different house style.

- `from __future__ import annotations` at the top of every module; standard-library
  imports first, third-party next, then relative imports.
- Type-annotate public functions. Use built-in generics (`list[str]`, `dict[str, Any]`,
  `str | Path`) — the codebase targets 3.10+ and does not use `typing.List`.
- Structured values are `@dataclass(slots=True)`. Errors are narrow module-level
  subclasses of the closest built-in (`RunnerError(RuntimeError)`,
  `SubmissionSpecError(ValueError)`, `SandboxPolicyError`).
- Filesystem work goes through `pathlib.Path`; JSON is read through
  `mib_runner.validation.load_json`, which reads UTF-8 explicitly.
- Every artifact written to disk carries `mib`, `kind`, and a version field, and is
  validated against its schema in `schemas/`. If you change the shape of an emitted
  artifact, change the schema in the same commit.
- Timestamps are UTC ISO-8601 with a `Z` suffix (`utc_now()`), never local time.
- Determinism is a correctness property. Anything seeded must be derived from an
  explicit seed, and digests use the canonical helpers so that two runs of the same
  input produce byte-identical output.
- No new runtime dependencies without discussion. The package depends on
  `jsonschema` and `cryptography`, and that list is deliberately short.
- Documentation voice is precise and declarative: state what the code does, name the
  file that proves it, and do not claim capability the implementation lacks. When a
  metric is specified but not implemented, say so.

### Tests

- Tests import `mib_runner` directly and pull canonical paths from `tests/paths.py`.
  Add a constant there instead of hard-coding a repository path in a test.
- Gate platform-dependent tests with `SANDBOX_AVAILABLE` / `SANDBOX_REASON` and
  evaluator-pack-dependent tests with `OFFICIAL_PACK`, so an unsupported host skips
  instead of failing.
- A change to scoring, redaction, or the report shape needs a test that recomputes
  the published numbers — `verify-score` exists precisely so that a report is
  checkable without the evaluator's secrets.

---

## Pull requests

- One concern per pull request. Schema change, Scenario change, and Runner change are
  three reviews, not one.
- Say what you verified and on which platform. If a sandbox or calibration test could
  not run locally, say that too.
- Update the English document and its `docs/cn/` counterpart together; a translation
  that drifts is worse than none.
- If your change makes a shipped example, count, or artifact stale, regenerate or
  correct it in the same pull request.

Security issues do not go in pull requests or public issues. Follow
[SECURITY.md](SECURITY.md).

---

## License

MIB is licensed under the GNU General Public License v3.0. By contributing you agree
that your contribution is licensed under the same terms.
