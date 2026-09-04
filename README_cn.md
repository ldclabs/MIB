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

因此，记忆不仅仅是一个持久化键值存储或向量数据库。

> **记忆是跨时间连接经验、知识与未来决策的认知桥梁。**

当前的智能体评测体系在这一维度上存在明显空白。现有基准主要衡量两类极端：

- 纯粹的无状态基座模型能力；
- 将超长文本强行喂入注意力窗口的“大海捞针”式检索能力。

如果智能系统要在长时间跨度内真正与人类深度协作，它就必须具备真正的**记忆智能**。

---

## 核心原则

MIB 建立在以下核心原则之上：

### 1. 记忆必须产生因果效应

如果从系统的历史中移除某段记忆，其未来的决策行为**毫无变化**，那么这段历史就只是一份死板的存档，而未转化为真正发挥效力的记忆。

记忆系统的优劣，不能仅凭其存储体积或检索相似度来评判，而必须检验其是否真正改善了后续的行为决策。

### 2. 记忆必须具备情境敏感性

在某一场景下有用的记忆，在另一场景下可能完全无关，甚至造成误导。

高水平的记忆智能体不仅要懂得何时应用技能，更要深刻理解**何时克制不要迁移**。

### 3. 记忆必须保留关键区分

一套完善的记忆系统必须清晰区分：

```text
当前事实   vs   历史状态
主观陈述   vs   客观事实
信源身份   vs   事实溯源
偶发事件   vs   亲历经验
陈述性知识 vs   程序性技能
认识未知   vs   断言为假
承诺约定   vs   触发条件
```

### 4. 记忆应当持续演化与巩固

随着时间推移，记忆不应仅仅不断线性追加，而必须能够经历：

```text
更新（Update）
修正（Correction）
冲突化解（Contradiction Resolution）
选择性遗忘（Selective Forgetting）
后台巩固（Consolidation）
策略编译（Skill Compilation）
```

### 5. 评测对象是完整认知系统

MIB 评测的不是一个孤立的检索器模块。

评测的实体是：

> **作为跨时间认知系统的“智能体 + 记忆系统”整体。**

---

## MIB 评测维度

MIB-Core 在 v0.2 中评测七个核心能力维度：

| 能力维度 | 评测核心问题 |
| --- | --- |
| **保持与检索（Retention & Retrieval）** | 在间接线索与生成的干扰下，能否直接或跨跳（multi-hop）准确恢复相关过往信息？ |
| **时序记忆（Temporal Memory）** | 能否准确区分状态演变中的当前值、先前值与初始值？ |
| **认知记忆（Epistemic Memory）** | 能否记住谁说了什么，准确区分认知修正与事实冲突，遵从信源权威，并将未知与错误清晰区分开来？ |
| **经验记忆（Experience Memory）** | Agent 自身亲历并经历的失败，能否改变它下一次的行为决策？ |
| **技能学习与迁移（Skill Learning & Transfer）** | 习得的前置约束能否在适用场景准确迁移，并在不适用场景严格克制？ |
| **前瞻与自省记忆（Prospective & Self Memory）** | 延期承诺是否在触发条件成熟时精准触发且不早熟？关于 Agent 自身的既定准则能否在面对违规要求的任务时坚守不移？ |
| **选择性遗忘（Selective Forgetting）** | 被撤回的事实是否彻底停用，同时其周边关联事实依然可用？ |

记忆是否产生因果影响不再作为第 7 个能力维度，而是作为一组并列报告的因果诊断量；其中一项——内容追踪率（Content Tracking Rate）——充当了该得分能否算作记忆得分的准入门槛（详见下文）。

未来的评测 Profile 将扩展支持以下一等评测维度：

```text
跨智能体记忆（Cross-Agent Memory）
多模态记忆（Multimodal Memory）
隐私保护边界（Privacy Boundaries）
```

---

## 记忆必须产生因果效应

MIB 认为纯粹的检索质量评估是有益的，但远远不够。

核心评测范式是成对配对干预：

```text
完整记忆条件（Full Memory）
    vs
相关记忆消融条件（Relevant Memory Ablated）
```

如果相关记忆真正起到了作用，那么将其移除必然会导致性能下降。

MIB 同样会检验反向假设：

