# MIB 设计审查与执行清单（第二轮）— 2026-09-23

> 修复状态：本报告记录审查证据；实现为 0.14.0 / measurement 0.5.0。完成项与仍需实测的事项见 [修复记录](../harness/MIB-v0.5-Review-Resolution.md)。文末的第三轮审查在发布前并入了同一测量版本。

审查基线：`08d1afd`，实现 `0.13.0`，measurement `0.4.0`。已通读英文规范、上一轮审查与修复记录，以及生成器、WorldModel、Runner、评分器、聚合与依赖门槛、固定模型 harness 和 Adapter 文档。跳过 `*_CN.md`、`*_cn.md` 和 `docs/cn/`，未使用 subagents。未深审的部分：service、hidden、sandbox、transports 的安全性，longitudinal learning，experimental transfer/reality，以及 v0.1 静态模板。

## 判断

0.4.0 的修复实际生效：精确标量判分、固定机会的联合孪生、缺失证据 fail-closed、Program/rung 身份统一，以及交错历史。基线测试为 **419 passed, 8 skipped**。

剩下的问题不在 bug 层面，而在于**默认运行条件下，测到的大多不是记忆**：

- canonical rung 没有记忆压力；
- 零记忆策略在不同维度拿到 0–79% 的结构性底分；
- 依赖门槛在默认样本量下检验力很低；
- 此外还有两处参与者可见的协议/泄漏问题。

以下数字都来自无模型脚本，直接调用真实的生成器、Runner 和门槛函数；都不是真实模型结果。

## A. 测量有效性

**A1. 默认条件下没有记忆压力。**
- Core Dev 在 canonical rung 1 的可见历史为 187–247 词，最高一档为 829–973 词。
- Pilot 的 rung 20 渲染后完整历史为 2,941–3,934 字符，8192 字符上限在 35 个实例中 0 个触发。
- 结果是：B1 能看到全部历史，B2 和 B3 只是被 `top_k` 截断。这样的实验回答不了"哪种记忆架构更好"。

**A2. 零记忆底分高，且各维度差异很大。**
- 语法策略 Agent 不存任何历史：状态题答 contested，其余题答 unknown，从不发提醒，任务直接结束。
- 它在 Core Dev 上的得分为 withdrawal **60**、prospective **39.2**、epistemic **23.3**，总分 MIB **15.5**；在 `cancelled_commitment` 上为 **79%**。
- 原因有三个：
  - withdrawal 与 cancellation 的 full 条件下，正确行为恰好就是默认行为；
  - 世界状态预置了 `migration_applied=True`；
  - `p-unknown` 的答案恒为 unknown。

**A3. 依赖门槛检验力低，且混同了准确率与依赖。**
- 用真实 `joint_dependence` 模拟（5 seeds，2000 次 bootstrap）：联合成功率 90% 的系统，整个 Profile 的通过率只有 **15%**；95% 时为 **44%**。
- temporal、experience、skill 每个实例只有 1 个孪生机会，错 1 个就使下界降到 0.4。
- 联合成功率约等于准确率的平方，因此这个门槛本质上是准确率门槛。

**A4. 全输出禁用值扫描惩罚"记得历史"。**
- 禁用值随 rung 增长：recall 为 0 → 2.3 → 5.1（共 5.7 个）。
- 当前值答对并附上 "It changed from X to Y." 时，得分为 **0**。

## B. 泄漏与协议

**B1. 评分任务带有可见角色标签。**
- 评分任务的目标文本写的是 `Process item held-out …`，训练任务写的是 `practice-1`。

**B2. 提醒契约自相矛盾。**
- `commitment_id` 从不可见，结构化提醒无法得分。
- Adapter 文档里的示例在 lifecycle 评分下会得 0；标准句式只写在固定模型 prompt 中。
- 同一次提前提醒会被扣两次。

**B3. 公开语法可被利用，验证是循环的。**
- 满分 fixture 用生成器自身的解析器和 WorldModel 作答。
- 隐藏 seed 只能保护答案，保护不了公开语法。

