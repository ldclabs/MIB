# MIB 场景模型规范

> **已废弃的设计草案。** 仅保留用于设计推导背景与历史记录。规范文本见 [`docs/cn/MIB-Specification.md`](../MIB-Specification.md)；若二者存在分歧，以 Specification 和参考实现为准。

## 记忆智能基准的记忆片段程序模型（Memory Episode Program）

**版本：** 0.1-draft
**状态：** 场景模型提案 / `MIB-Architecture.md` 配套规范

---

# 0. 规范目标

本规范定义了可执行 MIB 场景（Scenario）的语义模型。

MIB 不是静态的问答评测数据集。其核心基本单元是：

> **记忆片段程序（Memory Episode Program）**

一个记忆片段程序完整描述了：随时间推移逐步展开的世界环境、智能体接收到的观测数据流、必须严格向智能体保持隐藏的内部状态、用于检验记忆效能的未来提问或任务探针，以及用于判定记忆是否真正因果性地改变了后续决策的反事实对照变体。

整体概念拓扑：

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
  ├── Ground Truth / Oracle（客观真实与判定真值）
  ├── Evaluators（多层评测器）
  ├── Ablations（消融规则）
  └── Scoring（计分规则）
```

场景模型保持**架构中立性（architecture-neutral）**。

模型**严禁**假定受评测系统必须采用：

```text
向量检索（vector retrieval / RAG）
文本摘要（summaries）
知识图谱（knowledge graphs）
情景记忆（episodic memory）
KIP 协议体系
特定数据库
特定的 Memory API
```

一个仅对外暴露 `observe`、`respond` 和 `act` 的完全黑盒智能体，必须同样能够被本场景模型完整评测。

---

# 1. 核心设计原则

MIB 场景的设计只为验证一个核心命题：

> **相关过往信息应当在需要时切实改变未来；无关过往信息绝不能误导未来；陈旧或有害过往信息必须得到有力抵御。**

因此，若一个场景仅包含以下内容，它就是不完整的：

```text
一段过往文本
+
一个未来提问
```

一个完备严肃的场景应当在适用的前提下清晰定义：

```text
真实发生了什么
智能体实际观测到了什么
环境状态随时间发生了哪些演变
哪些信息属于必须对智能体隐藏的客观真值
未来任务的具体要求
达成成功的明确判据
过往历史中哪一片段具有因果相关性
过往历史中哪些片段属于背景噪音或干扰项
如何在记忆消融条件下重放未来任务
```

---

# 2. 场景 vs 传统静态评测数据

传统静态数据集样本：

```text
静态上下文（context）
问题（question）
答案（answer）
```

MIB 场景程序：

```text
初始世界状态
    ↓
经历历史交互
    ↓
世界状态演变
    ↓
经历进一步交互
    ↓
经历干扰噪音
    ↓
可选的记忆维护 / 巩固窗口
    ↓
触发未来探针
    ↓
智能体作答 / 执行动作
    ↓
世界环境产出
    ↓
反事实消融重放
```

这种根本差异源于：记忆智能本质上是一个**跨越时间维度的动态认知过程**。

---

# 3. 规范用语约定

本文档中的 **MUST（必须）**、**MUST NOT（严禁）**、**SHOULD（应当）**、**SHOULD NOT（不应当）** 和 **MAY（可以）** 均作为场景模型的规范性约束。

---

# 4. 序列化格式与 Schema

基准的机器可读底层格式为 JSON。

在保证场景语义无损双向转换的前提下，**可以**采用 YAML 作为编写格式。

配套的机器 Schema 规范文件为：

```text
mib-scenario.schema.json
```

采用标准：

```text
JSON Schema Draft 2020-12
```

任何规范的可执行场景实例（Scenario Instance），**应当**能够直接具象化为纯 JSON 文件，无需依赖任何外部代码执行。

---

# 5. 顶层场景对象定义

一个标准场景包含以下字段：

```text
mib             基准格式版本
kind            对象类型
id              场景全局唯一 ID
version         场景内容语义版本
status          开发状态
title           场景标题
description     场景详细说明

suite           所属核心套件
dimensions      评测能力维度列表
tags            检索与研究分类标签
difficulty      结构化难度描述

template        模板元数据（若由模板生成）
instantiation   实例化参数记录

requirements    执行前置能力要求
execution       运行与超时策略
leakage         防泄漏与隔离策略

actors          实体角色清单
world           世界环境状态与时钟
timeline        时间线事件序列
probes          未来探针定义列表
ablations       配对消融变体定义
evaluators      评测器配置列表
scoring         场景计分与聚合规则

