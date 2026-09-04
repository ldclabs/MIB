# MIB 规范

## 记忆智能基准（Memory Intelligence Benchmark）—— v0.2 规范性规范

[ [English](../MIB-Specification.md) | 简体中文 ]

**版本：** 0.2（实现版本 0.9.0）  
**状态：** 规范性（Normative）。本文档定义了 `src/mib_runner/` 中参考实现所执行与评分的全部语义。所有已设计但尚未执行的特性均收录于附录 A（路线图），不出现在正文中。

v0.2 以**生成的场景实例（generated Scenario Instances）**取代了手写场景：每个实例均由一个**程序（Program）**在一个内部的、双时态（bitemporal）、分信源的世界模型上推导生成；答案、相关记忆消融集、反事实孪生（counterfactual twins）以及泄漏证明均为计算生成，而非人工编写。v0.2 将**过往与探针之间的距离**作为主自变量（§8.1），将因果检验从“移除事件”升级为“改变事件内容并观察答案是否跟随”（§7.2），让智能体（Agent）**亲历（live）**其历史而非单纯阅读历史叙述（§5.3），基于**自发发射（spontaneous emissions）**评测**前瞻记忆（prospective memory）**（§4.6），并要求提供带有认识状态（epistemic status）和置信度的**结构化答案**（§4.7）。v0.1 的因果维度被调整为一组并列报告的因果诊断量，并作为一项资格门控指标：**记忆依赖性（memory dependence）**（§7.10）。

设计推导背景参见 `docs/proposals/MIB-v0.2-Evolution.md`；已废弃的 v0.1 草案归档于 `docs/archive/`。若设计推导文档与本文档存在分歧，以本文档及代码实现为准。Agent Adapter 通信线协议在 `MIB-Agent-Adapter.md` 中单独定义；托管评测服务见 `MIB-Leaderboard-Evaluation-Service.md`；补充性的迁移智能（Transfer Intelligence）和 MIB-R 层见 `docs/experimental/`。

规范性用词 **必须（MUST）**、**严禁（MUST NOT）**、**应当（SHOULD）**、**可以（MAY）** 遵循标准定义。各章节编号保持稳定，并在代码注释中被引用。

---

# 0. 评测范围

MIB 衡量智能体（Agent）及其长期记忆系统利用过往经历改善未来认知与行为决策的有效程度。它并不主要评测系统能够从过去检索出多少信息。

被评估的对象是：

```text
智能体（Agent）+ 长期记忆系统，在时间跨度中的行为表现
```

MIB 保持架构中立：参赛者只需提供一个实现了 `reset`、`observe`、`respond` 和 `act`，并且**可以（MAY）**实现 `maintain` 的黑盒 Agent。基准不强制要求任何特定的记忆表示、记忆 API 或 KIP 遵从性，这些也不会带来额外加分。

---

# 1. 核心论题与原则

## 1.1 核心论题

> 评价一套记忆系统，不应看它能从过往检索出多少信息，而应看正确部分的过往经历是否以正确的方式改变了未来。

由此引出三项核心要求：

1. **记忆必须产生因果效力。** 如果改变一段理应相关的记忆并不能改变相关的未来决策，那么该项内容只是被存储的历史记录，而非发挥功用的记忆。
2. **记忆必须具备情境敏感性。** 在某一情境中有益、却在不相关情境中带来危害的记忆，体现的是薄弱的记忆智能。
3. **记忆必须保留关键区分。** 当前真实 vs 历史真实、单方陈述 vs 采纳信念、信源 vs 溯源、客观事件 vs 主观经验、陈述性知识 vs 程序性技能、未知 vs 错误、承诺约定 vs 触发条件。

## 1.2 场景所检验的命题

每一个场景的存在，均为了检验如下命题：

> 过往应当在相关时改变未来，在无关时不控制未来，并在陈旧或有害时受到抵御。

## 1.3 识别条件：v0.2 所能确立的结论

重放消融（Replay ablation）干预的是 Agent 的**输入**；而记忆是 Agent 的**内部状态**。只要过往事件仍处于工作上下文窗口之内，“过往改变未来”就完全不需要经过记忆系统。因此，v0.2 不会在单一点位上报告记忆分数，而是同时报告共同构成记忆识别条件的两个维度：

- **保持曲线（retention curve）**（§8.1）：同一个程序在递增的干扰距离下执行；在超出工作上下文的距离下依然保持的性能，才是穿透工作上下文而留存的记忆性能；以及
- **内容追踪（content tracking）**（§7.2）：在同一个实例的反事实孪生条件下正确答案发生改变；如果 Agent 的回答不跟随改变后的内容，说明其回答源自先验，此时其能力分不能算作记忆得分（§7.10）。

目前随版本附带的所有程序仍处于 **MIB-S** 尺度（最多几百个事件）。干扰阶梯是因果识别条件，而非难度调节旋钮；更大的尺度（附录 A）是对阶梯的自然延展，而非替代。

---

# 2. 基准评测结构

## 2.1 评测轨道（Tracks）

**Track A —— 记忆系统轨道（Memory System）。** 基座模型、智能体提示词、推理策略、工具集、运行环境和 Runner 均保持固定；仅记忆系统发生变化。推荐用于评测和对比不同的记忆架构。

**Track B —— 完整智能体轨道（Integrated Agent）。** 基座模型、智能体策略、记忆机制、编排调度与工具策略均可自由变化。衡量完整 Agent 借助记忆赋能后的综合能力，刻意不对模型基础能力进行归一化。

Track A 与 Track B **严禁（MUST NOT）**合并在同一个排行榜中排序。

## 2.2 能力维度

MIB-Core-0.2 评测七个核心能力维度：

| 标识符 | 能力维度 | 评测核心问题 |
|---|---|---|
| `retention_retrieval` | 保持与检索（Retention & Retrieval） | 在间接线索与生成的干扰下，能否直接或跨跳（multi-hop）准确恢复相关过往信息？ |
| `temporal_memory` | 时序记忆（Temporal Memory） | 能否准确区分状态演变中的当前值、先前值与初始值？ |
| `epistemic_memory` | 认知记忆（Epistemic Memory） | 谁说了什么；认知修正 vs 事实冲突；信源权威；区分未知与错误；争议中 vs 已确认？ |
| `experience_memory` | 经验记忆（Experience Memory） | Agent 自身亲历并经历的失败，能否改变它下一次的行为决策？ |
| `skill_learning_transfer` | 技能学习与迁移（Skill Learning & Transfer） | 习得的前置约束能否在适用场景准确迁移，并在不适用场景严格克制？ |
| `prospective_self_memory` | 前瞻与自省记忆（Prospective & Self Memory） | 延期承诺是否在触发条件成熟时精准触发，且不在条件成熟前早熟触发？关于 Agent 自身的既定准则能否在面对违规要求的任务时坚守不移？ |
| `selective_forgetting` | 选择性遗忘（Selective Forgetting） | 被撤回的事实是否彻底停用，同时其周边关联事实依然可用？ |

`causal_memory_impact` 保留为 v0.1 Profile 的 Schema 标识符；v0.2 Profile 不为其分配权重。因果相关指标作为**诊断量（diagnostics）**并列报告（§7），且其中一项充当参赛资格门控（§7.10）。

## 2.3 配置文件（Profiles）

**Profile** 是一个具有版本管理的 JSON 策略对象，它规定了：`id`、`version`、`track`、`scale`、`official`、`scenario_pack`、`repetitions`、`instance_seeds`、各维度 `weight`、`required_coverage` 以及 `statistics`（置信水平、bootstrap 重采样次数、`min_templates_per_dimension`）。v0.2 Profile 还额外规定了：

- `programs[]` —— `{id}`（可选包含 `ladder`），该数据包所包含的程序列表（§4.2）；
- `ladder` —— 各档位干扰事件数，默认 `[0, 20, 100]`（§8.1）；
- `canonical_rung` —— 读取能力基准分的指定档位（§8.3）；
- `memory_dependence` —— `{metric, floor}`，记忆依赖性资格门控（§7.10）；
- `statistics.interval_method` —— `percentile`（默认百分位法）或 `bca`（BCa 法）（§8.2）。

v0.1 Profile 规定 `required_templates` 而非 `programs`；此时执行的数据包完全由这些静态模板构成（§5.1）。所有公开发布的分数均须标明所属 Profile；不同 Profile 的权重**严禁（MUST NOT）**混合。带有 `official: false` 的 Profile 生成的是开发分数，绝不可作为官方榜单分数。

## 2.4 数据包与可见性

**生成的场景包（generated pack）**由 `programs × instance_seeds × ladder rungs` 笛卡尔积构成。程序定义、表面改写词表与生成器完全公开；官方评测使用评测方保密的种子（evaluator-secret seeds），因此参赛者能够检查每一处构造逻辑，却永远无法提前窥见官方实例（§11）。目前随版本发布两套开发 Profile：`MIB-Core-0.2-Dev`（MIB-S 尺度，阶梯 `[0, 20, 100]`，基准档位为 rung 1）与 `MIB-Core-0.2-Dev-M`（MIB-M 尺度，阶梯 `[0, 100, 1000]`，基准档位为 rung 2，采用 BCa 区间）。静态的 v0.1 数据包（24 个公开 Dev 模板、30 个隐藏 Eval 模板、6 个私有 Holdout 模板）依然作为超集可执行，供本地开发与回归测试使用。

---

# 3. 角色职责划分

```text
Program + seed + rung ──generate──▶ 场景实例 (Scenario Instance)  (世界模型 → oracle, 支持集, 反事实孪生)
                                         │
                               ┌─────────▼──────────┐
                               │       Runner       │  掌控时间线、虚拟时钟、
                               │  + 世界模拟器      │  隐藏事实基准、工具集
                               └───┬────────────┬───┘
                     观察事件      │            │  tool_result
                     探针 / 任务   ▼            ▲  tool_call / emissions
                               ┌───────────────────┐
                               │  Agent (Adapter)  │  黑盒接口: reset / observe / respond / act [/ maintain]
                               └───────────────────┘
                                         │ 输出、发射、动作轨迹、世界执行结果
                               ┌─────────▼──────────┐
                               │     评测器集       │  确定性匹配、结构化、自发发射、世界状态、轨迹
                               └─────────┬──────────┘
                               ┌─────────▼──────────┐
                               │     评分引擎       │  probe → instance → template → dimension → MIB; 保持度; 依赖度
                               └────────────────────┘
```

