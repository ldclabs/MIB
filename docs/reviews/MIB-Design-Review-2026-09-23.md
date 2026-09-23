# MIB 设计审查与执行清单 — 2026-09-23

> 修复状态：本报告记录原始审查证据；后续实现为 0.13.0 / measurement 0.4.0。完成项与仍需实测的事项见 [修复记录](../harness/MIB-v0.4-Review-Resolution.md)。

审查基线：`bb46321`，实现 `0.12.0`。审查英文规范、当前生成器、Runner、评分/汇总、固定模型与 memory-backend 路径、纵向学习扩展、隐藏评测边界及主测试。跳过 `*_CN.md`、`*_cn.md` 和 `docs/cn/`；未使用 subagents。混合中英文的新增 harness 文档不属于镜像，阅读其英文内容。

## 判断

MIB 已经具备有价值的受控记忆实验框架：历史干预、内容/策略孪生、实际工具反馈、首尝试评分、失败保留分母，以及可复核的报告。原始历史也是合法记忆架构；不应因为简单系统能成功就否定它。

当前主要问题是：部分判据仍可误判；准入门槛有非单调性；几个任务的分布允许绕开声称施加的压力；实现复杂度和校准成本已经超过现有真实模型证据所能支撑的程度。下一轮应先修复测量，再收窄公开结论，完成真实模型试验，随后决定扩展。

适合目前证据的定位是：**在声明的任务分布、交互边界和资源条件下，评估历史信息如何影响后续行为的开发实验平台。** 尚不能将其总分解释为已验证的通用长期记忆、技能学习或物理遗忘能力。

## 验证范围

- 主测试：`.venv/bin/python -m pytest -q tests` → **387 passed, 8 skipped**，39.68 秒。跳过项涉及 Linux sandbox 与 evaluator-private pack；不代表这些路径已在本次环境验证。
- 无参数 `pytest -q` 会收集本地 `debug/` 历史副本，产生 12 个 collection import mismatch；按 CI 的 `tests` 范围运行正常。这是本地测试发现配置问题，不是上述 387 个测试失败。
- 另外运行了无模型、无外部网络调用的最小复现和生成包实验，结果见下文。合成评分数据明确标出；没有把它们当作真实 Agent 实测。
- 本次没有运行真实模型校准，没有评估生产部署安全。没有修改实现、Profile 或既有测试；本文件是新增审查产物。

## A. 已复现的问题

### A1. 结构化标量评分仍允许否定答案、多答案和候选池枚举得满分

位置：`src/mib_runner/evaluator.py:286`，默认 `match="contains"`；`_match_value` 在 71 行附近执行词边界包含判断；`generate/base.py:432` 的默认 rubric 没有覆盖该设置。

使用真实生成实例 `mib.recall.v1`、seed 101、rung 0，oracle 为 Toronto。以下四个 `value` 配合 `status=known` 均得 **1.0**：

```text
Toronto
Definitely not Toronto
Toronto or UNRELATED-IMPOSSIBLE-VALUE
Lisbon / Tokyo / Berlin / Toronto / Nairobi / Seoul / Denver / Warsaw
```

`forbidden` 只覆盖 oracle 中列出的错误值，无法穷举全部错误陈述。修复 forbidden 不能替代验证实际答案。这个复现证明单题判分漏洞，不声称候选池枚举已经攻破整个包含孪生门槛的 benchmark。

建议：对标量答案使用类型约束及规范化后的精确等价；别名只允许明确列出的等价表达。自由文本判定另设 lane。撤回信息的全输出 disclosure 检查继续保留，不能因答案改用 exact 而削弱。

### A2. 依赖门槛会因原始回答变得更准确而从通过变为失败

位置：`scoring.py:647` 的 `counterfactual_evidence` 和 `scoring.py:697` 的 `memory_dependence`。

当前规则同时使用：只有 full 得满分才进入 eligible；一个 Instance 的全部 eligible twins 都成功才算 tracking instance。