```text
完整记忆条件（Full Memory）
    vs
无关记忆消融条件（Irrelevant Memory Ablated）
```

移除无关的历史干扰，系统的性能应当保持大体稳定。

针对陈旧或有害记忆：

```text
纯净当前基线条件（Clean / Current Condition）
    vs
存在有害或陈旧记忆条件（Harmful or Stale Memory Condition）
```

一套具备足够能力的记忆系统，应当能主动抵御可避免的记忆诱发错误。

对抗场景族（`MIB-ADV-*`）将有害记忆条件推向了最极致的形式：注入的事件**纯粹由问句构成**，这些问句预设了未曾建立的习惯、日期或规程。因为疑问句本身并未断言任何事实，两个条件下的理论 Oracle 完全一致——任何成对的性能滑坡直接揭示了单纯的提问就会将未经证实的事实植入记忆，该现象通过标准的记忆危害（Memory Harm）与危害抵御度（Harm Resistance）指标直接测量。

移除事件只能证明该事件中的*某些信息*起到了作用。v0.2 引入了更强大的检验方式——**反事实内容置换（counterfactual content）**：同一个实例在重放时将某单一事件的内容替换为另一表述，正确答案随之改变。

```text
完整记忆条件（Full Memory）
    vs
完全相同的过往，单一眼前事件内容被置换
```

若 Agent 的回答能够紧跟置换后的内容，才证明它切实运用了记忆。若无论内容如何置换，Agent 的回答均保持不变，那么即便其分数再高，也仅仅是在凭借先验知识作答。

这产生了一组丰富的诊断指标：

```text
记忆收益（Memory Benefit）
顶空间归一化记忆收益（Headroom-Normalized Memory Benefit）
内容追踪率（Content Tracking Rate）          ← 记忆依赖性门控指标
陈旧记忆采纳率（Stale Adoption Rate）
无关记忆稳定性（Irrelevant Memory Stability）
记忆危害（Memory Harm）
危害抵御度（Harm Resistance）
净记忆增益（Net Memory Gain）
错误复发率（Error Recurrence Rate）          （亲历失败，见下文）
巩固收益（Consolidation Benefit）            （实现了 maintain 的系统）
负迁移及其发生率（Negative Transfer / Rate） （不匹配任务上的标准化对照）
学习增益与曲线面积（Learning Gain / Curve Area）（亲历试验）
权威混淆率、历史保真度、信源归属度、自我准则延续度
```

主 **MIB 综合得分**衡量的是在固定的干扰距离下的绝对记忆赋能能力。因果诊断量与该能力分并列呈现，而非混杂成一个不透明的分数；Profile 的**记忆依赖性**准入门槛（默认内容追踪率 ≥ 0.5）决定了该分数是否有资格被认定为官方有效成绩。负迁移通过其标准化对照进行测量：扣留技能记忆下的不匹配任务表现，与包含该记忆时的相同任务表现进行对比（`docs/cn/MIB-Specification.md` §7.8）。

---

## MIB 不只是长上下文问答

一个系统完全可以在文本检索上得分很高，却在记忆智能上彻底不及格。

例如：

```text
“我住在 UTC+8 时区。”

数周之后……

“我搬家了，我现在使用 UTC+1 时区。”
```

一个真正实用的记忆系统必须明确掌握：

```text
当前时区   → UTC+1
历史时区   → UTC+8
```

它绝不能简单粗暴地将历史记录直接覆写抹除。

同样地：

```text
“设备序列号是 AX-19。”

“抱歉修正一下，我刚才说错了，正确的序列号是 AX-91。”
```

与下述变化在本质上截然不同：

```text
“我们的旧办公室在蓝色大楼。”

“我们搬家了，新办公室在绿色大楼。”
```

前者属于**认知修正（Epistemic Correction）**，后者属于**真实世界的客观状态演迁（World Transition）**。

MIB 的设计宗旨就是让这些深层认知区别在评测中变得清晰可辨。

---

## 重视经验与技能积累

MIB 还会深度评测智能体能否从实际行动交互中吸取经验教训。

一个典型的经验记忆场景如下：

```text
目标（Goal）
  ↓
执行动作（Action）
  ↓
遭遇意外失败（Unexpected failure）
  ↓
获得环境观测（Observation）
  ↓
排查诊断（Diagnosis）
  ↓
恢复纠正（Recovery）
  ↓
任务成功（Success）
```

