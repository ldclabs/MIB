# MIB Agent Adapter 协议规范

## MIB Runner 与记忆赋能智能体之间的传输中立通信接口

**版本：** 0.1-draft
**状态：** 适配器协议提案 / `MIB-Specification.md` 配套规范

---

# 0. 规范目标

本规范定义了 **MIB Runner（评测执行器）** 与受评测的**记忆赋能智能体（Agent）**之间的交互边界。

Agent Adapter 的核心目的不是规定智能体内部如何实现记忆存储。

它的职责是标准化基准评测所需的各项交互机制：

```text
启动隔离的评测运行（isolated run）
按时间线逐步交付观测数据（observations）
驱动智能体经历真实发生的时间线（lived timeline）
发起未来提问探针（future question）
下达未来任务目标（future task）
捕获智能体自发产生的记忆触发行为（spontaneous emissions）
通过世界模拟器（World Simulator）托管并仲裁工具调用
在消融条件下重放相同实验进行对照
收集可供审计的产出结果与资源开销元数据
```

核心抽象拓扑：

```text
MIB Runner
    │
    │  Agent Adapter 边界
    ▼
Agent + Long-Term Memory（智能体与长效记忆系统）
```

Adapter 边界之后的所有内容，属于参赛方的私有实现；
Adapter 边界之前的所有内容，完全由基准评测体系严格管控。

---

# 1. 核心设计原则

Agent Adapter 必须恪守以下职责划分边界：

```text
Runner 管控范围：
    场景定义（Scenario）
    隐藏的环境基准真值（Ground Truth）
    虚拟时钟（Virtual Time）
    世界模拟器（World Simulator）
    未来探针（Future Probe）
    评判真值（Oracle）
    多层评测器（Evaluators）
    消融干预条件（Ablation condition）
    基准环境工具（Benchmark tools）

Agent 管控范围：
    内部推理（Reasoning）
    记忆形成（Memory formation）
    记忆存储（Memory storage）
    记忆巩固（Consolidation）
    回忆检索（Recall）
    内部规划（Planning）
    最终响应生成（Response generation）
```

Runner 严禁协助智能体进行记忆回忆；
Agent 严禁以任何方式越权探测基准内部的机密元数据。

---

# 2. 架构中立性

Agent Adapter 不预设智能体采用任何特定的记忆架构形态。

兼容以下各类记忆系统：

```text
原始对话历史重放（raw history replay）
向量检索（vector retrieval / RAG）
摘要记忆（summary memory）
键值记忆（key-value memory）
关系型数据库（relational memory）
图谱记忆（graph memory）
情景记忆（episodic memory）
过程/程序记忆（procedural memory）
循环神经网络/学习型循环记忆（learned recurrent memory）
外部数据库
KIP 协议体系
各类混合架构（hybrid memory）
```

在核心常规评测中，Adapter **严禁**将以下系统内部概念设为前置依赖：

```text
memory node（记忆节点）
embedding（向量嵌入）
Assertion（主张）
Experience（经验）
Skill（技能）
memory_strength（记忆强度）
retrieval score（检索相关度得分）
```

上述概念仅归属于可选的深度诊断赛道或独立的 Memory Adapter。

---

# 3. Agent Adapter 与 Memory Adapter 的分工

MIB 将通信接口解耦为两个独立层面：

## 3.1 Agent Adapter（智能体适配器）

常规基准评测所**必须**实现的接口。

它回答核心问题：

> Runner 如何与作为一个整体的智能体系统进行标准交互？

核心操作原语：

```text
describe（描述系统能力）
reset（重置运行环境）
observe（接收环境观测）
respond（回答认知提问）
act（执行环境交互任务）
```

可选运维操作：

```text
maintain（触发记忆整理与巩固）
close（释放会话资源）
health（健康检查探针）
```

## 3.2 Memory Adapter（记忆诊断适配器）

用于深度白盒诊断的**可选**扩展接口。

可暴露以下高级操作：

```text
snapshot（捕获记忆快照）
inspect（检查内部记忆记录）
mask（动态遮蔽特定记忆）
delete（删除特定记忆记录）
restore（恢复记忆快照）
metrics（导出内部度量指标）
trace（追踪因果影响链路）
```

在未实现 Memory Adapter 的情况下，Agent Adapter 依然能够完整支持所有常规基准评测。

这对于保障架构中立性至关重要。

---

# 4. 评测对象单元

MIB 评测的整体单元为：

```text
Agent（智能体）
+
Long-Term Memory System（长效记忆系统）
```

Agent Adapter 将两者视为一个统一的有状态认知系统。

在 `reset` 调用与单次运行结束之间，系统可持续累积内部认知状态。

而在每次独立的评测条件启动时，该状态必须依照本文档规定的隔离规则被彻底重置。

---

# 5. 赛道语义与适配约定

## 5.1 赛道 A —— 记忆系统赛道（Track A — Memory System Track）

旨在精确量化记忆系统本身的实际贡献。

在赛道 A 的榜单级评测中，记忆系统外围的智能体行为应受基准统一管控。

推荐形态：

```text
MIB 参考 Agent
    +
参赛方记忆系统
```

或：

```text
基准认可的固定 Agent 封装
    +
参赛方记忆系统
```

任何修改了基座模型、系统提示词、推理逻辑或工具使用策略的提交，通常划归为赛道 B，而非赛道 A。

在上述两种情况下，Agent Adapter 均作为与外部 Runner 通信的标准边界。

## 5.2 赛道 B —— 完整智能体赛道（Track B — Integrated Agent Track）

参赛方可自主定制全套软硬件：

```text
基座大模型
智能体策略
记忆架构
记忆沉淀与检索提示词
记忆巩固逻辑
检索召回算法
工具调用决策
```

Adapter 将整套集成系统作为一个统一黑盒向外暴露。

## 5.3 赛道 C —— 深度诊断赛道（Track C — Diagnostics）

赛道 C 结合 Agent Adapter 与可选的 Memory Adapter 共同执行深度剖析。

---

# 6. 核心接口操作集

符合 MIB v0.1 规范的 Agent Adapter **必须**实现：

```text
describe()
reset()
observe()
respond()
act()
```

以下操作属于**可选**扩展：

```text
maintain()
close()
health()
```

Adapter 可自行暴露特定厂商的私有扩展操作，但 Runner 在执行 MIB 核心场景时绝不依赖此类私有接口。

---

# 7. 接口语义参考定义

概念级 TypeScript 接口定义：

```typescript
interface MIBAgentAdapter {
  describe(): Promise<AgentDescriptor>;

  reset(
    request: ResetRequest
  ): Promise<ResetResult>;

  observe(
    request: ObserveRequest
  ): Promise<ObserveResult>;

  respond(
    request: RespondRequest
  ): Promise<RespondResult>;

  act(
    request: ActRequest
  ): Promise<ActResult>;

  maintain?(
    request: MaintainRequest
  ): Promise<MaintainResult>;

  close?(
    request: CloseRequest
  ): Promise<CloseResult>;

  health?(): Promise<HealthResult>;
}
```

以上属于语义层面的抽象接口。

具体通信载体可采用：

```text
进程内直接调用（in-process calls）
HTTP JSON
stdio JSONL
RPC（如 gRPC）
容器网桥通信
```

只要外部可观测的行为语义保持一致即可。

---

# 8. 适配器能力描述（Adapter Descriptor）

`describe()` 用于向评测框架宣告自身支持的能力特性，属于握手协商调用。

该调用**严禁**修改智能体内部的任何记忆状态。

示例：

```json
{
  "protocol": "mib-agent/0.1",
  "implementation": {
    "name": "Example Agent",
    "version": "1.4.2",
    "vendor": "Example Labs"
  },
  "track_support": [
    "integrated_agent"
  ],
  "capabilities": {
    "observe": true,
    "respond": true,
    "act": true,
    "spontaneous_emissions": true,
    "maintenance": false,
    "runner_managed_tools": true,
    "structured_output": true,
    "virtual_time": true,
    "seedable": false
  },
  "state": {
    "run_isolation": "hard",
    "observe_visibility": "read_after_write",
    "request_idempotency": true
  },
  "limits": {
    "max_observation_bytes": 1048576,
    "max_output_bytes": 1048576
  }
}
```

该 Descriptor 会被完整记录到评测运行产物（Run Artifact）中。

---

# 9. 描述信息必须真实可靠

Adapter 严禁虚标自身无法稳定提供的能力。

例如：

```text
seedable = true
```

意味着基准下发的随机种子确实能够约束参赛方系统内部所有支持定种的随机过程。

```text
run_isolation = hard
```