对 5 个合成独立实例，每例各有 easy/hard 两题，孪生得分固定为 `[1,0]`：

| Full 得分 | Full 平均 | Eligible coverage | Tracking instances | 门槛 |
|---|---:|---:|---:|---|
| `[1,0.8]` | 0.9 | 0.5 | 5/5 | 通过，Wilson 下界 0.5655 |
| `[1,1]` | 1.0 | 1.0 | 0/5 | 不通过 |

提高原始回答的正确率反而丧失“记忆分数”资格。增加 probe 或 repetition 也会提高“全对”的难度：若各机会成功率为 p 且独立，实例全对概率为 `p^k`；独立假设只是说明这种试次数依赖，并非对当前 Agent 的经验估计。

建议：将条件 tracking 保留为诊断；核心证据改为固定、预注册 probe 集合上的 joint twin success，先在 Instance 内求均值，再以 Instance 为 cluster 求区间。题数和重复数只应改变被定义的统计量或精度，不能悄悄改变通过标准。若保留全对可靠性指标，必须显式固定机会数并单独命名。

### A3. 校准准入把缺失因果证据当作通过

位置：`same_model_calibration.py:478`。`irrelevant_stability` 和 `causal_sensitivity` 都使用 `metric is None or metric >= threshold`。该结果进入 `provisional_full_gate_including_causal`，后者又被用于 release eligibility（约 779 行）。

调用当前 `_aggregate_calibration`，提供满足能力阈值的合成 B0–B3 数据，并令 `causal={}`，得到：

```text
memory_benefit = null
irrelevant_memory_stability = null
causal_sensitivity gate = true
irrelevant_stability gate = true
provisional_full_gate_including_causal = 1 / 1
```

这验证了缺失证据被计入通过数；没有实际提交或发布一个官方结果。它与规范“缺失证据保持不可评估”的要求冲突。

建议：统一使用 `pass / fail / unassessable`；缺失必要对照、无效生命周期、零有效独立样本时不能进入 release pass。正式准入还应核验声明必需的对照及样本数，不能只检查模型调用是否报错。

### A4. Memory-backend 的生成任务汇总把 rung 当成独立 Template

位置：`same_model_calibration.py:83` 的模板加载为每个 rung 添加 `-R0/-R1/-R2`；`backend_benchmark.py:188` 复用这些模板，271 行将它们直接交给 `build_pack_report`。后者按 canonical rung 筛选 Instance，但覆盖率分母仍包含全部 rung Templates。

直接运行该生成/物化/汇总路径，无 HTTP，使用 StructuredMemoryAgent 完成 Calibration Profile 的 14 Programs × 3 rungs × 1 seed：

```text
42 / 42 full runs 已执行
capability score = 100
coverage = 0.3333333333333333
partial = true
profile_eligible = false
retention = 42 个 block，每个只有 1 个 rung
```

应该是 14 个 Program，各有 3 个 rung，完整覆盖且形成完整曲线。此处本意用于校准的执行单元标识与正式汇总的 Program 身份混用，单靠共享平均公式未能避免错误。

建议：统一 `program_id / instance_seed / rung / repetition / condition` 的身份模型，所有运行入口共享物化与聚合路径。不要用将 required coverage 降至 1/3 的方式绕过。

### A5. 固定模型内置策略的 memory limit 不是硬限制

位置：`same_model_agent.py:114`。当一个 Observation 已超过上限时，`_limit` 仍保留整条。渲染时添加的序号与换行也未统一纳入这条路径的预算。

复现：10,000 字符内容、`limit_chars=100`，选中内容连同元数据为 **10,020 字符**，仅设置 `truncated=true`。HTTP backend 路径已有另外一套更严格的界限，因此两个实验入口的同名预算语义不一致。

建议：显式区分无界参考与有界实验；有界策略对最终注入内容实施同一个硬上限，超大记录采用预先固定的分块或丢弃政策，并报告丢失。字符预算不是 token 预算；实际上下文实验需要锁定 tokenizer 和完整 prompt 预算。