未来的能力检验并非简单提问：

> “上次发生了什么？”

而是检验：

> **当未来再次出现类似情境时，智能体能否主动规避已知的失败覆辙？**

技能场景更进一步：

```text
经历（Experience）
    ↓
抽象出可复用的规程策略（Reusable Rule）
    ↓
实现正向迁移（Positive Transfer）
    ↓
遭遇反例边界（Counterexample）
    ↓
细化适用边界（Refined Applicability Boundary）
```

一套高水准的记忆系统必须同时学会：

> **何时应当执行该技能**

以及：

> **何时严格克制不应执行该技能。**

---

## 基准体系结构

MIB v0.2 不再采用手写场景，而是采用**程序（Programs）**：在内部双时态、分信源的世界模型上运行的确定性生成器 `(seed, rung) → Scenario Instance`。正确答案、相关记忆消融集合、反事实孪生以及泄漏证明完全由模型程序化推导，绝不手动撰写。

```text
mib.recall.v1        恢复单个事实以及带有诱饵的双跳关联链
mib.temporal.v1      经历一次或两次更新：准确区分当前值、先前值与最初值
mib.epistemic.v1     修正、带权威的冲突、日历工具化解、谁说了什么、未知
mib.experience.v1    Agent 自身亲历并破坏的部署任务，随后的相关部署
mib.skill.v1         学得的前置条件：在适用处准确迁移，在不适用处严格克制
mib.prospective.v1   延期承诺、拟真触发项、真实触发项、压力下的自我准则
mib.forgetting.v1    被撤回的事实必须停用；周边事实依然已知
```

每个程序均在**距离阶梯（distance ladder）**上运行——同一个实例在过往经历与探针之间分别插入 0、20 和 100 个生成的干扰事件（MIB-M 开发 Profile 中为 0 / 100 / 1000）——因此评测产出的是一条**保持曲线（retention curve）**，而非单一孤立的点。干扰距离以事件数、token 数和虚拟小时数分别记录。能力基准分在 Profile 的规范档位（canonical rung）读取；所有档位的数据共同描绘曲线。每个程序还包含一次整理窗口（带有配对的无维护对照），每个亲历任务均可携带试验 Oracle，因此学习曲线直接来源于 Agent 自身的实际行动表现。

评测数据包由 `programs × seeds × rungs` 构成。程序定义、改写词表与生成器完全公开；官方评测使用评测方保密的私有种子，确保参赛者可以审查每处构造逻辑，却永远无法提前窥探官方实例。

v0.1 的 24 个静态公开 Dev 模板（以及隐藏 v0.1 数据包）依然作为超集可执行，用于集成开发与回归测试。它们不再是基准的核心形态。

---

## 场景模型

MIB 的基本评测单元是**记忆情节程序（Memory Episode Program）**。

场景由以下核心组件构成：

```text
场景（Scenario）
  ├── 世界环境（World）
  ├── 交互角色（Actors）
  ├── 虚拟时钟（Virtual Time）
  ├── 时间线（Timeline）
  │    ├── 过往经历（Past Episodes）
  │    ├── 干扰噪声（Interference）
  │    └── 巩固整理窗口（Consolidation Windows）
  ├── 未来探针（Future Probes）
  ├── 事实真值（Ground Truth / Oracle）
  ├── 评测器集（Evaluators）
  ├── 消融设定（Ablations）
  └── 评分规则（Scoring）
```

场景执行严格模拟真实时间序列展开：

```text
初始世界状态
    ↓
过往经历交互
    ↓
世界客观状态演迁
    ↓
干扰噪声阶段
    ↓
可选的巩固整理窗口
    ↓
触发未来探针
    ↓
智能体作答或执行动作
    ↓
判定世界客观结果
    ↓
反事实重放比对
```

未来的探针在记忆形成阶段绝不会提前泄露给智能体。

---

## 行为级交互评测

MIB 绝不仅仅评测文本问答。

智能体可以通过 Runner 管控的受控工具执行动作：

```text
智能体（Agent）
  ↓
发出工具调用（tool_call）
  ↓
MIB Runner 执行器
  ↓
世界模拟器（World Simulator）
  ↓
返回工具结果（tool_result）
  ↓
智能体继续决策
```