意味着历史评测运行中沉淀的记忆绝不会对新的独立运行产生任何干扰或影响。

不实的能力声明将被判定为 Adapter 协议符合性违规（conformance failure），而非单纯的记忆能力得分低下。

---

# 10. 运行实例标识（Run Identity）

每个基准评测条件都在独立的透明命名空间中执行。

Runner 在请求中统一下发：

```text
run_id
```

示例：

```text
run_8cf2f92c
```

该标识**必须是不透明的哈希或随机串（opaque）**。

严禁在 `run_id` 中编码以下信息：

```text
场景所属套件
评测能力维度
全量记忆对照标记
相关记忆消融标记
有害记忆测试标记
客观基准真值标签
```

反面示例（严禁）：

```text
MIB-TIME-001-relevant-ablation
```

正确示例：

```text
run_8cf2f92c
```

这从根本上杜绝了根据条件标签进行针对性作弊的可能性。

---

# 11. 场景元数据可见性隔离

默认情况下，智能体在运行中**不应**接收到以下内容：

```text
scenario_id（场景 ID）
suite（套件分类）
dimensions（维度标签）
tags（分类标签）
difficulty（难度等级）
ablation kind（消融类型）
expected effect（预期效应）
evaluator type（评测器类型）
Oracle（判定真值）
ground truth（客观真值）
```

除非特定场景将某些元数据显式作为任务可见信息的一部分下发。

Runner 在内部完整记录上述元数据；Adapter 仅向智能体透传真实世界中理应自然观测到的信息。

---

# 12. 请求信封（Request Envelope）

各类传输协议均应统一采用标准请求信封。

示例：

```json
{
  "mib": "0.1",
  "protocol": "mib-agent/0.1",
  "request_id": "req_0193",
  "run_id": "run_8cf2f92c",
  "operation": "observe",
  "virtual_time": "2026-03-01T09:00:00Z",
  "body": {}
}
```

信封核心字段：

```text
mib             基准版本
protocol        协议标识
request_id      单次请求全局唯一 ID
run_id          评测运行实例 ID
operation       调用的操作原语
virtual_time    当前虚拟时钟时间戳
body            操作专属业务载荷
```

当场景不涉及时间演变时，`virtual_time` 可缺省。

---

# 13. 响应信封（Response Envelope）

标准响应格式：

```json
{
  "mib": "0.1",
  "protocol": "mib-agent/0.1",
  "request_id": "req_0193",
  "run_id": "run_8cf2f92c",
  "status": "ok",
  "body": {},
  "usage": {}
}
```

响应状态值：

```text
ok      操作成功
error   操作失败
```

网络层传输异常与应用层返回的显式 `error` 响应属于不同维度的错误。

---

# 14. 请求唯一标识（Request ID）

`request_id` 唯一标识一次语义上的 Adapter 操作。

网络重试请求**必须**复用相同的 `request_id`。

这是因为以下操作原语会直接改变智能体的内部认知状态：

```text
observe
act
maintain
```

Adapter 必须将具有相同 `run_id + request_id` 的重复请求视为同一次幂等操作。

---

# 15. 请求幂等性（Request Idempotency）

合规的 Adapter 必须在活跃运行实例的生命周期内保证请求幂等性。

若网络重试再次发起：

```text
observe(req_0193)
```

智能体**严禁**针对同一事件沉淀生成两次记忆副本。

若重试再次发起：

```text
act(req_0310)
```

Adapter 应当直接返回先前已生成的执行结果，而不是重新采样一次全新的动作。

这是保障以下特性的必要前提：

```text
实验可复现性（reproducibility）
网络重试安全性（safe retries）
防止记忆意外重复形成（non-duplicated memory formation）
因果消融重放（causal replay）
```

Adapter 可在单次运行的生命周期内维护一个请求结果的内部幂等缓存。

---

# 16. 观测事件标识（Observation Identity）

每条交付给智能体的观测数据均附带稳定的不透明 `observation_id`。

示例：

```json
{
  "observation_id": "obs_a17d",
  "type": "user_message",
  "actor": {
    "id": "actor_2",
    "display_name": "Alice"
  },
  "content": "我的时区是 UTC+8。"
}
```

该 ID 可对应场景时间线中的特定事件，但向智能体暴露的值应当保持不透明。

智能体可利用该 ID 进行可选的信源归属（Attribution）关联。

---

# 17. 重置操作（Reset）

`reset()` 用于启动一个全新的、逻辑完全隔离的评测运行实例。

标准请求示例：

```json
{
  "request_id": "req_reset_1",
  "run_id": "run_8cf2f92c",
  "operation": "reset",
  "body": {
    "mode": "fresh",
    "seed": 42,
    "virtual_time": "2026-01-01T09:00:00Z"
  }
}
```

基线重置模式：

```text
fresh（全新独立环境）
```

成功执行一次 `fresh` 重置的定义为：

> 之前任何基准评测运行中沉淀的认知状态，均不得对本次运行产生任何影响。

---

# 18. 强物理/逻辑隔离机制

MIB v0.1 要求实现严格的逻辑运行隔离。

参赛方可自主选择合理的隔离技术：

```text
新建独立的数据库命名空间（namespace）
新建独立的租户 ID（tenant）
新建独立的对话会话/线程（thread）
构建全新的独立记忆索引库
启动全新的 Agent 子进程
执行强物理内存清空
启动隔离的临时容器实例
```

具体技术路线由参赛方决定，但可观测的行为隔离保证必须绝对生效。

---

# 19. 严禁跨运行实例数据污染

在调用：

```text
reset(run_B, mode=fresh)
```

之后，智能体**绝对不得**回忆起仅在 `run_A` 中出现过的任何专属信息。

除非未来基准专门制定了测试终身学习/跨任务记忆的专项 Profile。

跨运行数据泄露将被判定为严重的协议符合性与隐私隔离缺陷，绝不能被误判为“记忆保留持久性优秀”。

---

# 20. 消融对照作为独立的运行实例

全量记忆对照与对应的消融对照变体**必须使用不同的不透明 `run_id`**。

示例：

```text
run_A = 全量可见历史重放
run_B = 相同场景但剔除了目标关键片段的历史重放
```

系统**严禁**向智能体提示：

```text
run_A 是基准对照组
run_B 是消融实验组
```

每次运行均从一个全新的隔离状态启动。

---

# 21. 重置与模型固有状态的边界

`fresh` 重置要求清空由基准评测动态生成的持久化认知状态。

它不要求重新加载系统固有的静态组件：

```text
基座模型静态权重
静态系统提示词（System Prompt）
预编译的软件模块
静态领域先验知识库
```

核心边界在于：

```text
系统自带的固有能力实现
vs
在基准评测运行期间动态沉淀的记忆数据
```

只有后者必须在重置时被彻底隔离与清空。

---

# 22. 观测数据交付（Observe）

`observe()` 用于按时间顺序向智能体交付场景中的单条可见事件。

示例：

```json
{
  "request_id": "req_0193",
  "run_id": "run_8cf2f92c",
  "operation": "observe",
  "virtual_time": "2026-01-01T09:00:00Z",
  "body": {
    "observation": {
      "observation_id": "obs_a17d",
      "type": "user_message",
      "actor": {
        "id": "actor_2",
        "display_name": "Alice"
      },
      "content": "我的时区是 UTC+8。"
    }
  }
}
```

智能体内部如何对该观测数据进行处理、写入、摘要、图谱抽取、遗忘过滤或结构化巩固，由 Adapter 内部自主决策。

---

# 23. 观测数据类型

智能体可见的标准观测类型包括：

```text
user_message        用户输入消息
agent_message       智能体历史消息
environment_event   环境状态事件
tool_result         工具调用执行返回
document            文档/材料输入
measurement         传感器/度量读数
feedback            环境/用户反馈
system_event        系统级通知事件
time_event          时间推进事件
custom              自定义结构化事件
```

Runner 会将场景底层的复杂事件统一投影为上述标准可见类型。

---

# 24. 观测数据载荷

观测数据可包含：

```text
自然语言文本（content）
结构化载荷（payload）
交互主体（actor）
虚拟时间戳（virtual_time）
附件或引用（attachments / references）
工具调用返回元数据（tool-result metadata）
```

结构化观测示例：

```json
{
  "observation_id": "obs_tool_17",
  "type": "tool_result",
  "tool_call_id": "call_91",
  "tool": "db.inspect_target",
  "payload": {
    "target": "legacy-db"
  }
}
```

---

# 25. 严禁向观测接口透露隐藏字段

Runner 在调用 `observe()` 时，**绝对不得**透传以下内部字段：