### A6. 固定模型 wrapper 没有持久化自己的回答和主动 emission

位置：`same_model_agent.py:333` 的 observe 将输入写入记忆，但 emission 只返回和缓存；`respond`（506 行）只缓存输出；与 `act` 在任务完成时持久化真实轨迹不同。

用记录调用的脚本模型验证 B1：前一次 emission、回答和问题均不在下一次相应模型输入中。响应缓存也没有被读入模型上下文。外部 memory backend 同样不会自动收到这些事件。

这不足以证明当前单触发提醒题必然失败，但限制了“我已经提醒过”“我刚承诺了什么”、跨轮指代与对话中自我纠错的可测范围。模型有时能从两次触发输入推断已执行，仍不等价于保存真实输出事件。

建议：把公开问题、真实回答、真实 emission 及执行回执纳入统一的可观察交互日志；B0 只在当前任务内保留，其他条件按各自记忆政策处理。禁止将 evaluator 的 oracle、评分或隐藏标签作为 feedback 写回。对 Probe 是否产生后续学习效应，分别定义冻结测试和在线连续任务协议。

### A7. Core 的固定阶段结构允许绕开持续记忆压力

构造：继承公开 StructuredMemoryAgent，只在第一次 `maintain` 后忽略所有 `user_message`；继续处理工具反馈和环境触发。它不读取 oracle，也不使用隐藏 event 标签。

对现有 Core Dev 全部 5 seeds、3 rungs：

```text
105 Instances，861 条 full/干预 runs
MIB Score = 100
Coverage = 1
所有 Program 的三个 rung 均为 1.0
Memory dependence gate = true
```

它确实使用了早期记忆，因此不是“无记忆作弊”。问题在于维护边界标出了一个可整体忽略的未来消息区域；增加 noise 几乎不再增加选择、修订或保留的难度。Expanded 的 interleaved recall/relearning 已局部缓解这个问题，不能据此声称所有 Profiles 均有同样漏洞，也不能说交错机制完全缺失。

建议：在各主要机制中交错有效信息、修订、撤销和无关信息；随机化维护位置且不与信息价值绑定。为“仅保存前缀”“最后值覆盖”“关键词优先”“总是弃权”等简单策略保留专门挑战集。

### A8. 纵向学习任务存在无需跨任务记忆的满行为成功策略

位置：`learning/workflow.py:19`，`inspect` 直接返回当前 preparation requirement；预算允许最多 4 次工具调用。

只依赖当前任务工具结果：

| Requirement | 无跨任务记忆策略 | 工具次数 | behavior_success |
|---|---|---:|---|
| required | inspect → prepare → commit | 3 | true |
| forbidden | inspect → commit | 2 | true |
| unnecessary | inspect → commit | 2 | true |

此策略适用于当前所有 action requirements，包括漂移后。只复现行为成功；因 token 等计量未知，native outcome 仍为 unknown，没有将其描述为学习 PASS。

这类任务适合测量过度泛化的危害与检查习惯，单靠成功率不能证明正向记忆学习收益。不要人为删掉合理检查工具制造记忆优势。保留安全检查，另设可验证的工具成本、冗余调用和完成时间目标；或增加真实需要跨任务信息、且当前工具无法直接查回的任务。

## B. 还需要改善的测量设计

### B1. Experience / Skill 的标签宽于实际测量

`generate/procedural.py:32` 采样 opaque family 与随机 opcode 列表；失败反馈给出完整 `required_recipe`（`world.py:185` 附近）；未来题重复 family；composed skill 在请求中明确要求反转列表。

一个 `family -> recipe` 字典及列表反转足以覆盖这些机制。它们有效测试反馈记忆、程序检索、版本修订和适用范围，但不能单独证明从多次经验中抽象未知规则、复杂规划或跨领域迁移。不要要求真正的记忆架构比字典复杂；应该收窄名称，或增加能区分这些能力的任务。