智能体绝不可直接篡改基准的内部世界状态。

这使得 MIB 能够同时评测：

```text
世界最终达成状态（World Outcome）
```

与：

```text
交互动作轨迹（Action Trajectory）
```

因此，即使智能体口头宣称：

> “任务已完成。”

如果模拟世界中的客观状态依然存在错误，依然无法得分。

即便最终侥幸达成目标，如果智能体在过程中重复犯了本应规避的已知错误，同样会被扣除相应分数。

---

## 评测赛道

### 赛道 A —— 记忆系统评测（Track A — Memory System）

对比不同记忆架构的首选赛道。

保持完全固定：

```text
基座模型
智能体提示词
工具集合
任务环境
推理策略
评测执行器（Runner）
```

唯一允许变量：

```text
记忆系统
```

赛道 A 核心追问：

> **在基座智能体完全相同的前提下，哪套记忆系统能赋予其更高的记忆智能？**

### 赛道 B —— 集成智能体评测（Track B — Integrated Agent）

参赛者可以自由定制与调整：

```text
基座模型
智能体架构
记忆机制
编排调度
工具交互策略
```

赛道 B 核心追问：

> **这套完整的软硬件智能体整体具备多强的记忆赋能能力？**

赛道 A 与赛道 B 严禁混合在同一个排行榜中排序比较。

---

## 同模型经验校准（Same-Model Calibration）

在正式冻结官方榜单数据包之前，MIB 会运行“同模型实证基线工具（Same-Model Empirical Baseline Harness）”。

实验锁定配置严格保持不变：

```text
完全相同的基座模型
相同的模型服务节点
相同的系统级提示词
相同的推理策略
相同的工具定义
相同的解码采样参数
相同的场景实例
相同的未来探针
相同的配对抽样种子
```

唯一发生变化的是记忆条件：

```text
B0 —— 无记忆基线（No Memory）
B1 —— 全可见历史基线（Full Visible History）
B2 —— 朴素检索记忆基线（Simple Retrieval Memory）
B3 —— 结构化记忆基线（Structured Memory）
```

这确保了我们能回答一个极度严谨的问题：

> **系统展现出的性能差异，究竟有多少来源于记忆系统的精妙设计，又有多少仅仅来源于更强的基座模型？**

该校准工具还会对测试条件的执行顺序进行轮替平衡，并严格校验模型无状态性、成对配对有效性、上下文截断以及实验锁的完整性。

---

## 当前开发进展

MIB v0.2（实现版本 0.9.0）目前包含：

```text
✓ 基准评测总体架构
✓ 双时态、分信源的世界模型与程序化推导 Oracle
✓ 七个在三档干扰阶梯上运行的生成程序（MIB-S 与 MIB-M profiles）
✓ 支持集、泄漏证明、反事实孪生（全部自动推导）
✓ 亲历任务与试验（Agent 亲手创建经历；试验形成学习曲线）
✓ 基于自发发射评测的前瞻记忆
✓ 结构化答案：value / status / confidence，确定性解析器
✓ 评分模型：规范档位能力基准分 + 保持曲线
✓ 因果诊断指标体系 + 记忆依赖性门控
✓ 标准化负迁移对照组
✓ 全流程行为诊断（错误复发、权威混淆、历史保真度、信源归属度、自我准则延续度、记忆诱发错误）
✓ 巩固整理窗口与配对无维护对照
✓ 百分位法与 BCa 置信区间；Runner 实测效率统计块
✓ 评测报告 Schema、分数独立核验工具、能力卡片渲染器

✓ 参考执行器 Runner（支持 respond / act / observe_only，maintain 钩子）
✓ 工具交互循环世界模拟器
✓ 因果消融、反事实置换与无维护重放机制
✓ 数据包级聚合引擎
✓ 分层 Bootstrap 重采样（生成包以实例为基本抽样基元）

✓ 外部 stdio / HTTP Agent Adapter 适配器
✓ 隐藏评测基础设施
✓ 外部提交隔离沙箱
✓ 评测调度服务
✓ 任务清单与评测结果数字签名
✓ 排行榜系统与配对显著性对比分析

✓ 六套分值高下顺序完全符合设计预期的规则 Agent
  StructuredMemoryAgent   保持曲线平坦，内容追踪率 1.0
  WindowMemoryAgent       性能随干扰阶梯发生衰减
  ConsolidatingAgent      在滑动窗口基础上实现 maintain() 带来巩固收益
  RecencyAgent            呈现陈旧采纳与权威混淆，无法遗忘
  OvergeneralizingAgent   在不匹配任务中产生负迁移
  NoMemoryAgent           得分极低，依赖性无法评估
  （仅用于验证调用管道，不代表真实模型面临的任务难度）

✓ 24 个静态 v0.1 公开 Dev 模板，依然作为超集可执行

✓ 迁移智能诊断层（Transfer Intelligence diagnostics）
  仅供深度分析：不改变任何 MIB 主分

○ MIB-R 现实任务评测轨原型（Reality Track）
  原型阶段；拥有独立结果族，无官方总分，绝不与 MIB-Core 混合排名

○ 基于真实固定模型的全阶梯实证校准
  待进行

○ 超越任何当前工作上下文的 MIB-L 长阶梯
  待进行（目前 MIB-M 达到 1,000 个干扰事件，约 8k tokens）

○ MIB v0.2 官方榜单数据包冻结
  等待实证校准完成
```

