# MIB 迁移智能（Transfer Intelligence）

## 形成、路由、采纳与迁移距离

[ [English](../../experimental/MIB-Transfer-Intelligence.md) | 简体中文 ]

**版本：** 0.1-draft  
**状态：** 诊断性扩展 / `MIB-Specification.md` 配套规范

---

# 0. 规范目标

MIB-Core 核心基准回答了一个核心问题：

> 过去经历中的哪些部分正确参与了未来的认知与行为计算？

它以行为主义的方式给出了极高质量的回答。但它自身无法直接回答的是：一次迁移为何会失败？一个在相关记忆消融下性能下降的技能场景（Skill Scenario）可以确证记忆切实起到了作用。但它无法分辨系统究竟是没有编译出可用的操作流程、编译了却未能检索召回、还是成功召回了正确的技能却无法成功执行。

本文档定义了解构上述不同情形的诊断层：

```text
经历（Experience）
    ↓
形成（Formation）
    ↓
持久化记忆 / 技能（Persistent Memory / Skill）
    ↓
路由（Routing）
    ↓
适用性（Applicability）
    ↓
采纳（Uptake）
    ↓
未来行为（Future Behavior）
```

本文档中的所有内容均属于**补充诊断量（supplemental diagnostics）**。本文档定义的任何指标均不进入 MIB 综合分、因果得分、覆盖率，亦不进入模板或维度的聚合分值。对于模板未携带迁移支持标注（Transfer Support Annotation）的数据包，其生成的报告与本扩展引入前生成的报告逐字节完全一致。

---

# 1. 核心不可变原则

## 1.1 记忆始终作为唯一的干预变量

该扩展提升了诊断的分辨率。它**严禁（MUST NOT）**将 MIB 变成通用的自我进化或智能体综合性能基准。此处定义的每一个诊断单元，均只改变记忆状态，并严格控制其他所有变量保持不变。

## 1.2 评分完全兼容

引入该扩展**严禁（MUST NOT）**改变原有的 `MIB-Core-0.1` 得分。针对未修改的报告，其模板聚合、维度聚合、MIB 综合分、因果得分、覆盖率、Bootstrap 置信区间以及 `verify-score` 验证结果必须保持完全一致。

除非未来的 Profile 明确主动声明纳入，否则任何迁移指标均不进入官方基准得分。

## 1.3 架构中立性

本文档不预设记忆必须是向量数据库、图数据库、对话历史存储、技能文件还是检索系统。编译出的策略、演化出的提示指令、工作流补丁或内部持久化状态均属合格范畴。功能性判定准则保持不变：

> 只要过去的经历所产生的持久化状态参与了未来的计算，它就属于记忆。

## 1.4 缺失证据绝非负面证据

当某个评测单元不可用，或 Oracle 上限缺乏足够的提升空间（headroom）时，受影响的比率指标报告为 `eligible: false` 并附带具体原因。它**绝不（never）**报告为 `0`。

## 1.5 黑盒评测依然作为一等公民

四个诊断单元中的三个均可在普通的黑盒 Agent 上直接运行。仅有一个单元需要 Memory Adapter 接口支持，而官方 Track B 评测路径绝不强制要求使用该接口。

## 1.6 隐藏评测知识绝不透露给 Agent

能力（Ability）标识符、支撑事件 ID、Oracle 适用性判定、迁移关系类型、反例关系、Oracle 路由以及距离等级纯属评测方机密。它们**严禁（MUST NOT）**出现在 `ResetRequest`、`ObserveRequest`、`RespondRequest`、`ActRequest`、工具调用结果、参赛者可见的提交元数据、公开报告或排行榜响应中。

---

# 2. 核心术语定义

## 经历（Experience）

一条情境化的因果轨迹：

```text
目标（goal） → 动作（action） → 观察（observation） → 反馈（feedback） → 结果（outcome）
```

## 能力（Ability）

由评测方定义、潜在贯穿于一次或多次经历中的可复用胜任力。Ability 属于**基准标注（benchmark annotation）**，并非对 Agent 内部表征结构的先验假设。

## 技能（Skill）

基于经历形成的持久化、可复用策略或操作规程。Agent 可以自由选择其内部表示形态。

不要将 `Ability == Skill` 混为一谈。Ability 属于评测方的概念本体；Skill 属于 Agent 的记忆内部状态。MIB 关心的是未来的行为是否体现出了该能力，而非内部表示是否与评测方的措辞匹配。

