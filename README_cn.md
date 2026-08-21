# MIB —— 记忆智能基准（Memory Intelligence Benchmark）

[ [English](README.md) | 简体中文 ]

> **MIB 评测的不是智能体记住了多少，而是它能否智能地运用记忆。**

**Memory Intelligence Benchmark (MIB)** 是一项开放评测基准，用于衡量智能系统利用过往经验提升未来认知与行为决策的有效性。

绝大多数记忆评测关注的是：

> *系统能否从过往检索出某条信息？*

MIB 关注一个更深层的问题：

> **过往经历中正确的部分，是否以正确的方式改变了未来的决策？**

这不仅包括记忆事实，还包括追踪状态演变、保留不确定性与证据来源、从失败经验中吸取教训、技能迁移、抵御陈旧或有害记忆的干扰，并证明记忆对后续行为产生了可测量的因果影响。

---

## 为什么需要 MIB

MIB 诞生于对**知识、经验与记忆**三者关系的深入探索。

一个清晰的逻辑起点是：

> **知识是经验规律的压缩。**

知识告诉我们通常什么是事实。

但智能系统面对的不仅是静态事实。它需要采取行动、观察结果、经历失败、排查恢复、修正预期，并习得操作流程。

由此引出第二层界定：

> **经验不仅是发生过的事实，而是一条贯穿目标、动作、观测、反馈与结果的情境化因果轨迹。**

当系统通过重复经验，在全新但相关的场景中改变了行动策略时，就实现了质的飞跃：

> **技能是编译为决策策略的经验。**

这自然导向了一个更本质的问题：

> **究竟什么是记忆？**

记忆不只是被存储的文本；
不只是向量数据库；
也不只是一长串对话历史。

对于智能系统而言：

> **记忆是过往经验参与未来计算的机制。**