- **程序（Program）**是一个确定性生成器 `(seed, rung) → Instance`。它构建底层世界模型，将其具象化为时间线，并从模型中推导出全部 Oracle 与消融设定（§4.2）。
- **Runner（执行器）**负责加载实例、投递可见的时间线事件、执行亲历任务、剥离隐藏字段、投递探针、通过世界模拟器执行工具调用、收集发射事件、在整理窗口调用 `maintain`、运行评测器、执行消融与反事实重放，并生成运行产物（Run Artifact）。
- **世界模拟器（World Simulator）**掌控世界状态、隐藏真实基准（ground truth）、工具状态与虚拟时钟。Agent 绝不可直接修改世界状态，只能观察工具调用的执行结果。
- **Agent Adapter** 是连接参赛系统的唯一通信信道。进程内 Agent 实现 `types.py` 中的 Python 协议；外部 Agent 遵循 `MIB-Agent-Adapter.md` 中规定的 stdio JSONL 或本地 HTTP 协议。
- **Runner 严禁（MUST NOT）协助 Agent**：不得进行文本总结、不得高亮相关记忆、不得标注干扰项、不得暴露信源权威等级、不得注入 Oracle 内部状态、不得暗示某条观察属于前瞻触发器。

---

# 4. 场景模型（可执行子集）

机器通信契约遵循 `schemas/mib-scenario.schema.json`（JSON Schema 2020-12）。Schema 中定义的所有枚举值均可由参考 Runner 直接执行；参考场景校验器（Scenario Validator）还会额外拦截任何 Runner 无法执行的内容（§4.10）。

## 4.1 顶层对象

必填字段：`mib`（`"0.2"`；仍兼容接受 `"0.1"` 内容）、`kind`（`MemoryEpisodeProgram`）、`id`、`version`、`title`、`suite`、`dimensions`、`world`、`timeline`、`probes`、`evaluators`、`scoring`。可选字段：`status`、`description`、`tags`、`difficulty`、`template`、`instantiation`、`requirements`、`execution`、`leakage`、`actors`、`ablations`、`metadata`、`extensions`。

生成的实例使用 `id = MIB-GEN-<PROGRAM>-V<n>` 与 `status: "generated"`；静态模板遵循 `MIB-<FAMILY>-<NNN>`。若程序的构造逻辑、Oracle 推导规则、消融语义或评分发生变更，**必须（MUST）**至少增加其次版本号（minor version）。

`dimensions` 列出该场景所覆盖的维度；`scoring.dimension_weights`（§4.9）在该场景所声明的维度间分配其证据权重。

## 4.2 程序、世界模型与实例

**程序（Program）**（`src/mib_runner/generate/programs.py`）使用形如 `mib.temporal.v1` 的唯一标识符注册，并暴露模板形式的**描述符**（`template.program = {id, version, ladder}`）以及 `generate(seed, rung)` 生成入口。生成过程是关于 `(program id, program version, seed, rung, ladder)` 的纯函数；相同输入**必须（MUST）**产生逐字节完全相同的实例文件。

**世界模型（World model）。** 程序构建一个双时态、分信源的模型（`worldmodel.py`）：包含一系列断言 `(event, source, subject, attribute, value, kind)`，其中 `kind ∈ state | update | correction | contradiction | question | hypothetical`。处理规则如下：

- 权威信源作出的 `state` 或 `update` 断言承载真实状态，并覆盖该主体/属性的先前历史值；
- `correction`（修正）具有**溯及力（retroactive）**：它在真实状态演变序列中直接替换被修正的断言，因此“在此之前的取值是什么”的查询将基于修正后的历史来回答；
- 非权威信源作出的 `contradiction`（事实冲突）仅记录为“被如此陈述”，但不代表真实状态；该属性的认识状态变为 `contested`（存疑），直到某一权威信源（具备权限的人或工具观测）将其化解；
- `question`（疑问）与 `hypothetical`（假设）不确立任何事实；它们是审讯植入陷阱与陈旧采纳陷阱的基础构造材料；
- `retraction`（撤回，例如“请遗忘我的访问密钥”）从所有层级中抹去该断言——包括真实状态、证据链与历史记录——其自身不确立任何新事实；被撤回的值变为禁止回答项；在相关记忆消融中扣留该撤回操作将恢复原断言，这正是选择性遗忘消融所评测的内容；
- 工具观测（tool observation）天然具备权威性。

针对世界模型可以执行**查询（Queries）**：`current`（当前值）、`as_of`（变更前的值）、`first_stated`（最初陈述的值）、`said_by`（某指定信源陈述的内容）、`known`（是否已知任何内容）、`status`（认识状态：`known | contested | unknown | historical`）以及 `hop`（带有诱饵的多跳属性链）。查询返回的结果为 `(kind, value, status)`，其中 `kind ∈ value | unknown | contested`。

**Oracle 推导。** 每个探针声明其内部 `query`（仅限评测套件内部使用）；`finalize()` 将查询结果转换为 `oracle.accepted`（该值的所有标准自然语言表达形式）、`oracle.forbidden`（该主体/属性历史上曾出现过的所有其他值，含已被覆盖和被撤回的值）、`oracle.expected_status` 以及 `oracle.failure_code_by_value`——详述每个禁止项为何属于错误：被覆盖或被撤回的值对应 `stale_memory_adoption`（陈旧记忆采纳），修正前的初始错误值对应 `correction_loss`（修正丢失），非权威冲突值对应 `authority_confusion`（权威混淆），仅在提问或假设中提及的值对应 `memory_hallucination`（记忆幻觉）。Oracle 中没有任何内容需要人工手动撰写。

**实例标识符。** 生成的实例记录 `instantiation` 信息：`template_id`、`program`、`program_version`、`rung`、`interference_count`、`seed`、`parameter_digest`（事件与探针的 SHA-256 摘要）、`generator_version`。其唯一实例键为 `<template_id>:<seed>:r<rung>`。隐藏评测在数据交付给参赛者前，会将 seed 替换为不透明的别名（§11）。

**随版本发布的程序列表（均为 0.2.0 版本）：**

| 程序标识 | 对应维度 | 评测内容 | 所需能力 |
|---|---|---|---|
| `mib.recall.v1` | retention_retrieval | 在生成的干扰下，恢复单个事实以及带有诱饵的双跳关联链 | observe, respond, virtual_time |
| `mib.temporal.v1` | temporal_memory | 经历一次或两次更新：准确区分当前值、先前值与最初值 | observe, respond, virtual_time |
| `mib.epistemic.v1` | epistemic_memory | 修正；组织者 vs 同事的信息冲突（在一半种子中由日历工具化解）；谁说了什么；状态；未知 | observe, respond, virtual_time |
| `mib.experience.v1` | experience_memory | 针对错误目标的两次**亲历（lived）**部署试验（先失败，后排查恢复），每次附带试验 Oracle，随后执行相关的后续部署 | + act, tools |
| `mib.skill.v1` | skill_learning_transfer | 亲历“提交前必须激活上下文”的教训；首先执行不匹配任务（负迁移对照，§7.8），再执行匹配任务 | + act, tools |
| `mib.prospective.v1` | prospective_self_memory | 延期承诺；绝不可提前激发的拟真触发项；真实触发项；针对 Agent 自身的既定准则（“严禁重启服务”）在面对要求重启的任务时的守则表现 | + act, tools |
| `mib.forgetting.v1` | selective_forgetting | 两个事实，随后撤回其中一个；被撤回的事实必须呈现为未知（当前与历史上均未知），未撤回的事实必须依然已知 | observe, respond, virtual_time |

每个程序在其历史记忆阶段与干扰块之间，均包含一次整理窗口（`maintenance_window`，§4.5）。

静态的 v0.1 模板包含 `template.parameters`（`fixed`、`choice`、`integer_range`、`number_range`，使用 `random.Random(str(seed))` 播种，支持 `${name}` 变量替换），其实例化流程保持不变。

## 4.3 能力需求、执行策略与防泄漏策略

`requirements.capabilities` 声明了 Agent 必须支持的能力：`observe`、`respond`、`act`、`tools`、`virtual_time`、`maintenance`（Schema 中还保留了 `snapshot`、`memory_inspect`、`memory_delete`、`memory_restore`）。仅当 Agent 描述符明确将某项所需能力声明为 `false` 时，该模板才会被标记为**不支持（unsupported）**（§6.6）。附带的程序均未将 `maintenance` 设为强制必选：未实现 `maintain` 的 Agent 仅将整理窗口作为普通系统事件接收。

`execution` 针对每个 act 探针及亲历任务设定 `max_agent_turns`（默认 20）和 `max_tool_calls`（默认 20）。唯一允许的执行策略是 `fail_probe`（§5.4）。

`leakage` **必须（MUST）**将 `future_probe_visible_during_formation`、`oracle_visible_to_agent`、`ablation_labels_visible_to_agent` 以及 `hidden_world_state_visible_to_agent` 均声明为 `false`；校验器将拒绝任何其他设定。`probe_sampling` 取值为 `fixed`、`late` 或 `hidden_late`（§4.6）。

## 4.4 参与角色与世界设定

`actors` 定义了基准环境中的身份实体（`id`、`kind`、`display_name`）；Runner 仅将这三个字段投影到观察事件中。Actor 身份不代表已通过鉴权，其权威等级属于世界模型内部事实，绝不会作为标签直接暴露。

`world` 包含：

