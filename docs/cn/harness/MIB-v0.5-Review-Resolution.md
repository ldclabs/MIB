# 2026-09-23 第二轮设计审查实施台账

实施版本 **0.14.1**，Core 度量版本 **0.5.0**，题库报告 **0.6.0**。Core 开发 Profile 为 **0.5.0**；Mechanism Challenges 和 Brain 产品回归 Profile 以及产品程序为 **0.2.0**（因为共享生成器变更了它们的实例）。场景格式保持为 **0.2**。内存后端报告、纵向度量及内嵌的原生工作流契约保持不变。

本台账落实了[第二轮设计审查](../../reviews/MIB-Design-Review-2026-09-23b.md)。它将工程实现与实证验证严格区分开来。来自度量版本 0.4.0 的报告与示例保留其源/版本标识（`examples/validation/measurement-0.4.0.json` 属于历史记录），不得与 0.5.0 的结果直接对比。上一版本的台账见 [MIB-v0.4-Review-Resolution.md](MIB-v0.4-Review-Resolution.md)。

## 已落实项

| 审查项 | 变更内容 | 验证证据 |
|---|---|---|
| P0-1 可见角色标签 | 工作流目标此前对计分任务标记为 `item held-out`，对获取任务标记为 `practice-1`。项目现在改用不透明的种子/角色键控 ID（`ScenarioBuilder.opaque`），在跨阶梯与跨条件间保持稳定。 | 24 个程序 × 2 个种子 × 3 个阶梯的所有参赛者可见字符串中，无任何字符串匹配角色词汇（held-out、practice、probe、distractor、oracle、placebo、relevant）。 |
| P0-2 记忆压力 | 实例记录 `visible_history_chars`（Core 规范档位为 969–1,495 字符）。同模型预估与报告携带 `memory_pressure`；中位数历史/预算比率低于 `min_memory_pressure` 的有界非冒烟实验在发起任何模型调用前即被拒绝。有界的 B1 被标记为 `most_recent_visible_history_within_budget`。Pilot 调整为 100 个干扰事件和 3,500 字符预算。 | 旧 pilot：8,192 字符预算在 0/35 个实例中生效（历史仅 2,941–3,934 字符）。新 pilot：中位数比率为 4.18，在 35/35 个实例中均实质生效。100,000 字符预算被拒绝；smoke 冒烟测试豁免。 |
| P0-3 零记忆底分 | `conditional_on` 条件计分：撤回探针依赖保留的邻居事实，认知弃权探针依赖修正值，状态探针依赖主张本身。取消承诺程序保留第二个有效承诺。自省准则合规性采用 `eval-action-strict`（复合 `require_all`），移除恒为 true 的世界断言。近触发与重复触发探针权重设为 0。新增公开测试 fixture `GrammarOnlyAgent`。 | 仅语法零记忆策略得分此前为：withdrawal 60，prospective 39.2，epistemic 23.3，cancelled commitment 79%，Core MIB 15.5。修改后：在每个 Core 与 Expanded 维度均为 0；`NoMemoryAgent` 同样为 0。完整测试 fixture 依然得 100 分。 |
| P0-4 依赖门槛 | Profile 以 `content_following_effect`（内容跟随效应，CFE）作为门槛：在每个冻结测试机会上，输出在孪生历史下是否携带孪生值，减去其在原始历史下是否携带该值（结构化答案取值部分）。完整运行记录 `counterfactual_cross`；孪生运行记录 `counterfactual.follows`。分层实例聚类置信下限设为 0.2；`joint_twin_success` 保留作为诊断量。 | 使用发布函数在每个实例 1 个机会、5 个种子、所有七个维度下模拟：90% 跟随率通过 97% 的题库包（0.4 联合门槛在 90% 联合成功率下仅通过 15%）；80% 跟随率通过 71%；70% 跟随率通过 32%；公开候选池猜测通过率为 0%。端到端：完整 fixture 具备 CFE 1 并通过；仅语法 fixture 具备 CFE 0 并失败；篡改存储的 CFE 将被拒绝。 |
| P0-5 提醒契约 | 结构化提醒按接收者与主题匹配；可选的 `commitment_ref` 必须等于该承诺的可见观测 ID；绝不要求评测方的隐藏 ID。Adapter 文档示例更新为计分的规范句式，§32 记录生命周期规则。早熟发射仅被惩罚一次。 | 规范文本、带正确引用的载荷、带错误引用的载荷在前瞻、取消及承诺生命周期程序上分别得 1、1 和 0 分。 |
| P1-6 披露作用域 | 生成评测器使用 `disclosure_scope: "withdrawn"`。Oracle 列出 `withdrawn`（已撤回）值；仅这些值出现在输出任何位置均判定为失败。其他禁用值仅作为答案时判定失败。遗留评测器保留全输出检查。 | 正确当前值附带 "It changed from X to Y" 得 1 分；解释中包含已撤回值则得 0 分。解释中罗列候选池中所有其他值的 fixture 在每个阶梯均得 1 分（此前禁用值集合跨阶梯从 0 增长到 5.7 个中的 5.1 个）。 |
| P1-7 孪生取值 | 未使用的 `seen` 选择被非干扰事件分层取值取代：首先选择未提及的值，其次选择主体血统之外的值。每个枢轴事件对应一个孪生。 | 时序无变化更新孪生比例从 16.5% 降为 0（119 个种子）；孪生值与被替换事件在跨阶梯间保持一致。 |
| P1-8 公开语法 | `generate_instance(..., surface_bank=...)` 接收评测方私有措辞库，用于陈述/提及/撤回模板、提问提示词与程序短语，记录为 `surface_bank_digest`。干扰措辞拥有独立随机流，因此措辞变动无法改变干扰语义。 | 在最长阶梯档位下，所有 24 个程序 × 3 个种子的 Oracle 在带与不带措辞库下完全一致。公开语法 fixture 在 recall、temporal 与 withdrawal 上的得分从 1.0 降至 0.5 以下（实测为 0）。 |
| P1-9 规程适用范围 | 规程适用性将配方作用域限定到可见的不透明系列（series）；未来项目为各系列的新项目族。每个系列具备一个策略孪生。 | “项目族到配方”查表 fixture 在两个未来项目上均失败；完整 fixture 与两个孪生均得 1 分。 |
| P1-10 机会与顺序 | 时序与认知历史探针增加孪生；规程适用性增加两个策略孪生。连续的 respond 探针按种子置换顺序，跨阶梯与跨条件一致；保留动作与发射顺序。 | 跨 24 个种子进行顺序测试。每实例变更探针机会：temporal 1→3，epistemic 2–3→3–4，procedural applicability 1→2（experience 保持为 1）。 |
| P1-11 提问对照 | 被提问的备选项从自身的数据流中抽样；安慰剂为相同发言人、相同字数的自然无关提问。 | 每个 Core 程序与种子字数均严格匹配；移除了 "Perhaps … weather?" 安慰剂。 |
| P2-12 干预调度 | Profile 声明 `intervention_rungs: "canonical"` 与 `maintenance_control: "declared_maintenance_only"`，在公开与隐藏题库执行间共享。 | Core Dev 运行数从 864 次（0.4.0 记录）减少到 377 次（包含更多孪生机会）；Session 从 1,749 减少到 742。仅规范档位调度与全档位调度产出完全相同的得分、维度分、因果指标、依赖性与保持曲线。 |
| P2-13 模型顺序 | `_check_model_order` 拒绝任何受测查询断言候选项与世界模型顺序不符的时间线顺序。 | 顺序被打乱的历史会抛出 `GenerationError`。 |
| P2-14 导入边界 | 核心度量模块惰性导入实验性 Transfer 代码。 | 全新解释器导入 runner、evaluator、scoring、aggregation、dependence、episode、worldmodel、world、generate、benchmark、report、capability 和 validation 时，不加载任何 `experimental` 或 `learning` 模块。 |
| P2-15 头条重排 | 能力卡片现在优先展示各维度得分、依赖性证据、包含等权与留一维度敏感性分析的综合分、以及资源消耗。HMB/IMS/HRS/NMG 等指标收纳在“因果诊断量（不计入头条）”下。 | 卡片展示顺序与敏感性分析测试通过。 |