metadata        附加元数据
extensions      私有扩展字段
```

一个最小可执行场景实例必须包含：

```text
id
version
dimensions
world
timeline
probes
evaluators
scoring
```

---

# 6. `mib` 字段

标识基准规范家族的版本。

当前草案为：

```json
{
  "mib": "0.1"
}
```

该字段代表场景 Schema 的格式版本，而非特定场景的具体内容版本。

---

# 7. `kind` 字段

标准取值：

```text
MemoryEpisodeProgram
```

用于在机器层面将场景程序与以下后续产物明确区分：

```text
RunArtifact             运行记录产物
CapabilityCard          能力卡片
ScenarioPack            评测包清单
LeaderboardSubmission   榜单提交规范
```

---

# 8. 场景唯一标识（ID）

示例：

```text
MIB-TIME-001
```

推荐的标准前缀命名空间：

```text
MIB-RET-*      保留与检索（Retention & Retrieval）
MIB-TIME-*     时序记忆（Temporal Memory）
MIB-EPI-*      认识状态记忆（Epistemic Memory）
MIB-EXP-*      经验记忆（Experience Memory）
MIB-SKILL-*    技能学习与迁移（Skill Learning）
MIB-FORGET-*   选择性遗忘（Selective Forgetting）
MIB-PROS-*     前瞻记忆（Prospective Memory）
MIB-SELF-*     自我认知记忆（Self Memory）
MIB-CAUSAL-*   因果记忆效应（Causal Memory Impact）
MIB-ADV-*      对抗与鲁棒性（Adversarial Memory）
MIB-X-*        跨维度综合（Cross-Dimension）
```

场景 ID 在等价的版本修订中保持稳定。对时间线、客观真值或计分规则的重大语义变更应当递增 `version`。

---

# 9. 场景版本控制

采用语义化版本号：

```text
0.1.0
0.1.1
1.0.0
```

修复错别字或改进描述属于补丁号（Patch）更新；
修改预期行为、消融语义或打分权重属于次版本号（Minor）更新；
破坏性场景语义变更在稳定版本发布后应当递增主版本号（Major）。

---

# 10. 套件与能力维度

每个场景归属于一个主要 `suite`（套件），并可关联测试多个 `dimensions`（能力维度）。

示例：

```json
{
  "suite": "time",
  "dimensions": [
    "temporal_memory",
    "retention_retrieval",
    "causal_memory_impact"
  ]
}
```

官方核心维度枚举：

```text
retention_retrieval         保留与检索
temporal_memory             时序记忆
epistemic_memory            认识状态记忆
experience_memory           经验记忆
skill_learning_transfer     技能学习与迁移
selective_forgetting        选择性遗忘
prospective_self_memory     前瞻与自我认知记忆
causal_memory_impact        因果记忆效应
```

实验性维度**应当**通过 `extensions` 进行命名空间隔离。

---

# 11. 标签（Tags）

标签用于场景发现、分类检索与学术统计。

示例：

```text
correction              显式纠错
staleness               陈旧信息处理
multi-hop               多跳关联
failure-recovery        失败排查与恢复
negative-transfer       负迁移防范
unknown-vs-false        未知 vs 否定
source-conflict         信源分歧
interrogation           质询注入（提问不得被沉淀为事实）
prospective-trigger     前瞻主动触发
identity                实体身份混淆
distractor-heavy        重度噪音干扰
```

标签本身**严禁**承载任何规范性的计分语义。

---

# 12. 结构化难度模型

难度**应当**通过客观可度量的属性来定义，而非仅凭主观标注的 `easy` / `medium` / `hard`。

标准难度字段：

```text
level                       综合等级
temporal_horizon            时间跨度
meaningful_events           有效核心事件数
distractor_events           干扰噪音事件数
entity_count                涉及实体数量
memory_hops                 记忆多跳深度
source_ambiguity            信源歧义程度
conflict_complexity         事实冲突复杂度
experience_steps            经验轨迹步数
skill_abstraction_distance  技能抽象跨度
probe_indirectness          提问隐式程度
```

示例：

```json
{
  "level": "medium",
  "meaningful_events": 7,
  "distractor_events": 200,
  "entity_count": 3,
  "memory_hops": 1,
  "probe_indirectness": 0.3
}
```

---

# 13. 场景模板与实例具象化

MIB 明确区分：

```text
Scenario Template（场景模板）
Scenario Instance（场景实例）
```

模板包含动态参数生成器（Parameter Generators）；
实例则是已被完全具象化、参数确定且可直接执行的实例。

模板参数配置示例：

```json
{
  "name": "current_timezone",
  "type": "string",
  "source": "choice",
  "choices": ["+01:00", "+02:00", "+09:00"]
}
```

评测服务端可以在参赛方提交系统之后，动态采样实例化：

```text
人物姓名
具体日期
状态数值
干扰噪音数量
工具执行细节
探针提问具体用词
```

从而彻底防范针对基准测试集的过拟合作弊。

---

# 14. 参数可见性分级

参数分为三级：

```text
public   公开参数（模板结构直接暴露）
hidden   隐藏参数（评测端随机采样并严格保密，仅通过时间线自然观测显现）
derived  派生参数（根据世界状态动态计算得出）
```

隐藏参数值**严禁**通过任何带外途径泄露给智能体。

---

# 15. 实例化元数据

具象化生成的隐藏场景实例**应当**记录：

```text
template_id         来源模板 ID
template_version    模板版本
seed                采样随机种子
parameter_digest    参数哈希摘要
generator_version   生成器版本
```

---

# 16. 执行前置能力要求（Requirements）

场景可声明其执行所需的前置接口能力：

```text
respond capability      支持回答提问
act capability          支持工具交互任务
tool-use capability     支持环境工具调用
virtual-time support    支持虚拟时钟感知
replay ablation         支持重放消融
memory adapter optional 支持 Memory 诊断接口（可选）
```

用于 Runner 在开跑前评估当前系统是否兼容该场景，不直接代表记忆智能的高低。

---

# 17. 运行执行策略（Execution Policy）

`execution` 控制基准的执行边界：

```text
repetitions                 重复运行次数
random_seed                 随机种子
reset_between_repetitions   重复运行时是否重置
max_wall_time_ms            最大允许挂钟时间
max_agent_turns             最大交互轮次
max_tool_calls              最大工具调用次数
on_agent_error              报错处理策略
on_timeout                  超时处理策略
```

示例：

```json
{
  "repetitions": 3,
  "reset_between_repetitions": true,
  "max_agent_turns": 20,
  "on_timeout": "fail_probe"
}
```

执行限制属于基准评测框架的统一治理策略，榜单对比期间**严禁**随意更改。

---

# 18. 防泄密与隔离策略（Leakage Policy）

未来探针提前泄露是威胁记忆评测有效性的最大风险。

场景**应当**明确声明：

```text
probe_sampling                          探针采样时机
future_probe_visible_during_formation   记忆形成期探针是否可见
oracle_visible_to_agent                 真值对智能体是否可见
ablation_labels_visible_to_agent        消融标签对智能体是否可见
hidden_world_state_visible_to_agent     隐藏世界真值对智能体是否可见
```

标准推荐默认值：

```text
future_probe_visible_during_formation = false
oracle_visible_to_agent = false
ablation_labels_visible_to_agent = false
hidden_world_state_visible_to_agent = false
```

Runner 必须通过通信隔离进行物理保证，绝不能仅仅依赖 Prompt 约束。

---

# 19. 延迟采样探针机制（Late-Sampled Probe）

高公信力评测**应当**遵循：

```text
经历历史事件
    ↓