- `clock` —— `{mode: "virtual", start: <ISO 8601 UTC>, timezone}`；Runner 掌控时钟推进（§4.5）。
- `state` —— 模拟器的可变状态，通过 JSON Pointer 定位访问。
- `hidden_ground_truth` —— 仅供 Oracle 使用的事实；绝不投递给 Agent。
- `tools` —— 暴露给 act 探针和亲历任务的工具定义。每个工具声明 `id`、`version`、`operations[]`（`name`、`description`、`input_schema`）以及 `simulator_binding`。参考世界模拟器实现了 `mib.deployment.v1`（检查/选择目标、执行数据迁移、重启服务）、`mib.workspace.v1`（选择工作区、编辑、保存）和 `mib.contextual_save.v1`（激活上下文、编辑、提交，带有一个 `context_required` 标志，当为 false 时调用激活将视为策略违规）。工具调用以 `<tool id>.<operation>` 格式呈现给 Agent。

## 4.5 时间线（Timeline）

每个事件包含 `id`、`stage`（`seed` | `past` | `interference` | `consolidation` | `pre_probe`）、`type`、`at`、`visibility`，以及可选的 `actor`、`content`、`payload`、`world_updates`、`task`、`oracle_labels`、`tags`。

可执行的事件类型及其投影形式：

| 场景事件类型 | 投递为（Delivered as） | 补充说明 |
|---|---|---|
| `interaction`, `distractor` | `user_message` | 普通交互或闲聊干扰 |
| `observation` | `environment_event` | 环境事件推送 |
| `tool_result` | `tool_result` | 包含 `tool_call_id`、`tool`、`payload` |
| `document`, `feedback`, `custom` | 同名投递 | 文档、反馈或自定义事件 |
| `task` | act 循环 | **亲历任务（lived task）**（§5.3）：包含 `task.goal`、`task.available_tools`、`task.constraints`、`task.max_agent_turns`；可选的 `task.oracle` + `task.evaluators` 使其成为学习曲线试验（§7.9） |
| `time_advance` | `time_event` | 推进虚拟时钟（见下文） |
| `maintenance_window` | `system_event` | 若 Agent 实现了 `maintain` 钩子则触发调用（透传 `payload.budget`）；每个程序在其干扰块之前均会触发一次，并与 `no_maintenance` 消融配对（§4.8） |
| `checkpoint`, `world_update` | 不向 Agent 投递 | 仅供评测套件内部使用 |

`visibility` 包含 `agent`、`harness`、`both`；仅标记为 `agent`/`both` 的事件才会投递给 Agent。`oracle_labels`、`tags`、相关性标注、`query` 字段及隐藏事实基准绝不投递。

`world_updates`（对 JSON Pointer 路径执行 `set`、`unset`、`increment`、`append`、`remove` 操作）是评测套件内部操作，而非记忆写入。它们在**所有**执行条件下均会无差别执行，包括消融该事件的条件（§5.2）。

**生成的干扰块。** 程序会在过往记忆与探针之间插入 `ladder[rung]` 个干扰事件（`generate/interference.py`），通过种子从三大类别中采样抽取：`neutral`（0.60 概率；完全无关的日常对话）、`similar`（0.25 概率；由另一位 actor 陈述自己关于相同属性的值，属于关于他人的真实事实）、`confusable`（0.15 概率；目标 actor 就相同属性探讨其他可能取值或进行假设性提问，其本身不确立任何事实）。Similar 和 confusable 类别的事件均登记在世界模型中，因此 Oracle 已将其纳入考量。干扰内容**严禁（MUST NOT）**泄漏该实例中任何探针的正确答案；解析层检查已纳入自动化测试集，且 §4.8 中的泄漏证明覆盖了相关记忆消融。实例使用三种单位记录干扰距离——`interference_count`（事件数量）、`interference_tokens`（干扰块的空格分词 token 数量）以及 `distance_hours`（从最后一个记忆形成事件到探针检查点所经历的虚拟小时数），因此可以基于其中任何一个维度来解读保持曲线（§8.1）。

**虚拟时间。** Runner 维护当前的虚拟时间，初始值为 `clock.start`。事件的 `at.time` 会设定该时间；`time_advance` 事件也可以通过 `payload.duration`（ISO 8601 时长字符串，如 `P3D`、`PT2H30M`）向前推进时间。所有投递给 Agent 的观察事件和探针均携带当前的虚拟时间戳。`at.sequence` 规定事件序号，若存在则**必须（MUST）**保持严格单调递增。

## 4.6 探针（Probes）

探针代表未来的能力测试。必填字段：`id`、`kind`、`trigger`、`delivery`、`input`、`oracle`、`evaluators`。可选字段：`dimensions`、`weight`（默认 1.0）、`query`（评测内部使用；§4.2）、`tags`、`extensions`。

- `trigger` 形式为 `{after_event: <event id>}`。探针在对应事件处理完毕后按场景中声明的顺序立即触发。
- `delivery` 包含 `respond`（认知问答；`input.content`）、`act`（交互任务；`input.goal`、`input.available_tools`、`input.constraints`）或 `observe_only`（仅观察，见下文）。
- `input.context` 指定了**提问者身份**（`{actor, display_name}`）；Runner 注入该上下文，以便第一人称问题（如“我的时区是什么？”）能够被正确理解。该上下文不携带任何权限或权威信息。
- `input.answer_schema`（包含 `{value, status, confidence}` 布尔开关）请求结构化格式的回答（§4.7）。Agent **可以（MAY）**以自由文本回答；评测器使用确定性解析器完成映射并记录映射过程。
- `kind` 为描述性类别（`factual`、`implicit`、`multi_hop`、`temporal`、`epistemic`、`experience`、`skill`、`prospective`、`self`、`action`、`historical`、`audit`、`abstention`、`custom`）。它决定了错误代码的词表范围（§5.4）以及全流程诊断量的计算资格（§7.9：`historical`、`audit`、`self`），但不直接决定分值计算。
- `dimensions` 用于标注该探针归属于哪些能力维度的证据归属（§6.3）。

**仅观察探针（Observe-only Probes，前瞻记忆）。** `input.observation`（`type`、`actor`、`content`、`payload`）作为普通的日常观察事件投递给 Agent，不附带任何显式提问。Agent 对每个 `observe` 请求的响应中**可以（MAY）**携带 `emissions[]`；Runner 会记录这些发射项并打上产生该发射的观察事件索引。`oracle.expected_emission` 格式为 `{must_contain[], window, must_not_emit}`：当在 `[trigger index, trigger index + window]`（默认窗口为 1）范围内产生的某条发射包含 `must_contain` 中的所有 token 时，探针判定通过；若设置了 `must_not_emit: true`，则只有在窗口内未产生任何匹配发射时才算通过（否则记为 `premature_trigger` 早熟触发）。拟真干扰触发探针通常使用 `window: 0`，以避免后续正确的合法发射被错误归罪。仅观察探针只接受 `emission` 评测器打分（§4.7），并在整条时间线执行完毕后统一判定。

**延迟采样（Late sampling）。** 当 `leakage.probe_sampling` 设定为 `late` 或 `hidden_late` 时，Runner 仅在探针实际触发的瞬间才从 `extensions["mib.probe_sampling"].input_variants` 中动态挑选输入变体。这一选择是关于 (scenario id, instance seed, repetition, probe id) 的确定性函数，因此在完整运行与所有消融运行之间完全一致；实际投递输入的摘要信息会被记录用于配对有效性验证（§7.7）。Oracle 与评测器配置绝不参与动态采样。

未来的探针**严禁（MUST NOT）**在记忆形成阶段被 Agent 提前感知。Runner 会严格强制执行这一限制：`probes` 中的任何字段都不会泄露给观察事件，仅观察探针在形式上与普通观察事件完全无异。

## 4.7 Oracle 与评测器（Evaluators）

`oracle` 可以包含 `accepted[]`、`forbidden[]`、`failure_code_by_value`（§4.2）、`expected_status`（`known` | `unknown` | `contested` | `historical` | `not_applicable`）、`world_assertions[]`、`trajectory_requirements[]`、`expected_emission` 以及自由文本的 `expected`、`reference`、`notes`。Oracle 数据纯属评测套件内部机密。

评测器通过 `evaluators[]` 列表中的 id 进行引用。每个评测器产出 `score ∈ [0,1]`、`passed`、`failure_codes[]` 以及 `details`。

**通用值匹配策略。** `config.normalization` ∈ `none` | `trim` | `casefold_trim` | `casefold_trim_collapse_ws` | `answer_normalized`（默认；合并连续空白、转小写、剥离两端标点符号，使得 "AX-91." 等同于 "AX-91"）。`config.match` ∈ `contains`（默认；整词 token 包含匹配，避免 "AX-9" 误匹配入 "AX-91"）| `exact`。

匹配判定逻辑：

```text
命中 accepted 中任一值，且未出现任何 forbidden 值       → 1 分
在任何位置出现了 forbidden 中的值                        → 0 分，按 failure_code_by_value[value] 记录，默认为 stale_memory_adoption
既未命中 accepted 也未命中 forbidden                     → 0 分，retrieval_miss（检索缺失）
若 expected_status = unknown:
  明确弃权（abstention），或命中 accepted 中的值          → 1 分
  给出任何其他确定性答案                                 → 0 分，false_certainty（虚假确定性）
若 expected_status ≠ unknown 但选择弃权                  → 0 分，retrieval_miss（检索缺失）
```

若回答在当前值与被覆盖的历史值之间模棱两可（如“UTC+1，此前为 UTC+8”），且探针将历史值列入了 forbidden，则判定失败。此类探针仅询问当前状态值；若程序需要考察历史情境，会通过单独的专用探针进行考察。

**`set_match`** —— 针对短文本答案，遵循上述通用匹配策略。对于标量类型的结构化输出，将其转换为标量文本后进行比较。