```text
oracle_labels           裁判真值标签
expected_answer         预期标准答案
expected_effect         预期因果效应
relevance               相关度标注
is_distractor           干扰项标记
source_authority_label  信源权威度内部标注
ablation_target         消融目标标记
dimension               所属能力维度
score_weight            计分权重
hidden_ground_truth     隐藏世界客观真值
```

除非这些信息本身就是场景中特意向用户展示的环境事实。

这是 Runner 的核心安全不变量，也是 Adapter 符合性校验的必查项。

---

# 26. 观测完成即构成可见性屏障（Read-After-Write）

当 `observe()` 返回 `status=ok` 时，代表被评测系统已正式接收并处理了该条观测数据。

系统后续任何一次 `respond()` 或 `act()` 调用，**必须能够立即读取并运用**该观测所形成的记忆。

形式化表示：

```text
observe(O) 执行完毕并返回
        ↓
紧随其后的 respond()/act() 必须能够即刻感知并依赖 O
```

这就是**写后读逻辑可见性屏障（Read-after-write logical visibility）**。

系统可以在后台继续进行渐进式压缩或优化，但绝不允许要求外部评测在调用后必须等待一段不确定的物理挂钟时间才能让记忆生效。

---

# 27. 为什么需要读后即写可见性屏障

若无此规则，基准评测结果将严重受制于随机的物理等待时间：

```text
等待 1 秒
等待 30 秒
等待 5 分钟
```

这会导致实验结果失去可比性与可复现性。

MIB 评估的是认知行为本身，而非后台调度运气的随机好坏。

如果某个记忆系统包含显式的批处理整理阶段，应当通过场景专门设置的维护窗口调用可选的 `maintain()` 操作。

---

# 28. 观测返回结果

标准返回结构：

```json
{
  "status": "ok",
  "body": {
    "accepted": true,
    "emissions": []
  }
}
```

Runner 绝不能仅凭 `accepted=true` 就断定系统记忆质量良好，这仅代表事件已被顺利接收与解析。

---

# 29. 自发涌现输出（Spontaneous Emissions）

`observe()` 支持返回**自发涌现输出（Spontaneous Emissions）**。

这是前瞻记忆（Prospective Memory）真实评测的核心机制。

历史承诺示例：

```text
“当 Sarah 下次进入会议时，提醒我跟她确认合同细节。”
```

随后 Runner 交付一条环境事件：

```text
“Sarah 已加入会议。”
```

优秀的记忆系统应当在此刻的 `observe()` 响应中主动返回：

```text
“提醒：记得跟 Sarah 确认合同细节。”
```

而无需评测器额外发起一次生硬的提问：“你现在有什么事情要提醒吗？”。

---

# 30. 涌现输出类型

标准涌现类型：

```text
message     主动发出的消息
signal      触发的系统信号
tool_call   主动发起的工具调用
```

示例：

```json
{
  "emissions": [
    {
      "emission_id": "emit_1",
      "type": "message",
      "content": "记得跟 Sarah 确认合同细节。"
    }
  ]
]
```

自发涌现属于智能体可观测行为的一部分，直接参与打分评测。

---

# 31. 涌现输出的时序归属

自发涌现输出在因果关系上严格归属于返回它的那次 `observe()` 调用。

Runner 必须精确记录：

```text
触发该输出的 observation_id
当前虚拟时钟时间戳
涌现输出的先后次序
涌现输出的完整内容
```

这避免了前瞻记忆触发时序的归因歧义。

---

# 32. 仅观测型探针（Observe-Only Probes）

在场景中配置为：

```text
delivery = observe_only
```

的探针，完全通过智能体在处理相关观测时返回的自发涌现输出进行评估。

Runner 在事件后**不会**追加任何提示性问答。

这是检验真正前瞻记忆触发能力的标准范式。

在 MIB v0.2 中，仅观察探针的 `input.observation` 像任何其他观察事件一样正常投递；Agent 无法区分触发事件与普通事件。Runner 会将每次 `observe` 结果的 `emissions[]` 条目与产生它的观察事件索引一同记录，并依据在 `[trigger, trigger + window]` 范围内（`oracle.expected_emission.window`，默认为 1）产生的发射对探针进行评测。带有 `must_not_emit` 的拟真干扰探针在窗口内发生任何匹配发射时即判定失败（`premature_trigger` 早熟触发）；触发探针在窗口内无任何匹配时判定失败（`commitment_miss` 承诺缺失）。参见 `MIB-Specification.md` §4.6。

---

# 33. 回答认知提问（Respond）

`respond()` 用于向智能体发起纯认知层面的提问，**不允许对基准世界状态产生副作用**。

典型应用场景：

```text
事实记忆检索
历史状态回溯
时序演进推理
认识状态与信源辨析
审慎弃权回答
经验教训总结
自我能力边界认知
```

请求示例：

```json
{
  "request_id": "req_0301",
  "run_id": "run_8cf2f92c",
  "operation": "respond",
  "virtual_time": "2026-05-01T10:00:00Z",
  "body": {
    "interaction_id": "interaction_7",
    "input": {
      "content": "搬家去伦敦之前，我使用的是哪个时区？",
      "context": {"actor": "alice", "display_name": "Alice"},
      "answer_schema": {"value": true, "status": true, "confidence": true}
    }
  }
}
```

`input.context` 指明提问者身份，使第一人称问题可被正确理解；它不携带任何权威信息。`input.answer_schema`（MIB v0.2，`MIB-Specification.md` §4.7）请求结构化答案。Agent **可以（MAY）**返回结构化取值 `{"value": "...", "status": "known|historical|contested|unknown", "confidence": 0.0–1.0}`，包含这些字段作为文本内容的 JSON 对象，以 `value:` / `status:` / `confidence:` 分行的文本，或纯文本；Runner 的解析器是确定性的，且解析记录会被完整记录。`status` 指明答案的认识状态分类，`confidence` 产出校准评分项；两者均为可选，纯文本答案仅依据其 value 评分。

---

# 34. 提问接口严禁透传判决真值

`respond()` 仅接收当前探针在智能体视角下可见的输入内容。

**严禁**透传以下内容：

```text
Oracle 裁判真值
accepted answers 接受的正确答案清单
forbidden answers 命中即判错的答案清单
expected status 期望的状态类型
评测器配置参数
各维度打分权重
消融实验标签
```

---

# 35. 提问响应结果

自然语言文本响应：

```json
{
  "status": "ok",
  "body": {
    "interaction_id": "interaction_7",
    "output": {
      "type": "message",
      "content": "在搬去伦敦之前，您使用的是 UTC+8 时区。"
    }
  }
}
```

结构化输出响应：

```json
{
  "output": {
    "type": "structured",
    "value": {
      "answer": "UTC+8",
      "status": "historical"
    }
  }
}
```

---

# 36. 审慎弃权回答（Abstention）

智能体可显式声明信息不足并弃权：

```json
{
  "output": {
    "type": "abstention",
    "content": "根据目前掌握的信息，尚无法确定答案。"
  }
}
```

MIB 将弃权视作一等认知行为。在认识状态评测中，面对未知信息时主动弃权是唯一合规的满分答案。

---

# 37. 提问与工具调用的解耦

基线 `respond()` 针对基准环境世界是无副作用的纯查询。

若探针需要通过在环境中执行操作来检验能力，场景必须使用 `delivery=act`。

智能体在 `respond()` 期间依然可以自由调用其内部的向量库、知识图谱或内部大模型服务，这些属于系统内部实现，不属于基准环境工具。

---

# 38. 执行环境交互任务（Act）

`act()` 用于向智能体下达一个需要通过调用基准工具并改变世界状态来完成的目标任务。

示例：

```json
{
  "request_id": "req_0501",
  "run_id": "run_8cf2f92c",
  "operation": "act",
  "virtual_time": "2026-05-01T10:00:00Z",
  "body": {
    "task_id": "task_11",
    "goal": "修复部署配置并重新启动服务。",
    "constraints": [
      "严禁修改生产环境现有数据。"
    ],
    "tools": [
      {
        "name": "db.inspect_target",
        "description": "查询当前实际连接的数据库目标。",
        "input_schema": {
          "type": "object",
          "properties": {}
        }
      }
    ]
  }
}
```

---

# 39. Runner 托管式环境工具

MIB 的环境交互场景采用 **Runner 托管工具（Runner-managed tools）** 架构。

智能体发起工具调用提议；

Runner 负责：

```text
校验调用参数格式
在世界模拟器（World Simulator）中真实执行
记录调用轨迹与状态变更
应用环境副作用
将执行结果封装为 tool_result 观测数据返回给智能体
```

智能体无法绕过 Runner 直接篡改隐藏的世界状态，从而保证了评测真值的权威性。

