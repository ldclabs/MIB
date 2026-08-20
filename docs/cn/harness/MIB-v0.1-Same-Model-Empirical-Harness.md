# MIB v0.1 同模型实证基准测试框架

**版本：** 0.1-draft  
**状态：** 工程实现候选规范 / 发布级校准核心基础设施  
**目标 Profile：** `MIB-Core-0.1`

---

## 1. 设计目标

同模型实证校准框架（Same-Model Empirical Harness）用于回答一个更聚焦、更严格的科学问题：

> **在基座模型、System Prompt、工具集、推理策略、场景实例与解码参数完全锁定的前提下，仅仅改变长期记忆条件，对未来的认知与行为会产生多大程度的改变？**

四大核心实证基线：

```text
B0  完全无记忆基线（No Memory）
B1  完美可见历史基线（Full Visible History）
B2  简单词法检索基线（Simple Lexical Retrieval / RAG）
B3  结构化确定性记忆基线（Structured Deterministic Memory）
```

本测试框架为正式冻结 MIB v0.1 官方榜单题库包提供权威的实证科学依据。

---

## 2. 实验核心不变量（Experimental Invariant）

在一场合规的同模型实验中，以下要素必须保持绝对一致：

```text
相同的基座大模型
相同的模型 Endpoint / 模型唯一标识
相同的 System Prompt
相同的推理策略
相同的基准环境工具集
相同的解码超参数（温度、Top-p 等）
相同的场景实例（Scenario Instance）
相同的重复运行 / 配对随机种子策略
相同的未来考核探针（Future Probe）

唯有长效记忆策略允许发生改变。
```

若上述任何锁定字段发生变更，该实验即丧失“同模型记忆对比”的资格。

---

## 3. 无状态模型交互边界（Stateless Model Boundary）

每次 `respond()` 与 `act()` 交互轮次均为一次全新的独立模型请求。

模型服务提供方**严禁**在多次请求之间跨轮次保留隐式上下文会话状态。长效记忆历史仅允许通过框架受控的 `LONG_TERM_MEMORY_CONTEXT` 区域注入。

当前行动循环内的即时工具返回结果属于即时瞬态，通过 `CURRENT_TASK_TRANSIENT_STATE` 区域等权提供给 B0~B3。

由此彻底杜绝服务端 Session 隐式演变为未经度量的“第五套记忆系统”。

---

## 4. 四大实证记忆条件定义

### B0 — 完全无记忆（No Memory）

时间线观测在探针触发时不予保留。当前行动任务中产生的即时工具返回值在任务结束前临时可用。

### B1 — 完美可见历史（Full Visible History）

在每个未来探针触发时，将所有智能体可见的时间线事件完整回放给固定模型。

仅当框架明确记录以下指标时，B1 方被判定为合规的 Full Context 基线：

```text
memory_truncations = 0
```

若模型上下文窗口导致 B1 发生截断，必须修正场景规模或模型配置，否则不可用于发布级校准。

### B2 — 简单词法检索（Simple Lexical Retrieval）

过往观测逐字原样存入。在探针触发时，依靠确定性 Token 命中重叠度检索固定的 `top_k` 条记忆。无时序更新模型、无信源拓扑、无经验提炼与技能适用性判断。

### B3 — 结构化确定性记忆（Structured Deterministic Memory）

同样保留原始观测，但检索融合了：

```text
词法相关性评分
纠错与最新状态线索
信源与权威度线索
失败与排障恢复线索
适用边界与反例线索
轻量时间衰减项
显著性补充权重
```

B3 保持确定性且使用与 B0~B2 完全相同的基座模型，其优势完全源自记忆策略与数据结构，而非引入了第二台大模型。

---

## 5. 实验锁定机制（Experiment Lock）

`MIBSameModelExperimentLock` 在密码学层面紧密绑定：

```text
模型客户端类型
模型 ID
模型 Endpoint 或子进程启动命令
模型调用参数
随机种子策略
System Prompt 哈希摘要
推理策略哈希摘要
Scenario Schema 哈希摘要
Profile 哈希摘要
官方 Scenario Pack 哈希摘要
B0–B3 记忆策略配置定义
```

该锁定配置生成唯一的 SHA-256 摘要。不同锁定摘要下的报告严禁混合为同一次实验。API Key 等敏感密码不计入锁定哈希中。

---

## 6. 配对解码与随机性对齐

发布级校准在模型支持时推荐使用确定性解码（`temperature = 0`）。

针对非确定性模型，框架支持**语义调用粒度配对随机种子（Paired-per-call seed）**，种子由运行种子加上 `respond:<probe_id>` 或 `act:<task_id>:<turn>` 计算得出，且绝不包含记忆条件标签。某个条件中较长的工具循环绝不会导致后续探针的采样种子发生错位漂移。