## 第三轮审查（并入同一修订版本）

发布前对上述修订版本进行的第三轮审查发现了额外的一处零记忆底分、不完整的压力机制以及未标注的裸上下文机制。所有问题均在同一度量修订版本中实现解决，因此 0.5.0 从未以旧行为发布过。

| 审查项 | 变更内容 | 验证证据 |
|---|---|---|
| 任务内恢复底分 | `evaluate_world_state` 对其断言取平均，因此在模拟器纠错反馈后完成的工作流在毫无记忆的情况下也能获得一半分数。计分工作流、特征策略与产品结果现在改用 `eval-world-strict`（`require_all`）。特征策略挑战的全禁用项（其正确首次尝试为空配方，恰好是所有零记忆策略提交的内容）现在改为新项目族上的单标志项，其策略孪生覆盖边界后的所有项。新增公开测试 fixture `RecoverOnlyAgent`。 | 仅恢复策略此前得分：Core 与 Expanded 规程维度 50 分（综合分 14.5），Mechanism Challenges 规程维度 75 分。修改后：处处为 0；完整 fixture 依然得 100 分；该 fixture 已纳入底分测试与验证脚本。 |
| 规程维度合并 | `experience_memory` 与 `skill_learning_transfer` 属于由可见标识符索引、由相同 oracle 评分的相同配方回忆，在每个 Core 题库包中分别仅有 5 个和 10 个孪生机会。二者合并为统一的 `procedural_memory` 维度（权重 0.20；retention 0.17，temporal 0.17，epistemic 0.20，prospective 0.14，withdrawal 0.12）。旧标识符对历史工件依然有效。 | 六个维度；每个 Core 题库包 15 个规程孪生机会；综合分敏感性分析照常报告。 |
| 有界 B1 与发布门槛 | 在 3,500 字符预算下，B1 仅能看到中位数 14,620 字符渲染历史的最近 24%，然而 `full_context` 门槛与记忆区分度分母此前仍使用该臂。现在每当 B1 有界时，引入 `unbounded_reference` 附加基线（无预算的 B1）作为 `full_context`、MDI 与记忆差距闭合度的输入；若缺失该臂，这些门槛判定为无法评估，且公平性检查 `full_context_reference_not_truncated` 取代 B1 截断检查。 | 有界 stub 运行：各程序 `full_context` 等于参考臂得分，MDI 为参考臂减去 B0；缺失该臂时所有卡片标记为无法评估。 |
| 各臂预算实质绑定 | Pilot 的 B2 仅保留 4 条记录（3,500 字符中约 550 字符），B3 保留 16 条（约 2,200 字符）；预检比率无法发现 `top_k` 先于预算达到饱和。`memory_pressure` 现在报告每个臂的 `selection_capacity_chars` 与 `budget_binds`，预检直接拒绝选择容量无法填满预算的臂。Pilot 改为 B2 top-30、B3 24+8。 | 3,500 字符下 `retrieval_top_k: 4` 因选择容量不足而被拒绝；发布的 pilot 顺利通过。 |
| 裸上下文机制标注 | 此前没有任何机制标注 0 / 20 / 100 阶梯中 969–1,495 字符的规范历史。实例行携带 `visible_history_chars`；能力卡片在能力档位标注该范围并带有裸上下文告警。新增 `MIB-Core-0.2-Horizon-Dev`（100 / 2,000 / 10,000；能力档位约 90,000 可见字符，保持档位约 450,000 字符；关闭诊断）。世界模型缓存活跃行，使 10,000 事件实例在数秒内生成而非数分钟。 | 卡片测试；Horizon 生成测试；跨阶梯可接受答案完全一致。 |
| 强制会话隔离执行 | Runner 此前仅检查 `{"accepted": true}`。在 `session_isolation: "persisted_state"` 下，Runner 在每个边界关闭 Agent 实例，新建全新实例，执行 reset 并通过新增的 `restore` 操作仅回灌 `persisted_state` 字符串（stdio 与 HTTP 传输均支持转发），在每轮运行与卡片上记录边界数与持久化字节数。工具调用 ID 现在必须全运行唯一，因为观测 ID 从其推导而来。Session Profile 声明该策略。 | 完整 fixture 持久化其记录并获得 100 分且持久化大小为正；不回传任何状态的 fixture 丧失分数；损坏的 `restore` 使运行失效；缺失 factory 会被直接拒绝。 |
| 认知分支平衡 | `resolved = rng.random() < 0.5` 导致 Core 的所有 5 个种子均未裁决（20 个种子中仅 35% 裁决），因此权威工具裁决分支在 Core 题库包中从未执行过，且 `p-status` 恒定。该分支现改为按种子奇偶性交替（字符串种子采用稳定哈希）。 | 每个 Core 种子集合均包含两种分支（3/5 裁决）。Core Dev 在开启诊断时现运行 377 个条件：每个裁决实例多携带一个相关对照和一个孪生对照。 |
| 仅运行头条调度 | `measurement_regime.diagnostics: "off"` 跳过相关消融、无关消融、危害对照、无维护对照与负迁移对照。 | Core Dev 条件数从 377 降至 182，各维度得分、综合分、CFE 与合格资格完全相同。 |
| 传输故障有界重试 | 单次掉线会导致 100% 覆盖率要求下的整个维度无法评估。`AgentTransportError` 现在有界重试一次（`transport_retries`），并记录在操作遥测与运行警告中；Agent 的答案绝不重试。 | `observe` 上的单次故障保持运行有效并记录一次重试；持续性故障或 `transport_retries=0` 会使运行失效。 |
| 表层措辞库可读性校验 | 金丝雀测试此前仅证明措辞库破坏了公开解析器；但不可读的坏词表同样会破坏它。`validate_bank` 拒绝丢弃了取值或属性的模板、丢弃了精确答案词（`unknown`、`resolved`/`contested`）的提示词、未知类型及不支持的占位槽；`generate_instance` 对每个词表进行强制校验。 | 可读性测试；现有的私有措辞库通过校验。 |
| 提示词取值泄漏回归测试 | 此前无回归覆盖。对每个程序的所有计分 respond 提示词扫描属性候选池与公认答案值（枚举答案词除外）。 | 零命中。 |