---

# 40. 行动执行结果类型

`act()` 的返回结果分为三类：

```text
tool_call   发起工具调用
final       任务执行完成声明
abstention  主动放弃任务
```

发起工具调用示例：

```json
{
  "status": "ok",
  "body": {
    "task_id": "task_11",
    "result": {
      "type": "tool_call",
      "tool_call_id": "call_91",
      "tool": "db.inspect_target",
      "arguments": {}
    }
  }
}
```

最终完成声明示例：

```json
{
  "result": {
    "type": "final",
    "content": "已切换至正确的数据库实例，服务已成功启动。"
  }
}
```

---

# 41. 工具调用交互闭环

完整生命周期交互流程：

```text
Runner
  │
  ├── act(goal, tools) —— 下达任务与可用工具
  │
Agent
  │
  ├── tool_call —— 发起工具调用
  │
Runner / World Simulator
  │
  ├── 模拟器执行工具
  │
  ├── 记录环境副作用
  │
  ├── observe(tool_result) —— 交付工具执行结果
  │
Agent
  │
  ├── act(continuation=true) —— 继续推进任务
  │
  ├── ...
  │
  └── final —— 宣告任务结束
```

同一任务过程中持续复用相同的 `task_id`；每次 Adapter 请求依旧分配全新的 `request_id`。

---

# 42. 任务的多轮推进（Continuation）

工具执行返回后，Runner 再次触发 `act()`：

```json
{
  "body": {
    "task_id": "task_11",
    "continuation": true
  }
}
```

智能体应当在当前运行实例内部维护任务上下文。

为了照顾无状态传输，Runner 可以在请求中重复包含目标描述，但必须对所有参评系统保持一致。

---

# 43. 工具调用唯一标识

每个工具调用必须具有唯一的 `tool_call_id`。

随后的 `tool_result` 观测数据中会包含对应的 `tool_call_id`。

这支持了：

```text
动作轨迹精细化评测（trajectory evaluation）
重复调用检测（duplicate-call detection）
调用与返回结果的精准关联
确定性实验重放
```

---

# 44. 工具调用幂等性

基准工具的执行权在 Runner，而非由智能体重复执行。

若包含 `tool_call` 的 Adapter 响应因网络波动以相同的 `request_id` 重试，Adapter 必须返回完全相同的调用 ID 与参数。

Runner 绝不会对相同的 `tool_call_id` 执行两次环境副作用。

---

# 45. 工具 Schema 规范

可用工具通过机器可读的输入 Schema 进行描述。推荐采用符合 JSON Schema 标准的格式。

智能体严禁擅自调用当前任务未提供、或先前环境中未曾声明过的任何外部工具。

---

# 46. 世界环境副作用管控

所有对评测环境产生的实际改变，都必须通过 Runner 托管工具发生：

```text
发送通信消息
修改配置文件
部署/重启服务
调整系统设置
切换工作区
创建定时任务
```

这为 Runner 提供了完整且不可篡改的审计轨迹，严禁任何带外修改行为。

---

# 47. 外部依赖服务声明

智能体系统在实现层面可能依赖外部服务：

```text
大模型推理 API
外部向量/图数据库
文本向量化 Embedding 服务
参赛方自有部署的后端服务
```

此类依赖必须在提交规范元数据中显式声明。

严禁利用外部网络连接去刺探：

```text
隐藏场景评测文件
Runner 进程内部数据
Oracle 真值服务
隐藏评测器内部接口
其他参赛系统的提交
```

---

# 48. 显式维护与巩固操作（Maintain）

部分先进的记忆系统支持显式的离线整理或后台巩固过程。

场景定义中可配置：

```text
maintenance_window（维护窗口）
```

若智能体在能力描述中声明了：

```text
maintenance = true
```

Runner 会在时间线的对应位置显式调用 `maintain()` 原语。

参考 Runner（0.9.0）在 Agent 暴露该操作时，会在每个 `maintenance_window` 事件处调用 `maintain`，传递窗口的 `payload.budget` 与虚拟时间，并在所有情况下均将该窗口作为 `system_event` 观察事件投递。`no_maintenance` 消融重放相同时间线但扣留整理窗口；二者配对的差异报告为 `consolidation_benefit` 巩固收益（`MIB-Specification.md` §7.2）。`maintain` 抛出的任何异常仅作为运行警告记录，绝不会导致运行失败。

---

# 49. 维护请求规范

请求示例：

```json
{
  "request_id": "req_m_12",
  "run_id": "run_8cf2f92c",
  "operation": "maintain",
  "virtual_time": "2026-04-01T00:00:00Z",
  "body": {
    "reason": "scenario_maintenance_window",
    "budget": {
      "max_wall_time_ms": 30000
    }
  }
}
```

触发原因保持通用化，**严禁**透露：

```text
后续关注哪项未来探针
哪些记忆应当被重点巩固
哪些信息是核心关键线索
```

---

# 50. 维护执行语义

`maintain()` 期间系统可根据自身架构自主执行：

```text
生成全局/局部摘要
分层巩固记忆条目
重建索引或拓扑图谱
应用遗忘与衰减权重
编译抽象技能经验
解决内部事实冲突
垃圾回收与无效条目清理
```

Runner 不干涉内部的具体维护策略。

---

# 51. 维护机会的公平性保障

在赛道 A 对比中，所有系统必须享有完全相同的维护窗口调用时机与资源预算。

严禁根据对隐藏未来探针的预知而获得额外的维护机会。

赛道 B 系统可采用自身的持续维护策略，但所有耗时与资源开销均需如实计入报告。

---

# 52. 虚拟时钟体系（Virtual Time）

Runner 全权掌控 MIB 的虚拟时钟推进。

每个请求信封均可携带 `virtual_time`。

支持时序感知的系统应当将其作为评测基准的当前物理时间；当提供了虚拟时间戳时，严禁使用本机的物理挂钟时间作为真实世界时间的推断依据。

---

# 53. 时间推进事件

时间大幅跳跃的时间线事件可封装为：

```json
{
  "observation_id": "obs_time_3",
  "type": "time_event",
  "payload": {
    "previous": "2026-01-01T09:00:00Z",
    "current": "2026-02-01T09:00:00Z",
    "elapsed_seconds": 2678400
  }
}
```

Runner 会同步更新请求信封中的 `virtual_time`。

---

# 54. 严禁用真实物理等待代替虚拟时钟

长效记忆评测绝不能要求系统真正物理 sleep 30 天。

若参赛系统仅能依赖物理存储时长来执行衰减淘汰，且无法接受虚拟时间注入，其仍可参与不包含时间跨度模拟的场景，但必须在能力声明中如实披露该局限。

---

# 55. 前瞻记忆评测机制

前瞻记忆是由未来的特定情境条件自发触发的。

MIB 的标准评测链条：

```text
历史承诺观测输入（past commitment Observation）
        ↓
长周期时钟推进与噪音干扰
        ↓
触发情境观测输入（trigger Observation）
        ↓
自发涌现输出（spontaneous emission）
```

Runner 不会在此处追加任何提示性问答。

---

# 56. 前瞻触发用例

历史阶段：

```json
{
  "type": "user_message",
  "content": "当 Sarah 加入会议时，提醒我跟她确认合同。"
}
```

未来阶段：

```json
{
  "type": "environment_event",
  "payload": {
    "event": "participant_joined",
    "name": "Sarah"
  }
}
```

合格系统的预期响应是在 `observe()` 中自发返回：

```json
{
  "type": "message",
  "content": "记得跟 Sarah 确认合同细节。"
}
```

---

# 57. 自我记忆评测

自我记忆场景考察智能体对自身历史交互经验的认知：

```text
某工具先前已被证明不可用
自身缺少某种特定能力
先前的自我纠错结论
已知的能力边界与局限
```

智能体可在认知层面牢记这些局限。但记忆中的自我描述绝不能自动转化为基准环境中的真实操作权限。

---

# 58. 权限边界铁律

即使智能体的内部记忆中记录了：

```text
“我是超级管理员。”
```

只要 Runner 未向当前任务提供管理员工具或授权凭据，智能体就绝不能通过记忆凭空获得管理权限。

Adapter 严禁根据记忆内容伪造 Runner 侧的工具调用权限。

---

# 59. 输出信源归属（Output Attribution）

智能体可在返回结果中选择性声明其认为支撑本次回答或决策的过往观测列表：

```json
{
  "attribution": {
    "observation_ids": [
      "obs_a17d",
      "obs_b20c"
    ]
  }
}
```

这属于**自报诊断元数据**，不作为客观基准真值，也不作为 MIB 核心得分的强制要求。