v0.2 目前能够与不能够声称的事：

- 当前附带的每个程序均处于现代上下文窗口之内：MIB-S 阶梯上限为 100 个干扰事件，MIB-M 达到 1,000 个（约 8k tokens）。干扰阶梯与反事实置换共同将**记忆**与**阅读**区分开来——Agent 必须在长距离下保持记忆内容，并且必须在内容改变时做出跟随响应——但在 rung 2 档位，全上下文模型依然可以通过直接阅读来通过测试。唯有当阶梯跨越工作上下文地平线之后，保持曲线才能彻底演变为不同记忆系统之间的纯粹较量，这一步仍在推进中。
- 规则 Agent 的行为规则绑定了生成语言的特定表达。它们的高下排序（Structured > Window > NoMemory；Recency 呈现陈旧采纳）验证了 Runner 与评分管道的正确性；这绝不代表真实基线。
- 尚未在真实基座模型上完成全量实证校准。

---

## 参考实现架构

![MIB 参考实现架构](docs/diagram/mib-architecture.svg)

---

## 仓库结构导航

项目围绕一组规范文档与可执行产物组织，每个文件均有明确的定位：

```text
MIB/
├── docs/                                  规范文档（英文）
│   ├── MIB-Specification.md               v0.2 核心规范：程序与世界模型、
│   │                                      执行语义、评分体系、因果诊断、
│   │                                      距离阶梯、报告规范（附录含路线图）
│   ├── proposals/                         MIB-v0.2-Evolution.md —— 设计推导背景
│   ├── MIB-Agent-Adapter.md               Agent Adapter 通信协议（stdio / HTTP）
│   ├── MIB-Leaderboard-Evaluation-Service.md
│   ├── MIB-v0.1-Test-Plan.md
│   ├── experimental/                      迁移智能与 MIB-R 规范
│   ├── archive/                           已归档的旧版设计草案（仅供背景参考）
│   ├── harness/                           校准、同模型、隐藏评测与评测服务工程笔记
│   └── diagram/                           参考实现架构图
│                                          （JSON 规格、SVG、交互式 HTML）
│
├── docs/cn/                               规范文档（中文版，与 docs/ 1:1 对齐）
│   ├── MIB-Specification.md               v0.2 核心中文规范
│   ├── proposals/                         MIB-v0.2-Evolution.md
│   ├── MIB-Agent-Adapter.md
│   ├── MIB-Leaderboard-Evaluation-Service.md
│   ├── MIB-v0.1-Test-Plan.md
│   ├── experimental/                      迁移智能与 MIB-R 中文规范
│   ├── archive/                           已归档的旧版设计草案（中文版）
│   └── harness/                           校准与服务工程笔记中文版
│
├── schemas/                               JSON Schema 规范定义（场景、报告、
│                                          提交配置、任务清单、认证签名、
│                                          校准报告、同模型实验）
│
├── scenarios/                             静态 v0.1 场景包（超集；成员由各
│   │                                      Profile 的 required_templates 确定）
│   ├── dev/                               MIB-Core v0.1 公开 Dev 包，24 篇
│   │   ├── recall/        4 篇    ├── skill/       3 篇
│   │   ├── time/          4 篇    ├── causal/      3 篇
│   │   ├── epistemic/     4 篇    └── cross/       3 篇
│   │   └── experience/    3 篇
│   └── transfer/                          迁移诊断包，6 篇（置于 dev/ 之外，
│                                          以确保 MIB-Core 恰好为 24 篇）
│
├── reality/                               MIB-R 原型 Reality Pack
│
├── src/mib_runner/                        参考 Runner、评测器集、适配器、
│   │                                      校准工具、服务与排行榜
│   ├── worldmodel.py                      双时态分信源世界模型、查询、
│   │                                      支持集推导、反事实孪生与泄漏证明
│   ├── generate/                          程序生成器、改写词表、干扰阶梯、
│   │                                      实例构建器与程序注册表
│   ├── agents/v2.py                       v0.2 的规则 Agent 实现
│   └── experimental/                      迁移智能、Memory Adapter 与 MIB-R
│                                          （绝不进入 MIB 主分）
├── tests/
│
├── profiles/                              基准评测 Profile 配置
│                                          （MIB-Core-0.2-Dev.json 与 -Dev-M.json：
│                                          程序列表、阶梯档位、规范档位、
│                                          记忆依赖性门槛、Bootstrap 区间方法）
├── baselines/                             B0–B3 记忆基线条件定义
├── prompts/                               固定同模型提示词
├── fixtures/                              合成的本地私有评测测试集
├── tools/                                 运维与工具脚本
│
└── examples/
    ├── agents/                            参考 stdio / HTTP Agent 实现
    ├── submissions/                       Agent 参赛提交配置示例
    ├── runs/                              场景与数据包运行产物示例
    │                                      （MIB-Core-0.2-Dev.* 为 v0.2 数据包）
    ├── service/                           评测服务产物示例
    ├── calibration/                       校准产物示例
    ├── same-model/                        固定模型实验产物示例
    ├── scenario-instances/                物化的场景实例文件
    │                                      （generated/ 包含各程序生成的实例）
    └── validation/                        Schema 校验结果示例
```

