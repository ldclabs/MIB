# Brain legacy eval migration / 旧评测迁移

The public profile `profiles/MIB-Brain-Product-Regression-0.1-Dev.json` preserves
the useful product goals of the nine retired Brain scenarios. It uses ordinary
MIB Programs, Scenario schema, `mib.workspace.v1`, `world_state` evaluation and
the existing score verifier. There is no new combined evaluator or graph metric.

公开 profile 保留旧九个场景中有效的产品行为目标；使用既有生成器接口、场景 schema、
workspace 工具模拟器、world_state 判据和 verify-score。没有复制旧 KIP 图形状、
关键词命中、图 COUNT 或“多读即强化”判据，也没有新增综合 evaluator。

## Exact mapping / 逐项映射

| Retired file / 旧文件 | Program | Observable criterion / 可观察判据 |
| --- | --- | --- |
| `style_preference.json` | `mib.product_style.v1`, rung 0 | Editor draft policy actually saved as concise/direct/non-promotional; saying the words is insufficient. 保存到编辑器的实际配置必须匹配。 |
| `project_budget.json` | `mib.product_budget.v1` | The whole draft binds Alice's project, Orange County, numeric amount, USD and `certainty: approximate`. Exact/guaranteed or Bob's project fails even with the right amount. |
| `fact_correction.json` | `mib.product_correction.v1` | Current shipping draft uses Berlin following the correction; earlier Tokyo remains in observation history. 当前应用正确，不要求删除历史。 |
| `preference_reversal.json` | `mib.product_reversal.v1` | Dinner-planning configuration applies current vegetarian policy after maintenance/session boundary. |
| `counterparty_boundary.json` | `mib.product_boundary.v1` | Alice's metric/concise and Bob's imperial/detailed settings are separately applied; payload actor claims cannot impersonate the observation actor. |
| `travel_logistics.json` | `mib.product_travel.v1` | Combine separately recorded home airport and aisle preference; destination stays null. Invented destination or another actor's plan fails. Local draft only, no booking. |
| `expiring_discount.json` | `mib.product_discount.v1` | Past `valid_until`, the saved current-pricing draft contains no SPRING20 code. Source history remains available; elapsed time is not a deletion/count test. |
| `noisy_style_preference.json` | `mib.product_style.v1`, interference 20 (rung 1) | Same task, policy and time span with additional unrelated observations; not another independent ability/sample family. |
| `usage_reinforcement.json` | `mib.product_usage.v1` | Apply strong oolong preference twice across maintenance/session boundary. Both applications are checked; no conclusion about strength, confidence, adoption or read count. |

The profile fixes seeds `[101,202]`, one repetition, interference counts `[0,20]`
and explicit session boundaries: **8 Programs × 2 seeds × 2 rungs = 32 full runs**,
plus four declared interventions per instance, **160 runs total**. The Programs
also support the ordinary `[0,20,100]` default ladder for expanded manual runs.
These are product instances, not eight new statistically independent abilities.

Product facts are explicit, user-owned structured records accompanied by their
natural-language statements. The fixture sees only the actual public observations
and task intent, never oracles or evaluator annotations. The future task identifies
the requested actor/project and asks for a local draft; it does not contain the
answer. Travel combines two records. A source-withholding intervention removes
the required history, causing an unknown/null draft rather than a guessed value.

记录同时包含公开自然语言及结构化产品事实，fixture 只从观测和当前任务构造草稿。
未来请求仅指定 actor/project，不携带隐藏答案。缺少必要历史时使用 unknown/null，
不能由默认值或另一个主体的记录填补。预算、出行及主体隔离以完整 JSON 对象相等检查，
因此正确关键词不能掩盖错误确定性、虚构字段或属性串台。

Writing-style regression checks actual selection/application of a structured
editing policy. It does **not** by itself establish free-form prose quality.
The local drafting tool does not send email or book a flight. Organic writing,
real-provider performance and broader product quality require separate empirical
evaluation; fixture PASS must not be described as Brain competence.

写作测试检查结构化编辑策略的真实应用，不冒充自由文本质量评估；草稿工具不实际发邮件
或订机票。真实模型表现仍需独立实跑。旧 eval 退役不意味着这些经验性结论已成立。

## Public CI entry / CI 入口

After installing MIB dependencies, Brain can run this from any working directory:

```sh
python ../mib/scripts/check-brain-product-regression.py --output-dir /tmp/brain-product-regression
```

The script uses only `ProductMemoryFixture`, calls the existing generated-pack
runner and score verifier, and exits nonzero for missing files/dependencies,
invalid schema, unexpected fixture behavior or unsuccessful report replay. It
does not inspect model environment variables, call a provider or silently skip a
missing dependency. It writes:

- `brain-product-regression.report.json`: complete ordinary MIB report.
- `brain-product-regression.summary.json`: the ordinary pack summary.
- `prospective-refusal.report.json`: retained explicit unsupported-capability run.
- `checks.json`: CI checks, with `no_model=true`,
  `product_behavior_evaluated_on_Brain=false`, `learning=not_evaluated`.

CI 仅检查无模型软件合同。Brain CI 应 checkout/install 同级 MIB 并执行此脚本；文件或
依赖缺失必须失败。目前跨仓库开发内容仍需提交发布后，GitHub 才能运行相同入口；本地
验证不能冒充 GitHub CI 已运行。

## A real adapter / 实际模型接入

Use the existing public submission route after configuring a real Agent host:

```sh
python -m mib_runner benchmark \
  --profile profiles/MIB-Brain-Product-Regression-0.1-Dev.json \
  --schema schemas/mib-scenario.schema.json \
  --submission /path/to/real-agent.submission.json \
  --output-report /tmp/product-real.report.json \
  --output-summary /tmp/product-real.summary.json
python -m mib_runner verify-score /tmp/product-real.report.json
```

The submission must support observe, respond, act, runner-managed tools,
maintenance, virtual time and session boundaries. It must execute the supplied
local workspace tool contracts. The host owns authentication and native dispatch;
MIB's task intent never grants additional authority. An integrated Bot is Track B;
evaluating Brain alone requires the separate evaluator-owned same-model memory
backend harness. This migration did not run any real model.

## Unsupported capabilities and retained Brain tests / 未支持与保留边界

An `observe_only` probe requires `spontaneous_emissions:true`. The Runner refuses
an adapter that explicitly lacks it, preserves all planned probes as execution
failures, and marks the run invalid. This is not a passed notification test or a
mere missed reminder. The CI script validates that refusal using an ordinary
prospective Program. The retired discount scenario's expiry behavior is covered
separately; expiry does not imply proactive notification support.

主动通知不支持时必须明确拒绝并保存无效样本，不能用图清理或 fixture 成功声称 Bot
支持通知。到期折扣的当前行为测试与主动通知能力是两件事。

Brain retains deterministic tests for native BELIEF/unknown semantics,
append-only correction/supersession, auth-time separation, native record identity
and usage ledgers that do not alter confidence or mnemonic strength. A public
MIB product draft does not replace those engine invariants. P6's production
normal/ungated bindings, independent complete measurement and real-provider
comparison remain **pending**, independently of retiring the old eval code.

Brain 的原生 BELIEF、纠错追加、鉴权时钟、真实 ID 使用账本和不提升真值/standing 等
白盒测试仍须保留。P6 真正正常组/无门槛组接线及实测保持未完成，与 P7 旧入口退役独立。