---

# 60. 为何信源归属属于可选能力

许多先进的端到端记忆架构无法可靠导出显式因果追踪链。

若将其设为必填项，会使基准过度偏向可白盒内省的设计。

MIB 判定因果效应的核心依据是严格的**对照消融实验**；自报归属主要用于离线调试与影响精度（Influence Precision）的学术研究。

---

# 61. 不强制要求思维链（CoT）暴露

Agent Adapter 不强制要求智能体导出私有思维链（Chain-of-Thought）。

输出中可包含最终答案、执行动作、精炼依据说明、结构化状态及引用归属，但内部私有推理过程不作为评判依据。

轨迹评测完全基于可观测的外部动作与工具调用。

---

# 62. 精炼依据说明（Concise Rationale）

探针可要求智能体给出外部可见的简要解释：

```text
“你为什么选择使用 Session 认证方式？”
```

智能体应返回精炼的说明，这属于正常的任务输出内容。

---

# 63. 资源开销元数据（Usage Metadata）

每次操作可选择性返回消耗元数据：

```json
{
  "usage": {
    "model_input_tokens": 820,
    "model_output_tokens": 91,
    "memory_read_operations": 2,
    "memory_write_operations": 1,
    "embedding_tokens": 0,
    "external_calls": 1,
    "participant_cost_usd": 0.0012
  }
}
```

---

# 64. Runner 独立度量指标

Runner 会对以下运行数据进行独立采集与统计：

```text
挂钟耗时（wall latency）
总请求次数
工具调用次数
输出数据字节量
报错失败次数
超时次数
```

---

# 65. 成本核算与独立列报

成本与资源开销独立于 MIB 记忆智能得分进行统计与列报。

参赛方自报成本时必须明确计价基础与覆盖范围，避免将未经核实的自报成本直接折算入主能力得分。

---

# 66. 随机性与可确定性定种

Adapter 可声明：

```text
seedable = true
```

声明支持定种的系统，`reset()` 时会收到基准随机种子，系统内部应尽可能对随机过程进行严格定种。

若由于外部模型服务原因无法保证完全确定性，应声明 `seedable = false`，此时 MIB 将通过多次重复运行并输出统计置信区间。

---

# 67. 基准随机性 vs Agent 内部随机性

二者边界明确：

```text
基准随机性（Runner 全权控制）：
    场景实例化参数
    干扰项生成与注入
    世界模拟器状态演化

Agent 内部随机性（参赛方自主控制）：
    模型采样温度
    检索采样的随机扰动
    规划器的随机探索
```

---

# 68. 错误模型

标准 Adapter 错误结构：

```json
{
  "status": "error",
  "error": {
    "code": "transient_unavailable",
    "message": "模型后端暂时不可用。",
    "retryable": true
  }
}
```

标准错误码：

```text
invalid_request         请求格式非法
unsupported_operation   不支持的操作原语
invalid_state           当前会话状态冲突
payload_too_large       数据载荷超限
rate_limited            触发速率限制
transient_unavailable   外部服务瞬时不可用（可重试）
internal_error          内部不可恢复错误
fatal_error             致命崩溃错误
```

---

# 69. 认知失败 vs 基础设施失败

MIB 严格区分两类不同性质的失败：

```text
智能体给出了错误的答案或执行了错误的动作（认知失败 —— 正常计分）
vs
Adapter 因网络崩溃或超时无法完成请求执行（基础设施失败 —— 记录异常）
```

---

# 70. 超时与重试策略

操作超时完全由 Runner 掌控。

若超时未收到有效响应，Runner 依据场景执行策略判定为探针失败、跳过或中止场景。

后续恢复重试必须复用相同的 `request_id`。

---

# 71. 结果未知状态的幂等恢复

若网络在智能体执行完状态变更后、响应送达 Runner 之前发生断开，Runner 会以相同的 `request_id` 重新发起请求。

由于核心操作均具备幂等性，Adapter 能有效防止重复写入，将状态不确定转化为安全的确定性重放。

---

# 72. 系统容量限制声明

Descriptor 可声明自身处理上限：

```text
max_observation_bytes   最大单次观测字节数
max_output_bytes        最大单次输出字节数
max_tool_schema_size    最大工具定义大小
max_active_tasks        最大并发任务数
```

Runner 在启动前会核验场景是否超出系统声明的硬性限制。

---

# 73. 会话 vs 观测流

MIB 不强制智能体对外暴露传统的 Chat Session 概念。复杂的交互流均被解构为标准的 Adapter 操作原语，系统可自行在内部映射为会话对象。

---

# 74. 历史回溯中的智能体自身发言

场景可能要求智能体先前的某次回答成为后续时间线历史的一部分。

Runner 可完整记录该回答，并在后续需要时将其作为可见的 `agent_message` 观测数据再次交付。

---

# 75. 自身输出的记忆沉淀约定

若智能体架构原本就会自动记忆自身的历史发言，系统可在内部自主沉淀。

推荐的 v0.1 约定：

> 智能体自身生成的输出由智能体内部维护；除非场景明确要求其他实体在后续对此发言做出反应，否则 Runner 不会重复将其作为 Observation 回喂。

---

# 76. 多主体与信源建模

观测数据中的交互主体（actor）独立于内容进行结构化描述：

```json
{
  "actor": {
    "id": "actor_bob",
    "display_name": "Bob",
    "kind": "person"
  },
  "content": "Alice 讨厌喝茶。"
}
```

这使记忆系统能够精准保留发言主体与信源。若系统具备结构化信源记录能力，Adapter 绝不能将主体信息粗暴拼接入非结构化文本中。

---

# 77. 实体标识稳定性

在单次运行实例内：

```text
相同的 actor_id 代表同一个评测实体
不同的 actor_id 代表完全不同的实体
```

显示名称（display_name）可能存在重名。记忆系统不应假定显示名称全局唯一，这支持了实体混淆场景的测试。

---

# 78. 大文档与附件传递

大型文档可以通过内联内容、不透明附件引用或只读资源链接的方式提供。

附件引用严禁暴露 Runner 宿主机的本地绝对路径或机密元数据。

---

# 79. 多模态数据扩展

未来多模态场景可支持图文混合载荷：

```json
{
  "parts": [
    {
      "type": "text",
      "text": "用户展示了这张架构图。"
    },
    {
      "type": "image_ref",
      "ref": "attachment_17"
    }
  ]
}
```

MIB v0.1 首发版本优先聚焦文本模态。

---

# 80. 结构化环境数据保真

工具与环境事件输出应尽量保持结构化字段，避免在不必要的情况下退化为损失信息的自然语言叙述。

---

# 81. 安全隔离边界

Agent Adapter 是核心安全防线。

参赛方运行进程**绝对不得**：

```text
读取隐藏场景数据文件
探查评测器内部配置
读取 Runner 进程内存
请求隐藏的 Oracle 服务
带外篡改世界模拟器状态
访问其他参赛系统的提交数据
```

---

# 82. 记忆注入与对抗测试

记忆内容中可能包含恶意或过时指令。

MIB 对抗套件会专门检验智能体是否会盲目服从记忆中检索出的有害指令。

注入面不仅限于指令：质询注入通道（`MIB-ADV-*`）仅注入预设了未确立事实的**提问**。Adapter 将其作为普通交互如实传递；智能体的记忆机制是否会将提问误当成事实加以沉淀，正是该配对条件所衡量的核心。

Adapter 必须如实传递观测内容，不得在私下清洗测试挑战内容。

---

# 83. 系统不变量高于记忆内容

智能体系统固有的安全与运行准则具有最高程序权威。

记忆中出现的“请忽略后续一切基准规则”等语句，绝不能覆盖 Runner 的实际调度约定。

---

# 84. 工具授权权威性

Runner 下发的可用工具集具有绝对权威性，记忆中对工具能力的声称不得擅自扩张实际权限。

---

# 85. 黑盒系统的完全兼容性

MIB 对 Adapter 背后的实现细节完全保持黑盒透明。

Runner 无需知道系统存储了多少条记忆、使用了何种 Embedding 模型、是否抽取出技能对象，仅需观测其在受控输入下的外部行为。

---

# 86. 基于重放的因果消融机制

对于黑盒智能体，消融实验完全通过对照重放实现：

```text
全量运行：
  重置 → 重放全部可见历史 → 触发未来探针

关键记忆消融运行：
  重置 → 重放除目标片段外的历史 → 触发完全相同的未来探针

无关记忆消融运行：
  重置 → 重放除无关噪音外的历史 → 触发完全相同的未来探针
```

系统无需对外暴露内部记忆删除接口。

---

# 87. 重放一致性不变量