**`structured`** —— v0.2 中针对问答类（respond）探针的默认评测器。采用确定性解析器将任何输出解析映射为 `{value, status, confidence}`：弃权表述 → `status: unknown`；标准结构化输出或 JSON 对象 → 提取其 `value`/`answer`、`status`、`confidence` 字段；否则匹配 `value:`/`answer:`、`status:`、`confidence:` 独立行；若均无则将全部文本作为 value。参考实现绝不调用大语言模型进行主观裁决；即使未来引入模型辅助将非结构化文本映射为该 Schema，映射产物本身即为审计日志，而非评分结论。评分依据 `config.weights`（默认 `value 0.8, status 0.2`）逐字段展开：`value` 依据通用策略打分；`status` 在命中期望的认识分类时得 1 分（`known` → `known`；`historical` → `historical` 或 `known`；`contested` → `contested`；`unknown` → `unknown`；`not_applicable` → `not_applicable` 或 `unknown`），若回答对未知事项妄称已知则追加 `false_certainty` 错误代码；`confidence ∈ [0,1]` 产生校准评分项 `1 − (confidence − value_score)²`，该项始终如实记录，但仅在评测器明确配置了其权重时才计入总分。`status` 为 `unknown` 或 `value` 声明为 "unknown" 均视为有效弃权。

**`emission`** —— 针对仅观察探针（§4.6）。得分为 1 或 0；错误代码包括 `commitment_miss`（未能在规定窗口内产生匹配发射）和 `premature_trigger`（在禁止发射的窗口内过早发射）。

**`world_state`** —— 针对模拟器最终状态评估 `oracle.world_assertions[]` 中的 `{path, operator, value}`，支持操作符 `eq`、`neq`、`exists`、`not_exists`、`contains`、`gte`、`lte`。得分等于满足断言的比例；任何未满足的断言均记入 `trajectory_collapse`。世界客观事实的优先级高于 Agent 的任何口头陈述。

**`trajectory`** —— 针对 act 探针的工具调用序列评估 `oracle.trajectory_requirements[]`：包括 `required_action`、`forbidden_action`、`before` / `after`（首个发生次序）、`max_occurrences`、`min_occurrences` 以及 `no_recurrence`（不复发约束 `{action, without_prior}` —— 除非在同一次轨迹的前文已经执行了 `without_prior`，否则**严禁（MUST NOT）**执行该 `action`；这是“不得重蹈亲身经历的覆辙”的操作化表达，违背时记为 `error_recurrence`）。得分为满足要求的比例。`forbidden_action` 和 `no_recurrence` 只有在**非空轨迹**下才算通过；不执行任何操作的 Agent 不会因为逃避动作而获得避免犯错的加分。违反禁止动作时，在 `experience` 探针中标记为 `error_recurrence`，在 `self` 探针中标记为 `self_model_drift`，其他场景标记为 `negative_transfer`。

**`composite`** —— 由 `{evaluator, weight}` 构成的 `components[]`；计算各子评测器得分的加权平均值，权重自动归一化，错误代码取并集。

若探针引用了多个评测器，其得分为各评测器得分的未加权算术平均；程序生成的探针每个通常只引用一个评测器。

## 4.8 消融设定（Ablations）

消融机制将普通的记忆测试转化为因果检验。必填字段：`id`、`kind`、`probes[]`（参与打分的探针子集）、`method`、`expected_effect`。可选字段：`targets.event_ids[]`、`injections[]`、`counterfactual`、`tolerance`、`oracle_value_survives_by_design`、`description`。

消融类型（Kinds）：`relevant_memory`（预期效果为 `degrade` 性能下降）、`irrelevant_memory`（`neutral` 性能中立）、`no_memory`（`degrade`）、`harmful_memory` 与 `stale_memory`（`resist` 抵御侵害）、`counterexample`（`degrade`；§7.8）、`negative_transfer`（`resist`；§7.8 标准化对照）、`counterfactual_content`（`track` 答案跟随；§7.2）、`no_maintenance`（`informational` 信息性；§7.2；仅允许扣留 `maintenance_window` 事件；为每个程序自动生成）、`custom`。

消融实现方法（Methods）：

- `replay_excluding_events` —— 重放完整时间线，但向 Agent 扣留 `targets.event_ids` 中指定的事件。这些事件携带的 `world_updates` 仍会在世界中正常执行。
- `replay_with_injections` —— 重放完整时间线，并追加 `injections[]` 中由评测方注入的事件，通过普通观察信道投递。带有 `at.after_event` 锚点的注入事件将在指定事件之后、且在由该事件触发的任何探针之前投递；否则按 `at.sequence` / `at.time` 顺序混入。注入事件**严禁（MUST NOT）**携带 `world_updates`：记忆是干预变量，世界客观真实不是。
- `swap_parameter` —— 重放完整时间线，但将核心支点事件的**内容**进行替换（对普通事件使用 `counterfactual.events[pivot] = {content}`，对工具结果使用 `{payload}`），并依据 `counterfactual.oracle[probe]` 对指定探针进行打分，在反事实 Oracle 中原始值被明确设为 forbidden。除此以外——其他所有事件、所有干扰语句、时钟演变——完全保持一致，因此两个运行之间仅存在单一记忆内容的微观差异。

**支持集与泄漏证明。** 针对每个返回有效查询值的探针，生成器会在世界模型中推导该查询的**支持集（support set）**：当且仅当某单个事件的移除会导致查询结果改变时，该事件被称为*必要事件*；若在任何单个事件移除下查询答案均能存活，则共同承载该事实的冗余事件组被界定为因果信息集，并通过整组移除进行验证。相关记忆消融会精确扣留该最小支持集；除非世界模型能严格证明查询答案在幸存事件中已不可推导，否则生成过程将直接报错中断（抛出 `GenerationError`）。冗余分组情况记录在消融的 `description` 中。静态模板采用 v0.1 的弱校验规则：若可接受的答案仍字面出现在幸存事件中，将产生警告，可通过 `oracle_value_survives_by_design: true` 消除警告。

**反事实孪生。** `swap_parameter` 消融的支点事件选自支持集中的最后一个必要事件。生成器在孪生世界模型中重新推导出各个探针的 Oracle，并将结果发生变化的探针精确列入 `probes[]`；答案不依赖于支点事件的探针不会作为该反事实设定的测试项。

`tolerance`（容差，默认 0）是容错 IMS 和容错 HRS 公式（§7.3、§7.4）所采用的随机波动允许阈值，作为 `ablation_tolerance` 拷贝到该消融条件的每次运行记录中。

## 4.9 评分配置块

`scoring.probe_aggregation` 设定为 `weighted_mean`。`scoring.score_range` 设定为 `{min: 0, max: 100}`。`scoring.dimension_weights` 将所声明的各维度映射为其证据权重，总和**必须（MUST）**等于 1；`scoring.causal_metrics[]` 列出该场景拟产出的因果诊断指标项（仅为描述性；实际计算完全依据声明的消融类型展开）。

## 4.10 场景校验规则

场景只有通过以下全部校验项，方可入选评测数据包：

1. JSON Schema 规范校验。
2. 内部引用消解：事件、探针、评测器、消融、角色标识符全局唯一；引用的角色、触发事件、评测器、复合评测器组件、消融目标探针、消融目标事件、注入锚点、可用工具项以及任务工具均能成功解析匹配。
3. 时间线序号在为数值型时必须严格单调递增。
4. 防泄漏策略标志位全部必须为 `false`；`dimension_weights` 权重之和必须等于 1；复合评测器权重之和必须等于 1（否则产生警告，Runner 将强制执行归一化）。
5. 注入事件不得携带 `world_updates`，且其 id 不得与时间线事件碰撞。
6. Runner 可执行性检查：评测器类型、触发器类型、投递模式、消融方法、模拟器绑定、事件类型、`set_match`/`structured` 配置、世界状态断言操作符以及轨迹约束类型，必须全部为参考 Runner 实际实现的内容。任何符合 Schema 但会导致 Runner 崩溃或导致所有 Agent 得 0 分的场景，均视为严重错误，而非仅产生警告。
7. v0.2 语义校验：`observe_only` 探针必须具备 `input.observation`、`oracle.expected_emission` 且只能配置 `emission` 评测器；`swap_parameter` 消融必须为每个目标提供替换内容，并为每个计分探针提供反事实 Oracle；`no_maintenance` 消融仅允许扣留 `maintenance_window` 事件；`task` 只能使用已声明的可用工具，且试验 Oracle 必须搭配可执行的评测器与断言。
8. 相关记忆消融泄漏校验（§4.8）——程序生成时若泄漏则报错中断，静态模板时产生警告。

生成的实例在实际执行前均需经过完全相同的规则校验；生成器的输出绝不享有免检特权。

## 4.11 场景实例范例

以下展示 `mib.temporal.v1` 生成的 rung-1 阶梯实例（节选；由 `mib generate --program mib.temporal.v1 --seed 7 --rung 1` 生成）：

```json
{
  "mib": "0.2", "kind": "MemoryEpisodeProgram", "id": "MIB-GEN-TEMPORAL-V1", "version": "0.2.0",
  "status": "generated", "dimensions": ["temporal_memory"],
  "instantiation": {"template_id": "MIB-GEN-TEMPORAL-V1", "program": "mib.temporal.v1", "program_version": "0.2.0",
                    "rung": 1, "interference_count": 20, "seed": 7, "parameter_digest": "…", "generator_version": "mib-generate/0.9.0"},
  "timeline": [
    {"id": "e-1", "stage": "past", "type": "interaction", "actor": "p1", "content": "My timezone is UTC+8.", "…": "…"},
    {"id": "e-2", "stage": "past", "type": "interaction", "actor": "p1", "content": "Update: my timezone is now UTC+1.", "…": "…"},
    {"id": "i-1", "stage": "interference", "type": "distractor", "…": "20 generated events"},
    {"id": "cp", "stage": "pre_probe", "type": "checkpoint", "visibility": "harness"}
  ],
  "probes": [
    {"id": "p-current", "kind": "temporal", "delivery": "respond", "trigger": {"after_event": "cp"},
     "query": {"op": "current", "subject": "p1", "attribute": "timezone"},
     "input": {"content": "What is my timezone? Answer with the UTC offset only.",
               "context": {"actor": "p1", "display_name": "Mara"}, "answer_schema": {"value": true, "status": true, "confidence": true}},
     "oracle": {"expected_status": "known", "accepted": ["UTC+1", "+01:00"], "forbidden": ["UTC+8", "+08:00"]},
     "evaluators": ["eval-structured"], "dimensions": ["temporal_memory"]}
  ],
  "ablations": [
    {"id": "a-relevant-p-current", "kind": "relevant_memory", "probes": ["p-current"],
     "method": "replay_excluding_events", "targets": {"event_ids": ["e-2"]}, "expected_effect": "degrade"},
    {"id": "a-swap-p-current", "kind": "counterfactual_content", "probes": ["p-current"], "method": "swap_parameter",
     "targets": {"event_ids": ["e-2"]},
     "counterfactual": {"events": {"e-2": {"content": "Update: my timezone is now UTC+2."}},
                        "oracle": {"p-current": {"expected_status": "known", "accepted": ["UTC+2", "+02:00"], "forbidden": ["UTC+8", "+08:00", "UTC+1", "+01:00"]}}},
     "expected_effect": "track"}
  ],
  "evaluators": [{"id": "eval-structured", "type": "structured", "config": {"normalization": "answer_normalized", "weights": {"value": 0.8, "status": 0.2}}}],
  "scoring": {"probe_aggregation": "weighted_mean", "score_range": {"min": 0, "max": 100}, "dimension_weights": {"temporal_memory": 1.0}}
}
```