## commit 7291876 后续修正（实现版本 0.14.1）

该实现补丁修正了既有 measurement-0.5.0 契约中的四处缺陷。度量、程序、Profile 与报告版本保持不变；报告与实验锁依然绑定可执行源码摘要，因此早期证据需要其原始源码包。

| 发现项 | 修正内容 | 回归验证证据 |
|---|---|---|
| 失败的完整条件从 CFE 覆盖率中消失 | 缺失的每实例指标贡献 0 效应与 0 有效配对，同时在分母中保留每个冻结的测试机会。 | 6 个回忆实例中包含 1 个失败实例，产出 10/12 有效配对并导致覆盖率不达标；重复轮次保留 6 个独立实例。报告核验拒绝篡改后的计数。完全缺失 CFE 证据保持为无法评估。 |
| 协议 Host 未分发 `restore` | `AgentHost` 将状态、运行/请求 ID 及虚拟时间转发给恢复后的 Agent。缺失钩子将被显式报告为不支持。 | HTTP 会话重建保留回忆事实；JSONL 服务器转发精确状态与请求上下文。 |
| 畸形 `persisted_state` 可能产生成功的空运行 | 在确认的生命周期调用内部、记录成功之前校验状态。 | 对象类型的状态记录会话边界失败并使所有计划探针失效（包括已评分探针）；生成的报告通过核验。 |
| 准入参考被排除在公平性检查之外 | 当有界 B1 使用 `unbounded_reference` 时，将其调用纳入标识/错误检查，将其运行纳入生命周期与配对种子/探针检查。未使用的参考保持为诊断项。 | 纯净参考通过；传输、解析、标识、生命周期与种子故障会触发对应的审计检查失败。 |