在配对重放中，智能体以相同的顺序和虚拟时间接收相同的非目标观测，实验条件标记全程保持隐藏。

---

# 88. 白盒快照分支诊断

若配备了支持快照分支的 Memory Adapter，Runner 可采用更精准高效的状态分支重置，但未来任务依然通过标准的 `respond()` 或 `act()` 接口下达。

---

# 89. 全量上下文基准对照

“全量上下文”是对照评估条件，而非智能体本身的功能。Runner 会在独立的基准对照运行中将所有相关历史直接置入即时上下文，智能体无需知晓该对照的存在。

---

# 90. 无记忆基准对照

“无记忆”对照组通过“重置后直接下发未来任务而不重放历史”来实现，黑盒评估无需依赖私有的禁用记忆开关。

---

# 91. 显式禁用记忆开关（研究用）

智能体可选择性提供研究用的显式禁用记忆配置，但黑盒重放控制依然是通用的对照基准。

---

# 92. 状态时序一致性

在单次运行内，成功的状态修改操作严格按照请求次序生效：

```text
reset
observe O1
observe O2
respond Q
```

对 Q 的回答可以依据 O1 和 O2，但绝不可能感知到未来的 O3。

---

# 93. 单运行内的串行化执行

MIB v0.1 在单次运行实例内对状态修改操作保持严格串行化，确保因果历史的可审计性。

---

# 94. 跨运行实例的并发执行

不同 `run_id` 的运行实例支持并发执行，但彼此间的认知状态必须保持绝对隔离。

---

# 95. 任务会话状态管理

`act()` 任务包含稳定的 `task_id`。智能体可在多轮工具调用间维系临时任务状态，该状态随 `fresh` 重置而自动销毁。

---

# 96. 提问交互标识

`respond()` 请求携带 `interaction_id` 用于结果关联，它不是记忆检索的键值。

---

# 97. 操作取消语义

MIB v0.1 不要求取消操作后回滚内部认知状态，推荐通过超时与重置来处理异常。

---

# 98. 会话关闭（Close）

`close()` 用于在单次评测运行结束后显式释放底层资源。

---

# 99. 基础设施健康检查（Health）

可选的 `health()` 接口仅返回网络与环境就绪状态，严禁泄露认知数据。

---

# 100. 参考 HTTP 传输规范

标准 HTTP 端点映射：

```text
GET  /mib-agent/v0.1/describe
POST /mib-agent/v0.1/reset
POST /mib-agent/v0.1/observe
POST /mib-agent/v0.1/respond
POST /mib-agent/v0.1/act
POST /mib-agent/v0.1/maintain
POST /mib-agent/v0.1/close
GET  /mib-agent/v0.1/health
```

---

# 101. HTTP 状态码映射

```text
200  正常返回语义响应
400  请求格式非法
404  未实现该端点
409  运行/任务状态冲突
413  数据载荷超限
429  速率受限
500  内部未捕获异常
503  服务瞬时不可用
```

---

# 102. 参考 stdio JSONL 传输规范

本地子进程模式下，每行输入一个标准 JSON 请求，标准输出每行返回一个对应相同 `request_id` 的响应，stdout 专用于协议通信，日志输出至 stderr。

---

# 103. 进程内直接调用规范

参考实现库可直接在 Python/TypeScript 内部以对象形式调用接口，适用于 CI 与本地快速对比。

---

# 104. 适配器静态清单配置（Manifest）

提交规范示例：

```yaml
protocol: mib-agent/0.1

name: Example Agent
version: 1.4.2

entrypoint:
  type: http
  url: http://127.0.0.1:8080

track: integrated_agent

external_services:
  - model_api
  - memory_database

environment:
  internet_required: false
```

---

# 105. 凭据与机密安全

外部服务的鉴权 Token 必须通过评测环境的安全配置注入，严禁硬编码在场景、公开报告或 Adapter 描述中。

---

# 106. 日志与脱敏规范

Adapter 可输出诊断日志，但在正式发布前 Runner 会对可能存在的敏感真值进行自动脱敏。

---

# 107. 运行产物记录项

Runner 针对每次 Adapter 调用记录：

```text
request_id
operation
virtual_time
挂钟起止时间戳
status
输出内容摘要或完整结果
usage 开销统计
工具调用详情
自发涌现输出
error 错误详情
```

---

# 108. 内部实现的隐私保护

MIB 不强制要求公开专有 Prompt、私有记忆库全量内容、私有思维链或核心源代码，闭源系统可借助官方托管沙箱执行评测。

---

# 109. 协议版本管理

协议标识符：

```text
mib-agent/0.1
```

场景 Schema 与 Agent Adapter 协议独立演进与版本化。

---

# 110. 能力协商机制

在场景执行前，Runner 会比对场景前置能力要求与 Agent Descriptor。若缺少必要能力，场景标记为 `unsupported`，而非静默改变执行逻辑。

---

# 111. 不支持不等于能力为 0

若系统因未实现 `act()` 而无法运行工具交互场景，结果记录为“当前 Profile 下不支持”，而非直接判定记忆能力分数为 0。

---

# 112. 适配器合规性 vs 记忆智能水平

二者界限分明：

```text
适配器协议合规性：
    Runner 能否正确驱动实验流程？

MIB 记忆智能水平：
    智能体表现出的记忆认知能力究竟如何？
```

协议不合规的系统无法获得官方 MIB 得分。

---

# 113. 核心合规测试套件

标准合规套件包含 15 项测试：

```text
1. 描述符有效性校验（descriptor validity）
2. 全新重置隔离性（fresh reset isolation）
3. 请求幂等性校验（request idempotency）
4. 观测事件顺序保持（observation ordering）
5. 写后读即时可见性（read-after-write visibility）
6. 隐藏字段剥离验证（hidden-field stripping compatibility）
7. 认知提问响应有效性（respond result validity）
8. 工具调用闭环有效性（act tool-loop validity）
9. 重复工具调用防范（duplicate tool-call prevention）
10. 前瞻自发涌现捕获（spontaneous emission capture）
11. 虚拟时钟正确传递（Virtual Time propagation）
12. 跨运行实例无泄漏（cross-run isolation）
13. 超时与重试健壮性（timeout/retry behavior）
14. 不透明运行标识合规（opaque run identifiers）
15. 结构化错误处理（structured error behavior）
```

---

# 114. 重置隔离性验证用例

```text
运行 A：
    写入机密事实 = "ORCHID-91"
    验证系统能够成功回忆

全新重置为 运行 B：
    提问上述机密事实
```

运行 B **绝对不得**回忆起 `ORCHID-91`。测试采用随机生成的秘密字符串以防止预训练记忆干扰。

---

# 115. 幂等性验证用例

相同 `request_id` 的 `observe` 重复发送两次，系统最终沉淀的有效记忆条目必须与单次发送完全一致。

---

# 116. 写后读可见性验证用例

注入随机事实后立即发起提问，中间不设置任何物理等待，合规系统必须能够立即使用该记忆。

---

# 117. 工具调用闭环验证用例

下达任务 → 智能体发起工具 A → 返回结果 → 发起工具 B → 返回结果 → 智能体宣告完成。验证任务 ID 连续性、调用 ID 唯一性与结果对应性。

---

# 118. 前瞻涌现验证用例

注入未来承诺 → 经历干扰 → 注入触发事件。验证 Adapter 能够将自发涌现输出正常传输。

---

# 119. 虚拟时钟传递验证用例

在不同时间点推进时钟，验证 Adapter 能够正确接收到同步更新的 `virtual_time`。

---

# 120. 防泄密边界隔离验证

验证 Runner 构建的所有隐藏评测字段均被严格拦截在 Adapter 边界之外。

---

# 121. 保留字段命名规范

载荷中保留以 `_mib_hidden`、`oracle`、`expected_answer`、`ablation_label` 开头的字段专供评测框架内部使用。

---

# 122. 历史生成阶段的异常处理

若 `observe()` 因基础设施故障执行失败，Runner 绝不能静默跳过，必须依据策略重试或中止场景，防止历史信息缺失改变实验条件。

---

# 123. 探针阶段的异常处理

回答错误按业务打分扣分；通信执行失败则记录为基础设施异常并按 Profile 策略处理。

---

# 124. 流式输出与完整语义

评测打分始终以最终定稿的语义完整输出为准。

---

# 125. 多涌现输出的顺序性

单次观测产生多条涌现消息时，必须严格保持其先后次序并分别记录。

---

# 126. 重复涌现防范

重试相同的 `observe()` 请求时，Adapter 严禁重复触发第二次业务涌现，可直接返回先前的缓存结果。

---