可增加最小特征组合与反例：训练时多个实体共享潜规则，测试时新实体、新表述及未见组合；另设表面相似但适用条件不同的题。把“给出同等信息的说明文档”作为诊断参考，判断经验收益究竟来自存储反馈还是额外的学习过程。

### B2. 干预统计要区分有符号效应和单侧风险

`scoring.py:319` 的 Memory Benefit 是有符号差值，但 Harm 与 Negative Transfer 对每个样本先 `max(0, delta)` 再平均。若两组本来无平均差异但有随机波动，后者依然可能大于 0。它可以是平均单侧损失，不能直接当作系统性伤害的无偏效应估计。

建议主表报告原始配对有符号差值和 cluster CI；单侧损失另列。Relevant-history 的删除还改变长度、事件机会与可能的学习轨迹，现有 harm placebo 不能替代 relevant deletion 的匹配对照。对确需分离内容效应与长度/调度效应的结论，增加等预算替换对照，且不要把“Perhaps Perhaps weather?”式占位当作自然干扰的充分验证。

条件正确后的 tracking 不能单独分离记忆、读取和格式服从。可使用同一个基础模型、真实任务输入，加入只在诊断 lane 提供最小充分证据的参考：该参考也失败时，先归因于任务可解性/读取执行问题。文档已经正确说明 oracle-supported reference 不是数学上界，这一限制应继续保留。

### B3. 真实模型校准、独立语义泛化与不确定性尚未补齐

现有规范明确声明真实固定模型校准和正式 freeze 尚待完成，值得保留。当前 B3 的同模型内置实现实际为词重合、人工 salience cues、recency 的排序，见 `same_model_agent.py:165`；不要把其结果当作完整结构化/agentic memory 类别的代表。

需要：无记忆、同预算最近窗口、同预算检索、候选系统；无界历史和充分证据可作单独参考。至少在不止一个固定基础模型上检查方向能否复现，再对架构泛化作结论。先用 pilot 方差和预先指定的最小有用效应决定独立实例数，不能把 5 seeds × 多次 bootstrap 当成广泛证据。

隐藏 seed 保护实例答案，不能保护公开生成语法。应把 holdout 分成参数、措辞/作者、机制/组合至少三个层次；按 Program/机制报告分层结果。独立手工真值用例和盲审要与 generator/reference parser 分离，避免共享 world model 的错误自洽。

可借鉴的外部校准入口：LongMemEval 的跨会话、时间更新、弃权任务，以及 MemoryAgentBench 的增量交互任务。它们提供不同来源的验证数据，不意味着要混合各 benchmark 原始总分，也不是 MIB 的正确性证明。