### 6.1 拉丁方条件次序对齐（Latin Rotation）

真实远程大模型可能存在负载、缓存、限流或时间波动。框架坚决避免“先跑完全部 B0、再跑完全部 B1”的批次偏置做法。

每个 `(模板, 场景实例, 重复轮次)` 构成一个配对实验单元。在该单元内部，B0/B1/B2/B3 按照确定性的拉丁轮转顺序交替执行：

```text
单元 0: B0 → B1 → B2 → B3
单元 1: B1 → B2 → B3 → B0
单元 2: B2 → B3 → B0 → B1
单元 3: B3 → B0 → B1 → B2
...
```

在 36 模板 $\times$ 4 实例种子 $\times$ 2 重复轮次构成的 288 个单元中，各记忆条件在每一个执行位次上均精确出现 72 次，彻底消除批次时序偏差。

---

## 7. 准入门槛矩阵

继承 v0.1 模板准入标准：

\[
FC \ge 0.80,\quad NM \le 0.60,\quad MDI \ge 0.25
\]

\[
\text{基线跨度} \ge 0.20,\quad IMS \ge 0.90,\quad MB \ge 0.20
\]

同时增补同模型公平性检验门槛：

```text
模型身份严格锁定
System Prompt 严格统一
推理策略严格统一
工具接口严格统一
解码参数严格统一
解码过程确定性或显式定种
模型调用完全无状态
唯一变量仅限记忆策略
B1 历史绝对无截断
模型通信与解析零故障
```

---

## 8. 模型适配器支持

框架内置：

```text
http_json                 标准 HTTP JSON 协议
openai_compatible_chat    兼容 OpenAI 格式的 Chat 接口
subprocess_jsonl          本地子进程 JSONL 接口
deterministic_stub        确定性工程调试桩（仅供开发）
```

使用调试桩产出的报告显式标记：`release_calibration_eligible = false`。

---

## 9. 产物输出

完整运行产出：
- 同模型报告 JSON（Same-Model Report JSON）
- Markdown 格式摘要（Same-Model Markdown summary）
- 36 行模板明细 CSV（36-row Template CSV）
- 实验锁定清单 JSON（Experiment Lock JSON）
- 详细的模型与记忆系统遥测指标（Telemetry）

---

## 10. 遥测度量指标

针对 B0~B3 细致记录：调用次数、解析错误、输入输出字符量、Token 统计、记忆检出条数、记忆截断次数等，作为效率与成本分析依据。

---

## 11. 命令行操作参考

```bash
# 调试桩工程测试
mib-same-model-calibrate \
  examples/same-model/same-model-experiment.stub.json \
  --experiment-schema schemas/mib-same-model-experiment.schema.json \
  --report-schema schemas/mib-same-model-report.schema.json \
  --output-json examples/same-model/same-model-stub.report.json \
  --output-md examples/same-model/same-model-stub.report.md \
  --output-csv examples/same-model/same-model-stub.csv \
  --output-lock examples/same-model/same-model-stub.lock.json

# 启动外部大模型前估算调用开销
mib-same-model-calibrate \
  examples/same-model/same-model-experiment.external-http.json \
  --estimate-only \
  --experiment-schema schemas/mib-same-model-experiment.schema.json

# 正式执行外部固定模型实证校准
mib-same-model-calibrate \
  examples/same-model/same-model-experiment.external-http.json \
  --experiment-schema schemas/mib-same-model-experiment.schema.json \
  --report-schema schemas/mib-same-model-report.schema.json \
  --output-json empirical.report.json \
  --output-md empirical.report.md \
  --output-csv empirical.csv \
  --output-lock empirical.lock.json
```

---

## 12. 发布决策标准

36/36 测试桩通过证明了场景的**内部逻辑闭环**；

而在真实固定模型下的 **36/36 同模型实证通过** 则证明了：在真实大模型驱动下，官方题库在全历史下高度可解、无历史下切实需要记忆、对关键记忆剥离高度敏感、对无关噪音高度免疫，且能在不改动基座智力水平的前提下清晰区分不同的记忆架构。

唯有满足后者，才具备正式发布与冻结 v0.1 榜单题库的充分科学依据。

---

## 13. 发布运行规模估算与当前状态

候选发布级配置：36 官方模板 $\times$ 4 隐藏种子 $\times$ 2 重复轮次 $\times$ (B0/B1/B2/B3 全量 + B3 消融)，共计需执行 **2,232 场场景运行**，至少消耗 **3,152 轮大模型调用**。

当前环境由于尚未绑定特定生产模型的 Endpoint 与凭证，当前状态保持为：

```text
pending_external_model_run
release_calibration_eligible = false
```