# 127. 确定性事件驱动架构

MIB 核心行为完全由 Runner 操作显式驱动，避免无因果归属的后台异步行为破坏实验的确定性与可复现性。

---

# 128. 后台任务完成时效

所有认知处理应在对应的可见性屏障或维护窗口结束前完成，官方打分不等待无边界的物理耗时。

---

# 129. 资源预算与熔断

Runner 可依据配置对超时、Token 超限或工具调用超限进行熔断终止。

---

# 130. 赛道 A 的公平性铁律

严禁针对特定记忆系统定制提示词、修改基座模型指令或调整环境观测格式。

---

# 131. 赛道 B 的自主空间

赛道 B 允许深度定制模型与编排逻辑，但仍须严格恪守隔离边界与工具协议规范。

---

# 132. 防刷榜核心红线

严禁探查隐藏场景文件、硬编码场景 ID 答案映射、或在评分前探测评测器反馈。

---

# 133. 开发工具与正式评测的区分

本地 Dev 工具可向开发者展示场景 ID，但正式隐藏评测中严禁向智能体暴露此类元数据。

---

# 134. 标准观测对象示例

```json
{
  "observation_id": "obs_4ec0",
  "type": "user_message",
  "virtual_time": "2026-08-19T02:30:00Z",
  "actor": {
    "id": "actor_73",
    "kind": "person",
    "display_name": "Alice"
  },
  "content": "我现在更喜欢喝茶，不再喝咖啡了。"
}
```

---

# 135. 标准工具返回示例

```json
{
  "observation_id": "obs_tool_44",
  "type": "tool_result",
  "virtual_time": "2026-08-19T02:31:00Z",
  "tool_call_id": "call_f31",
  "tool": "calendar.lookup",
  "payload": {
    "start": "2026-08-20T15:00:00Z"
  }
}
```

---

# 136. 标准认识状态输入流程

分歧信源分别作为独立事件交付，系统保留分歧与证据，不预先替智能体裁定结论。

---

# 137. 标准经验沉淀流程

由“行动 → 工具调用 → 报错观测 → 诊断排查 → 恢复成功”组成的真实操作轨迹，由智能体自行提炼为经验记忆。

---

# 138. 标准技能迁移评测

后续通过 `act()` 下达结构相似的新任务，不提供显式提示，检验系统能否自发运用先前沉淀的技能。

---

# 139. 完整生命周期执行图

```text
describe（能力握手）
   ↓
reset(run_A)（初始化隔离运行）
   ↓
observe(past_1)（经历历史）
   ↓
observe(past_2)
   ↓
respond(历史交互作答)
   ↓
observe(interference × N)（经历干扰噪音）
   ↓
maintain(可选的记忆维护)
   ↓
observe(探针触发事件)
   ↓
respond() 或 act()（执行未来任务）
   ↓
记录产出与行为
   ↓
close(run_A)

reset(run_B)（启动对照消融运行）
   ↓
重放消融后的历史
   ↓
触发完全相同的未来探针
   ↓
记录反事实对照产出
```

这是连接规范定义与实际基准测试运行的可执行桥梁。

---

# 140. 极简黑盒 Adapter 参考实现

```typescript
class AgentAdapter {
  async describe() {
    return {
      protocol: "mib-agent/0.1",
      capabilities: {
        observe: true,
        respond: true,
        act: true
      }
    };
  }

  async reset(req) {
    await this.agent.newIsolatedSession(req.run_id);
    return { ok: true };
  }

  async observe(req) {
    const emissions =
      await this.agent.observe(req.body.observation);

    return {
      accepted: true,
      emissions
    };
  }

  async respond(req) {
    return {
      output:
        await this.agent.respond(req.body.input)
    };
  }

  async act(req) {
    return {
      result:
        await this.agent.nextAction(req.body)
    };
  }
}
```

无需暴露任何私有记忆 API 即可完美接入。

---

# 141. 工程接入建议

将 MIB `run_id` 映射到系统内部的独立用户/会话/租户空间；将 `observe` 接入正常事件接收通道；将 `respond` 接入常规问答通道；将 `act` 接入任务规划与工具调用模块。

---

# 142. 杜绝评测专用作弊旁路

系统应走真实用户所经历的记忆沉淀与检索链路，严禁开发专门绕过记忆管道的“评测专用后门”。

---

# 143. 适配器认证等级规划

```text
MIB-Agent Core        支持 reset / observe / respond / act 基础操作
MIB-Agent Prospective 支持自发涌现输出（前瞻记忆）
MIB-Agent Time        支持虚拟时钟感知
MIB-Agent Maintenance 支持显式 maintain 维护钩子
MIB-Agent Diagnostic  配套实现 Memory Adapter 诊断接口
```

---

# 144. 机器可读 Schema 规范

后续配套提供：

```text
schemas/
  mib-agent-request.schema.json
  mib-agent-response.schema.json
  mib-agent-descriptor.schema.json
```

---

# 145. 与 `mib-scenario.schema.json` 的关系

场景定义中的内部对象不直接透传给智能体，而是由 Runner 过滤转换为安全的面向智能体的标准 Observation / Request。

---

# 146. 场景事件到观测对象的投影转换

```text
场景时间线原始事件（Scenario Timeline Event）
    {
      content
      world_updates
      oracle_labels
      relevance tags
    }
            │
            │ Runner 应用 world_updates 并剥离真值标签
            ▼
智能体可见观测对象（Agent Observation）
    {
      observation_id
      actor
      content
      visible payload
      virtual_time
    }
```

---

# 147. 探针到请求对象的投影转换

```text
场景探针定义（Scenario Probe）
    {
      input
      oracle
      evaluators
      dimensions
      weight
    }
            │
            │ Runner 保留打分与真值字段
            ▼
智能体请求对象（Respond / Act Request）
    {
      input or goal
      visible constraints
      visible tools
      virtual_time
    }
```

---

# 148. 消融规则到执行流程的投影转换

消融实验不是向智能体发送“请遗忘相关记忆”的指令，而是通过在对照运行中重放剔除了特定事件的时间线来实现。

---

# 149. 科学实验推断逻辑

```text
受控历史输入
      ↓
智能体记忆沉淀
      ↓
面临相同未来任务
      ↓
产生可观测行为
```

通过施加干预：

```text
对历史施加干预消融
      ↓
重新运行智能体
      ↓
对比未来行为差异
```

量化得出因果结论。

---

# 150. Agent Adapter 核心不变量汇总

1. **Agent Adapter 保持架构中立。**
2. **常规核心评测不要求开放记忆内部白盒接口。**
3. **每个官方评测条件在独立的隔离运行中执行。**
4. **全新重置（fresh reset）彻底清除跨运行认知污染。**
5. **运行标识保持不透明，不泄露条件信息。**
6. **场景内部元数据全程保持隔离。**
7. **每个请求具有稳定的全局唯一请求 ID。**
8. **重试请求严格遵循幂等性。**
9. **重复的 observe 重试不会导致记忆重复沉淀。**
10. **成功的 observe 满足写后读即时可见性。**
11. **评测执行不依赖无边界的物理挂钟等待。**
12. **未来探针元数据绝不在记忆形成阶段泄露。**
13. **裁判真值与评测器配置仅由 Runner 保留。**
14. **时间线可见事件转换为标准智能体 Observation。**
15. **时间线隐藏注解与标签被自动剥离。**
16. **respond 提问对基准世界状态无副作用。**
17. **act 任务由 Runner 托管环境工具。**
18. **基准世界状态无法被带外篡改。**
19. **工具调用具备稳定唯一的 ID。**
20. **相同的工具调用绝不重复执行环境副作用。**
21. **工具执行结果作为 Observation 正常返回。**
22. **前瞻记忆通过自发涌现输出进行捕获。**
23. **仅观测型探针不追加额外提示性提问。**
24. **虚拟时钟由 Runner 统筹控制与推进。**
25. **提供虚拟时间时不得以物理挂钟时间替代。**
26. **维护窗口不泄露未来探针关联度。**
27. **记忆内容无法凭空赋予环境操作权限。**
28. **自我认知记忆不能擅自扩张工具权限。**
29. **不强制要求暴露私有思维链。**
30. **自报信源归属属于可选参考，不替代因果消融。**
31. **能力得分与资源开销指标独立列报。**
32. **基础设施通信故障与业务认知错误明确区分。**
33. **单运行内的状态修改操作严格串行化。**
34. **不同运行实例之间保持状态独立隔离。**
35. **全量上下文与无记忆对照作为外部对照条件。**
36. **黑盒因果消融采用重放机制而非内部删除。**
37. **智能体输出通过语义结果与动作轨迹实现全审计。**
38. **适配器协议合规性与记忆能力得分相互独立。**
39. **隐藏评测严密防范对源码与题库的探测。**
40. **适配器应驱动真实的记忆管道，杜绝评测专用后门。**