精简验证记录与同模型 stub 工件已针对 0.14.1 重新生成。这些依然是工程 fixture，而非真实模型证据。

## 复现命令

```bash
PYTHONPATH=src python -m pytest tests -q
python tools/validate-review-20260923.py --output-dir /tmp/mib-review-0.5
python -m mib_runner run examples/same-model/same-model-generated.pilot.json --estimate-only
python -m mib_runner.same_model_cli examples/same-model/same-model-generated.stub.json \
  --output-json /tmp/mib-smoke-0.5.json --report-schema schemas/mib-same-model-report.schema.json
```

本地最终验证（0.14.1）：在 Python 3.14.7/macOS 上 **522 passed, 8 skipped**；跳过的测试需要 Linux 沙箱或评测方私有题库包。验证脚本在 Core、Expanded 和（仅针对 recover-only）Mechanism Challenges 上运行 grammar-only 和 recover-only fixture，若任一 fixture 在任何维度获得超过 10 分或通过依赖门槛则判定失败。其精简记录为 `examples/validation/measurement-0.5.0.json`：完整 fixture 在 Core、Expanded 和 Session 上得分 100 且 CFE 为 1，在 Mechanism Challenges 上得分 100；仅前缀 fixture 得分 63.72 且不具备依赖资格；仅语法与仅恢复 fixture 得分 0 且不具备资格。42 单元 stub 运行包含 `fairness_valid: true` 和 `release_eligible: false`，属于无界参考机制。这些均不是真实模型证据。