---

# 5. 执行语义

## 5.1 数据包执行

涉及 `run_generated_pack`（v0.2 Profile）、`run_benchmark_pack`（静态公开模板）和 `run_materialized_pack`（评测方物化的隐藏实例）：

1. 生成的数据包严格等于 `profile.programs × profile.instance_seeds × ladder rungs`；静态数据包严格等于 `profile.required_templates`。缺失或多出任何程序或模板均视为严重错误，绝不允许悄然改变评测分值。
2. 每个描述符和实例在执行前**必须**通过前述校验（§4.10）。
3. 针对每个实例的每次重复测试 `r`，生成的实例对应的 Agent 种子为 `"<seed>:r<rung>:<r>"`，静态实例为 `"<instance seed>:<r>"`（隐藏实例则使用混淆别名）。完整条件（full condition）与每个已声明的消融条件均作为独立隔离的运行进行。
4. Agent 不支持的模板（§6.6）不予执行，并在报告中完整罗列。

## 5.2 条件隔离与环境独立性

每次重复测试中的各个条件——首先是 `full` 完整条件，随后按声明顺序依次执行各消融条件——均在**全新的 Agent 实例**（通过 `agent_factory()` 产生）上独立运行，使用相同的场景实例、相同的随机种子、相同的虚拟时钟演进以及相同的延迟采样探针输入。彼此之间仅存在记忆干预手段的差异。任何状态严禁跨越不同条件传递；进程隔离或网络传输的 Agent 在每个条件开始时接收全新的 `reset` 请求和全新生成的不透明 `run_id`，且在所有退出路径上均会被强制关闭释放。

消融条件必须执行该实例**完整**的探针序列，以确保前序探针的提问或行为动作不会变为隐蔽的二次干预；因果比对计算中仅对消融所声明的 `probes[]` 分配权重（其余探针按权重 0 记录）。

客观世界的状态演变在所有条件下均保持完全一致（§4.5）。条件标识符、消融 id、反事实替换值及预期效果对 Agent 始终完全不可见。

## 5.3 动作交互循环与亲历任务

对于 act 类型的探针，Runner 在首轮交互中向 Agent 投递任务目标、约束条件与可用工具定义，随后进入轮替交互：Agent 须返回一个 `tool_call`（带有唯一的 `tool_call_id`、属于提供列表的工具名、以及符合该工具 `input_schema` 的输入参数）或终止性的 `final` / `abstention`。每次工具调用由世界模拟器执行，其执行结果作为 `tool_result` 观察事件回传。该循环在 Agent 返回终止响应、耗尽 `max_agent_turns` 轮次或耗尽 `max_tool_calls` 次数时结束。完整的动作轨迹（调用顺序、工具、参数、执行结果）记录在探针结果中，供轨迹评测器打分。

**亲历任务（lived task）**（`task` 事件，§4.5）在历史记忆阶段运行完全相同的交互循环。其目标是一项真实的业务指令，其工具结果是真实的环境观察，而其遭遇的失败——例如由于未执行数据迁移而崩溃的部署操作——是 Agent 自己亲手导致的结果，而非别人告知的故事。该动作轨迹被记录为该次运行的经验轨迹，并且**绝不计入能力得分**：任务的存在是为了让系统形成亲身经历，任务期间出现的 Agent 协议失常（§5.4）仅作为运行警告记录。带有**试验 Oracle（trial oracle）**（包含 `task.oracle` 与 `task.evaluators`）的任务还会像 act 探针一样被评估，其结果记录在该次运行的 `task_results[]` 中；一系列此类试验构成了学习曲线（§7.9），属于不进入综合分数的诊断量。这些过往经验是否真正改变了 Agent 的决策，由后续带有 `no_recurrence` 约束的 act 探针进行严格检验（§4.7、§7.9）。

## 5.4 故障分类体系

每个执行的探针均具有唯一的 `outcome` 归属：

| 判定结果（Outcome） | 核心含义 | 分值认定 | 运行状态 |
|---|---|---|---|
| `scored` | 探针成功执行并完成评测。**认知性失败（cognitive failure）**依然属于 `scored`：回答错误、对可知事实选择弃权、执行了被禁止或复发的操作、错过或过早产生了发射事件，以及 Agent 自身行为失常——耗尽 `max_agent_turns` 或 `max_tool_calls`（记为 `trajectory_collapse` 轨迹崩溃）、调用未提供的工具、提供无法通过 Schema 校验的参数、复用旧的 `tool_call_id`、使用未知的响应步骤类型（记为 `agent_protocol_violation` 协议违规）。 | 获得评测器打分，或 0 分并标记对应错误代码 | `succeeded` |
| `execution_failure` | Runner、世界模拟器、评测器自身发生故障或传输层异常（属于 Agent 契约之外的异常、传输层超时等）。 | 记 0 分，保留权重 | `failed` |
| `unsupported` | 专用于不支持模板中的探针；此类模板将被整体跳过（§6.6）。 | — | — |

错误代码严格采纳报告 Schema 的封闭词表：`formation_miss`、`retrieval_miss`、`identity_mismatch`、`stale_memory_adoption`、`source_confusion`、`correction_loss`、`false_certainty`、`trajectory_collapse`、`skill_non_transfer`、`negative_transfer`、`error_recurrence`、`counterexample_neglect`、`commitment_miss`、`premature_trigger`、`self_model_drift`、`memory_hallucination`、`irrelevant_memory_interference`、`authority_confusion`、`agent_protocol_violation`、`execution_failure`、`timeout`、`rate_limited`、`adapter_error`、`tool_error`、`evaluator_error`、`custom`。

之所以做严格区分，是因为**执行失败率（execution failure rate）**（§6.6）直接关乎榜单准入资格：死循环或违反协议的 Agent 不得以系统故障为由推高执行失败率。

## 5.5 运行产物（Run Artifact）

单次运行记录（某次重复测试下的某一特定条件）包含：`run_id`（不透明字符串）、`scenario_instance_id`、`template_id`、`template_version`、`instance_seed`、`condition`、`ablation_id`、`ablation_method`、`ablation_tolerance`、`repetition`、`agent_seed`、`status`、时间戳、`scenario_score`、`probe_results[]`、`warnings[]` 以及 `validity`（§7.7）。探针结果携带 probe id 和 kind、outcome、分值、权重、维度标签、评测器详情、错误代码、延迟、输出摘要，以及适用的 `counterfactual {tracks, stale}`（§7.2）、`recurrence {eligible, recurred}`（§7.9）和 `traps[]`（Oracle 可诱发的潜在错误代码，用于界定 §7.9 各比率的有效分母）。带有试验 Oracle 的运行记录包含 `task_results[]`（`task_id`、`index`、`score`、`succeeded`、`failure_codes`）。Runner 私有调试扩展（最终世界状态及其哈希、动作轨迹明细、经验轨迹明细、发射事件日志、延迟采样摘要）在公开发布的报告中将被剥离。

---

# 6. 评分计算体系

所有内部数值计算均采用完全精度（`math.fsum`）；数值舍入仅在展示层进行。内部得分为 `p ∈ [0,1]`；对外展示的能力分数为 `100p`；因果差异指标以百分点（percentage points）展示，且允许为负数。

## 6.1 评测器打分 → 探针得分

探针得分为其对应评测器的得分；若引用了多个评测器，则为其未加权的算术平均值（§4.7）。

## 6.2 场景得分（Scenario score）

对于单次运行：

\[
S = rac{\sum_q w_q P_q}{\sum_q w_q}
\]

分母与分子遍历所有判定为 `scored` 或 `execution_failure` 的探针。执行失败的探针保留在分母中按 0 分计算（`fail_probe` 策略）；将其剔除将导致发生部分崩溃的 Agent 仅对其侥幸成功的探针计算平均分。

## 6.3 实例得分（Instance scores）

在实例的 `R` 次完整条件重复测试中，`full_score = mean_r S_r`。

针对该实例所声明的每个维度 `d`，其维度得分为完整条件运行中带有 `d` 标签的探针的加权平均值；无标签探针默认计入所有维度；若无任何探针携带该标签，则直接采用场景综合分。生成的实例聚合记录同时包含其所属 `rung` 与 `interference_count`（§8.1）。任何能力维度均严禁直接由配对因果指标折算；在 v0.1 Profile 赋予因果维度权重时，按 §7.6 方式计算。

## 6.4 模板与能力维度聚合

聚合遵循“模板优先（Template-first）”原则，确保实例数量绝不会隐蔽演变为语义权重：

\[
T_{t,d} = rac{1}{N_t}\sum_{s \in t} S_{s,d}
\qquad
D_d = 100 \cdot rac{\sum_t v_{t,d}\,T_{t,d}}{\sum_t v_{t,d}}
\]