## 形成（Formation）

从过往经历转化为持久化、可复用记忆状态的过程。

## 路由（Routing）

针对当前未来任务，选择并分发相关记忆状态的过程。

## 采纳（Uptake）

Agent 在行为决策中成功运用所分发的相关记忆的过程。

## 迁移（Transfer）

由过往推导出的可复用能力所引起的未来行为改善。

## 适用性边界（Applicability Boundary）

一项技能应当主导行为、以及不应当主导行为的条件边界。

## 迁移支持（Transfer Support）

评测方的一项断言：特定过往经历所包含的信息，足以通过一项或多项能力支撑特定的未来探针。

---

# 3. 迁移支持标注规范

## 3.1 承载形式

标注信息存放在场景定义的 `extensions` 扩展字段下：

```text
mib.transfer_support.v1
```

它不是 v0.1 场景的顶层字段。所有既有的场景文件依然有效，现有的 v0.1 解析器可以直接忽略它，隐藏数据包可以渐进式采纳。在未来的数据格式版本中，它可能会被提升为一等字段。

其具体数据形态由 `schemas/mib-transfer-support.schema.json` 严格定义。

## 3.2 数据结构

```text
过往事件（Past Events）
    ↓ 支持（support）
能力（Ability）
    ↓ 适用于（applies_to）
未来探针（Future Probe）

反例事件（Counterexamples）
    ↓ 修正/细化（refine）
适用性边界（Applicability Boundary）
```

```json
{
  "version": "1.0.0",
  "abilities": [
    {
      "id": "ability.class_a7_scoped_commit",
      "kind": "procedure",
      "support_event_ids": ["e-failure", "e-rule"],
      "counterexample_event_ids": ["e-counterexample"],
      "applicability": {
        "positive_cues": ["class=A7"],
        "negative_cues": ["class=G2"]
      },
      "oracle_artifact": {
        "artifact_type": "skill",
        "content": "当项目标记为 Class A7 时，在编辑和提交前必须先激活其匹配的上下文。"
      }
    }
  ],
  "probe_relations": [
    {
      "probe_id": "p-match",
      "ability_ids": ["ability.class_a7_scoped_commit"],
      "relation": "exact_replay",
      "support_expected": true,
      "transfer_distance": {"class": "D0", "normalized": 0.0}
    }
  ]
}
```

## 3.3 事件引用语义

`support_event_ids` 和 `counterexample_event_ids` **必须（MUST）**引用场景时间线中的事件 ID，且每个被引用的事件**必须（MUST）**真实存在。

一项能力**可以（MAY）**需要多个事件联合支撑，因为因果信息集并不等同于单一记忆记录。一次失败、一次诊断与一次恢复，可能共同编码了一项可复用的能力。

## 3.4 冗余支持

当两个独立的经历各自均编码了相同能力时，仅消融其中一个可能不会导致性能下降。此时需显式声明冗余集：

```json
{
  "causal_information_sets": [["e-a1", "e-a2"], ["e-b1", "e-b2"]],
  "minimum_sets_required": 1
}
```

如果基线条件依然留存了有效的支持集，则该基线无效。诊断运行环境会同时扣留所声明的*全部*支持集。

## 3.5 迁移支持与因果消融的关系

二者密切相关但并不等同：

```text
迁移标注     这些事件支撑了该项能力
因果消融     移除该信息集并观察系统行为
```

一个设计优良的技能场景通常会将二者对齐——`support_event_ids` 通常恰好对应相关记忆消融的目标——但冗余支持和负向对照会打破这种对齐，因此二者分别独立声明。

## 3.6 公开与私密边界

对于公开 Dev 内容，能力 ID 和通用关系类型**可以（MAY）**公开；精确的适用性判定断言、支撑事件因果集合与 Oracle 路由策略**可以（MAY）**仅保留在评测内部文件中。

对于隐藏评测（Hidden Eval）和私有保留集（Private Holdout），完整的标注信息纯属评测方私密。公开报告仅可暴露聚合指标：距离等级聚合分、受支持迁移聚合分、拟真抵抗聚合分以及形成/路由/采纳聚合分。公开报告**严禁（MUST NEVER）**暴露标准的私有能力 ID、支撑事件 ID、隐藏适用线索或私有任务图谱。