## C. 生成器细节

- **C1. 孪生取值：** `seen` 变量未被使用；temporal 中有 **16.5%** 的孪生是"无变化更新"。
- **C2. 事件顺序：** 交错历史后未重排 WorldModel 的 seq。目前无害，但没有不变量保护。
- **C3. experience 与 skill 构念重合：** 二者本质上都是"family → 随机 hex 配方"查表，合计占 29% 权重。
- **C4. 诊断通道偏弱：** 有害提问固定取 `alternatives[0]`，placebo 用的是 `Perhaps … weather?`。

## D. 简化

- **D1.** 非 canonical rung 的干预运行不进入任何聚合。Core Dev 每 seed 每 rung 有 57 次运行，只在 canonical rung 做干预即可省约 58%。另外，未声明维护能力的 Agent 仍在跑 no-maintenance 运行。
- **D2.** 核心测量代码约 336KB；experimental、service、same-model、v0.1 calibration、learning 合计约 520KB。
- **D3.** 7 个维度、每实例 1–3 题；总分权重未经验证，HMB/IMS/HRS/NMG 等指标分散了头条。

## 可执行清单与完成状态

| 状态 | ID | 动作 | 验收 |
|---|---|---|---|
| [x] | P0-1 | 不透明 item ID，并对可见文本做角色词回归测试 | 全部 Program × seeds × rungs 无角色词 |
| 部分 | P0-2 | `pressure_ratio` 与 preflight；Pilot 改为 ratio ≥ 4；B1 改名 | 在 Track A 实施。Track B 无法强制预算，canonical rung 已标注为短历史 regime |
| [x] | P0-3 | 平衡零记忆底分（条件计分、第二个有效承诺、合取式规则、诊断题零权重） | 语法策略在各维度 ≤ 10（实测为 0）；完整 fixture 仍为 100 |
| [x] | P0-4 | 依赖门槛改用 CFE；检验力回归测试 | p=0.9 时通过率 ≥ 80%（实测 97%）；猜测时 ≤ 5%（实测 0%） |
| [x] | P0-5 | 提醒契约：可见 `commitment_ref`、文档与一致性测试、只扣一次 | 标准句式与正确引用得 1，错误引用得 0 |
| [x] | P1-6 | 全输出扫描只用于撤回值 | 附历史说明得 1；啰嗦 fixture 在各 rung 均为 100 |
| [x] | P1-7 | 孪生取值分层，且跨 rung 一致 | 无变化更新比例 16.5% → 0 |
| 部分 | P1-8 | 私有措辞层钩子、干扰措辞独立随机流、金丝雀测试 | 加与不加措辞层 oracle 不变；公开解析器 1.0 → 0。hidden store 接线、承诺/规则措辞、独立撰写的措辞库和盲审仍待完成 |
| [x] | P1-9 | 按 series 限定适用范围，未来任务为新 family | family 查表失败 |
| 部分 | P1-10 | 增加孪生机会；按 seed 打乱作答顺序 | temporal 1→3，epistemic →3–4，procedural →2；experience 仍为 1 |
| [x] | P1-11 | 匹配的自然 placebo，随机抽取备选值 | 词数一致 |
| 部分 | P2-12 | 只在 canonical rung 做干预；维护对照只在声明维护时运行 | Core Dev 运行数 864 → 377（第三轮平衡 epistemic 分支后），聚合结果相同。合并 relevant 消融未做 |
| [x] | P2-13 | WorldModel 顺序不变量 | 顺序被打乱时报错 |
| 部分 | P2-14 | 核心模块与 experimental 的导入边界 | 边界测试通过；物理拆包未做 |
| 部分 | P2-15 | Capability Card 头条重排，并加入总分敏感性 | 已完成；机会水平校正分数未单列（底分已通过设计降为 0） |

真实模型 pilot（上一轮遗留的 P1-12）仍未运行。它应在本轮的有预算 regime 下运行。

## 第三轮审查（2026-09-24，并入同一测量版本）