隐藏评测与私有保留集的具体场景内容刻意不保存在公开仓库中。评测方的数据包通过环境变量 `MIB_OFFICIAL_PACK` 定位；缺少该变量时校准测试将自动安全跳过。

---

## 快速上手

本地安装参考实现：

```bash
python -m pip install -e .
```

要求 Python 3.10+、`jsonschema >= 4.18` 以及 `cryptography >= 46`。

安装后会在系统 `PATH` 中注册四个 CLI 命令 —— `mib`、`mib-service`、`mib-calibrate` 以及 `mib-same-model-calibrate`。它们是在 `pyproject.toml` 的 `[project.scripts]` 中声明的控制台脚本入口；其中 `mib` 映射到 `mib_runner.cli:main`。如果不想全局安装，可直接通过模块方式调用：

```bash
PYTHONPATH=src python -m mib_runner.cli --help
```

从生成程序中实例化生成单个场景（种子为 7，阶梯档位 rung 1 = 20 个干扰事件）：

```bash
mib generate --program mib.temporal.v1 --seed 7 --rung 1 --schema schemas/mib-scenario.schema.json --output MIB-GEN-TEMPORAL-V1.json
```

针对规则 Agent 运行 v0.2 开发包 —— 遍历所有程序、所有种子、所有阶梯档位 —— 并输出报告、摘要与能力卡片：

```bash
mib benchmark --profile profiles/MIB-Core-0.2-Dev.json --schema schemas/mib-scenario.schema.json --report-schema schemas/mib-report.schema.json --agent mib_runner.agents:StructuredMemoryAgent --output-report report.json --output-summary summary.json --card card.md
```

可将 `StructuredMemoryAgent` 替换为 `WindowMemoryAgent`、`ConsolidatingAgent`、`RecencyAgent`、`OvergeneralizingAgent` 或 `NoMemoryAgent`，以观察设计所预期的分值变化；也可以传入自定义的 `module:Class`（实现 `reset` / `observe` / `respond` / `act`，可选 `maintain` 的进程内 Agent）。`profiles/MIB-Core-0.2-Dev-M.json` 以 MIB-M 尺度运行相同的程序，并采用 BCa 置信区间。