---

# 4. 迁移关系分类体系

`relation` 字段用于定性描述支撑关系的类型。它与迁移距离**并非**同一概念。

| 关系类型 | 核心含义 | 评测目标 |
|---|---|---|
| `exact_replay` | 相同的底层任务，相同的能力应用 | 程序性记忆召回下限 |
| `surface_shift` | 实体、措辞或工具名称不同；底层能力一致 | 超越字面词汇匹配的抽象能力 |
| `structural_transfer` | 任务结构或业务领域不同；相同的底层操作流程 | 更远距离的正向迁移 |
| `compositional_transfer` | 必须组合两项或更多先前学得的能力 | 组合式迁移能力 |
| `supported_transfer` | 通用正向迁移；距离单独声明 | — |
| `near_match_non_applicable` | 表面相似度高，但适用条件不满足 | 负迁移抵御能力（适用边界识别） |
| `unsupported_novel` | 没有任何可用的已知能力支持 | 克制盲从、认识谦逊（审慎弃权） |
| `stale_support` | 曾经有效，但已被当前客观世界状态作废 | 时序记忆与技能的交互作用 |
| `harmful_support` | 记忆中包含了误导性或错误的操作规程 | 记忆危害抵御能力 |

---

# 5. 迁移距离（Transfer Distance）

**仅针对受支持的正向迁移（supported positive transfer）**划分阶梯：

```text
D0  精确复现（exact_replay）            0.00
D1  表层偏移（surface_shift）           0.33
D2  结构迁移（structural_transfer）     0.67
D3  组合迁移（compositional_transfer）  1.00
```

设计上刻意不为拟真不适用设立 `D4`，也不为未支持场景设立 `D5`。那些情况并不属于更远距离的正向迁移；它们属于不同类别的因果对照组，将其强行折算到同一轴线上，会导致“迁移能力差”与“正确克制未迁移”混淆为同一个数值。

负向对照组**严禁（MUST NOT）**声明 `transfer_distance`。校验器将严格拒绝此类配置。

由上述各阶梯构成的能力曲线称为**迁移画像（Transfer Profile）**：

```text
D0  ███████████
D1  █████████
D2  ███████
D3  ████
```

该画像与 MIB 综合分并列报告，绝不混入主分之中。

---

# 6. 2×2 诊断矩阵

包含内容形成（Content Formation）与路由（Routing）两个正交维度，各自分为自动（Automatic）与真值（Oracle）：

```text
                    路由（ROUTING）
                自动（Automatic）  真值（Oracle）

内容     自动         AA              AO
（CONTENT）
        真值         OA              OO
```

`AA`
: 普通的 `full` 完整条件。代表系统在实际部署中的真实行为表现。

`AO`
: 自动形成内容，真值辅助路由。检验在路由完全理想的前提下，系统能否沉淀出有用的记忆内容？

`OA`
: 真值标准内容，自动自主路由。检验在内容质量完全理想的前提下，路由环节是否构成瓶颈？

`OO`
: 真值标准内容，真值辅助路由。代表**采纳上限（uptake ceiling）**，并非实际部署方法。

## 6.1 矩阵单元构建

```text
B   支撑经历被移除，不额外提供任何补充
AA  支撑经历正常存在，不额外提供任何补充
AO  支撑经历正常存在，在任务执行时刻将系统自身形成的
    最佳匹配记忆产物推送给系统             （需 Memory Adapter 支持）
OA  支撑经历被移除，将标准的真值产物放置在原经历所处的
    过往信息流中                           （兼容黑盒 Agent）
OO  支撑经历被移除，在任务执行时刻将标准的真值产物直接
    推送给系统                             （兼容黑盒 Agent）
```

`OA` 和 `OO` 均承载标准真值内容，唯一区别在于其**何时**对系统可见，从而精确隔离出路由（Routing）能力。`AA` 和 `AO` 均承载系统自发形成的内容，唯一区别在于路由机制，从而精确隔离出形成（Formation）能力。

标准真值内容**取代（replaces）**其所代表的经历。若原有的自然支撑经历依然保留，则 `OA` 测量的将是“自然记忆 + 额外提示”，而非纯粹的路由能力。

## 6.2 路由代表推送，而非直接提供答案

推送的记忆产物通过普通的观察信道投递，前缀采用记忆系统唤回技能的常规呈现方式：

