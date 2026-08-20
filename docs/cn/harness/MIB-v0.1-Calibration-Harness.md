# MIB v0.1 基准校准执行框架

**版本：** 0.1-draft  
**评测 Profile：** `MIB-Core-0.1`  
**状态：** 参考校准执行框架实现

---

## 1. 设计目标

校准框架（Calibration Harness）旨在回答一个根本问题：**所提议的 MIB 场景是否真正具备作为记忆基准的有效性与区分度？**

针对每个官方场景模板，校准框架测量四大基准参考条件：

```text
B0 — 完全无记忆基线（No Memory）
B1 — 完美可见历史测试桩基线（Full Visible History Fixture）
B2 — 简单词法检索基线（Simple Lexical Retrieval / RAG）
B3 — 结构化/智能体高级记忆基线（Structured / Agentic Memory）
```

核心校准计算量：

```text
FC   = B1 全上下文可解表现（Full Context）
NM   = B0 无记忆基底表现（No Memory）
MDI  = FC - NM（记忆区分度指数）

MGC_B2 = (B2 - NM) / (FC - NM)（B2 记忆差距弥合率）
MGC_B3 = (B3 - NM) / (FC - NM)（B3 记忆差距弥合率）
```

校准框架严格采用测试计划建议的准入门槛：

\[
FC \ge 0.80,\quad NM \le 0.60,\quad MDI \ge 0.25
\]

此外，框架完整统计并输出：

```text
基线跨度（Baseline Span）
结构化相对检索增益（Structured-over-Retrieval Gain）
消融重放下的记忆收益（Memory Benefit）
无关记忆稳定性（Irrelevant Memory Stability）
记忆损害与抗诱导得分（Memory Harm / Harm Resistance）
```

---

## 2. 两个独立的校准维度

校准框架明确区分两个正交的认知问题：

### 2.1 记忆依赖性（Memory Dependence）

```text
在提供完整历史时，系统能否正确解决未来的目标任务？
在剥离全部历史后，系统是否确实无法解决该任务？
```

主要通过 $FC$、$NM$ 与 $MDI$ 衡量。

### 2.2 干预敏感性（Intervention Sensitivity）

```text
当移除目标相关记忆时，任务性能是否发生了实质性下跌？
当移除无关背景噪音时，任务表现是否保持了高度稳定？
```

主要通过记忆收益（$MB$）、净空间归一化收益（$HMB$）、无关稳定性（$IMS$）与抗有害得分（$HRS$）衡量。

若消融规则剔除了错误的信息集，场景可能通过了记忆依赖性测试，却无法通过干预敏感性检验。

---

## 3. 参考基线系统设计

### B0 — 完全无记忆基线（No Memory）

丢弃全部过往观测。仅允许在当前未来的行动循环中临时使用即时工具返回值。

B0 用于评估仅凭提问词面、当前工具入口与模型默认行为能够侥幸做对多少题。若 B0 得分过高，表明题目在无记忆下即可解，缺乏基准有效性。

### B1 — 完美可见历史测试桩基线（Full Visible History Fixture）

保留全部对智能体可见的历史，并提供给评测端的确定性推理机。

用于迅速排查场景本身是否存在不可解的逻辑死锁，属于**测试桩（Fixture）**，而非正式发布级的外部大模型基线。

### B2 — 简单词法检索基线（Simple Lexical Retrieval）

仅基于词法 Token 命中重叠度检索 Top-2 记忆，不具备时序演进模型、信源追踪机制或技能适用性判断。用于识别那些仅凭简单关键词匹配即可轻松满分的初级场景。

### B3 — 结构化/智能体高级记忆基线（Structured / Agentic Memory）

引入显式的内容显著性与记忆类型线索（更新标记、权威信源、排障轨迹与适用边界），展现高级认知记忆系统相较于纯检索的明显优势。

---

## 4. 场景校准卡片（Calibration Card）

每个模板生成专属校准卡片，涵盖：

```text
FC / NM / MDI 核心指标
B2 / B3 实测表现
MGC_B2 / MGC_B3 弥合率
基线跨度与因果诊断指标
各准入门槛达成状态
综合处置建议
```

处置建议包含：
- `provisional_pass`：通过确定性测试桩门槛；
- `revise_or_empirically_review`：需修订或需实证复核；
- `retire_or_redesign_candidate`：建议退役或重新设计。

---

## 5. 发布级校准边界（Release Calibration Boundary）

参考报告默认标记：

```text
release_calibration_eligible = false
```

发布级正式校准必须使用：
- **B0：** 相同的固定大模型，在剥离历史或禁用记忆下运行；
- **B1：** 相同的固定大模型，在直接提供全量相关历史下运行；
- **B2：** 完全可复现的开源简易检索实现；
- **B3：** 至少一套具备代表性的高级记忆系统实测实现。

框架支持通过命令行覆盖基线实现：

```bash
mib-calibrate ... \
  --baseline-override B1=my_package:FixedModelFullContextAgent
```

---

## 6. 命令行调用（CLI）

```bash
mib-calibrate \
  /private/MIB-v0.1-Official-Canonical-Pack \
  --schema schemas/mib-scenario.schema.json \
  --profile profiles/MIB-Core-0.1.json \
  --seeds 101,202,303,404 \
  --bootstrap-resamples 2000 \
  --output-json calibration.json \
  --output-md calibration.md \
  --output-csv calibration.csv
```

---

## 7. 核心判定准则

校准不是 B0~B3 基线之间的打榜竞赛，基线只是诊断仪器。

基准追问的核心始终是：

> **该场景是否成功构建了一个可控的未来任务，使得记忆在此处既不可或缺、切实有效，又具备清晰可辨的因果归因性？**

---

## 校准状态总结

4 随机种子参考测试桩校准在基础 FC/NM/MDI 门槛上达成 **36/36 全量通过**，在纳入因果敏感性与无关稳定性后同样达成 **36/36 全量通过**（详见 `MIB-v0.1-Calibration-Findings.md`）。当前测试桩基线保持 `release_calibration_eligible = false`。