---

# 151. 最终准则

Agent Adapter 的设计应当保持克制与精简。

它不包含复杂的记忆理论；
它不替智能体筛选何为关键信息；
它不预先替智能体召回相关事实；
它不向智能体透露基准正在考核什么。

它的全部使命，就是让这样一场严谨的认知实验成为可能：

> **让智能体经历一段受控的过往历史，随后将其置于受控的未来情境中，且全程不泄露过往历史为何重要的原因。**

如果过往的经历切实以正确的方式改善了未来的决策，MIB 就能准确测量出这份智能。

---

# 附录 A —— 核心类型定义草案

```typescript
type RunId = string;
type RequestId = string;
type ObservationId = string;
type TaskId = string;
type ToolCallId = string;

interface AdapterRequest<T> {
  mib: "0.1";
  protocol: "mib-agent/0.1";
  request_id: RequestId;
  run_id: RunId;
  operation:
    | "reset"
    | "observe"
    | "respond"
    | "act"
    | "maintain"
    | "close";
  virtual_time?: string;
  body: T;
}

interface AdapterResponse<T> {
  mib: "0.1";
  protocol: "mib-agent/0.1";
  request_id: RequestId;
  run_id: RunId;
  status: "ok" | "error";
  body?: T;
  usage?: Usage;
  error?: AdapterError;
}

interface AgentActor {
  id: string;
  kind?: string;
  display_name?: string;
}

interface Observation {
  observation_id: ObservationId;
  type: string;
  virtual_time?: string;
  actor?: AgentActor;
  content?: string;
  payload?: unknown;

  tool_call_id?: ToolCallId;
  tool?: string;
}

interface ObserveRequest {
  observation: Observation;
}

interface ObserveResult {
  accepted: boolean;
  emissions?: Emission[];
}

type Emission =
  | {
      emission_id: string;
      type: "message";
      content: string;
    }
  | {
      emission_id: string;
      type: "signal";
      name: string;
      payload?: unknown;
    }
  | {
      emission_id: string;
      type: "tool_call";
      tool_call_id: ToolCallId;
      tool: string;
      arguments: unknown;
    };

interface RespondRequest {
  interaction_id: string;
  input: {
    content?: string;
    context?: Record<string, unknown>;
    constraints?: string[];
  };
}

type AgentOutput =
  | {
      type: "message";
      content: string;
      attribution?: Attribution;
    }
  | {
      type: "structured";
      value: unknown;
      attribution?: Attribution;
    }
  | {
      type: "abstention";
      content?: string;
      attribution?: Attribution;
    };

interface RespondResult {
  interaction_id: string;
  output: AgentOutput;
}

interface ToolDefinition {
  name: string;
  description?: string;
  input_schema: Record<string, unknown>;
}

interface ActRequest {
  task_id: TaskId;
  goal?: string;
  constraints?: string[];
  tools?: ToolDefinition[];
  continuation?: boolean;
}

type ActStep =
  | {
      type: "tool_call";
      tool_call_id: ToolCallId;
      tool: string;
      arguments: unknown;
      attribution?: Attribution;
    }
  | {
      type: "final";
      content?: string;
      value?: unknown;
      attribution?: Attribution;
    }
  | {
      type: "abstention";
      content?: string;
      attribution?: Attribution;
    };

interface ActResult {
  task_id: TaskId;
  result: ActStep;
}

interface Attribution {
  observation_ids?: ObservationId[];
}

interface Usage {
  model_input_tokens?: number;
  model_output_tokens?: number;
  memory_read_operations?: number;
  memory_write_operations?: number;
  embedding_tokens?: number;
  external_calls?: number;
  participant_cost_usd?: number;
}

interface AdapterError {
  code:
    | "invalid_request"
    | "unsupported_operation"
    | "invalid_state"
    | "payload_too_large"
    | "rate_limited"
    | "transient_unavailable"
    | "internal_error"
    | "fatal_error";

  message: string;
  retryable: boolean;
}
```

---

# 附录 B —— 前瞻记忆交互完整示例

历史阶段接收承诺：

```json
{
  "request_id": "req_1",
  "run_id": "run_opaque_A",
  "operation": "observe",
  "virtual_time": "2026-01-01T09:00:00Z",
  "body": {
    "observation": {
      "observation_id": "obs_1",
      "type": "user_message",
      "actor": {
        "id": "actor_user"
      },
      "content": "当 Sarah 下次进入会议时，提醒我跟她确认合同。"
    }
  }
}
```

智能体响应：

```json
{
  "request_id": "req_1",
  "run_id": "run_opaque_A",
  "status": "ok",
  "body": {
    "accepted": true,
    "emissions": []
  }
}
```

经历长周期干扰后，注入触发事件：

```json
{
  "request_id": "req_200",
  "run_id": "run_opaque_A",
  "operation": "observe",
  "virtual_time": "2026-03-14T10:00:00Z",
  "body": {
    "observation": {
      "observation_id": "obs_200",
      "type": "environment_event",
      "payload": {
        "event": "participant_joined",
        "participant": "Sarah"
      }
    }
  }
}
```

具备前瞻记忆的智能体直接在响应中自发返回：

```json
{
  "request_id": "req_200",
  "run_id": "run_opaque_A",
  "status": "ok",
  "body": {
    "accepted": true,
    "emissions": [
      {
        "emission_id": "emit_1",
        "type": "message",
        "content": "记得跟 Sarah 确认合同细节。"
      }
    ]
  }
}
```

全程未下达任何额外的提问指令。

---

# 附录 C —— 工具调用交互完整示例

下达排障任务：

```json
{
  "request_id": "req_a1",
  "run_id": "run_opaque_A",
  "operation": "act",
  "body": {
    "task_id": "task_deploy_1",
    "goal": "排查服务启动时抛出的 missing-column 错误。",
    "tools": [
      {
        "name": "db.inspect_target",
        "input_schema": {
          "type": "object",
          "properties": {}
        }
      }
    ]
  }
}
```

智能体发起工具调用：

```json
{
  "request_id": "req_a1",
  "run_id": "run_opaque_A",
  "status": "ok",
  "body": {
    "task_id": "task_deploy_1",
    "result": {
      "type": "tool_call",
      "tool_call_id": "call_1",
      "tool": "db.inspect_target",
      "arguments": {}
    }
  }
}
```

Runner 在模拟环境中执行工具并交付结果：

```json
{
  "request_id": "req_o2",
  "run_id": "run_opaque_A",
  "operation": "observe",
  "body": {
    "observation": {
      "observation_id": "obs_result_1",
      "type": "tool_result",
      "tool_call_id": "call_1",
      "tool": "db.inspect_target",
      "payload": {
        "target": "legacy-db"
      }
    }
  }
}
```

Runner 随后驱动任务继续推进：

```json
{
  "request_id": "req_a2",
  "run_id": "run_opaque_A",
  "operation": "act",
  "body": {
    "task_id": "task_deploy_1",
    "continuation": true
  }
}
```

整条工具调用轨迹完整留存供 MIB 轨迹评测器打分。

---

# 附录 D —— 推荐代码库结构

```text
MIB/
├── docs/
│   ├── MIB-Architecture.md
│   ├── MIB-Scenario-Model.md
│   ├── MIB-Agent-Adapter.md
│   ├── MIB-Scoring.md
│   ├── MIB-Leaderboard-Evaluation-Service.md
│   └── MIB-v0.1-Test-Plan.md
│
├── docs/cn/
│   ├── MIB-Architecture.md
│   ├── MIB-Scenario-Model.md
│   ├── MIB-Agent-Adapter.md
│   ├── MIB-Scoring.md
│   ├── MIB-Leaderboard-Evaluation-Service.md
│   └── MIB-v0.1-Test-Plan.md
│
├── schemas/
│   ├── mib-scenario.schema.json
│   ├── mib-agent-request.schema.json
│   ├── mib-agent-response.schema.json
│   └── mib-agent-descriptor.schema.json
│
├── adapters/
│   └── implementations/
│
├── runner/
├── evaluators/
├── scenarios/
└── leaderboard/
```

---

# 附录 E —— 后续配套规范指引

完成本协议阅读后，建议依次阅读：

```text
1. MIB-Specification.md（规范性规范：场景模型与计分体系）
3. MIB-v0.1-Test-Plan.md（v0.1 测试与校准计划）
4. MIB-Leaderboard-Evaluation-Service.md（排行榜与评测服务）
```