```text
从先前工作中唤回的可复用规程: <产物内容>
```

对所有系统采用统一的信道接口，确保黑盒 Agent 与可解构 Agent 之间的测试单元保持严格配对。

## 6.3 配对原则

每个单元**必须（MUST）**保持完全一致：

```text
相同的场景实例（Scenario Instance）
相同的重复测试编号（repetition）
相同的未来探针（future Probe）
相同的未来客观世界状态（future world）
在支持的情况下保持相同的 Agent 种子
```

诊断运行记录保存在独立的列表中，**严禁**合并入 `results.runs`。将其合并会干扰条件得分、因果配对集合以及执行次数统计，补充性诊断量绝不可产生此类副作用。

---

# 7. 真值技能产物（Oracle Skill Artifacts）规范

真值技能产物**必须（MUST）**满足：

```text
陈述一条可复用的操作规程
在适度的抽象层级上陈述其触发条件
避免泄露任务特有的隐藏答案
避免泄露隐藏测试实体的具体取值
避免透露评测校验器的内部机制
避免透露未来探针的具体措辞
```

良好范例：

```text
"当项目标记为 Class A7 时，在编辑和提交前必须先激活其匹配的上下文。"
```

错误反例：

```text
"针对明天要处理的项目 Q-391，调用 workspace.select('west') 并回答 42。"
```

校验器严格把关：若真值产物复述了探针的可接受值、世界状态断言值或隐藏真实基准文本，将直接判定为严重错误。

真值路由意味着评测方帮 Agent 选出了标注中为该探针声明的能力；它绝不意味着直接将答案、隐藏世界状态或评测判定结果馈赠给 Agent。

---

# 8. Memory Adapter 适配器接口

仅有 `AO` 单元需要深入介入记忆系统内部。可选的 Memory Adapter 接口（`src/mib_runner/memory_adapter.py`）暴露如下方法：

```text
describe_memory
reset_memory
observe_memory_event
consolidate_memory
export_artifacts
retrieve_artifacts
inject_artifacts
```

任何方法均不得强制要求暴露思维链（chain of thought），黑盒提交亦无需实现该接口中的任何方法。

导出产物上的 `metadata.source_event_ids` 仅用于辅助诊断。该字段由参赛系统自行上报，**严禁（MUST NOT）**作为评分或真值路由的事实依据。评测方通过将导出产物与自身对该能力的权威描述进行语义匹配来筛选产物；系统自称的溯源仅用于打破平局。因此，参赛系统无法通过给无用产物虚假标注正确事件 ID 来在 `AO` 单元中蒙混过关。

---

# 9. 诊断指标定义

设：

```text
B  = 移除记忆后的基线得分（memory-removed baseline）
AA = 自然完整条件下的得分（natural automatic score）
AO = 自动形成内容 + 真值辅助路由得分
OA = 真值标准内容 + 自动自主路由得分
OO = 真值标准内容 + 真值辅助路由得分
```

## 9.1 自然迁移收益（Natural Transfer Gain）

```text
NTG = AA - B
```

带符号指标。正值代表有益迁移；负值代表有害负演化。绝不要取绝对值：负向收益本身就是关键发现，而非微小的正数。

## 9.2 形成效率（Formation Efficiency）

```text
FE = (AO - B) / (OO - B)
```

## 9.3 路由效率（Routing Efficiency）

```text
RE = (OA - B) / (OO - B)
```

## 9.4 自然迁移效率（Natural Transfer Efficiency）

```text
NTE = (AA - B) / (OO - B)
```

## 9.5 指标有效资格（Eligibility）

上述三项比率指标仅在满足以下条件时具备计算资格：

```text
OO - B > ε        （默认 ε = 0.05）
```

若低于该阈值，分母将纯属噪声扰动。此时指标将报告为：

```json
{"value": null, "eligible": false, "reason": "insufficient_oracle_headroom",
 "numerator": 0.0, "denominator": 0.02, "epsilon": 0.05}
```

原始计算值低于 0 或高于 1 具有科学意义，予以如实保留；仅在展示层面进行合理裁剪。

## 9.6 采纳能力（Uptake）

设计上刻意不定义归一化的“采纳效率”，因为该指标缺乏严谨的理论上限。报告采用：