- [LongMemEval 原论文](https://arxiv.org/abs/2410.10813)
- [MemoryAgentBench 原论文](https://arxiv.org/abs/2507.05257)

### B4. 长期记忆、容量、遗忘和主动性需要更明确的实验条件

- Session boundary 在固定 wrapper 内清 transient；对黑盒 Agent 仍是声明契约。增加可控运行环境的新进程/新会话测试：只允许声明的持久存储生存，并用独立 run/tenant canary 检查污染。
- 不只增加 noise，还要独立改变有效事实数量、更新密度、相似实体数量、检索预算与跨会话次数；有用信息总量超过预算时才真正测试选择与压缩取舍。虚拟 24 小时不等于实际在线运行 24 小时。
- 当前 selective forgetting 是“停止操作性使用/披露”；容量驱动遗忘、依法物理删除、反事实内容编辑是不同目标。优先把当前 lane 称为 withdrawal compliance，避免更宽结论。
- Prospective/self 合并了触发执行和持续授权两类行为。保留分项；增加同人重复加入、多承诺、取消/恢复、交叉触发和宽容时间窗。结构化匹配优先，自然语言表达质量另测。
- 当前总分权重和维度独立性未被经验验证。保留七个诊断标签，优先显示分项与成本；综合分仅用于固定 Profile 的摘要，并检查权重/rung/Program 选择是否改变排名。跨 Profile 不混排的既有规则应保留。

## C. 简化方案

### C1. 一个执行内核，两个参与接口

```text
Program / Fixture
        ↓
统一 EpisodePlan（program、seed、rung、repetition、condition）
        ↓
Runner + World + 公共交互日志
        ↓
Evidence → Score / Contrast / CI → Report / Verify

Track A：固定 Agent + MemoryBackend
Track B：AgentAdapter
```

Core、calibration、backend、hidden、longitudinal 调度可有不同计划，但不应复制身份、生命周期、预算、分母和统计语义。先统一纯数据契约及聚合，再逐条迁移执行路径，避免一次性重写。

Brain 原生审计要求固定 tokenizer 字符串、`C-`/`X-` 引用和 native standing（`learning/contract.py:31`、67 行附近）。这些对特定集成合理，但应放在可选 Brain binding；通用 MIB 学习测量不能要求每种架构拥有该内部对象模型。

### C2. 默认只展示三类结果

1. 能力：声明任务分布上的行为成功率、必要分项和区间。
2. 历史效应：同条件下对空记忆/匹配对照的配对差值、固定集合的 twin 成功及证据完整性。
3. 资源与边界：实际预算、延迟/调用/存储已知项、未知成本、会话实施方式。

HMB、IMS、HRS、NMG、half-distance、复合 legacy causal score 留作展开诊断或旧报告兼容项。不必为每个新现象增加一个主分数，也不必马上删掉有用诊断。单位应统一：目前部分 JSON 字段值为 0..1 的差值却标记 percentage_points，Capability Card 再乘 100；应选择一种表示并在 schema 固定。

### C3. 缩小默认实验矩阵

按现有 `same-model-generated.external-http.json` 调用 `estimate_experiment`：

```text
42 个 Program/rung 单元 × 5 seeds × 2 repetitions
1,680 次主 baseline condition runs
3,072 次因果干预 runs
  840 次附加诊断 runs
合计 5,592 runs
至少 234,630 次模型调用
```

最后一项尚不包含所有工具 continuation、重试、预检和附加 baseline 调用，不是成本报价。主要成本之一是统一开启 observe decisions 后，对大量普通观测也调用业务模型。

建议设 `smoke / pilot / full` 三个明确 preset。Pilot 先覆盖机制和关键对照，在一个预算/rung 上估计难度和方差；retention ladder、maintenance/harm/transfer 消融使用预注册子集或单独诊断批次。写入公共观测不必天然等于业务模型思考一次；按公开契约制定统一调度策略，各比较组相同，禁止只在 evaluator 知道的隐藏 trigger 上唤醒。

统一入口可逐步收敛为 `mib run / compare / verify`，旧命令保留 alias。Profile 用少量基础定义加明确参数生成，但每次执行前展开并锁定完整配置，不能牺牲可复现性。发布服务和新增实验维度可暂缓扩展，已有签名与验证功能保留。

## D. 可执行清单

P0 表示在新的正式对外结论之前应完成；P1 为下一轮测量质量改进；P2 为之后的简化。不是生产安全事件等级。验收数量/阈值若需经验确定，先记录 pilot 和预注册规则，不能以观察到的结果反向挑选。

| 完成 | 优先级 / ID | 动作与主要位置 | 验收条件 |
|---|---|---|---|
| [x] | P0-01 | 标量答案使用 typed exact/alias；修改 evaluator 与 generated rubric | 否定、多值、候选池枚举得 0；合法别名通过；withdrawal 全输出扫描保持有效 |
| [x] | P0-02 | 重定依赖门槛；`scoring.py` | 固定题集 joint success；以 Instance 为统计 cluster；A2 的提升 full 正确率反例不再逆转资格；重复数据不伪增独立 n |
| [x] | P0-03 | 准入缺失证据 fail closed；`same_model_calibration.py` | missing/invalid/zero-eligible 对照均为 unassessable，release=false；报告说明缺什么 |
| [x] | P0-04 | 统一 backend 与 core 的 Program/rung 身份及汇总 | 14×3 全执行覆盖率为 1、14 条完整三点曲线；与 core 的同实例聚合相同；删掉必要 rung 时明确失败 |
| [x] | P1-05 | 统一最终注入上下文硬预算；`same_model_agent.py` / backend | 超长单记录、Unicode、序号分隔符都计入；所有有界路线不能超限；无界参考单独标识 |
| [x] | P1-06 | 持久化公开双向对话与 emission 回执 | 跨会话能够查到实际已说/已发内容；重复触发不重复履约；B0 无跨任务日志；隐藏分数不写回 |
| [x] | P1-07 | 在各主要机制交错有效信息和干扰，解除 maintenance/相关性绑定 | 前缀策略在后期修订/新事实挑战集明确失败；完整参考仍正确；保留跨 rung 任务不变性 |
| [x] | P1-08 | 将当前技能 lane 收窄为配方记忆；独立新增抽象/组合迁移题 | family 查表在明确的新特征组合挑战集不足以满分；oracle 仍可确定复核；不强制参与者采用复杂内部架构 |
| [x] | P1-09 | 纵向学习分离安全与正向收益 | always-inspect 基线保留；行为正确、节省调用、漂移损害分别报告；原生审计不冒充学习效果 |
| 部分 | P1-10 | 规范干预估计量和统计单位 | signed paired effects + cluster CI；单侧风险另列；needed content/长度对照明确；JSON 与显示单位一致 |
| [x] | P1-11 | 增加诊断解题参考、同预算最近窗口/检索 baseline；重命名启发式 B3 | 区分任务不可解、读不懂与记忆失败；比较组预算一致或明确为无界参考；不预设 B3 必须赢 |
| [ ] | P1-12 | 小规模真实模型 pilot，再据方差设正式实验 | 保留正负结果、独立实例数、预定义有用效应和停止规则；跨基础模型复核；没有结果前继续 developmental |
| 部分 | P1-13 | 增加独立语义 holdout 与 oracle 审核 | 参数/措辞/机制泛化分开报告；手工真值不调用同一 oracle 推导；公开语法专用策略有挑战集 |
| 部分 | P1-14 | 定义 persistence/withdrawal/prospective 的范围并补边界测试 | 新进程只接回声明持久层；跨 run/tenant 无污染；多承诺/重复触发/取消恢复正确；不宣称物理删除 |
| 部分 | P2-15 | 抽出统一 EpisodePlan、Evidence、aggregation 契约 | core/backend/hidden 的同一输入给相同统计结果；旧报告经版本化 reader 可复核；保留失败分母和不泄漏边界 |
| [x] | P2-16 | Brain native audit 下沉到可选 binding | 通用参与者无需 C-/X- 内部对象或特定 tokenizer；Brain 专用合同测试保留且单独标识 |
| 部分 | P2-17 | 三类默认结果、三档运行 preset、预注册诊断子集 | pilot 有明确 run/call 预算；score/contrast/cost 可独立解读；不按结果决定追加哪些对照 |
| [x] | P2-18 | 收敛 CLI/Profile 文档和版本元数据 | 一个主执行入口；旧命令 alias；展开配置可锁定；规范页反映当前实现/报告版本；默认 pytest 不收集 debug 副本 |

建议顺序：01–04 → 05–07、10–11 → 08–09、12–14 → 15–18。部分 P2 的纯数据契约提取可伴随 04 提前做，但不要让重构阻塞测量修复。没有预先登记的样本量与资源计划，不直接启动默认的完整真实模型配置。

第一轮完成的最低产物：修复版 measurement revision、上述对抗回归、统一汇总对照、一份有已知边界的真实模型 pilot 报告。是否增加维度、上线排名或扩大模型矩阵，应由这些证据决定。


审查、实现与回归验证署名：**OpenAI Codex**，2026-09-23。未使用 subagents。清单中的“部分”或未勾选项目没有被冒充为已完成；具体边界见修复记录。