这一理念构成了 **[KIP v2 (Knowledge Interaction Protocol)](https://github.com/ldclabs/kip)** 的核心设计——一个面向持久化认知的协议模型，它明确区分了命题与信念、证据与权威、置信度与记忆强度、当前事实与历史事实，以及语义知识与经验技能。

然而，协议并不等同于评测基准。

KIP 规范了*记忆系统应如何表征并治理认知*，但无法衡量该记忆系统的实际效能。

MIB 正是为了填补这一空白而生。

```text
知识（Knowledge）
    ↓
经验规律的压缩
    ↓
经验（Experience）
    ↓
目标 → 动作 → 观测 → 反馈 → 结果
    ↓
技能（Skill）
    ↓
编译为可复用决策策略的经验
    ↓
记忆（Memory）
    ↓
让过往经验参与未来计算的机制
    ↓
KIP v2
    ↓
持久化认知的协议模型
    ↓
MIB
    ↓
衡量记忆智能水平的评测基准
```

MIB 具有**架构中立性**。参评系统无需实现 KIP 协议即可接入评测。

---

## 核心原则

评估记忆系统的优劣，不能单看它能检索出多少过往内容。

评判的核心标准在于：

```text
恰当的记忆
    在恰当的时机出现
        得到恰当的解读
            并切实改进了未来的正确决策
```

这彻底改变了评测的着眼点，从传统的：

```text
过往信息
  ↓
存储
  ↓
检索
  ↓
回答问题
```

转变为面向完整认知周期的：

```text
过往经验
      ↓
记忆形成
      ↓
记忆状态
      ↓
巩固 / 修正
      ↓
回忆检索
      ↓
未来决策
      ↓
行动执行
      ↓
环境产出
      ↺
```

因此，MIB 评估的对象不仅是一个检索器，而是**将智能体与记忆系统作为一个跨时序认知系统整体进行评测**。

---

## MIB 评测维度

MIB-Core v0.1 覆盖六大核心维度：

| 评测维度                                        | 核心考量                                                                                                 |
| :---------------------------------------------- | :------------------------------------------------------------------------------------------------------- |
| **保留与检索（Retention & Retrieval）**         | 能否在间接线索或噪声干扰下，准确检索到相关的历史信息？                                                   |
| **时序记忆（Temporal Memory）**                 | 能否分清当前状态、历史状态、状态跃迁、认知修正以及陈旧过时信息？                                         |
| **认识状态记忆（Epistemic Memory）**            | 能否准确记住信源（谁在何时说了什么）、保留不确定性、正确处理纠错与矛盾，且不将未提及的信息直接臆断为假？ |
| **经验记忆（Experience Memory）**               | 能否完整保留目标、动作、观测、失败教训、恢复排障与最终产出的结构化过程？                                 |
| **技能学习与迁移（Skill Learning & Transfer）** | 能否将多次经验提炼为可复用的策略，并在不适用的情境下准确识别出*不应迁移*的边界？                         |
| **因果记忆效应（Causal Memory Impact）**        | 能否证明相关记忆确实提升了未来行为表现，且无关、陈旧或有害记忆不会误导系统决策？                         |

后续 Profile 将逐步引入以下能力的评测：

```text
选择性遗忘（Selective Forgetting）
前瞻记忆（Prospective Memory）
自省/自我认知记忆（Self Memory）
多智能体协同记忆（Cross-Agent Memory）
多模态记忆（Multimodal Memory）
```

---

## 记忆必须产生因果效应

MIB 认为检索指标固然有用，但不足以衡量智能。

基准的核心评测范式是**配对干预（Paired Intervention）**：

```text
完整记忆条件（Full Memory）
    vs
相关记忆消融条件（Relevant Memory Ablated）
```

如果某条记忆确实发挥了关键作用，那么移除该记忆后，系统表现必然下降。

MIB 同时测试相反的情形：

```text
完整记忆条件（Full Memory）
    vs
无关记忆消融条件（Irrelevant Memory Ablated）
```

剔除无关的历史噪音后，系统的性能表现应保持基本稳定。

对于陈旧或有害记忆：

```text
纯净 / 当前状态条件（Clean / Current Condition）
    vs
有害或陈旧记忆条件（Harmful or Stale Memory Condition）
```

优秀的记忆系统应当具备免疫能力，抵御由有害或过时记忆引起的决策偏差。

基于上述干预，MIB 衍生出一套因果度量指标：

```text
记忆收益（Memory Benefit）
净空间归一化记忆收益（Headroom-Normalized Memory Benefit, HMB）
无关记忆稳定性（Irrelevant Memory Stability, IMS）
记忆损害（Memory Harm）
损害抵抗力（Harm Resistance）
净记忆增益（Net Memory Gain）
```

另有两项因果指标**已在规范中定义，但 v0.1 尚未实现**：

```text
负迁移（Negative Transfer）
错误重现率（Error Recurrence）
```

`docs/MIB-Scoring.md` 对二者均有定义，Scenario schema 也已接受这两个指标名，但 v0.1 参考 Runner
并不产出它们。通用的反例（counterexample）消融只能体现适用边界敏感性，因此**刻意不**被report
为负迁移——它不是评分模型所定义的标准化对照。请不要在 v0.1 报告中期待这两个值。

榜单主分数 **MIB Score** 衡量系统在记忆赋能下的绝对能力。因果指标会作为独立诊断维度并列输出，而不是混杂在单一分数中失去解释性。

---

## MIB 不只是长上下文问答

即使系统在检索任务上得分很高，在记忆智能上也可能完全不及格。

例如：

```text
“我住在 UTC+8 时区。”

（一段时间后……）

“我搬家了，现在使用 UTC+1 时区。”
```

具备实用价值的记忆系统应当明确：

```text
当前时区   → UTC+1
历史时区   → UTC+8
```

而不是简单粗暴地将历史记录直接覆盖。

再如：

```text
“设备序列号是 AX-19。”

“更正一下：刚才说错了，实际是 AX-91。”
```

这种认识上的更正，与现实世界的状态演变有着本质不同：

```text
“我们之前的办公室在蓝色副楼。”

“我们搬家了，现在搬到了绿色副楼。”
```

前者属于认识层面的纠错，后者属于现实世界的状态跃迁。

MIB 的设计正是为了在评测中让这些细微但关键的认知差异可被明确观测。

---

## 重视经验与技能积累

MIB 会评测智能体能否在实际行动中总结教训。

典型的经验评测场景如下：

```text
设定目标
  ↓
执行动作
  ↓
遭遇非预期失败
  ↓
观测报错
  ↓
诊断归因
  ↓
恢复排障
  ↓
达成成功
```

后续的评测重点并不是去提问：

> “上次发生了什么？”

而是检验：

> **当再次面临类似情境时，智能体是否懂得避开已知的失败路径？**

技能场景更进一步：

```text
经验积累
    ↓
抽象出可复用的通用规则
    ↓
正向迁移
    ↓
遇到反例
    ↓
收敛并修正适用边界
```

优秀的记忆系统既要学会：

> **何时该做（what to do）**

更要学会：

> **何时不该做（when not to do it）。**

---

## 基准体系结构

MIB v0.1 定义了 **60 个规范场景模板（Scenario Templates）**：

```text
检索与保留（Recall）      10
时序（Time）              10
认识状态（Epistemic）     10
经验（Experience）         8
技能（Skill）              8
因果（Causal）             8
跨维度（Cross）            6
─────────────────────────────
总计                      60
```

模板分为三个层级：

```text
24 个公开开发模板（Public Dev Templates）
30 个隐藏评测模板（Hidden Eval Templates）
 6 个私有保留模板（Private Holdout Templates）
```

公开 Dev 场景用于：

```text
系统集成
调试排错
方法研究
回归测试
本地开发
```

官方正式评测采用隐藏模板与私有保留模板，防止榜单成绩因针对特定基准的硬编码而失真。

---

## 场景模型

MIB 的核心执行单元是**记忆片段程序（Memory Episode Program）**。

一个完整的 Scenario 包含：

```text
Scenario（场景）
  ├── World（世界环境）
  ├── Actors（实体角色）
  ├── Virtual Time（虚拟时钟）
  ├── Timeline（时间线）
  │    ├── Past Episodes（历史片段）
  │    ├── Interference（干扰噪音）
  │    └── Consolidation Windows（巩固窗口）
  ├── Future Probes（未来探针）
  ├── Ground Truth / Oracle（真实基准）
  ├── Evaluators（评测器）
  ├── Ablations（消融规则）
  └── Scoring（计分规则）
```

执行严格遵循情境的时间流向：

```text
初始世界状态
    ↓
历史交互交付
    ↓
世界状态演变
    ↓
干扰信息注入
    ↓
可选的巩固窗口
    ↓
未来探针触发
    ↓
智能体作答 / 行动
    ↓
世界环境产出
    ↓
反事实消融重放
```

未来探针在记忆形成阶段严格对智能体不可见。

---

## 行为级交互评测

MIB 不仅评测文本生成答案。

智能体可以通过 Runner 托管的工具在模拟环境中执行交互：

```text
Agent（智能体）
  ↓
tool_call（工具调用）
  ↓
MIB Runner
  ↓
World Simulator（世界模拟器）
  ↓
tool_result（工具执行结果）
  ↓
Agent 继续推理
```

智能体无法直接修改基准的世界状态。

这使得 MIB 能够同时评估：

```text
世界最终状态（World Outcome）
```

以及：

```text
行动执行轨迹（Action Trajectory）
```

这意味着仅仅回复一句：

> “已完成。”

如果模拟环境中的实际状态并未达成，将无法得分。

而即使最终达成了目标，如果智能体在途中重复执行了此前已知会导致失败的操作，得分也会相应被扣减。

---

## 评测赛道

### 赛道 A —— 记忆系统评测（Track A — Memory System）

对比不同记忆架构的首选赛道。

保持固定不变：

```text
基座模型
智能体 Prompt
可用工具
任务环境
推理策略
评测 Runner
```

唯一变量：

```text
记忆系统
```

赛道 A 旨在回答：

> **哪一种记忆系统能让相同的智能体展现出更出色的记忆智能？**

### 赛道 B —— 集成智能体评测（Track B — Integrated Agent）

参赛方可以自由调整：

```text
基座模型
智能体设计
记忆系统
编排调度
工具使用策略
```

赛道 B 旨在回答：

> **作为一个完整的端到端系统，该智能体的综合记忆能力处于什么水平？**

赛道 A 与赛道 B 不共享同一个排行榜。

---

## 同模型经验校准（Same-Model Calibration）

在冻结官方榜单数据集之前，MIB 使用同模型经验基准测试工具（Same-Model Empirical Baseline Harness）进行基准校准。

实验环境严格锁定以下变量：

```text
相同基座模型
相同模型端点
相同系统提示词
相同推理策略
相同工具配置
相同解码参数
相同场景实例
相同未来探针
相同配对随机种子
```

仅改变记忆条件：

```text
B0 —— 无记忆（No Memory）
B1 —— 全量可见历史（Full Visible History）
B2 —— 简易检索记忆（Simple Retrieval Memory）
B3 —— 结构化记忆（Structured Memory）
```

这有助于回答一个干净纯粹的技术问题：

> **系统性能的差异中，有多大比例是由记忆系统带来的，而非源自更强大的基座模型本身？**

该工具还会平衡各条件的执行次序，并核验模型无状态性、配对一致性、上下文截断以及实验锁定机制的完整性。

---

## 当前开发进展

MIB v0.1 当前完成情况：

```text
✓ 基准架构设计
✓ 场景模型定义
✓ Agent Adapter 通信协议
✓ 计分模型与统计方法
✓ 评测报告 Schema

✓ 24 个公开 Dev 场景模板
✓ 30 个隐藏评测模板
✓ 6 个私有保留模板

✓ 参考 Runner 实现
✓ 工具交互世界模拟器
✓ 因果消融重放机制
✓ 评测包级聚合统计
✓ 分层 Bootstrap 置信区间计算

✓ 外部 stdio / HTTP Agent Adapter 支持
✓ 隐藏评测隔离基础设施
✓ 提交执行沙箱
✓ 自动化评测服务
✓ 任务清单与评测结果 Ed25519 签名认证
✓ 排行榜及配对显著性对比

✓ 规则基准校准（Fixture Calibration）
  36 / 36 个官方模板已通过结构校准

✓ 同模型经验校准工具

✓ 迁移智能诊断（Transfer Intelligence）
  形成 / 路由 / 采纳分解，迁移距离 D0–D3，
  近似匹配与无支撑两类负向对照
  仅为补充诊断：不改变任何 MIB Score

○ MIB-R 现实赛道（原型阶段）
  独立结果族，暂无官方分数，
  绝不与 MIB-Core 同榜排名

○ 真实固定模型经验校准（进行中）

○ MIB v0.1 官方榜单数据包冻结（等待经验校准完成）
```

---

## 仓库结构导航

项目围绕一组规范文档与可执行产物组织，每个文件均有明确的定位：

```text
MIB/
├── docs/                                  规范文档（英文）
│   ├── MIB-Architecture.md
│   ├── MIB-Scenario-Model.md
│   ├── MIB-Agent-Adapter.md
│   ├── MIB-Scoring.md
│   ├── MIB-Leaderboard-Evaluation-Service.md
│   ├── MIB-Transfer-Intelligence.md
│   ├── MIB-R-Reality-Track.md
│   ├── MIB-v0.1-Test-Plan.md
│   └── harness/                           校准、同模型、隐藏评测与评测服务工程笔记
│
├── docs/cn/                               规范文档（中文版）
│
├── schemas/                               JSON Schema 规范定义（场景、报告、
│                                          提交配置、任务清单、认证签名、
│                                          校准报告、同模型实验）
│
├── scenarios/                             公开 Dev 场景包
│   ├── manifest.json
│   ├── dev/                               MIB-Core 公开 Dev 包，24 篇
│   │   ├── recall/        4 篇    ├── skill/       3 篇
│   │   ├── time/          4 篇    ├── causal/      3 篇
│   │   ├── epistemic/     4 篇    └── cross/       3 篇
│   │   └── experience/    3 篇
│   └── transfer/                          迁移诊断包，6 篇
│                                          （刻意放在 dev/ 之外，
│                                          以保证 MIB-Core 包恰好 24 篇）
│
├── reality/                               MIB-R 原型 Reality Pack
│
├── src/mib_runner/                        参考 Runner、评测器、适配器、
│                                          校准工具、评测服务、排行榜
├── tests/                                 单元测试与集成测试套件
│
├── profiles/                              基准评测 Profile 配置
├── baselines/                             B0–B3 记忆条件定义
├── prompts/                               同模型校准基准 Prompt
├── fixtures/                              合成演示用私有评测库
├── tools/                                 运维与校准脚本
│
└── examples/
    ├── agents/                            参考 stdio / HTTP 智能体示例
    ├── submissions/                       智能体提交规范示例
    ├── runs/                              场景与评测包运行结果产物
    ├── service/                           评测服务产物
    ├── calibration/                       校准分析报告
    ├── same-model/                        固定模型实验产物
    ├── scenario-instances/                具象化后的场景实例
    └── validation/                        Schema 校验结果
```

隐藏评测与私有保留场景的内容不包含在公开仓库中。评测端通过环境变量 `MIB_OFFICIAL_PACK` 加载；若未配置该路径，相关私有包测试会自动跳过。

---

## 快速上手

安装参考实现：

```bash
python -m pip install -e .
```

环境要求：Python 3.10+、`jsonschema >= 4.18`、`cryptography >= 46`。

安装后会在系统 `PATH` 中注册四个 CLI 命令：`mib`、`mib-service`、`mib-calibrate` 和 `mib-same-model-calibrate`。它们是 `pyproject.toml` 中定义的控制台脚本入口；其中 `mib` 对应 `mib_runner.cli:main`。也可以在不安装的情况下直接调用：

```bash
PYTHONPATH=src python -m mib_runner.cli --help
```

参考实现支持的主要 CLI 工作流：

```bash
# 校验场景格式
mib validate scenarios/dev/time/MIB-TIME-003.json --schema schemas/mib-scenario.schema.json

# 运行单个场景
mib run scenarios/dev/time/MIB-TIME-003.json --schema schemas/mib-scenario.schema.json

# 运行完整 Benchmark 评测包
mib benchmark scenarios/dev --schema schemas/mib-scenario.schema.json --profile profiles/MIB-Core-0.1-Dev-M3.json

# 校验评测报告签名与打分
mib verify-score report.json
```

运行测试套件：

```bash
python -m pip install -e ".[test]"
PYTHONPATH=src python -m pytest tests -q
```

在全新的公开克隆中，有两组用例会跳过而非失败：

- 提交沙箱相关用例在非 Linux 宿主机上跳过，因为容器化隔离依赖 Linux
  user/mount/network namespace（详见下文）。
- `tests/test_calibration.py` 中的校准用例，除非 `MIB_OFFICIAL_PACK` 指向仅评测方持有的
  官方包，否则跳过——该包的 Scenario 正文不在本仓库发布。

外部智能体可通过以下通信协议接入 MIB Agent Adapter：

```text
stdio JSONL
HTTP
```

详细协议与评测语义规范请参阅：

```text
docs/cn/MIB-Agent-Adapter.md
docs/cn/MIB-Scenario-Model.md
docs/cn/MIB-Scoring.md
```

---

## 迁移智能与 MIB-R

MIB-Core 回答的是"过去的哪一部分正确地参与了这次未来计算"。它以行为方式回答，
这意味着一次失败的迁移看上去都一样——无论系统是根本没有编译出可用的程序、
编译出来却没有检索到、还是检索到了正确的程序却无法执行。

两个补充层用来区分这三种情况。

**迁移智能**（`docs/MIB-Transfer-Intelligence.md`）把评测方的隐含假设显式化——
哪些过去经验、通过哪一项 Ability、在什么适用边界内支撑哪一个未来 Probe——
然后对结果进行分解：

```text
经验 → 形成 → 技能 → 路由 → 适用性判断 → 采纳 → 未来行为
```

它报告形成效率（Formation Efficiency）、路由效率（Routing Efficiency）、
采纳上限（uptake ceiling），以及覆盖正向距离阶梯 `D0`–`D3` 的迁移剖面
（Transfer Profile），同时给出纯正向迁移基准无法表达的两类对照：
学到的程序**必须被抑制**的近似匹配陷阱，以及记忆**必须保持中性**的无支撑任务。
四个诊断单元中有三个可以直接在黑盒 Agent 上运行。

**MIB-R**（`docs/MIB-R-Reality-Track.md`）追问同一种记忆智能能否在真实外部任务
环境中存活：在只有记忆状态变化、其余全部配对固定的条件下，执行经验获取与
留出集迁移。

两层都是补充性的。二者定义的任何指标都不会进入 MIB Score、因果分数或覆盖率。
若某个评测包的模板不带迁移标注，其报告与该扩展存在之前逐字节一致。
MIB-R 处于原型阶段，属于独立结果族且没有官方分数，绝不与 MIB-Core 同榜排名。

```bash
mib benchmark scenarios/transfer \
  --profile profiles/MIB-Transfer-0.1-Dev.json \
  --schema schemas/mib-scenario.schema.json \
  --transfer-diagnostics

mib reality-benchmark reality/MIB-R-Demo-LedgerCodes/pack.json \
  --profile profiles/MIB-R-0.1-Dev.json \
  --agent mib_runner.agents.reality_fixtures:RuleLearningRealityAgent
```

---

## MIB 与 KIP 的关系

MIB 的认知模型吸收了 KIP v2 的核心设计理念，但两个项目定位明确不同：

```text
KIP
  → 如何对持久化认知进行结构化表征、修正演进、治理合规与安全交换？

MIB
  → 如何科学评估具备记忆能力的智能体的实际认知水平？
```

遵循 KIP 协议并不会直接增加 MIB 得分。

MIB 对智能体内部的记忆存储形态没有任何限制，参赛系统可以使用：

```text
原始对话历史
向量检索（RAG）
摘要记忆
关系型数据库
知识图谱
情景记忆（Episodic Memory）
过程/程序记忆（Procedural Memory）
KIP 协议体系
混合多级记忆
或任何全新的自主设计
```

基准唯一的衡量依据是智能体可观测的实际行为。

---

## MIB 追求的终极目标

MIB 背后追问的核心命题非常朴素：

> **过往的经验，究竟如何切实参与并赋能未来的决策？**

一个真正具备实用价值的记忆系统应当做到：

```text
精准记住关键信息
在适当时机进行操作性遗忘
完整保留历史变迁轨迹
准确追踪现实状态演变
维系证据链与不确定性
从失败中汲取教训
将经验编译为稳固技能
审慎辨析并执行迁移
坚决抵御过时与有害记忆
最终让未来的行动表现更优
```

这正是 MIB 所定义的：

# **记忆智能（Memory Intelligence）**

---

## 参与贡献

MIB 目前处于快速演进中。

欢迎通过以下方向参与贡献：

```text
设计全新的场景类别（Scenario families）
贡献新的基准记忆实现（Memory baselines）
开发多样化的 Agent Adapter 适配器
适配新的大模型及推理服务接入
改进评测器与环境模拟逻辑
优化统计分析与指标计算方法
参与基准数据集的校准验证
开展对抗性测试与鲁棒性验证
提交全新的记忆系统参与评测
```

在构思新场景时，建议思考这样一个核心问题：

> **历史中的哪一部分应当在此时发挥作用？哪一部分不应发挥作用？我们如何通过可量化的指标证明两者的差异？**

---

## 开源协议

MIB 以 **GNU General Public License v3.0** 发布，完整条款见 [LICENSE](LICENSE)。

---

## 引用规范

待 v0.1 官方评测包冻结后，将补充正式学术论文与 BibTeX 引用信息。

机器可读的引用元数据见 [CITATION.cff](CITATION.cff)。现阶段引用本项目请使用如下格式：

> **MIB — Memory Intelligence Benchmark**
>
> A benchmark for measuring how effectively an intelligent system uses the past to improve future cognition and behavior.