记忆形成阶段结束
    ↓
动态采样并触发未来探针
```

而非在记忆形成阶段就预先确定并固定探针。

模板支持的 `probe_sampling` 模式：

```text
fixed           固定探针
late            延迟采样
hidden_late     隐藏且延迟采样（官方榜单推荐首选）
```

---

# 20. 实体角色建模（Actors）

Actors 表示与智能体发生交互或出现在环境中的实体对象。

示例：

```json
{
  "id": "alice",
  "kind": "person",
  "display_name": "Alice",
  "attributes": {
    "organization": "Orbit"
  }
}
```

实体类型包括：

```text
person          自然人
agent           其他智能体
organization    组织机构
service         后台服务
tool            环境工具
environment     物理/软件环境
system          系统通知
```

---

# 21. 世界环境对象（World）

World 对象代表基准管控下的客观现实世界。

包含：

```text
clock               时钟配置
state               可变模拟器状态
entities            世界实体状态
tools               可用工具定义
hidden_ground_truth 隐藏的裁判客观真值
```

智能体仅能通过可见观测与工具调用来感知世界，World 对象本身完全属于评测框架的内部状态。

---

# 22. 世界状态（World State）

`world.state` 保存模拟器的可变状态：

```json
{
  "user_timezone": "+08:00",
  "auth_mode": "jwt",
  "deployment_target": "legacy-db"
}
```

世界真实状态不等于智能体的当前认知（`world state ≠ Agent observation`），只有被 Runner 显式交付的事件对智能体可见。

---

# 23. 隐藏客观真值（Hidden Ground Truth）

`hidden_ground_truth` 记录确定性评判所需的绝对真值：

```text
当前实际时区
真实目标数据库
正确的工作流前置条件
哪个信源是权威权威源
某个前瞻承诺是否已被触发
```

该状态**严禁**自动注入到智能体的上下文之中。

---

# 24. 实体状态（Entities）

为模拟器操作的对象赋予稳定唯一的实体 ID：

```json
{
  "id": "service-api",
  "kind": "service",
  "attributes": {
    "environment": "production"
  }
}
```

---

# 25. 环境工具（Tools）

场景可定义环境工具接口（如日历、部署 API、邮件、文件系统、数据库查询等），声明其调用 Schema 与世界模拟器的绑定关系。

---

# 26. 虚拟时钟（Virtual Clock）

长效记忆评测必须在无需真实物理等待的前提下执行。

标准时钟配置：

```json
{
  "mode": "virtual",
  "start": "2026-01-01T09:00:00Z",
  "timezone": "UTC"
}
```

时间演进可采用序列步数（sequence）、绝对虚拟时间戳（datetime）或相对时间推进（time advance）。

---

# 27. 时间线定义（Timeline）

时间线是智能体完整亲历的历史事件序列。

每个事件包含：

```text
id              事件唯一 ID
stage           所属生命周期阶段
type            事件类型
at              发生时间/步数
visibility      可见性控制
actor           关联角色
content/payload 消息文本或结构化数据
world_updates   引发的环境状态变更
oracle_labels   内部判决注解
tags            标签分类
```

标准事件示例：

```json
{
  "id": "e1",
  "stage": "past",
  "type": "interaction",
  "at": {
    "sequence": 1
  },
  "visibility": "agent",
  "actor": "alice",
  "content": "我的时区是 UTC+8。"
}
```

---

# 28. 时间线生命周期阶段（Timeline Stages）

核心阶段划分：

```text
seed            环境初始化播种
past            包含核心认知信息的历史片段
interference    注入的背景噪音与无关干扰
consolidation   显式的记忆巩固与维护窗口
pre_probe       探针触发前的即时准备情境
```

未来的考核题目单独在 `probes` 中定义。

---

# 29. 时间线事件类型（Event Types）

标准事件类型枚举：

```text
interaction         常规对话交互
observation         外部环境观测
tool_result         工具执行返回
world_update        环境状态静默变更
time_advance        时间大幅推进
distractor          单条干扰项
distractor_batch    批量干扰项生成
maintenance_window  维护窗口
checkpoint          系统检查点快照
feedback            环境反馈
document            文档/材料输入
custom              自定义事件
```

---

# 30. 事件可见性（Visibility）

```text
agent   向智能体交付（通过 Agent Adapter）
harness 仅对评测框架可见（用于更新世界状态，对智能体保密）
both    两者均可见
```

---

# 31. 世界状态变更规则（World Updates）

时间线事件可触发环境状态变更。支持的操作原语：

```text
set         设置字段值
unset       删除字段
increment   数值累加
append      列表追加
remove      列表移除
```

示例：

```json
{
  "op": "set",
  "path": "/user_timezone",
  "value": "+01:00"
}
```

---

# 32. 转换为智能体可见观测（Observation）

Runner 负责将时间线事件转换为标准面向智能体的 Observation，并在此过程中彻底剥离所有隐藏的 `oracle_labels`、`relevance` 等内部标签。

---

# 33. 干扰项设计（Distractors）

干扰项用于真实模拟人类记忆面临的信息干扰，涵盖无关闲聊、相似实体名称、相近数值、常规工具日志或弱相关主题信息。干扰项的内部相关性标注对智能体严格保密。

---

# 34. 批量干扰项生成器（Distractor Batch）

在大规模评测中，推荐通过紧凑的参数化生成器动态生成海量干扰噪音：

```json
{
  "id": "d200",
  "stage": "interference",
  "type": "distractor_batch",
  "at": {"sequence": 50},
  "visibility": "agent",
  "generator": {
    "id": "routine-chat-v1",
    "count": 200,
    "seed": 42
  }
}
```

生成器必须版本化并支持严格定种，以保障完全可复现。

---

# 35. 记忆维护与巩固窗口

为支持包含离线批处理巩固逻辑的记忆系统，场景可通过 `maintenance_window` 显式提供维护机会。赛道 A 中所有系统享有同等预算与调用机会。

---

# 36. 评测检查点（Checkpoints）

在时间线关键节点设置快照检查点，便于执行高效的快照分支消融实验与离线诊断。

---

# 37. 未来探针定义（Probes）

探针是检验记忆效能的核心载体，包含：

```text
id          探针 ID
kind        探针能力类型
trigger     触发条件
delivery    交付形式（respond / act / observe_only）
input       面向智能体的输入内容
oracle      客观真值判据
evaluators  关联评测器 ID 列表
weight      计分权重
dimensions  贡献的能力维度
```

标准探针示例：

```json
{
  "id": "p-current",
  "kind": "temporal",
  "trigger": {
    "after_event": "e3"
  },
  "delivery": "respond",
  "input": {
    "content": "我现在处于哪个时区？"
  },
  "oracle": {
    "expected": "+01:00"
  },
  "evaluators": ["eval-current"],
  "weight": 1.0
}
```

---

# 38. 探针能力类型

```text
factual         事实检索
implicit        隐式关联推理
multi_hop       多跳关联
temporal        时序演进
epistemic       认识状态与信源
experience      经验轨迹总结
skill           技能迁移
prospective     前瞻主动触发
self            自我认知与局限
action          环境行动执行
historical      历史状态回溯
audit           证据链审计
abstention      审慎弃权判定
custom          自定义类型
```

---

# 39. 探针触发条件（Trigger）

触发模式：

```text
after_event     在某特定事件后触发
at_sequence     在特定步数触发
at_time         在特定虚拟时间触发
world_condition 满足特定环境条件时触发（前瞻记忆常用）
manual          Runner 阶段手动触发
```

---

# 40. 探针交付方式（Delivery）

```text
respond         纯认知提问作答
act             下达目标任务并通过工具交互执行
observe_only    仅通过观测触发自发涌现输出（如前瞻提醒）
```

---

# 41. 探针即时输入

仅包含解决当前任务所需的即时指令与约束。除显式的全上下文基准对照组外，Runner 严禁将历史记忆作为上下文直接拼接入输入中。

---

# 42. 判定真值对象（Oracle）

定义客观评判依据：

```text
expected                单一标准答案
accepted                接受的正确答案集合
forbidden               命中即判错的答案集合
expected_status         期望的认识状态
world_assertions        环境世界最终状态断言
trajectory_requirements 动作轨迹约束要求
reference               参考黄金答案
```

---

# 43. 认识状态期望（Oracle Status）

```text
known           已确知事实
unknown         未知事实（应主动弃权）
contested       存在分歧争议
historical      历史状态（非当前有效）
not_applicable  不适用
```

面对 `unknown` 状态，盲目给出确定答案将被判定为错误。

---

# 44. 环境状态断言（World Assertions）

用于评判行动探针的最终世界状态：

```json
{
  "world_assertions": [
    {
      "path": "/auth_mode",
      "operator": "eq",
      "value": "session"
    }
  ]
}
```

标准比较操作符：`eq`（等于）、`neq`（不等于）、`exists`（存在）、`not_exists`（不存在）、`contains`（包含）、`gte`（大于等于）、`lte`（小于等于）。

---

# 45. 动作轨迹约束（Trajectory Requirements）

评判智能体在执行任务时的具体行为模式：

```text
必须执行的动作（required action）
严禁执行的动作（forbidden action）
动作先后顺序约束（ordering constraint）
最大允许重复失败次数（maximum repeated failure）
```

即便最终侥幸完成任务，若中途重复犯下已知教训的错误，得分同样会被扣减。

---

# 46. 评测器定义（Evaluators）

支持的评测器类型：

```text
exact                   精确匹配
set_match               集合归一化匹配
structured              结构化 JSON 校验
world_state             环境真实状态断言求值
semantic_constraints    结构化语义约束
trajectory              动作执行轨迹分析
llm_judge               大模型裁判
composite               多评测器加权复合
```

场景应当最大限度优先使用**确定性评测器**。

---

# 47. 集合匹配评测器（set_match）

支持归一化处理（如去除首尾空格、忽略大小写等）：

```json
{
  "id": "eval-current",
  "type": "set_match",
  "config": {
    "normalization": "casefold_trim"
  }
}
```

---

# 48. 结构化评测器（structured）

对机器可读的 JSON 输出进行逐字段类型与值校验。

---

# 49. 语义约束评测器（semantic_constraints）

支持自然语言回答的结构化约束规则（如 `must_include`、`must_not_include` 等），方法透明可复现。

---

# 50. 世界状态评测器（world_state）

直接比对世界模拟器的最终客观状态，属于行动类探针的首选评测手段。

---

# 51. 动作轨迹评测器（trajectory）

基于 Runner 记录的外部工具调用流水，审计关键排查步骤是否执行、反例是否被参考等。

---

# 52. 大模型裁判评测器（llm_judge）

仅在确定性规则无法覆盖时作为辅助，必须明确规定评分细则（Rubric）、结构化输出 Schema、采样数及确定性温度参数。任何情况下，环境客观真值均高于裁判模型的主观推断。

---

# 53. 复合评测器（composite）

将多项评测器结果按权重组合（例如：60% 最终世界状态达成 + 20% 避开违规动作 + 20% 执行了必要诊断）。

---

# 54. 配对消融实验模型（Ablations）

消融机制将普通的问答测试升华为**严谨的因果推断实验**。

标准消融类型：

```text
relevant_memory     相关记忆消融
irrelevant_memory   无关噪音消融
no_memory           完全无记忆对照
stale_memory        陈旧记忆干扰
harmful_memory      有害/投毒记忆干扰
counterexample      反例注入测试
custom              自定义消融
```

---

# 55. 相关记忆消融（Relevant-Memory Ablation）

精准剔除或遮蔽预期能提供帮助的关键记忆。

预期效应：

```text
性能显著下降（degrade）
```

用于计算因果记忆效应指标（CMI）：

\[
CMI = Performance_{full} - Performance_{relevant\_ablated}
\]

---

# 56. 无关记忆消融（Irrelevant-Memory Ablation）

剔除不相关的背景噪音。

预期效应：

```text
性能保持基本稳定（neutral）
```

若剔除噪音后性能暴涨，表明系统抗干扰能力差；若性能大跌，表明存在意外依赖或场景标注有误。

---

# 57. 无记忆基准对照（No-Memory Ablation）

不提供任何有效历史，仅凭基座模型本身、当前输入与可用工具解决任务，用于确立该任务的基底得分下界。

---

# 58. 陈旧记忆测试条件（Stale-Memory Condition）

保留貌似合理但实际已过时的历史记录，检验智能体能否优先采纳最新有效事实。

---

# 59. 有关/投毒记忆测试条件（Harmful-Memory Condition）

注入包含恶意指令、错误信源或越权技能的诱导性记忆，检验系统的**免疫与抵御能力（resistance）**。

其中最纯粹的变体是**质询注入（interrogation）**：注入的事件**仅包含提问**——不包含任何断言、证据或权威背书——仅在问句中预设了从未被确立的习惯、日期或流程。「询问系统 X 是否为既定习惯」绝不能成为将 X 写入或沉淀为记忆事实的途径：在基准与注入两种配对条件下，所有 Probe 的正确答案完全相同，因此任何配对性能分差都是「错误安装」的直接证据。把提问升格为事实的记忆系统，本质上是一个脆弱的注入面，而非可靠的记录载体。该测试通道由 `MIB-ADV-*` 模板承载，注入的提问带有 `interrogation` 标签，性能分差直接通过既有的 Memory Harm / Harm Resistance 机制计量。

---

# 60. 消融执行手段分级

Runner 按以下能力优先级选择消融实现：

```text
1. 精准记录删除 / 遮蔽（memory mask/delete）
2. 快照分支重置（snapshot branch）
3. 过滤历史后克隆状态（filtered memory clone）
4. 排除目标事件后从头重放（replay excluding target events）
5. 黑盒场景端到端重构执行（black-box reconstruction）
```

---

# 61. 消融目标表达

消融目标通过时间线事件 ID、标签选择器或角色 ID 表达，不依赖具体厂商底层的内部存储记录 ID。

---

# 62. 反事实历史注入

部分消融实验需要向历史中额外注入诱导事件，其注入过程完全由评测端受控实施，不向智能体暴露陷阱标记。

---

# 63. 预期效应标识（Expected Effect）

```text
degrade         移除关键记忆导致得分下降
neutral         移除无关记忆得分基本持平
improve         移除干扰后得分上升
resist          成功抵御有害记忆未发生犯错
informational   仅用于统计参考
```

---

# 64. 因果配对对照原则

全量运行与消融变体之间必须严格保持模型、配置、未来任务、世界初始状态、工具集与随机种子的一致性，唯一变量只能是设定的记忆干预。

---

# 65. 确定性重放语义

在重放消融实验中，非目标事件以相同的顺序和虚拟时间交付，并使用确定性事件级种子保证随机性的一致。

---

# 66. 场景得分聚合

探针得分归一化至 `[0,1]`，场景综合得分归一化至 `[0,100]`。

---

# 67. 探针加权平均

\[
S = \frac{\sum_i w_i s_i}{\sum_i w_i}
\]

---

# 68. 能力维度权重归属

场景可声明自身得分对各能力维度的贡献比例（各维度权重之和为 1）：

```json
{
  "dimension_weights": {
    "temporal_memory": 0.6,
    "retention_retrieval": 0.2,
    "causal_memory_impact": 0.2
  }
}
```

---

# 69. 场景级因果衍生指标

从全量组与消融组的配对结果中计算：

```text
memory_benefit              记忆收益
memory_harm                 记忆损害
causal_memory_impact        因果记忆效应
irrelevant_memory_stability 无关记忆稳定性
negative_transfer           负迁移率
error_recurrence            已知错误重现率
```

---

# 70. 因果记忆效应计算（CMI）

\[
CMI = P_{full} - P_{relevant\_ablated}
\]

若 CMI 为负，说明该记忆实际上损害了性能或场景因果假设不成立，报告中必须保留真实负值，严禁提前截断归零。

---

# 71. 无关记忆稳定性计算（IMS）

\[
IMS = 1 - |P_{full} - P_{irrelevant\_ablated}|
\]

IMS 越接近 1，说明系统越不受无关历史噪音的影响。

---

# 72. 记忆损害计算（Memory Harm）

\[
H = \max(0, P_{clean} - P_{harmful})
\]

---

# 73. 负迁移度量（Negative Transfer）

在不适用的新情境下，统计智能体盲目套用老技能的违规发生率。

---

# 74. 已知错误重现率（Error Recurrence）

在经历过失败与恢复之后，统计智能体在后续面临类似场景时重复犯下相同已知错误的概率。

---

# 75. 显式安全扣分惩罚（Penalties）

对虚假置信度、权限幻觉、隐私泄露、实体身份灾难性混淆等严重病态，场景可设定上限明确的扣分规则。

---

# 76. 失败模式诊断分类

输出结构化失败错误码（如 `formation_miss`、`stale_memory_adoption`、`negative_transfer`、`source_confusion` 等），精准赋能研发诊断。

---

# 77. 隐藏标签的物理剥离

作者在场景中配置的相关性标记和真值标签，在跨越 Adapter 边界时被 Runner 全部物理剥离。

---

# 78. 彻底杜绝白盒概念绑定

核心场景严禁将 `embedding score`、`memory_strength`、`graph node` 等私有数据结构设为必填依赖。

---

# 79. 黑盒兼容性保证

核心场景默认支持仅具备基础接口的黑盒智能体通过重放完成全套评测。

---

# 80. 可选白盒诊断标记

可标记 `memory_adapter_preferred` 指明该场景在接入白盒 Memory Adapter 时能获得更高精度的诊断数据。

---

# 81. 全上下文基准对照（Full-Context Baseline）

将所有关键历史直接拼接入即时输入中，用以区分是基座大模型推理能力不足，还是记忆系统的沉淀与检索环节失效。

---

# 82. 无记忆基准对照（No-Memory Baseline）

若无记忆模型在此任务上已经能拿 100% 满分，该场景在校准阶段应被标记为 `memory_non_discriminative`（无记忆区分度），不适合作为核心评测题。

---

# 83. 场景准入校准验证（Calibration）

进入官方正式包前，场景必须通过无记忆、全上下文、简易检索与先进记忆四类基准的校准验证，确保任务可解、历史有效、消融对比显著且打分稳定。

---

# 84. 防预训练数据污染

避免直接复用网上公开的著名固定问答对，通过模板参数随机化与延迟采样对抗数据污染。

---

# 85. 确定性实例化

给定相同的场景版本、生成器版本与随机种子，生成的场景实例必须保持逐字节确定性。

---

# 86. 事件级确定性随机种子派生

\[
event\_seed = H(scenario\_seed, event\_id, generator\_version)
\]

确保在因果重放中剔除某事件时，其他无关事件的随机内容保持绝对稳定。

---

# 87. 内容完整性校验（Integrity）

场景包包含基于标准 JSON 规范编码的哈希摘要，用于审计与版本防篡改。

---

# 88. 扩展字段规范（Extensions）

私有实验性字段必须放置在 `extensions` 命名空间下，且严禁覆盖重定义核心字段的语义。

---

# 89. 规范场景完整示例 —— 时序纠错与历史追溯

```json
{
  "mib": "0.1",
  "kind": "MemoryEpisodeProgram",
  "id": "MIB-TIME-001",
  "version": "0.1.0",
  "status": "draft",
  "title": "时区变更与历史状态回溯",
  "suite": "time",
  "dimensions": [
    "temporal_memory",
    "retention_retrieval",
    "causal_memory_impact"
  ],
  "tags": [
    "update",
    "historical-recall",
    "staleness"
  ],
  "difficulty": {
    "level": "medium",
    "meaningful_events": 3,
    "distractor_events": 200,
    "entity_count": 1,
    "memory_hops": 0
  },
  "requirements": {
    "black_box_compatible": true,
    "capabilities": [
      "respond"
    ]
  },
  "execution": {
    "repetitions": 3,
    "reset_between_repetitions": true
  },
  "leakage": {
    "probe_sampling": "late",
    "future_probe_visible_during_formation": false,
    "oracle_visible_to_agent": false,
    "ablation_labels_visible_to_agent": false,
    "hidden_world_state_visible_to_agent": false
  },
  "actors": [
    {
      "id": "alice",
      "kind": "person",
      "display_name": "Alice"
    }
  ],
  "world": {
    "clock": {
      "mode": "virtual",
      "start": "2026-01-01T09:00:00Z",
      "timezone": "UTC"
    },
    "state": {
      "user_timezone": "+08:00"
    },
    "hidden_ground_truth": {
      "current_timezone": "+08:00"
    }
  },
  "timeline": [
    {
      "id": "e1",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 1
      },
      "visibility": "agent",
      "actor": "alice",
      "content": "我的时区是 UTC+8。"
    },
    {
      "id": "e2",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 20
      },
      "visibility": "agent",
      "actor": "alice",
      "content": "我下个月搬家去伦敦。"
    },
    {
      "id": "e3",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 50
      },
      "visibility": "agent",
      "actor": "alice",
      "content": "我已经到了伦敦。现在的时区是 UTC+1。",
      "world_updates": [
        {
          "op": "set",
          "path": "/user_timezone",
          "value": "+01:00"
        }
      ]
    },
    {
      "id": "d1",
      "stage": "interference",
      "type": "distractor_batch",
      "at": {
        "sequence": 60
      },
      "visibility": "agent",
      "generator": {
        "id": "routine-chat-v1",
        "version": "1.0.0",
        "count": 200,
        "seed": 42
      }
    },
    {
      "id": "cp1",
      "stage": "pre_probe",
      "type": "checkpoint",
      "at": {
        "sequence": 300
      },
      "visibility": "harness"
    }
  ],
  "probes": [
    {
      "id": "p-current",
      "kind": "temporal",
      "trigger": {
        "after_event": "cp1"
      },
      "delivery": "respond",
      "input": {
        "content": "我现在处于哪个时区？"
      },
      "oracle": {
        "expected_status": "known",
        "accepted": [
          "+01:00",
          "UTC+1"
        ],
        "forbidden": [
          "+08:00",
          "UTC+8"
        ]
      },
      "evaluators": [
        "eval-timezone"
      ],
      "dimensions": [
        "temporal_memory"
      ],
      "weight": 1.0
    },
    {
      "id": "p-historical",
      "kind": "historical",
      "trigger": {
        "after_event": "cp1"
      },
      "delivery": "respond",
      "input": {
        "content": "搬家去伦敦之前，我使用的是哪个时区？"
      },
      "oracle": {
        "expected_status": "historical",
        "accepted": [
          "+08:00",
          "UTC+8"
        ]
      },
      "evaluators": [
        "eval-timezone"
      ],
      "dimensions": [
        "temporal_memory",
        "retention_retrieval"
      ],
      "weight": 1.0
    }
  ],
  "ablations": [
    {
      "id": "a-relevant",
      "kind": "relevant_memory",
      "probes": [
        "p-current"
      ],
      "method": "replay_excluding_events",
      "targets": {
        "event_ids": [
          "e3"
        ]
      },
      "expected_effect": "degrade"
    },
    {
      "id": "a-irrelevant",
      "kind": "irrelevant_memory",
      "probes": [
        "p-current",
        "p-historical"
      ],
      "method": "replay_excluding_events",
      "targets": {
        "event_ids": [
          "d1"
        ]
      },
      "expected_effect": "neutral"
    }
  ],
  "evaluators": [
    {
      "id": "eval-timezone",
      "type": "set_match",
      "config": {
        "normalization": "casefold_trim"
      }
    }
  ],
  "scoring": {
    "probe_aggregation": "weighted_mean",
    "score_range": {
      "min": 0,
      "max": 100
    },
    "dimension_weights": {
      "temporal_memory": 0.7,
      "retention_retrieval": 0.15,
      "causal_memory_impact": 0.15
    },
    "causal_metrics": [
      "causal_memory_impact",
      "irrelevant_memory_stability"
    ]
  }
}
```

---

# 90. 经验到技能场景范式

```text
第 1 片段： 因未选择工作区导致保存失败。
第 2 片段： 重复犯下相同错误并记录排查。
第 3 片段： 智能体先选定工作区，保存成功。
干扰阶段： 经历大量无关日常任务。