其中 `v_{t,d}` 为该模板的 `scoring.dimension_weights[d]`（即对维度 `d` 的证据权重）。对于生成的数据包，模板即代表程序，计入 `T_{t,d}` 的实例**仅限**处于**规范档位（canonical rung）**的实例（§8.3）；所有档位的数据共同汇总喂入保持曲线。

## 6.5 MIB 综合得分、覆盖率与资格判定

\[
MIB_{base} = \sum_d W_d D_d, \qquad \sum_d W_d = 1
\]

其中 `W_d` 来自 Profile 配置。未定义全局安全防护惩罚项，因此 `MIB = MIB_base`。

每个维度的覆盖率等于已评测证据权重除以所需证据权重，其中所需证据权重包含数据包中的全部模板——包括因 Agent 缺乏对应能力而未执行的模板。Profile 综合覆盖率为 `Σ_d W_d · coverage_d`。综合覆盖率低于 `required_coverage` 阈值的报告判定为**部分报告（partial）**，绝不可作为**官方报告（official）**。

报告被评定为 `official` 必须同时满足：Profile 标记了 `official: true`、达到综合覆盖率要求、并且——在 Profile 声明了 `memory_dependence` 时——必须满足记忆依赖性门控条件（§7.10）。未达依赖性阈值的报告将追加 `memory_dependence.below_floor` 警告；其 MIB 得分依然予以报告，但明确声明为“未证明通过记忆机制取得的能力得分”。

## 6.6 不支持率与执行失败率

当 Agent 描述符将其所需能力声明为 `false` 时，该模板被判定为**不支持（unsupported）**。该模板将被整体跳过，记录在 `coverage.unsupported_required_templates` 中，其权重全额计入覆盖率分母；`execution.unsupported_rate` 记录数据包中未支持模板的占比。