对上表实现后的 `d92feec` 再次审查，发现的问题与处理如下。数字仍来自无模型脚本。

| 状态 | ID | 发现 | 处理与验收 |
|---|---|---|---|
| [x] | R3-1 | `evaluate_world_state` 对断言取平均：只在任务内跟着反馈重试、不跨任务存记忆的策略在 experience/skill 各得 **50**（Core MIB 14.5），Mechanism Challenges 的 skill 得 **75**（全禁用项的正确首次提交恰是空配方） | 计分 workflow/feature/product 探针改用 `eval-world-strict`（合取）；全禁用项改为新 family 上的单标志项，孪生覆盖边界后全部项；新增 `RecoverOnlyAgent` 并加入底分测试与验证脚本。实测各维度 0，完整 fixture 仍 100 |
| [x] | R3-2 | 固定模型 harness 的 `full_context` 门槛和 MDI 分母仍用有界 B1（只看最近 24% 历史）；B2 的 top_k=4 只用了预算的 16%（B3 63%），preflight 看不到 | 新增 `unbounded_reference` 基线臂作为 full-context 参考与分母，缺失时门槛不可评估；`memory_pressure` 按臂报告 `selection_capacity_chars`/`budget_binds`，选取容量填不满预算即拒绝；pilot 改为 B2 top-30、B3 24+8 |
| [x] | R3-3 | Track B 的 canonical rung 只有 969–1,495 可见字符，任何模型都装得下，且卡片、README、规范无任何标注 | 实例行记录 `visible_history_chars`，卡片打印范围并注明裸上下文 regime；新增 `MIB-Core-0.2-Horizon-Dev`（100/2,000/10,000，计分 rung 约 9 万字符）；WorldModel 增加活跃行缓存使万级实例秒级生成 |
| [x] | R3-4 | 会话边界只检查 `accepted`，集成 Agent 可以什么都不清 | `session_isolation: "persisted_state"`：Runner 在边界丢弃 Agent 实例，重建后只回灌其返回的字符串（新增 `restore` 操作），报告边界数与持久化字节；Session Profile 启用；tool_call_id 改为全 run 唯一 |
| [x] | R3-5 | epistemic 的裁决分支 `rng.random() < 0.5` 在 Core 的 5 个 seed 全为未裁决 | 改为按 seed 奇偶确定性交替（字符串 seed 用稳定哈希）；每个 Core seed 集合两种分支都出现 |
| [x] | R3-6 | 374 次运行里 71% 只喂诊断 | `measurement_regime.diagnostics: "off"`：Core Dev 377 → 182 次，头条逐位相同 |
| [x] | R3-7 | 一次传输故障即让整个维度不可评估 | `AgentTransportError` 有界重试一次并记录；Agent 的回答从不重试 |
| [x] | R3-8 | 措辞层金丝雀只证明公开解析器归零，写坏的措辞库也会归零 | `validate_bank`：模板必须携带值与属性，`known`/`status` 提示必须含精确答案词；生成时强制校验 |
| [x] | R3-9 | 无提示词值泄漏回归测试 | 全 Program × seed × rung 扫描池值与 oracle 值（枚举答案词除外），无命中 |
| [x] | R3-10 | experience 与 skill 是同一构念、同一 oracle，合计 29% 权重，前者只有 5 个孪生机会 | 合并为 `procedural_memory`（0.20），六个维度：0.17/0.17/0.20/0.20/0.14/0.12；旧 ID 对历史工件仍有效 |

未做：真实模型 pilot 仍未运行；Track B 的两种压力（长历史、强制会话隔离）都还没有在真实集成 Agent 上跑过；措辞库的可读性只做了结构校验；合并 relevant 消融与物理拆包未做。

第三轮审查与实现署名：**Claude Fable 5.1**（Anthropic），2026-09-24。未使用 subagents。

审查、实现与回归验证署名：**Claude Opus 5.5**（Anthropic），2026-09-23。未使用 subagents。标为"部分"的项目没有冒充为已完成，具体边界见修复记录。