```text
Oracle 路由得分（Oracle Routed Score） = OO
Oracle 路由收益（Oracle Routed Gain）  = OO - B
```

若场景校准表明真值技能应当能带来接近完美的成功率，则偏低的 `OO` 意味着要么 Agent 无法有效执行理想技能，要么该场景实际上并未得到该技能的有效支撑。基准校准必须厘清这两种情况。

## 9.7 损失分解（Loss decomposition）

```text
形成损失（Formation Loss） = OO - AO
路由损失（Routing Loss）   = OO - OA
部署缺口（Deployment Gap） = OO - AA
```

以上属于展示性诊断量。由于形成与路由之间存在交互作用，该分解**并非**严格可加。报告通过交互残差（interaction residual）显式呈现这一点：

```text
交互残差（Interaction Residual） = (OO - AA) - ((OO - AO) + (OO - OA))
```

## 9.8 对照组指标

```text
受支持迁移成功率（Supported Transfer Success Rate）   正向迁移探针上的平均 AA 得分
拟真抵抗度（Near-Match Resistance）                   拟真非适用探针上的平均 AA 得分
未支持记忆中立度（Unsupported-Memory Neutrality）     未支持探针上的 1 - |AA - B|
组合迁移得分（Compositional Transfer Score）          组合迁移探针上的平均 AA 得分
负迁移率（Negative Transfer Rate）                    标注探针中出现 AA < B 的比例
```

拟真抵抗度是一项**结果性**衡量，并不等同于适用性精确率。答对并不证明系统成功克制了记忆的提取。仅当场景或可解构适配器提供了直接可观测的记忆应用证据时，方可计算适用性精确率（Precision）与召回率（Recall）。

`Negative Transfer Rate` 是该诊断层的专用命名。它不是 `MIB-Specification.md` 中定义的具有更严格控制语义的标准化 MIB 因果指标 `negative_transfer`。在迁移诊断中，请使用更明确的表述：拟真危害（Near-Match Harm）、错误能力危害（Wrong-Ability Harm）、未支持记忆偏移（Unsupported Memory Delta）、陈旧技能危害（Stale-Skill Harm）。

## 9.9 效率指标

先前的经历会改变完成任务的代价。MIB 记录以下指标，但不予计分：

```text
工具调用次数差异（tool call delta）
端到端延迟差异（latency delta）
```

两者均在探针级别进行成对统计，因为消融可能仅覆盖场景探针的子集，运行层面的总和会比较不同负载的工作量。

---

# 10. 指标聚合机制

聚合在整个流程中始终遵循“模板优先（Template-first）”：

```text
重复测试（Repetition）
    ↓
场景实例（Scenario Instance）
    ↓
模板（Template）
    ↓
迁移关系 / 距离等级
```

包含众多生成实例的模板绝不会因此获得更高的语义权重，包含四个 D2 探针的模板也绝不会压倒只有一个 D2 探针的模板。

置信区间采用模板级别的 Bootstrap 重采样；模板作为基本重采样单元，契合 MIB 核心聚合的分层抽样哲学。开发测试运行可使用较少的重采样次数；正式官方运行应当采用 10,000 次。

---

# 11. 报告与能力卡片呈现

诊断信息作为报告扩展项 `mib.transfer_diagnostics.v1` 承载。对于 `scope=public` 的公开报告，其主体内容缩减为混淆别名与聚合统计：每个探针的具体标识、具体关系类型以及能力图谱保持私密，否则频繁提交排行榜将演变为对 Oracle 的逆向探测通道。

能力卡片增加了两个可选展示区块，仅在存在诊断数据时渲染：

```text
Transfer Diagnostics
  Natural Transfer Gain  +18.4 pp
  Formation Efficiency     81.0
  Routing Efficiency       64.0
  Oracle-Routed Score      92.0
  Negative Transfer Rate    9.8%

Transfer Profile
  D0 Exact Replay          91.0
  D1 Surface Shift         82.0
  D2 Structural            69.0
  D3 Compositional         51.0
  Near-Match Resistance    76.0
  Unsupported Neutrality   94.0
```

缺失的指标项予以省略，绝不显示为零。

---

# 12. 诊断的可识别性验证

只有当已知的失败模式能够准确产生其所声称的指标特征时，该诊断才具备报告价值。`src/mib_runner/agents/transfer_fixtures.py` 中的参考规则 Agent 专门用于证明这一特性：

