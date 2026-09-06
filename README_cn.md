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

MIB 分别报告能力得分与因果证据。相关历史消融检验扣留过往经历是否会改变后续表现。内容孪生（content twins）检验回答是否跟随变更的历史内容而改变。策略孪生（policy twins）在习得反馈与未来验证中一致地变更潜在的工作流惯例；它们用于在匹配的规则世界下检验学得的行为。

修订后的开发 Profile 要求在**每个有权重的维度**上均具备证据。门控保留了合格/总探针数以及独立实例计数。默认情况下，每个维度需要至少 5 个合格实例、50% 的探针覆盖率，以及在实例追踪成功率上达到至少 0.5 的 95% Wilson 置信下限。证据缺失的情况保持为无法评估。

诊断指标包括记忆收益（Memory Benefit）、内容追踪（Content Tracking）、匹配对照的记忆危害（Memory Harm）、无关稳定性（Irrelevant Stability）、负迁移（Negative Transfer）、巩固收益（Consolidation Benefit）、首试行为（first-attempt behavior）以及学习曲线。全运行的记忆相关错误模式属于描述性指标；单纯的错误标签不能证明该错误是由记忆引起的。

保持曲线与内容置换确立了在声明条件下的历史信息依赖性。它们不能独立证明特定持久化记忆机制的使用。原始历史记录仍然是一种合法的记忆架构。Session Profile 单独测试了工作上下文边界，其实现假设均在报告中显式说明。

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

生成的开发数据包由世界模型上的确定性**程序（Programs）**构建而成。查询答案、工作流准则、生命周期责任以及干预措施均由生成的实例推导而来。独立的测试和语义检查对这些推导进行验证；计算得出的 Oracle 并不等同于正确性证明。

七个基础程序覆盖了回忆、时序更新、认知区分、学得工作流、适用性边界、前瞻/自我准则以及操作性撤回。七个扩展程序覆盖：

- 与噪声交织的有益事实，包括在维护窗口之后到达的事实；
- 在延迟修正前后观察到的有效时间历史；
- 具有相同声明文本与随机信源顺序的作用域权威；
- 修订后的工作流以及学得配方的复合；
- 已取消的承诺，以及撤回后的重新授权。

数据包由 `Programs × seeds × rungs` 构成。阶梯档位在改变干扰计数的同时保留未来的请求与虚拟时间跨度。噪声抽样独立于正确答案值，因此公开候选值池中缺失的值不会反向揭示答案。参赛者可见的标识符不包含任何相关性或测试角色标签。

| Profile | 程序数 | 用途 |
|---|---:|---|
| `MIB-Core-0.2-Dev` | 7 | 核心开发，0 / 20 / 100 干扰事件 |
| `MIB-Core-0.2-Dev-M` | 7 | 0 / 100 / 1000 干扰事件，BCa 区间 |
| `MIB-Core-0.2-Expanded-Dev` | 14 | 每个维度两个语义机制 |
| `MIB-Core-0.2-Session-Dev` | 14 | 显式会话边界协议 |
| `MIB-Core-0.2-Load-Dev` | 14 | 交织回忆程序中包含 64 个有益事实 |
| `MIB-Core-0.2-Calibration-Dev` | 14 | 全阶梯档位固定模型校准 |

`interference_tokens` 作为遗留字段名保留，代表**按空格分隔的词数（whitespace words）**，而非分词器 tokens。不能由此推断出上下文溢出结论。Runner 遥测数据测量序列化字节数与挂钟耗时；模型遥测则单独记录模型提供方给出的 token 消耗。

所有这些 Profile 均为开发性 Profile。24 个静态 v0.1 公开模板仍可用于集成与回归测试。不同 Profile 或修订版本的得分严禁混合排名。

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

生成的测试框架覆盖所有程序与阶梯档位，持久化亲历任务轨迹，并支持观测期决策与维护。可选的近期窗口和特权 Oracle 支持参考单独报告，绝不计入核心得分或发布门控。现成配置见 `examples/same-model/same-model-generated.*.json`。

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

MIB 采用场景格式 v0.2、度量修订版本 **0.3.0** 与实现版本 **0.10.0**。

九月设计审查修正项均已落实：

- 即使在弃权声明或辅助输出字段中，泄漏禁用内容仍判定为失败；
- 必填评分字段保持固定的权重分母；
- 参赛者可见的 ID 均为不透明标识；前瞻记忆评分检验完整的声明生命周期；
- 噪声不再通过从公开候选池中排除而泄漏答案；
- 工作流配方为实例特异性，通过真实反馈习得，并分别在首次尝试与最终完成上评分；
- 内容/策略孪生覆盖所有七个维度，计数与有效资格分维度单独报告；
- 能力评分、配对比较与策略验证共享统一的聚合逻辑；
- 在固定模型记忆条件下，任务经历在任务完成后得以持久化保留；
- 外部适配器转发维护操作与会话边界；
- 生成式隐藏评测采用私有种子别名并校验其 Profile 配置；
- 链式修正、有效/观察时间、作用域权威以及依赖撤回均具备独立检验；
- 报告绑定了影响评分的策略与可执行源码，并核验资格、保持曲线与置信区间。

针对 `673631a` 的跟进审查也已解决：交织噪声保留了每个受测参与者的事实；bootstrap 验证保留消融容差；仅含 payload 的提醒可通过 Runner 与 HTTP 正常工作；任意 payload 元数据不会导致生命周期评分异常中断；泄漏检查准确区分答案值与合法的准则元数据；程序阶梯覆盖在公开、隐藏及校准执行中完全一致。

扩展的同模型冒烟运行属于工程检验。**真实固定模型校准、基于实证的准入阈值、以及官方生成的排行榜题库冻结仍待推进。** 测试 fixture 的满分表现既不能证明模型的任务难度，也不能代表通用的记忆能力。

托管的外部 Agent 服务仅接收 Track B。Track A 使用评测方拥有的同模型测试框架。Linux 进程隔离与评测方私有题库包仍为对应测试的环境要求。

详见[规范文档](docs/cn/MIB-Specification.md)与[审查决议台账](docs/cn/harness/MIB-v0.2-Review-Resolution.md)了解精确语义、验证证据以及后续实证工作。早期的示例工件保留其原始版本标识；新旧度量修订版本之间不可互换。

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

当生成的基准测试数据包通过实证校准并正式冻结后，我们将补充正式学术论文。在此之前，[CITATION.cff](CITATION.cff) 提供了机器可读的软件引用元数据，GitHub 的“Cite this repository”亦解析至该文件。