Pilot 当前预估在相同排除规则下执行 **482 次条件运行**和**至少 1,927 次业务模型调用**；已包含无界参考臂。

## 待完成及后续实证工作

- **真实固定模型先导实验（遗留项）：** 尚未运行。它应当在上述有预算机制下运行；无界外部配置仍属于历史信息使用参考，而非架构比较。
- **Track B 记忆压力：** Runner 无法限制集成 Agent 的上下文。Core 规范档位属于裸上下文机制，能力卡片现已结合可见历史大小予以明确说明；`Horizon-Dev` 与强制会话隔离是 Runner 能够施加的两种压力，二者均不能识别具体机制。尚无集成 Agent 在这两种机制下运行过。
- **私有措辞库部署：** 措辞库钩子已就绪，但隐藏存储清单尚未携带措辞库；承诺、准则和任务简要的措辞尚未覆盖；仍需要独立编写的措辞库、真实模型的公开/私有对照以及双盲语义 Oracle 审查。
- **微弱依赖性：** 依然无法在 5 个种子下确立（70% 跟随率仅通过约三分之一的题库包）；合并后的规程维度在每个实例具备 3 个孪生机会，但正式样本量必须来自预先登记的 pilot。
- **机会水平校正报告：** 程序经过重新设计，使零记忆底分直接为 0 而非报告并减去。在某些探针中，候选池猜测仍具有微小的正期望得分；Track A 报告了 B0，Track B 尚无实测底分。
- **合并相关消融**（每实例运行一次“扣留全部支持”）与遗留/实验代码的**物理拆包**尚未实施；目前仅强制执行了导入边界，且 `diagnostics: "off"` 在不需要的地方移除了各项对照。
- **表层措辞库可读性**仅做了结构校验；真实模型阅读独立编写的措辞库是否与公开语法一样顺畅，仍是一个实证问题。

审查、实现与回归验证署名：**Claude Opus 5.5**（Anthropic），2026-09-23；第三轮审查及其实现署名：**Claude Fable 5.1**（Anthropic），2026-09-24。未使用子智能体（subagents）。