\[
EFR = rac{	ext{\#\ execution\_failure\ Probe\ attempts}}{	ext{\#\ scheduled\ Probe\ attempts}}
\]

执行失败率（EFR）作为独立指标报告；无论得分多高，EFR 超标均可导致成绩作废。

---

# 7. 因果诊断指标体系

## 7.1 测试条件与配对基元

对于单次实例及其单次重复测试，定义在消融声明的探针子集上的归一化性能表现如下：

```text
F   完整条件（full）
R   相关记忆消融条件（relevant-memory ablated）
I   无关记忆消融条件（irrelevant-memory ablated）
N   无记忆对照条件（no-memory）
H   存在有害/陈旧记忆条件（harmful / stale memory present）
C   反事实内容置换条件（counterfactual content，支点事件叙述了其他事实）
M   无维护整理条件（no maintenance，扣留了整理窗口）
```

所有指标均在**严格配对（paired）**的运行记录上计算：相同实例、相同种子、相同延迟采样输入，彼此仅存在记忆干预手段的不同。相关记忆消融是首选的因果基准；无记忆对照条件仅用于同一次重复测试中未配置相关消融的探针，确保单一因果单元绝不会被重复计数。

## 7.2 记忆收益、顶空间归一化记忆收益与内容追踪

\[
MB = F - R \qquad (	ext{带符号，绝不截断})
\]

\[
HMB = rac{\max(0, F-R)}{1-R} \quad 	ext{适用于 } R < 1 - \epsilon,\ \epsilon = 0.02
\]

若消融条件下的基线表现已经处于天花板 `1 − ε` 容差之内，说明该场景不具备可测量的提升空间（headroom），此时不纳入 HMB 计算；其原始的 MB 依然正常报告。

移除事件只能证明该事件中的*某些信息*起到了作用；反事实置换则进一步证明起作用的是其**具体内容**。在 `swap_parameter` 消融发生改变的探针集合上，唯有完整条件下的回答原本正确（`score = 1`）时，该对运行才具备计算**资格（eligible）**：若在两组条件下原本就均回答错误，则根本无法反映内容追踪特性。

\[
CTR = rac{\#\{	ext{答案在反事实 Oracle 下判定正确的资格对数量}\}}{\#	ext{资格对总数}}
\qquad
SAR = rac{\#\{	ext{回答了原始历史旧值的资格对数量}\}}{\#	ext{资格对总数}}
\]

`content_tracking_rate`（内容追踪率）同时报告 `eligible_n`、`total_n`（所有发生变更的探针总数）及其比值 `coverage`；`stale_adoption_rate`（陈旧记忆采纳率）则专门针对顽固停留在被替换旧内容的回答子集。依靠固有先验答题的系统，无论其完整得分多高，其 CTR 必然极低；该指标直接充当记忆依赖性的准入门槛（§7.10）。

`consolidation_benefit = F − M`（巩固收益，百分点，带符号）用于报告 Agent 自身的后台整理工作带来了多大性能收益（仅适用于实现了 `maintain` 的系统）。

## 7.3 无关记忆稳定性（IMS）

\[
IMS_	au = 1 - rac{\max(0, |F-I| - 	au)}{1-	au}, \quad 	ext{截断至 } [0,1]
\]

其中 `τ` 为消融设定的 `tolerance`。不论是理论上无关的记忆带来了意外帮助，还是带来了意外干扰，均会削弱稳定性得分。

## 7.4 记忆危害与危害抵御度（HRS）

以纯净基线 `C = F` 为参照：

\[
MH = \max(0, C-H), \qquad HRS_	au = 1 - rac{\max(0, C-H-	au)}{1-	au} \quad 	ext{截断至 } [0,1]
\]

审讯诱导车道（`MIB-ADV-*` 以及世界模型中的 `question` 断言）属于最纯粹的有害条件：注入事件纯粹由问句构成，不确立任何事实，因此有无注入下的理论 Oracle 完全一致，此时 `C − H` 的性能滑坡全额归因于虚假信息的错误植入。

## 7.5 净记忆增益（NMG）

`NMG = MB − MH`，以能力分（百分点）表达。该量为诊断量，**绝非** MIB 综合分。

## 7.6 因果诊断分

\[
CausalScore = HMB \cdot rac{0.50 + 0.20\,IMS + 0.30\,HRS}{0.50 + 0.20\,[IMS\ 	ext{存在}] + 0.30\,[HRS\ 	ext{存在}]}
\]

稳定性与危害抵御度的得分必须依据系统已展现的实际收益进行缩放：若无此门控约束，完全不具备记忆能力的 Agent 将轻而易举刷出 `IMS = HRS = 1` 的满分。在 v0.2 中，该指标纯属诊断量；仅在 v0.1 Profile 显式赋予 `causal_memory_impact` 权重时，该量才进入能力维度计算，且必须源自配对指标，绝不直接取自完整条件绝对表现。当不存在具备有效提升空间的相关/无记忆配对时，该单元的分值未定义。

因果诊断指标首先在模板内聚合，随后按模板证据权重（v0.1 Profile 下为因果证据权重）在模板间加权汇总。

## 7.7 配对有效性验证

因果配对有效的充要条件是：变体运行与完整运行具有完全一致的实例 id、模板 id、实例种子、Agent 种子以及延迟采样探针摘要，且变体运行包含的探针必须是完整运行探针的合法子集。每次运行均记录 `validity.causal_pair_valid`；无效的配对不贡献任何计算值，并在报告中触发 `causal.pair_invalid` 警告，绝不得伪造为常规数值。

## 7.8 负迁移对照与反例消融

**标准化负迁移对照（standardized Negative Transfer control）**是在不匹配任务上设置的 `negative_transfer` 消融：扣留导致技能形成的经验片段（`V`，未形成技能记忆的任务表现），并与完整条件进行比对（`F`，具备该技能记忆时的任务表现）。如果记忆对本不适用的任务产生了性能损害，即构成负迁移：

\[
NT = \max(0, V - F), \qquad NTR_	au = 1 - rac{\max(0, V - F - 	au)}{1 - 	au} \quad 	ext{截断至 } [0,1]
\]

`negative_transfer_rate` 指的是在该对照探针中，完整条件运行结果被打上 `negative_transfer` 错误代码的比例（即在明令禁止的场合错误应用了学得的动作）。唯有在探针序列前文没有任何环节会重新传授该技能时，该对照才成立，因此 `mib.skill.v1` 将不匹配任务安排在匹配任务**之前**执行。

`counterexample` 消融则专门移除指示某项学得操作不适用的警示片段。它体现的是对适用边界的敏感度，其自身不产出独立的因果指标；若某程序希望将其移除视为记忆收益，可将其声明为该任务探针的 `relevant_memory` 消融。

## 7.9 全流程单条件诊断指标

以下指标**仅从完整条件（full runs）**的运行记录中推导——核心在于考察 Agent 运用其记忆实际做了什么，而非考察移除记忆后会发生什么——若没有符合条件的样本，则标记为缺失，绝不记为 0。它们均可从报告中的 runs 记录复算（§9.2）：

- **错误复发率（Error recurrence）。** Oracle 带有 `no_recurrence` 约束的 act 探针构成符合资格的亲历失败情境；其结果记录 `recurrence {eligible, recurred}`。`error_recurrence_rate = recurred / eligible`；`error_avoidance_score = 1 − error_recurrence_rate`。
- **学习曲线（Learning curve）。** 包含至少两次试验结果（§5.3）的运行记录构成一条学习曲线：`learning_gain` = 末次试验得分 − 首次试验得分；`area_under_learning_curve` = 各试验的平均得分。两者均在多次运行间取平均。
- **记忆诱发错误率（Memory-induced error rate）。** 判定为错误的探针中，错误原因直接归咎于记忆机制的比例（错误代码为 `stale_memory_adoption`、`correction_loss`、`authority_confusion`、`memory_hallucination`、`source_confusion`、`identity_mismatch`、`negative_transfer`、`error_recurrence`、`irrelevant_memory_interference`、`premature_trigger`、`self_model_drift`）。
- **权威混淆率（Authority confusion rate）。** 在 `traps` 包含 `authority_confusion` 的探针中（其 Oracle 明令禁止采纳非权威陈述），Agent 依然盲从采纳的比例。
- **历史保真度（Historical fidelity）**、**信源归属准确率（Source attribution accuracy）**、**自我准则延续度（Self-limitation continuity）**。分别对应探针类别为 `historical`、`audit` 和 `self` 的平均得分。

## 7.10 记忆依赖性准入门槛

能力分唯有证明回答切实依赖于记忆内容，才有资格被称为记忆得分。Profile 中的 `memory_dependence = {metric, floor}`（默认为 `content_tracking_rate ≥ 0.5`）基于基准层面的综合诊断值进行判定：

```text
eligible = true    metric ≥ floor
eligible = false   metric < floor          → 产生 warning memory_dependence.below_floor，绝不可评定为 official
eligible = null    不存在具备资格的配对对  → 不可评估（not assessable），绝不可评定为 official
```

报告中的 `memory_dependence` 区块记录门控结论（`metric`、`floor`、`eligible`、`eligible_n`、`total_n`）以及并列的诊断指标：`content_tracking_rate`、`stale_adoption_rate`、`memory_benefit`、`headroom_normalized_memory_benefit`、`harm_resistance`、`consolidation_benefit`、`error_recurrence_rate`。门控阈值属于基准公共政策（§11）。

---

# 8. 统计度量与干扰距离阶梯

## 8.1 距离阶梯与记忆保持

程序的 `ladder` 定义了各档位的干扰事件数量（默认 `[0, 20, 100]`；MIB-M 开发 Profile 采用 `[0, 100, 1000]`）。某个种子的档位 `k` 实例，就是在过往与探针之间插入了 `ladder[k]` 个生成的干扰事件（§4.5）；记忆形成事件、探针提示词及其可接受答案完全保持一致，唯有禁止项列表会随着干扰中提及的新实体而相应扩充。性能随干扰距离变化的函数关系构成了该程序的**保持曲线（retention curve）**，在报告的 `retention` 块中按模板分别呈现；各档位均如实记录其对应的事件数、token 数与虚拟小时数：

```text
rungs[]                 {rung, interference_count, interference_tokens, distance_hours, full_score, n}
retention_index         各档位得分的算术平均值                       1.0 表示沿阶梯毫无衰减
half_distance           得分相较 rung-0 跌落一半时的干扰事件数，
                        在档位间通过线性插值求得；若阶梯全程未跌落一半，
                        则为 null，并标注 half_distance_beyond_ladder = true
canonical_rung          承载基准能力得分的指定档位（§8.3）
```

阶梯是 §1.3 阐述的核心识别条件：若系统在超出工作上下文窗口的距离下保持曲线依然平坦，说明它证实了记忆系统的存在；若系统在 rung 1 发生断崖式崩塌，说明它此前仅仅是在进行纯粹的上下文阅读。

## 8.2 统计基元与分层 Bootstrap 重采样

重复测试、实例、模板和能力维度是绝不可相互混淆的抽样层次。对于静态数据包，语义设计单元是模板，隐藏实例用于评估同一设计内的泛化能力。对于生成的数据包，程序代表设计，而**规范档位实例（canonical-rung Instance）**（单个种子）是基本统计单元：程序集合属于 Profile 的固定政策，不参与重采样。

为确保因果配对绝不被人工拆散，每次重复测试的充分统计量（全流程维度得分和配对因果指标）均进行预先计算。单次抽取流程如下：

```text
在每个模板内部重采样实例，并在每个实例内部重采样重复测试
        ↓
静态包：对模板集合进行一次全局统一重采样；生成包：保留全部固有程序
        ↓
基于该单次重采样数据，重新计算各个维度得分、每项因果诊断量及 MIB 综合分
```

静态包的模板重采样在所有维度间全局共享：跨维度模板使得维度得分之间天然具备正相关性，若按维度独立重采样模板，将人为破坏这一协方差结构，从而不合理地缩窄 MIB 得分的置信区间。

区间默认采用百分位区间（95% 水平对应 2.5% / 97.5% 分位点）。若设定了 `statistics.interval_method: bca`，则采用**偏差校正与加速（BCa）**方法：偏差参数 `z0` 来自落入点估计值下方的重采样抽取比例，加速参数 `a` 来自在同一统计基元（生成包基于实例，其他基于模板）上的刀切法（jackknife）留一估计；若抽样退化（所有值完全相同，或点估计落在抽样分布之外），则自动回退至百分位区间并在 `ci.method` 中明确批注。若支撑某维度的单元数量少于 `statistics.min_templates_per_dimension`（默认 5；静态包为模板数，生成包为规范档位实例数），则该维度不计算区间，且只要有任何具备权重的维度缺失区间，MIB 综合分区间亦一并略去；报告记录该阈值和受影响维度，并追加 `statistics.insufficient_templates` 警告。在区区三个样本点上套用百分位区间纯属装饰，绝非科学证据。

统计结果块中严格以 `mib_score.value` 记录单点估计值，绝不以 bootstrap 均值替代，确保单份报告具备唯一确定的 MIB 分值。

## 8.3 规范档位与基准能力得分

Profile 的 `canonical_rung` 指定了哪一个档位的实例有资格参与模板聚合（§6.4）、Bootstrap 计算（§8.2）以及记忆依赖门控判定。它**应当（SHOULD）**选用干扰距离明显超出短期工作上下文窗口的档位（随版本发布的 Profile 中选用 rung 1），确保能力得分是在远距离下读取，而非在毫无干扰的 rung 0 测得。分数核验（§9.2）同样执行相同的过滤标准；规范档位记录在 retention 块中，确保脱敏后的报告依然具备可验证性。

## 8.4 系统间的配对对比

针对相同隐藏实例评测的两套系统，对比时必须针对单元层面的差值进行配对 Bootstrap 分析，而非分别独立计算各自的 Bootstrap 区间后进行比对。当两者的配对差值区间包含 0 时，排行榜**应当（SHOULD）**将两套系统标定为在统计学上无显著差异。

---

# 9. 报告呈现与分数核验

## 9.1 评测报告

`schemas/mib-report.schema.json` 规范了报告的完整内容：基准身份（Profile、track、scale、pack）、系统与适配器标识、运行环境版本、执行摘要（runs 数量、探针尝试次数、执行失败率、不支持率）、`results.runs[]`、聚合统计量（实例层包含 rung 和干扰数量，模板层，维度层，MIB 综合分包含 `base_score` / `global_guardrail_penalty` / `final_score` / `official` / `partial`）、`causal_metrics[]`、`retention[]`（§8.1）、`memory_dependence`（§7.10）、`efficiency`（Runner 实测的探针延迟和工具调用总数，以及参赛者自行上报并在各次运行间累加的资源用量）、覆盖率明细、统计区间、运行警告以及溯源元数据。生成包报告的 `benchmark.mib_version` 规定为 `"0.2"`。

## 9.2 分数核验（Score verification）

`mib verify-score` 重新计算报告所承载的每一个计算层级，并标明其核验级别 `verification_level`：

- **`full`**（内部完整报告，携带 `results.runs`）：依据探针结果复算每次运行的场景分；基于配对运行复算每个实例的完整得分、各维度得分、因果诊断量及错误复发率（消融容差随运行记录携带）；随后复算模板（仅规范档位）、维度及 MIB 综合分。
- **`aggregates_only`**（脱敏公开报告，剥离了具体 runs）：仅核验模板、维度及 MIB 综合分的聚合一致性。

评测服务在对报告进行公开脱敏前，必须在 `full` 级别下核验内部报告；任何未能通过聚合一致性核验的公开报告都将被拒绝收录。

## 9.3 能力卡片（Capability Card）

所有发布的分数必须以多维度的能力卡片形式呈现，绝不得简化为单一孤立的分值：涵盖 Profile、轨道、尺度、Agent 标识；MIB 综合分及其置信区间；各个能力维度及其覆盖率；因果诊断量（记忆收益、记忆危害、净记忆增益、无关稳定性、危害抵御度、内容追踪率、陈旧采纳率、错误复发率、巩固收益）；行为诊断量（负迁移及其发生率、学习增益与曲线面积、历史保真度、信源归属度、权威混淆率、自我准则延续度、记忆诱发错误率）；按程序划分的保持度（各档位分值、保持指数、半距离）；记忆依赖门控判定结果；覆盖率达标情况；执行失败率；以及该成绩被认定为官方（official）、部分（partial）还是开发（development）性质。

## 9.4 分数标识的必要要素

任何公开引用的分数，必须完整注明其 MIB 版本、Profile 标识、评测轨道、评测尺度、场景包版本、规范档位编号，以及 Agent / 基座模型 / 记忆系统的版本号。单独声明 `MIB 77.2` 不构成有效的评测结论。

---

# 10. 基准校准（Calibration）

在场景包正式冻结之前，每个程序**应当（SHOULD）**在固定的模型基准线下进行全档位校准——B0 无记忆、B1 完整可见上下文、B2 朴素检索、B3 结构化记忆——保持模型、提示词、推理策略、工具、解码超参数及种子完全一致。通过记忆区分度指数 `MDI = FC − NM`（全上下文性能减去无记忆性能）甄别出记忆无法带来帮助（`FC` 过低）或根本不需要记忆（`NM` 接近天花板）的程序；此类程序必须进行重构或剔除。具体实施流程和准入门槛详见 `docs/harness/`。

随 v0.2 附带的规则 Agent 校准（fixture calibration）仅用于检验底层调用管道以及设计所预期的分值高下顺序，不代表更多含义。针对生成语言手写了六套规则 Agent（位于 `mib_runner.agents`）：

```text
StructuredMemoryAgent   针对所观察到的世界维护完美模型              保持曲线平坦，CTR = 1.0
WindowMemoryAgent       与上述类似，但仅保留最近 12 次观察记录       性能随干扰阶梯发生衰减
ConsolidatingAgent      在上述滑动窗口基础上实现 maintain() 归档     consolidation_benefit > 0
RecencyAgent            将所有提问/假设均视为事实，以最新提及者为准  呈现陈旧采纳与权威混淆，无法遗忘
OvergeneralizingAgent   不加节制地在所有场合应用学得的技能          在不匹配任务中产生负迁移
NoMemoryAgent           对所有问题一律弃权，采取朴素试错动作        得分极低，依赖性无法评估
```

这套规则 Agent 绝不代表真实模型所面临的任务难度。

---

# 11. 防泄漏、抗作弊与治理机制

- 未来的探针、Oracle 内部数据、查询语句、消融标识、反事实替换值、隐藏真实基准、相关性标注以及评测器判定结果，绝不对 Agent 进行透传，且评测器结果绝不在条件运行完成前提前返回。
- 程序定义、表面改写词表与生成器代码完全开源。隐藏评测使用评测方保密的私有种子生成实例，在对外物化产物中将实例 ID 和种子替换为加密哈希别名，在完全遮蔽评测方本地存储的沙箱环境中执行外部提交，并对任务清单和评测结果实施密码学数字签名（`MIB-Leaderboard-Evaluation-Service.md`）。由于生成逻辑完全公开，针对生成语言模式进行专门适配的 Agent 能够被精准检验：它依然必须在长距离下保持记忆内容，并且依然必须在反事实置换下做出跟随反应。
- 能力维度权重、程序权重、干扰阶梯、规范档位、依赖性阈值、因果分项权重及 Bootstrap 门槛均属于基准核心政策：公开且有版本管理。标准数据包中的程序仅在存在明确缺陷记录时方可修改，且必须发布版本更新并对所有受影响的历史提交重新跑分核算。
- 不同 Profile 或跨重大版本的分数绝不进行混合排名。

---

# 12. 核心不变量（Invariants）

1. 信息检索不等于记忆智能；单纯存储不等于发挥功用的功能性记忆。
2. 未来的探针绝不泄漏至记忆形成阶段；仅观察探针在外观上与普通观察事件完全无异。
3. Agent 绝不能直接修改世界客观状态；它只能通过工具调用观察动作带来的客观后果。
4. 世界演变逻辑在所有评测条件下完全无差别生效；消融与反事实重放改变的仅仅是告知 Agent 的观察内容。
5. 所有因果条件均成对配对、相互隔离，并在全新的 Agent 实例上执行。
6. 能力基准分取自规范档位下的完整记忆表现；因果量充当诊断指标，记忆依赖性作为准入资格门控而非混入分数。
7. 原始因果差值保持代数符号；归一化分项截断至 `[0,1]`。
8. 区分选择性的加分（IMS、HRS）必须依据系统已展现的记忆收益进行缩放。
9. 实例必须首先在模板内部完成聚合，随后模板方可进入维度聚合；阶梯档位聚合为保持曲线，绝不压缩为孤立单点。
10. 缺失或不支持的维度覆盖绝不能虚假拉高评测得分。
11. 认知性失败、执行故障与能力不支持属于严格互斥的判定结果。
12. 所有发布的分数必须能够在声明的核验级别下从报告中完全复算。
13. 确定性比对、结构化解析、自发发射以及世界状态断言的优先级高于语言相似度匹配；绝不使用模型进行主观打分。
14. 生成实例的所有 Oracle、支持集、反事实孪生和泄漏证明均由世界模型自动推导，绝不手动撰写。
15. 亲历任务属于经验积累过程，绝非能力得分；其中的试验形成学习曲线，绝非最终得分。
16. 撤回操作将某项事实从所有层级中彻底抹去；遗忘的有效性通过该值不再被使用来检验，而非通过 Agent 口头声称已遗忘来检验。
17. Track A 与 Track B，以及不同的 Profile，绝不可混合排列在同一榜单中。
18. 遵从 KIP 协议、记忆库存储体积以及特定供应商身份，均不带来任何额外加分。

---

# 附录 A — 路线图：已设计但未执行的功能

以下内容目前尚未在参考实现中执行或计分，未包含在场景 Schema 中，亦不应出现在 v0.2 评测报告中。

**评测尺度。** MIB-L（10,000+ 个事件）以及任何档位超越现代工作上下文极限的长阶梯。MIB-M 开发 Profile 目前达到 1,000 个干扰事件（约 8,000 token）；这代表一定的距离，但并非上下文溢出。目前的距离通过生成的干扰事件数、token 数和虚拟时间来计量——尚未基于 Agent 必须持续跟踪的“高信息密度真实事件”来计量。

**程序扩展。** 跨智能体记忆、多模态记忆、隐私保护边界（在信任前提下获知的事实严禁透露给其他提问者）、特定领域专业 Profile；在真实系统中体现关键价值的整理窗口程序（当前附带的窗口仅对规则巩固 Agent 具有关键价值）。

**评测轨道。** Track C 记忆组件诊断（记录级消融、快照对比、检索轨迹追踪、影响度追踪）及其所需的 Memory Adapter 专用底层操作。

**场景构造。** 评测器类型 `semantic_constraints`、`llm_judge`；探针触发器 `at_sequence`、`at_time`、`world_condition`、`manual`；消融方法 `memory_mask`、`memory_delete`、`snapshot_branch`、`filtered_memory_clone`、`context_filter`、`black_box_reconstruction`；动态参数源 `datetime_range`、`generator`、`derived`；执行策略 `skip_probe`、`abort_scenario`；场景级罚分及罚分上限；全局安全防护惩罚项；实例内容完整性密码签名（目前仅支持数字摘要）。

**高级指标。** 影响度精确率（Influence Precision）；记忆缺口闭合度（Memory Gap Closure，需依托校准工具的全上下文基线）；记忆系统工程效率（每次事件的写入次数、存储占用、写入放大率——当前实现的 `efficiency` 区块仅包含 Runner 实测的延迟与工具调用次数，以及参赛者自行上报的数据）；将运行成本作为一等公民的带预算约束 Profile。

**评测执行策略。** 面向自由文本回答的模型辅助解析器（固定版本、确定性解码、将解析出的结构体落盘作为可审计记录）；引入置信度加权的梯队制排行榜；全档位下基于真实固定基座模型的完整实证校准。

---

# 附录 B — 核心公式速查

```text
场景得分         S = Σ w_q P_q / Σ w_q                       （遍历 scored 与 execution_failure 探针）
实例得分         full = mean_r S_r ; 维度 d = 打上 d 标签的探针的加权平均值
模板得分         T_{t,d} = 规范档位实例上的算术平均值
维度得分         D_d = 100 · Σ_t v_{t,d} T_{t,d} / Σ_t v_{t,d}
MIB 综合分       MIB = Σ_d W_d D_d
维度覆盖率       Coverage_d = 已评测证据权重 / 所需证据权重（不支持的模板计入所需证据）

记忆收益         MB = F − R                                  （带符号）
顶空间收益       HMB = max(0, F − R) / (1 − R)               适用于 R < 0.98
内容追踪率       CTR = 反事实下答案正确的资格对数 / 资格对总数（要求 full 条件正确）
陈旧采纳率       SAR = 回答了历史旧值的资格对数 / 资格对总数
无关稳定性       IMS_τ = 1 − max(0, |F − I| − τ) / (1 − τ)
记忆危害         MH = max(0, C − H)
危害抵御度       HRS_τ = 1 − max(0, C − H − τ) / (1 − τ)
净记忆增益       NMG = MB − MH
巩固收益         ConsolidationB = F − M
负迁移           NT = max(0, V − F)                          V 为未注入技能记忆的不匹配任务
负迁移率         NTR_τ = 1 − max(0, V − F − τ) / (1 − τ)
错误复发率       ERR = 复发次数 / 具备资格的亲历失败机会数      （基于 full 条件）；EAS = 1 − ERR
学习增益/面积    LG / AULC = 末次 − 首次试验分 / 试验平均分    （针对试验次数 ≥ 2 的运行）
记忆诱发错误率   MIER = 归因于记忆故障的探针数 / 全部计分探针数
权威混淆率       ACR = 盲从非权威断言的探针数 / 设伏探针总数
历史/审计/准则   HF / SAA / SLC = 对应 kind 为 historical / audit / self 探针的平均得分
因果诊断分       CausalScore = HMB · (0.5 + 0.2·IMS + 0.3·HRS) / (0.5 + 实际存在的权重)  （诊断量；缺失 HMB 时未定义）
保持度           各档位得分；retention_index = 均值；half_distance 通过线性插值推算
依赖性门控       合格 ⇔ metric ≥ floor                       （默认 content_tracking_rate ≥ 0.5）
统计区间         百分位法（默认）或 BCa：z0 取自落入点估计下方的抽取比例，a 取自留一刀切估计
执行失败率       EFR = execution_failure 探针尝试次数 / 全部排期探针尝试次数
```

---

# 附录 C — 关联文档索引

| 主题领域 | 文档位置 |
|---|---|
| 本规范性规范 | `docs/MIB-Specification.md`（中文：`docs/cn/MIB-Specification.md`） |
| v0.2 架构演进与设计推导 | `docs/proposals/MIB-v0.2-Evolution.md` |
| 程序、世界模型与生成器实现 | `src/mib_runner/generate/`, `src/mib_runner/worldmodel.py` |
| Agent Adapter 通信协议（stdio JSONL、本地 HTTP、描述符、错误体系） | `docs/MIB-Agent-Adapter.md`（中文：`docs/cn/MIB-Agent-Adapter.md`） |
| 托管评测服务、沙箱机制、签名认证与排行榜 | `docs/MIB-Leaderboard-Evaluation-Service.md`、`docs/harness/` |
| v0.1 里程碑规划与静态模板清单 | `docs/MIB-v0.1-Test-Plan.md`（中文：`docs/cn/MIB-v0.1-Test-Plan.md`） |
| 迁移智能诊断、Memory Adapter 与 MIB-R 原型 | `docs/experimental/`（中文：`docs/cn/experimental/`） |
| 已归档的旧版设计草案（仅供背景参考） | `docs/archive/`（中文：`docs/cn/archive/`） |
| JSON Schema 规范定义 | `schemas/` |