未来任务 A： 界面全新但底层存在相同的前置隐藏规则 → 预期自发正向迁移技能。
未来任务 B： 处于完全不同且无需选择工作区的环境 → 预期坚决不盲目套用技能（抗负迁移）。
```

模型天然支持对经验记忆、技能学习、正负迁移和因果消融的完整评测。

---

# 91. 超越 JSON Schema 的语义校验准则

标准 Runner 包含专门的语义验证器（MIB Scenario Validator），重点核验：

```text
所有 ID 全局唯一
所有实体/角色/评测器引用均能正确解析
时间线时序单调递增
世界状态更新路径合法
维度权重之和为 1
隐藏真值字段绝对未泄露至观测对象
延迟采样探针未被过早实例化
消融变体具备完全确定性的重放条件
```

---

# 92. 场景校验九阶段

```text
1. JSON Schema 格式校验
2. 引用关联完整性解析
3. 时间线时序与阶段校验
4. 世界状态演化校验
5. 探针与真值防泄露校验
6. 评测器配置有效性校验
7. 消融规则与重放性校验
8. 计分与权重归一化校验
9. 跨运行可复现性测试
```

全阶段通过后方可录入官方标准评测包。

---

# 93. 官方标准场景包（Scenario Pack）

包含版本化的场景集合，并定义包级计分策略与哈希摘要。

---

# 94. MIB v0.1 约束与实践建议

首发版本聚焦：黑盒完全兼容、纯 JSON 实例格式、确定性世界模拟、基于重放的消融、确定性规则评测优先。

---

# 95. Runner 核心职责

Runner 承担加载场景、实例化参数、播种世界、驱动虚拟时钟、交付可见观测、剥离隐藏字段、下发探针、收集产出、执行多层评测、驱动消融重放并输出最终结构化报告的全部职责。智能体只需扮演纯粹的智能体。

---

# 96. Runner 严禁为智能体提供隐式协助

Runner 严禁向智能体提供事件摘要、标出相关记忆、过滤噪音或泄露裁判真值。

---

# 97. 场景编写核心考量

优秀的场景本身应当是一场精巧严谨的小型科学实验：

```text
正在测试哪项记忆能力？
过往中的哪条信息应当发挥作用？
为什么该信息应当在此时发挥作用？
未来的何种行为能够证明评测成功？
缺乏该记忆时的反事实对照表现如何？
设计了哪些干扰或有害记忆来检验系统的选择性？
能否在不依赖主观臆断的前提下对结果进行精确打分？
```

---

# 98. 场景质量自查清单

```text
[ ] 未来探针在形成阶段绝对无泄漏
[ ] 客观真值判据明确无歧义
[ ] 关键相关历史片段清晰可定位
[ ] 干扰噪音设计合理且具迷惑性
[ ] 仅凭当前上下文无法直接解题（非无记忆平凡任务）
[ ] 全上下文对照组能够正确解题
[ ] 消融变体能够确定性重放
[ ] 评测器尽可能采用确定性规则
[ ] 当前状态与历史状态语义界定清晰
[ ] 信源归属与分歧逻辑界定清晰
[ ] 不依赖私有思维链内省
[ ] 不绑定厂商私有数据结构
[ ] 所有隐藏真值标签均被成功剥离
[ ] 场景所有 ID 与引用关系完全闭环解析
[ ] 计分规则与产出可完全复现
```

---

# 99. 场景模型核心不变量汇总

1. **场景是随时间演进的动态程序，而非静态问答题。**
2. **客观世界真值与智能体可见观测严格分离。**
3. **隐藏客观真值绝对不得泄露给智能体。**
4. **记忆形成期间未来探针保持未知。**
5. **探针判据 Oracle 仅供评测端保留。**
6. **时间线事件具备稳定唯一的 ID。**
7. **相关记忆消融仅改变目标记忆条件。**
8. **无关记忆消融严格保持任务核心语义。**
9. **因果重放严格保持非目标事件的随机性一致。**
10. **场景语义完全独立于具体记忆系统架构。**
11. **黑盒智能体始终保持一等参评支持。**
12. **白盒内省属于可选诊断能力。**
13. **当前即时输入与过往记忆属于不同输入源。**
14. **历史事实与当前事实在不同时间坐标下均可保持为真。**
15. **陈述、矛盾、纠错与未知状态在真值中明确区分。**
16. **经验场景完整保留动作/观测/结果的因果轨迹。**
17. **技能场景必须考核适用边界，而非单纯重复动作。**
18. **负迁移必须具备可度量性。**
19. **遗忘场景明确区分过时抑制与历史追溯。**
20. **前瞻记忆通过情境触发，而非直接提问。**
21. **自我认知记忆绝不等于基准环境真实权限。**
22. **确定性与环境状态评测优先于大模型裁判。**
23. **大模型裁判绝不能推翻客观环境真值。**
24. **因果评测必须依赖严格配对的对照条件。**
25. **场景计分全流程保持可审计与可复现。**

---

# 100. 最终准则

场景模型的存在，是为了让这样一个核心理念在实验中切实可测：

> **记忆智能的体现，绝不仅仅在于智能体能够机械地复述过往，而在于受控的过往历史能够准确无误地改变未来正确的行为——且仅仅改变正确的行为。**

---

# 附录 A —— 极简可执行场景示例

```json
{
  "mib": "0.1",
  "kind": "MemoryEpisodeProgram",
  "id": "MIB-RET-001",
  "version": "0.1.0",
  "title": "直接延迟回忆",
  "suite": "recall",
  "dimensions": [
    "retention_retrieval"
  ],
  "world": {
    "clock": {
      "mode": "virtual",
      "start": "2026-01-01T00:00:00Z",
      "timezone": "UTC"
    },
    "state": {}
  },
  "timeline": [
    {
      "id": "e1",
      "stage": "past",
      "type": "interaction",
      "at": {
        "sequence": 1
      },
      "visibility": "agent",
      "content": "我的狗叫 Pixel。"
    }
  ],
  "probes": [
    {
      "id": "p1",
      "kind": "factual",
      "delivery": "respond",
      "input": {
        "content": "我的狗叫什么名字？"
      },
      "oracle": {
        "accepted": [
          "Pixel"
        ]
      },
      "evaluators": [
        "exact-1"
      ]
    }
  ],
  "evaluators": [
    {
      "id": "exact-1",
      "type": "set_match",
      "config": {
        "normalization": "casefold_trim"
      }
    }
  ],
  "scoring": {
    "probe_aggregation": "weighted_mean",
    "score_range": {
      "min": 0,
      "max": 100
    }
  }
}
```

---

# 附录 B —— 推荐代码库结构

```text
MIB/
├── docs/
│   ├── MIB-Architecture.md
│   ├── MIB-Scenario-Model.md
│   ├── MIB-Agent-Adapter.md
│   ├── MIB-Scoring.md
│   └── MIB-v0.1-Test-Plan.md
│
├── docs/cn/
│   ├── MIB-Architecture.md
│   ├── MIB-Scenario-Model.md
│   ├── MIB-Agent-Adapter.md
│   ├── MIB-Scoring.md
│   └── MIB-v0.1-Test-Plan.md
│
├── schemas/
│   └── mib-scenario.schema.json
│
├── scenarios/
│   ├── recall/
│   ├── time/
│   ├── epistemic/
│   ├── experience/
│   ├── skill/
│   └── causal/
│
├── adapters/
│   ├── MIB-Agent-Adapter.md
│   └── MIB-Memory-Adapter.md
│
├── runner/
├── evaluators/
└── leaderboard/
```

---

# 附录 C —— 后续配套规范指引

完成本模型阅读后，建议依次阅读：

```text
1. MIB-Scoring.md（计分与因果统计方法）
2. MIB-v0.1-Test-Plan.md（v0.1 测试与校准计划）
3. MIB-Leaderboard-Evaluation-Service.md（排行榜与评测服务）
```