| 规则 Agent | AA 表现 | AO 表现 | OA 表现 | OO 表现 | 特征签名 |
|---|---|---|---|---|---|
| Perfect（完美系统） | 高 | 高 | 高 | 高 | FE≈1, RE≈1 |
| BadFormation（形成不良） | 低 | 低 | 高 | 高 | FE≈0, RE≈1 |
| BadRouting（路由不良） | 低 | 高 | 低 | 高 | FE≈1, RE≈0 |
| NoTransfer（无迁移） | 低 | 低 | 低 | 高 | FE≈0, RE≈0 |
| BadUptake（采纳不良） | 低 | 低 | 低 | 低 | OO 低，比率无资格 |
| OverTransfer（过度泛化） | 高 | — | — | — | 迁移优秀，边界失守 |

它们是检验管道的规则 Agent，而非性能基准线。它们不构成对任何真实记忆系统的性能断言。

---

# 13. 基准校准准则

迁移校准增加了额外的准入门槛。它**并不能**替代 FC、NM、MDI 或因果敏感度，后者依然是首要的结构化准入门槛。

```text
oracle_artifact_declared    每个正向探针均配置了真值产物
oracle_skill_solvable       OO ≥ 阈值，且 OO - B ≥ 最小有效提升幅度
unsupported_memory_neutral  未支持探针上的 |AA - B| 在容差范围之内
near_match_trap_fires       过度泛化的规则 Agent 确实会触发并落入陷阱
```

准入门槛取决于**真值能力边界**。评测人员标注的能力并不因其听起来合理就天然有效：若真值技能在真值路由下仍无法改善目标探针的表现，说明该能力边缺乏实证支撑，该模板绝不可作为正向迁移案例入选。

若校准基线显示出零自然迁移，该情况记录为*关于该基线的评注*，而非模板本身的缺陷。参考的 B0–B3 规则 Agent 是确定性的关键词匹配智能体；它们无法跨越 D1 表层偏移是关于其自身的测试发现，而这恰恰是迁移画像的设计初衷所在。

---

# 14. 场景编写自检清单

在编写迁移支持标注之前，作者必须能够清晰回答以下问题：

```text
1. 应当习得哪项可复用的能力（Ability）？
2. 哪些过往事件共同支撑了该项能力？
3. 该能力的适用性边界是什么？
4. 哪个未来探针预期会发生迁移？
5. 未来的支撑关系是复现、表层偏移、结构迁移、组合迁移、拟真不适用还是未支持？
6. 哪项消融能够彻底剥离完整的因果信息集？
7. 提供的真值技能产物是否安全，且绝不泄露答案？
```

若无法清晰回答上述问题，切勿强行创建标注。

---

# 15. 工具链命令

```bash
# 校验场景及其包含的迁移标注
mib validate scenario.json   --schema schemas/mib-scenario.schema.json   --transfer-support-schema schemas/mib-transfer-support.schema.json   --require-transfer-annotations

# 检查单个标注的结构（评测方内部：将打印 Ability ID）
mib inspect-transfer scenario.json   --transfer-support-schema schemas/mib-transfer-support.schema.json

# 运行行为层面的迁移诊断
mib benchmark scenarios/transfer   --profile profiles/MIB-Transfer-0.1-Dev.json   --schema schemas/mib-scenario.schema.json

# 补充运行 AA/AO/OA/OO 诊断矩阵单元
mib benchmark scenarios/transfer   --profile profiles/MIB-Transfer-0.1-Dev.json   --schema schemas/mib-scenario.schema.json   --transfer-diagnostics
```

迁移诊断 Dev 数据包位于 `scenarios/transfer/`，而非 `scenarios/dev/` 之下。Runner 会递归遍历数据包根目录，若将其放置在公开 Dev 目录下，将无意中扩大 `MIB-Core-0.1-Dev-M3` 的规模并改变其得分。评分的向后兼容性优先级高于目录布局的整齐度。

---

# 16. 与 MIB-Core 及 MIB-R 的关系定位

```text
MIB-Core
    确立因果有效性（causal validity）

迁移诊断（Transfer Diagnostics）
    阐明深层内在机制（explains mechanism）

MIB-R
    确立生态现实效度（ecological validity）
```

切勿混淆这三个层次。详见 `MIB-R-Reality-Track.md`。
