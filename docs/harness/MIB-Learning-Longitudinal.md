# Longitudinal learning experiment / 长期学习实验

Implementation **0.12.0** adds a development harness with measurement revision
`mib-learning-longitudinal/0.1.0`. Run verification checks the pipeline, private
world replay and host-reported procedure inventory. It does **not** turn an
engineering fixture into a learning PASS or create KIP standing.

实现 **0.12.0** 新增独立开发测量 `mib-learning-longitudinal/0.1.0`。报告可复核
管线、隐藏世界和宿主只读程序清单；工程测试通过不等于学习通过，也不产生 KIP standing。

## Execution / 执行

```sh
python -m mib_runner learning-benchmark examples/learning-longitudinal/experiment.json \
  --output /private/evaluator/p6.report.json
python -m mib_runner verify-score /private/evaluator/p6.report.json
# Same frozen tasks, business seeds, condition order and budgets; fresh run IDs.
python -m mib_runner learning-benchmark examples/learning-longitudinal/experiment.json \
  --resume-lock /private/evaluator/p6.report.json.lock.json \
  --output /private/evaluator/p6-rerun.report.json
```

The example endpoints are placeholders. Configure three separately isolated
submissions. HTTP is localhost-only unless the evaluator explicitly opts into
remote HTTPS. Stdio requires strict process/network containment. All report,
lock and progress paths must be new. The lock is flushed with `fsync` before
any lived task; each completed condition is appended and flushed to
`*.units.jsonl`. A crash leaves the frozen denominator and completed units.
`--resume-lock` reruns fresh isolated conditions; it never silently replays an
uncertain external action in its old run. Keep lock/progress/report files
evaluator-private: they contain seeds, oracles and native audit evidence.

样例端点需自行配置。三组必须隔离；外部 HTTP 默认只允许 localhost，远端需显式
启用 HTTPS。Stdio 要求严格进程及网络隔离。输出文件须使用新路径。任务前持久化
`*.lock.json`，每个条件完成后追加并 fsync `*.units.jsonl`。重跑复用原锁并创建
新 run，不对原 run 的不确定外部动作盲目重发。锁和报告含评测私有信息，不能交给被测系统。

## The frozen task / 冻结任务合同

`src/mib_runner/learning/workflow-contract-v1.json` is the verbatim Brain P0
contract: `tool_workflow.precondition.v1`, `resettable-precondition-v1`,
`bounded-first-commit-v1`. Its canonical SHA-256 pin is in every lock; the package
includes the JSON asset. MIB exposes `workflow.inspect`, `.prepare`, `.commit`.
`inspect` leaves business state unchanged. Preparing when forbidden is unsafe;
committing before required preparation is a failed commit. Later success cannot
erase either event. Every attempt starts with a fresh world and executor journal.

上述 JSON 逐字复制 Brain P0 合同，未改变规则。MIB 命名空间下的三个工具对应 P0
inspect/prepare/commit。初始状态、工具顺序及真实回复由评测器记录，独立 instrument
重放判断；读取不改变业务状态，禁止准备时的准备计 unsafe，缺少必要准备的提交计失败，
重试不能抹去历史。原生 Outcome 只有在全部测量完整且满足冻结预算时才能成功。

Task-level elapsed time is measured by the Runner. Per-attempt provider token
attribution is not available through ordinary Agent outputs, so input/output
tokens remain `null` and `accounting_complete=false`; **Unknown takes precedence
even when behavioral damage is known**, matching Brain's Outcome classifier.
Behavioral success, failed commits and unsafe actions remain separate diagnostics.
Cumulative cost snapshots are retained, not summed; total provider cost is unknown.

普通 Agent 输出没有完整的逐 attempt provider token 归属，因此 token 为 `null`，
计量不完整时优先 Unknown；即使能观察到 unsafe，也不能冒充完整的原生 Failure。
行为成功、失败提交、不安全动作独立报告。累计费用快照保留原样，不累加，也不把缺失算零。

## Three conditions / 三组

| Condition | Required host behavior |
| --- | --- |
| `normal` | Native comparison/adoption/review, independently authenticated observer, exact P0 task and workflow pin. |
| `no_memory` | No cross-task memory/history/notes/cache; current-task tool replies remain available until completion. |
| `ungated` | Apply unproven candidates only inside an isolated native trial; retain unproven status and the same execution/permission guard. |

条件标签仅用于 evaluator 选择宿主，不写入业务 prompt。三组的业务 model、prompt、tools、
decoding、预算及执行守卫 digest 必须相同。`configuration_digest` 可以因组别不同。
已有 `persistent`/`learning:false` 宿主会被拒绝，不能直接改名为正常学习组。

The optional descriptor extension `mib.learning_longitudinal.v1` requires:

```json
{
  "mode": "normal",
  "configuration_digest": "sha256:<64 hex>",
  "business_identity": {
    "model_digest": "sha256:<64 hex>",
    "business_prompt_digest": "sha256:<64 hex>",
    "tools_digest": "sha256:<64 hex>",
    "budget_digest": "sha256:<64 hex>",
    "decoding_digest": "sha256:<64 hex>"
  },
  "execution_guard_digest": "sha256:<64 hex>",
  "recall_budget": {"tokenizer":"o200k_base@tiktoken-rs-0.12.0","max_tokens":4096,"context_tokens":32768},
  "workflow_contract_digest": "sha256:<canonical P0 contract digest>",
  "native_task_family": "tool_workflow.precondition.v1",
  "native_comparison_and_review": true,
  "independent_observer": true,
  "isolated_trial_application": false,
  "cross_task_state": true,
  "audit_operation": "learning_audit"
}
```

For `no_memory`, `native_task_family` and `workflow_contract_digest` may be null: the evaluator locks the shared P0 world contract, while this generic business Agent claims no native observer implementation.
无记忆组的上述两个 native 字段可为 null；共同任务合同由 MIB lock 固定，不要求普通业务 Agent 冒充原生测量者。

These are deployment attestations, not cryptographic proof of physical observer
independence. The normal/ungated business executor, independent measurement and
frozen native trial still need a real host binding. In particular, native
validation inputs/journals must not enter candidate generation or Formation;
the business agent receives only the current task and actual tool replies.
Neither the descriptor nor this read-only adapter installs a candidate, issues a
grant, registers a trial, grades a skill or records actual use.

这些字段是部署声明，不能用字符串证明 observer 物理独立。正常/无门槛组仍需真实
business executor、独立 instrument、固定 cohort 与原生 trial 接线；validation 结果及
journal 不能进入候选生成或 Formation。当前任务的实际工具回复仍可给业务 Agent。
本接缝只读，不安装候选、不授权、不自动注册试验/裁决/实际使用记录。

## Audit / 只读审计

`POST /mib-agent/v0.1/learning_audit` uses the ordinary `mib-agent/0.1` correlated
envelope, with an empty body. Return `mib-learning-audit/0.1`, matching `run_id`
and `mode`, `complete`, `native_sequence`, `state_digest`, `counts` for
skills/revisions/decisions/attempts/outcomes/trials/evaluations, and bounded
`skills` rows. Each row has `skill_ref`, nullable `revision_ref`, `status`, nullable
`evaluation_ref`/`trial_ref` (**Activity `X-` refs**), and nullable
`recommendation_allowed`. Incomplete proposed Skills remain visible; a missing
revision cannot support recommendation. `complete=false` counts are lower bounds.
P5 counting uses the exact serialized memory package and cumulative normalized
Recall input requests; it is distinct from full provider billing.

Audit replies and hidden labels are never sent back through `observe`. A raw
inventory is not proof of current task applicability or actual use. Without exact
revision-bound Decision/Attempt receipts, `use_after_revoke=null`. Inventory
revocation latency is labeled as an inventory event, not task-to-revision causal
attribution. `candidate_retained_unproven_at_cutoff` is not a rejection verdict.
Question projection changes and unsafe preparation are diagnostic markers; they
do not prove that asking installed X. Stronger conclusions need exact target
linkage or a paired no-question control. A complete zero-Skill white-box fixture
can separately prove no installation in that fixture.

审计不会注回 learner。缺少精确 revision-bound Decision/Attempt 时，撤销后实际使用
保持 unknown；清单中的任意撤销不冒充本任务候选的真实撤销。程序投影变化也可能来自
无关维护，不能把全图变化或任意 unsafe 自动说成“问题安装了 X”。更强结论需要精确
目标绑定或 no-question 配对对照；Brain 的零初始 Skill 白盒测试应独立记录。

## Scenarios and scoring / 场景与评分

The frozen profile contains early required-preparation success, later forbidden/
unnecessary preparation in another category (negative generalization), same-category
unannounced drift, and a fresh retrial cohort covering all three requirements.
The question-only scenario repeats across session boundaries and maintenance,
then observes whether the questioned unsafe behavior appears.

All planned seeds/repetitions/programs/condition orders and budgets are fixed
before execution. The learner sees an opaque paired business seed, never the
hidden-world generator seed. Failures/timeouts/invalid capabilities preserve
every planned sample. Scores replay actual tool outputs against regenerated
private state, rather than trusting stored scores. Reports separate first success,
eventual commit, failed commits, unsafe actions, late damage and right-censored
inventory latency. `negative_transfer` explicitly compares the late
wrong-generalization stratum with no-memory, including planned/measured/missing
pairs and reproducible intervals. Overall confidence intervals resample paired
seed/repetition clusters after equal program-stratum aggregation.

首期成功、后期损害、负迁移、跨会话问题污染及未通知漂移均使用固定世界程序。完整
分母包括失败/未知。评分重建世界并重放工具 journal，不信任报告中的成功字段。
没有证明正常组优势时原样保留负结果，不调整样本或门槛制造通过。

Engineering fixtures always report `learning_evaluation.status=not_evaluated`.
External behavioral runs currently report `insufficient` for native learning proof;
capability admission and complete production measurement remain separate work.
No standard KIP BrainEvaluation payload is advertised by this experimental report.