重新核验报告中的每一个计算层级：

```bash
mib verify-score report.json
```

静态的 v0.1 模板依然可以正常运行：

```bash
mib run scenarios/dev/time/MIB-TIME-003.json --schema schemas/mib-scenario.schema.json
```

```bash
mib benchmark scenarios/dev --schema schemas/mib-scenario.schema.json --profile profiles/MIB-Core-0.1-Dev-M3.json
```

运行完整自动化测试套件：

```bash
python -m pip install -e ".[test]"
```

```bash
PYTHONPATH=src python -m pytest tests -q
```

在全新的公开克隆仓库中，有两组测试会自动安全跳过（skip）：

- 提交隔离沙箱测试在非 Linux 系统上会自动跳过，因为进程容器隔离依赖 Linux 的非特权用户命名空间、挂载命名空间及网络命名空间（见下文）。
- `tests/test_calibration.py` 中的校准测试在未配置 `MIB_OFFICIAL_PACK` 环境变量时会自动跳过。

其余所有测试均可在任何支持 Python 3.10+ 的操作系统上顺畅运行。

### 运行外部提交需要 Linux 环境

执行参赛者提供的 **stdio** 智能体的相关命令 —— 包括在 stdio 提交上运行 `mib agent-smoke-test`、执行 `mib evaluate-hidden` 以及后台常驻的 `mib-service register-submission` / `worker-once` —— 会将参赛代码置于参考提交沙箱中运行，该沙箱依托 Linux 系统通过 `unshare` 建立的非特权用户、挂载与网络命名空间进行强隔离。这些命令仅在 Linux 系统上得到支持；在 macOS 和 Windows 上无法施加严格隔离，亦无法完全遮蔽评测方的隐藏路径。

HTTP 提交仅接受来自 `localhost` 本地的请求。远程 `base_url` 必须附带 `--allow-remote-http` 参数并强制使用 `https`；HTTP 传输通道的设计初衷是为了非 Python 语言 Agent 的本地调试，而非用于远程未隔离的正式评测。

CLI 的其余命令 —— 包含 `mib validate`、`generate`、`run`、`run-pack`、`benchmark`、`capability-card`、`verify-score`、`public-eval-manifest` 以及所有非执行态的 `mib-service` 子命令 —— 均完全跨平台支持。

外部智能体可通过以下两种方式接入评测：

```text
stdio JSONL
HTTP
```

通信遵循 MIB Agent Adapter 协议规范。

详见规范文档：

```text
docs/cn/MIB-Agent-Adapter.md
docs/cn/MIB-Specification.md
```

---

## 迁移智能与 MIB-R

MIB-Core 回答了*过往经历中的哪些部分正确参与了未来的计算*。它基于纯粹的外在行为表现进行判定，这意味着一次失败的迁移无论是因为系统未能归纳出有效规程、归纳了却未能检索召回、还是成功召回后无法执行，在宏观行为上都呈现为完全相同的失误。

有两个补充层专门用于解构这些不同情形。

**迁移智能（Transfer Intelligence）**（`docs/cn/experimental/MIB-Transfer-Intelligence.md`）把评测方的隐含假设显式化——哪段过往经验通过哪项能力、在何种适用边界下支撑了哪个未来探针——并将结果层层拆解：

```text
经历 → 形成 → 技能 → 路由 → 适用性 → 采纳 → 行为
```

它评估形成效率、路由效率、采纳上限，以及跨越正向距离阶梯 `D0`–`D3` 的迁移画像，并引入了纯正向迁移基准无法表达的两类核心对照组：学得技能必须克制不用的拟真陷阱（near-match trap），以及记忆必须保持中立的全新任务。四个诊断单元中有三个可以直接在普通的黑盒 Agent 上执行。

**MIB-R**（`docs/cn/experimental/MIB-R-Reality-Track.md`）追问同一种记忆智能能否在真实外部任务环境中存续，它在只有记忆状态发生变化的配对条件下运行获取与保留测试迁移。

两个层次均属于补充性设计。它们定义的任何指标均**不计入** MIB 综合得分、因果得分或覆盖率。未携带迁移标注的数据包生成的报告与引入前逐字节完全相同。MIB-R 是一套具备独立结果族的原型设计，不设官方总分，亦绝不与 MIB-Core 混合排名。

```bash
mib benchmark scenarios/transfer \
  --profile profiles/MIB-Transfer-0.1-Dev.json \
  --schema schemas/mib-scenario.schema.json \
  --transfer-diagnostics

mib reality-benchmark reality/MIB-R-Demo-LedgerCodes/pack.json \
  --profile profiles/MIB-R-0.1-Dev.json \
  --agent mib_runner.experimental.reality_fixtures:RuleLearningRealityAgent
```

---

## MIB 与 KIP 的关系

MIB 建立在先前关于知识、经验与记忆的深层探索之上。

这些思考最系统化的表达见于 [KIP (Knowledge & Intelligence Protocol)](https://github.com/ldclabs/KIP)。

在架构理念上：

```text
KIP
  定义了一套关于知识、经验、权威信源与长周期认知的参考模型。

MIB
  建立了一套开放中立的基准体系，用于客观衡量记忆系统的实际效力。
```

两者共享对以下核心认知的深刻理解：

- 经验应当沉淀为可复用的决策技能；
- 状态更新与认知修正存在本质区别；
- 证据来源、断言权威与时间演进至关重要；
- 记忆必须在长期连续运行中动态维护与提炼。

**但 MIB 不要求任何参赛系统实现 KIP。**

参赛智能体可以基于任何自研架构实现——从最极简的文本滑动窗口，到先进的图记忆数据库、向量检索模块或专有的符号记忆认知引擎均可无缝接入。

评测标准只看实际效果：

> **这套记忆系统能否让智能体在未来展现出更高的认知与决策智能？**

---

## MIB 追求的终极目标

一个真正合格的记忆基准，最终应当产出的不是一个虚荣的单一数字：

```text
Memory Accuracy: 84%
```

而应当是一张极具深度诊断价值的**记忆能力全景画像（Memory Capability Card）**：

```text
Retention & Retrieval:          88.2 / 100
Temporal Memory:                84.5 / 100
Epistemic Memory:               79.1 / 100
Experience Memory:              73.4 / 100
Skill Learning & Transfer:      68.2 / 100
Prospective & Self Memory:      77.0 / 100
Selective Forgetting:           82.6 / 100

Memory Dependence Gate:         PASS (CTR: 0.86 ≥ 0.50)
Retention Curve:                [r0: 92.4, r1: 85.1, r2: 78.0] (Half-Distance: 180 events)
Memory Benefit:                 +14.2 pp
Headroom-Normalized Benefit:    0.48
Irrelevant Memory Stability:    0.93
Harm Resistance:                0.89
Net Memory Gain:                +11.8 pp
Error Recurrence Rate:          8.3%
Consolidation Benefit:          +5.4 pp
```

这才能真正告诉整个学术界与工业界：

- 你的记忆系统在哪些认知维度切实带来了帮助；
- 在哪些场景下它未能成功召回必要经验；
- 在哪些复杂情境下它出现了过度泛化并导致负迁移；
- 以及它在长周期时间跨度下维持认知一致性的真实能力。

这正是 MIB 所全力衡量的核心价值：

# **记忆智能（Memory Intelligence）**

---

## 参与贡献

我们极其欢迎社区力量参与共建 MIB：

- 贡献全新的场景生成程序（特别是长时序、复杂多智能体协作、强工具交互场景）；
- 完善并贡献真实外部环境的现实任务数据包（MIB-R Reality Packs）；
- 接入并测试全新的记忆系统与智能体架构；
- 持续加固并演进评测执行器、世界模拟器与各项诊断评测工具。

参与指南详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 开源协议

本项目采用 **GNU General Public License v3.0**（GPL-3.0）开源协议。完整的协议文本请参阅 [LICENSE](LICENSE) 文件。

---

## 引用规范

如果您在学术研究或工业评测中使用了 MIB，请按照以下格式进行引用：

```bibtex
@software{mib2026,
  author = {0xZensh and the MIB Contributors},
  title = {MIB: Memory Intelligence Benchmark},
  year = {2026},
  url = {https://github.com/ldclabs/MIB}
}
```
