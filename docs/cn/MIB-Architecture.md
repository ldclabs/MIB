# MIB 架构设计规范

## 记忆智能基准（Memory Intelligence Benchmark）

**版本：** 0.1-draft  
**状态：** 架构提案 / 预规范草案

---

# 0. 摘要

MIB —— **Memory Intelligence Benchmark（记忆智能基准）** —— 是一套用于评测智能体（Agent）记忆能力的架构体系。

MIB **不以**以下问题为核心考量：

> 系统能从过往检索出多少历史信息？

它探究的是一个更为本质的问题：

> **过往经历中正确的部分，能否以正确的方式改变未来的认知与行为决策？**

这一区分构成了 MIB 的理论基石。

一个系统即使完整记录了所有交互历史，并能在检索任务中取得极高的 Recall，也可能在记忆智能上表现拙劣：例如当陈旧记忆覆盖了当前现实、相互矛盾的信源被粗暴合并为单一事实、特定场景下成功的操作流程被盲目套用到不适用的环境，或是记住了信息却从未对未来的行动产生实际影响。

因此，MIB 将记忆视为一种**具备因果效力的认知能力（causal cognitive capability）**，而不仅是一个单纯的存储或检索子系统。

```text
过往交互 / 经验
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

MIB 评测的是贯穿上述跨时序认知的完整闭环。

基准保持**架构中立性（architecture-neutral）**。参评系统可以使用向量记忆、摘要记忆、图记忆、情景记忆、关系型记忆、过程记忆、全上下文重放、基于 KIP 的记忆体系、学习型记忆模块或各类混合系统。

MIB 并不强制要求实现 KIP。KIP v2 提供了部分概念启发——尤其是将知识、证据、主张、经验、技能、记忆状态、时间演变、来源溯源与治理机制进行解耦的思想——但 MIB 是一个面向所有长效记忆系统的独立基准。

评测输出的主分数为：

```text
MIB Score
0 ─────────────────────────── 100
```

同时附带多维度的细粒度能力剖面图（Capability Profile），而非单一晦涩的分数。

---

# 1. 核心理论

评估记忆系统的优劣，不在于它能检索出多少历史数据，而在于过往经历中正确的部分是否以正确的方式改变了未来。

从形式化概念来看：

\[
Memory = Past\ State\ Capable\ of\ Conditioning\ Future\ Computation
\]
（记忆：能够对未来计算构成约束或条件的过往状态）

以及：

\[
Learning = Durable,\ Context\text{-}Appropriate\ Behavioral\ Change\ Caused\ by\ Prior\ Experience
\]
（学习：由先验经验引起的、持久且契合情境的行为改变）

由此引出三项核心准则。

## 1.1 记忆必须具备因果效应

如果移除某条理论上相关的记忆，并不会影响智能体后续的相关决策或行为，那么该条目充其量只是被存储的历史数据，在当前任务中并未真正发挥记忆的认知功能。

## 1.2 记忆必须具备情境敏感性

如果某条记忆在一个情境下提升了行为表现，却在不相关的场景中造成干扰与损害，这就不是高水平的记忆智能。

## 1.3 记忆必须维系关键认知区分

在需要的时候，高水平的智能系统应当能够清晰辨析以下概念：

```text
当前真实（current truth） vs 历史真实（historical truth）
他人陈述（statement） vs 自身认可的信念（accepted belief）
消息来源（source） vs 证据溯源（provenance）
孤立事件（Event） vs 结构化经验（Experience）
陈述性知识（Knowledge） vs 程序性技能（Skill）
系统置信度（confidence） vs 对信源的信任度（trust）
记忆的可访问性（accessibility） vs 记忆的重要性（importance）
实用价值（utility） vs 权威性（authority）
```

模糊上述界限往往会导致“检索虽然命中、认知却已失败”的现象。

---

# 2. MIB 评测对象与目标

MIB 的基本评测单元为：

```text
Agent（智能体） + Long-Term Memory System（长效记忆系统）
```

MIB 综合检验系统是否具备以下能力：

1. 保留关键信息；
2. 在需要时精准检索；
3. 基于时间跨度对状态演变进行推理；
4. 维护信源与认识状态的区分；
5. 重构具有因果结构的经验轨迹；
6. 习得可复用的操作流程与技能；
7. 执行选择性遗忘而不破坏历史事实；
8. 牢记自身承诺与自我认知状态；
9. 抵御陈旧、有害或无关记忆的误导；
10. 证明记忆对行为带来了可量化的因果收益。

MIB 并非单纯评测底层大模型的基础智商、纯代码生成能力、Embedding 表征质量、向量库吞吐量、孤立的向量召回率或 KIP 协议的符合性。

---

# 3. 评测赛道

## 3.1 赛道 A —— 记忆系统赛道（Track A — Memory System Track）

**目标：**

> 剥离大模型基座的影响，单独量化记忆系统本身的实际贡献。

基准尽量固定以下所有环境要素：

```text
基座大模型
智能体 Prompt
推理策略
可用工具
任务环境
交互接口
评估策略
```

参赛方仅替换其自研的记忆系统：

```text
固定 Agent 框架
   ├── 记忆系统 A
   ├── 记忆系统 B
   ├── 记忆系统 C
   └── 记忆系统 D
```

提交报告必须声明基座模型版本、Agent 版本、Prompt 哈希、工具集、环境版本、记忆系统版本及 MIB 评测套件版本。

## 3.2 赛道 B —— 完整智能体赛道（Track B — Integrated Agent Track）

**目标：**

> 衡量软硬件一体化完整智能体的最终记忆智能水平。

参赛方可自主决定模型选型、Agent 策略、记忆架构、检索策略、巩固机制与工具调用逻辑。

赛道 B 的成绩**严禁**直接与赛道 A 进行混排比较。

## 3.3 可选赛道 C —— 记忆组件诊断（Track C — Memory Component Diagnostics）

对于对外暴露内部 Memory API 的系统，可参与更深度的组件级诊断，包括精准记录消融、快照对比、检索轨迹追踪、存储开销分析、写入放大与影响链路溯源。

赛道 C 属于可选诊断项目，不作为常规参评的前提条件。

---

# 4. 能力模型

MIB v1 围绕八大核心维度构建：

```text
1. 保留与检索（Retention & Retrieval）
2. 时序记忆（Temporal Memory）
3. 认识状态记忆（Epistemic Memory）
4. 经验记忆（Experience Memory）
5. 技能学习与迁移（Skill Learning & Transfer）
6. 选择性遗忘（Selective Forgetting）
7. 前瞻与自我记忆（Prospective & Self Memory）
8. 因果记忆效应（Causal Memory Impact）
```

默认推荐权重分布如下：

| 能力维度 | 权重 |
|---|---:|
| 保留与检索（Retention & Retrieval） | 12 |
| 时序记忆（Temporal Memory） | 13 |
| 认识状态记忆（Epistemic Memory） | 15 |
| 经验记忆（Experience Memory） | 15 |
| 技能学习与迁移（Skill Learning & Transfer） | 15 |
| 选择性遗忘（Selective Forgetting） | 10 |
| 前瞻与自我记忆（Prospective & Self Memory） | 8 |
| 因果记忆效应（Causal Memory Impact） | 12 |
| **总计** | **100** |

权重属于基准治理策略的一部分，可能随主版本演进而调优。

---

# 5. 维度 1 —— 保留与检索（Retention & Retrieval）

**核心问题：**

> 系统能否在经历时间流逝、噪声干扰与上下文切换后，准确召回过往的关键认知信息？

MIB 细分为直接召回（Direct Recall）、隐式召回（Implicit Recall）、多跳召回（Multi-Hop Recall）、抗干扰能力（Distractor Resistance）以及实体精度（Identity Precision）。

直接召回示例：

```text
历史输入： 我的狗叫 Pixel。
未来提问： 我的狗叫什么名字？
```

隐式召回示例：

```text
历史输入：
  狗 = Pixel
  品种 = 吉娃娃
  体重 = 2.3 kg

未来提问：
  我应该买大号还是小号的胸背带？
```

多跳召回示例：

```text
Alice 在 Orbit 公司工作。
Orbit 的办公室位于东京。
东京属于 UTC+9 时区。

未来提问：
和 Alice 预约会议时我该参考哪个时区？
```

MIB 考核的是最终的认知产出质量，而非单纯计算内部中间层的 Recall@K。

---

# 6. 维度 2 —— 时序记忆（Temporal Memory）

**核心问题：**

> 系统能否准确表征随时间发生的状态演变，而非仅记录孤立的事实快照？

示例：

```text
T1： 我的时区是 UTC+8。
T2： 我下个月搬家去伦敦。
T3： 我已经到了伦敦。我现在处于 UTC+1 时区。
```

查询当前状态：

```text
我现在在哪个时区？
→ UTC+1
```

查询历史状态：

```text
搬家前我用的是哪个时区？
→ UTC+8
```

采用“最后写入覆盖（Last-write-wins）”策略的简单记忆系统只能答对其中一部分。

子项得分：

```text
当前状态准确率（Current State Accuracy）
历史状态准确率（Historical State Accuracy）
状态跃迁理解（Transition Understanding）
时间先后排序（Temporal Ordering）
有效时间区间推理（Valid-Time Reasoning）
陈旧信息回避（Staleness Avoidance）
```

---

# 7. 维度 3 —— 认识状态记忆（Epistemic Memory）

**核心问题：**

> 系统能否不仅记住内容本身，还能准确记住该内容代表何种认知承诺与证据效力？

这是 MIB 区别于传统评测的核心特色之一。

## 7.1 他人陈述 vs 客观事实（Statement vs Truth）

```text
Alice： 开会时间是下午 3 点。
Bob：   我觉得是下午 4 点。
日历系统： 15:00
```

系统应准确记录：Alice 说了 3 点，Bob 说了 4 点，而权威日历证据证实为 3 点。

## 7.2 纠错处理（Correction）

```text
历史输入： 我的生日是 5 月 12 日。
后续输入： 不好意思刚才说错了，实际是 5 月 21 日。
```

回答当前生日应为 5 月 21 日，同时在回溯历史时仍能厘清之前的口误陈述与纠错过程。

## 7.3 矛盾辨析（Contradiction）

```text
Alice： 我喜欢喝茶。
Bob：   Alice 讨厌喝茶。
Alice 随后： 我依然喜欢喝茶。
```

系统必须准确区分发言主体、信源可靠度、观点分歧、交叉佐证，以及本人声明与第三方揣测的矛盾。

## 7.4 未知 vs 为假（Unknown vs False）

若没有任何证据表明 Alice 是否是素食主义者，合规的回答应为 `未知（unknown）` 或 `信息不足（insufficient information）`，绝不能直接断定为 `否（no）`。

## 7.5 证据独立性（Evidence Independence）

```text
同一条原始消息
→ 生成摘要 A
→ 生成摘要 B
→ 抽取图谱三元组事实
```

严禁将上述派生信息视作三个相互独立的事实信源。

子项得分：

```text
信源归属（Source Attribution）
纠错响应（Correction Handling）
矛盾处理（Contradiction Handling）
审慎弃权/未知判定（Abstention / Unknown）
证据偏好仲裁（Evidence Preference）
历史归属回溯（Historical Attribution）
证据独立性维护（Evidence Independence）
```

MIB 可输出 **认识完整性得分（Epistemic Integrity Score）** 作为专属专项分数。

---

# 8. 维度 4 —— 经验记忆（Experience Memory）

**核心问题：**

> 系统能否完整保留“状态-动作-观测-结果”的因果经验轨迹，而非仅仅存储零散孤立的事实？

经验轨迹示例：

```text
目标： 部署 v2 版本
动作： 执行数据库 migration
观测： migration 执行成功
动作： 重启服务
观测： 报错提示 missing-column
动作： 检查 migration 详情
观测： migration 被误执行到了错误的数据库实例上
动作： 切换目标数据库并重新应用
结果： 部署成功
```

未来任务：

```text
另一次部署同样抛出了 missing-column 错误。
你首先应该排查什么？
```

优秀的经验记忆应当能够召回整条可复用的排障路径，而不是仅仅做关键词匹配。

子项得分：

```text
目标召回（Goal Recall）
轨迹召回（Trajectory Recall）
动作/观测时序性（Action/Observation Ordering）
结果判定召回（Outcome Recall）
失败与恢复路径召回（Failure/Recovery Recall）
预测偏差召回（Prediction Error Recall）
经验压缩保真度（Experience Compression Quality）
```

---

# 9. 维度 5 —— 技能学习与迁移（Skill Learning & Transfer）

**核心问题：**

> 系统能否将多段经验提炼编译为可跨情境复用的行为策略？

假设重复多次的任务揭示了如下隐含规则：

```text
在点击保存（Save）之前：
  必须先选定工作区（workspace）。
```

未来任务在页面、内容、操作对象与工具状态上均发生了变化，但底层仍遵循该隐藏流程规则。

MIB 评测指标包括：

```text
技能习得（Skill Acquisition）
正向迁移（Positive Transfer）
避坑能力（Failure Avoidance）
适用性边界判断（Applicability Detection）
反例利用（Counterexample Use）
抗负迁移能力（Negative Transfer Resistance）
```

抗负迁移能力至关重要。若新系统环境本就不需要提前选择工作区，盲目套用老技能导致额外开销或错误，系统评分将被扣减。

仅给出成功案例是不够的；合格的记忆系统必须懂得适用边界。

---

# 10. 维度 6 —— 选择性遗忘（Selective Forgetting）

**核心问题：**

> 系统能否有效阻止过时废弃的记忆支配当前行为，同时在需要回溯历史时完整保留相关记录？

示例：

```text
T1： API 采用 JWT 认证。
T2： API 已全量迁移至 Session 认证，严禁继续使用 JWT。
```

当前任务：

```text
请实现新接口的身份认证。
→ 采用 Session 认证
```

历史查询：

```text
在系统迁移之前，API 使用的是什么认证方式？
→ JWT 认证
```

这同时检验了：

```text
操作性遗忘（Operational Forgetting）
+
历史档案留存（Historical Preservation）
```

子项得分：

```text
陈旧记忆抑制（Stale Memory Suppression）
历史记录留存（Historical Preservation）
干扰项抑制（Distractor Suppression）
关键信号留存（Signal Preservation）
保留优先级判定（Retention Prioritization）
```

---

# 11. 维度 7 —— 前瞻与自我记忆（Prospective & Self Memory）

## 11.1 前瞻记忆（Prospective Memory）

```text
历史输入：
当 Sarah 下次进入会议室时，提醒我跟她确认合同细节。

（很久之后……）
系统事件： Sarah 已加入会议。
```

智能体应基于触发事件主动做出响应，无需用户再次显式下达查询指令。

## 11.2 自我记忆（Self Memory）

假设智能体在前期交互中多次确认过：

```text
在未配置对应扩展连接的情况下，我无权访问私有 GitHub 仓库。
```

后续任务：

```text
请帮我检查私有仓库中的代码。
```

智能体应维系自身能力的连续性认知，严禁假装自己拥有该权限。

MIB 同时测试反向缺陷：记忆中出现诸如 `我是管理员` 等语句，绝不能误导智能体认为自己凭空获得了实际权限。

子项得分：

```text
前瞻事件触发（Prospective Triggering）
承诺持久性（Commitment Persistence）
自身能力认知连续性（Capability Continuity）
自我纠错（Self-Correction）
自身边界与局限回忆（Self-Limitation Recall）
权限边界管控（Authority Boundary）
```

---

# 12. 维度 8 —— 因果记忆效应（Causal Memory Impact）

这是 MIB 架构的核心支柱。

**核心问题：**

> 记忆是否确实因果性地带来了更好的未来行为？

MIB 会在同一未来任务上执行对照变体实验：

## 12.1 全量记忆条件（Full Memory）

```text
智能体 + 完整的相关历史
```

## 12.2 相关记忆消融条件（Relevant Memory Ablated）

```text
相同智能体 + 精准移除/遮蔽关键相关记忆
```

## 12.3 无关记忆消融条件（Irrelevant Memory Ablated）

```text
相同智能体 + 移除无关的历史噪音记忆
```

## 12.4 存在有害/陈旧记忆条件（Harmful / Stale Memory Present）

```text
相同智能体 + 注入貌似合理但已过时或具误导性的记忆
```

定义因果记忆影响指数（Causal Memory Impact, CMI）：

\[
CMI = Performance_{full} - Performance_{relevant\_ablated}
\]

显著为正的 CMI 证明相关记忆切实改善了系统行为。

理想状态下：

\[
Performance_{full} \approx Performance_{irrelevant\_ablated}
\]

系统还应能抵御陈旧事实、错误信源记忆、高语义相似度无关干扰、脱离语境的技能生搬硬套、投毒记忆以及过远的虚假自传体记忆。

---

# 13. 记忆收益、损害与净增益

MIB 要求因果指标与综合能力分数独立并行报告。

## 记忆收益（Memory Benefit, MB）

\[
MB = Performance_{full} - Performance_{relevant\_ablated}
\]

## 记忆损害（Memory Harm, MH）

近似定义为：

\[
MH = P(记忆导致了原本可避免的错误)
\]

## 净记忆增益（Net Memory Gain, NMG）

\[
NMG = MB - MH
\]

结果示例：

```text
记忆收益（Memory Benefit）       +28.4%
记忆损害（Memory Harm）            5.2%
净记忆增益（Net Memory Gain）     +23.2%
```

---

# 14. 影响精度（Influence Precision）

MIB 提出了一个超越传统检索召回率的概念。

**核心问题：**

> 在切实影响了智能体行为的所有记忆中，有多少是以正确的方式发挥了积极作用？

形式化表示：

\[
Influence\ Precision =
\frac{起到正向帮助的记忆影响数}{检测到的全部记忆影响数}
\]

一个系统可能拥有完美的检索率，但如果它将大量无关记忆注入决策上下文造成干扰，其影响精度仍会很低。

深度诊断赛道可精确追踪记忆激活链路；黑盒赛道可通过行为表现的统计代理指标进行估算。

---

# 15. 学习曲线

MIB 包含长程纵向评测套件：

```text
任务 1
任务 2
任务 3
...
任务 N
```

持续追踪测量 `Performance(t)`。

衍生指标：

## 学习增益（Learning Gain, LG）

\[
LG = Performance_{late} - Performance_{early}
\]

## 已知错误重现率（Error Recurrence Rate, ERR）

\[
ERR = \frac{重复发生已知教训的失败次数}{遇到相关情境的总机会数}
\]

高水平的经验记忆系统能够显著降低对已知失败模式的重复犯错率。

---

# 16. 场景：评测的基本单元

MIB 不是静态的问答数据集。

其最根本的单元是描述世界随时间演变的**记忆片段程序（Memory Episode Program）**。

```yaml
id: MIB-TIME-001

world:
  initial_state:
    user_timezone: "+08:00"

timeline:
  - t: 1
    type: interaction
    content: "我的时区是 UTC+8。"

  - t: 20
    type: interaction
    content: "我下个月搬去伦敦。"

  - t: 50
    type: interaction
    content: "我已经到了伦敦。现在的时区是 UTC+1。"

  - t: 60
    type: distractor_batch
    count: 200

probes:
  - id: current
    type: factual
    ask: "我现在处于哪个时区？"
    expected: "+01:00"

  - id: historical
    type: temporal
    ask: "搬家之前我使用的是哪个时区？"
    expected: "+08:00"

ablations:
  - remove: [event:t50]
  - remove: [unrelated_distractors]
```

智能体是在**亲历场景的生命周期**，而非接收一个被预先拼装好的静态上下文窗口。

---

# 17. 场景生命周期

```text
RESET（重置环境）
  ↓
SEED WORLD（播种世界初始状态）
  ↓
PAST EPISODES（逐步经历历史片段）
  ↓
INTERFERENCE / DISTRACTORS（注入干扰与噪音）
  ↓
OPTIONAL CONSOLIDATION WINDOW（可选的记忆巩固窗口）
  ↓
FUTURE PROBE / TASK（触发未来探针 / 任务）
  ↓
OUTCOME（收集产出与行为）
  ↓
ABLATION RE-RUNS（执行对照消融重放）
  ↓
EVALUATION（综合打分评测）
```

除非场景专门测试面向已知未来目标的规划能力，否则在记忆形成阶段**严禁**泄漏未来的探针问题。

---

# 18. 严禁未来探针提前泄漏

核心设计约束：

> 记忆系统在决定沉淀和保留哪些信息时，绝不能预先知晓后续会面临何种未来探针。

错误做法：

```text
直接提示智能体：
“稍后系统会问你 Alice 的时区，请牢记。”
```

正确做法：

```text
产生历史事件
→ 智能体完整经历该过程
→ 记忆沉淀与形成结束
→ 后续动态抽取并触发未来探针
```

这真实检验了系统的自发信息筛选、压缩、显著性识别与保留能力。

---

# 19. 场景家族（Scenario Families）

MIB 采用参数化模板（Parameterized Templates）而非静态固化实例。

涵盖场景家族示例：

```text
属性更新（attribute update）
实体冲突（identity collision）
信源分歧（source disagreement）
显式纠错（explicit correction）
时序状态演变（temporal transition）
多跳关联（multi-hop relation）
失败排查与恢复（failure/recovery）
隐式工作流规则（hidden workflow rule）
技能反例（Skill counterexample）
前瞻承诺（prospective commitment）
自身局限认知（self-limitation）
陈旧记忆陷阱（stale-memory trap）
无关噪音过载（irrelevant-memory overload）
跨智能体共享记忆（cross-agent imported memory）
```

模板支持随机化实体名称、数值、日期、事件顺序、干扰项、提问措辞、工具配置、环境状态与失败条件。

---

# 20. 公开与隐藏评测机制

MIB 分别发布两套数据集：

```text
公开开发集（Public Dev Set）
隐藏评测集（Hidden Evaluation Set）
```

公开集用于适配器开发、本地调试与学术研究；隐藏集用于保障官方榜单的公正性，防止针对模板模式进行硬编码过拟合。

隐藏评测必须使用未公开的场景实例化参数，并可包含全新的模板组合。

---

# 21. 基准评测规模

MIB 依据认知跨度（Cognitive Horizon）而非单纯 Token 长度来划分规模。

## MIB-S（小规模）

```text
50–100 个有效事件
低到中度干扰
短运行耗时
```

适用于日常开发调试与 CI 自动化测试。

## MIB-M（中规模）

```text
约 1,000 个有效事件
高密度干扰噪音
多次状态演变与修正
包含多组经验轨迹与技能模式
```

官方排行榜的核心主力规模。

## MIB-L（大规模）

```text
10,000+ 个有效事件
大量交互实体
跨越多个时序纪元
多轮环境复杂任务
重度背景噪音与干扰
长程技能泛化与迁移
```

极限压力测试规模。

评测报告中应包含事件总量、有效状态变化数、经验记录数、干扰项数量及估算 Token 数。

---

# 22. Benchmark Runner 架构

```text
                  ┌─────────────────────┐
                  │  Scenario Registry  │ （场景注册表）
                  └─────────┬───────────┘
                            │
                  ┌─────────▼───────────┐
                  │   World Simulator   │ （世界模拟器）
                  │ state + clock + RNG │
                  └─────────┬───────────┘
                            │
                  ┌─────────▼───────────┐
                  │   Benchmark Driver  │ （基准驱动引擎）
                  └─────────┬───────────┘
                            │
          ┌─────────────────┴──────────────────┐
          │                                    │
┌─────────▼──────────┐              ┌──────────▼──────────┐
│    Agent Adapter   │              │ Ablation Controller │（消融控制器）
└─────────┬──────────┘              └──────────┬──────────┘
          │                                    │
┌─────────▼──────────┐                         │
│ Agent + Memory     │◄────────────────────────┘
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Output / Actions  │ （输出 / 执行动作）
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│    Evaluators      │ （多层评测器）
│ deterministic      │
│ world-state        │
│ semantic           │
│ trajectory         │
│ optional LLM judge │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Scoring Engine   │ （计分引擎）
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ MIB Capability Card│ （能力卡片报告）
└────────────────────┘
```

---

# 23. 场景注册表（Scenario Registry）

注册表管理场景与模板的元数据定义，包括版本、难度、能力维度标签、前置依赖、种子策略、Ground Truth 约束、消融规则与打分权重。

规范 ID 命名格式：

```text
MIB-RET-001    （检索）
MIB-TIME-001   （时序）
MIB-EPI-001    （认识状态）
MIB-EXP-001    （经验）
MIB-SKILL-001  （技能）
MIB-FORGET-001 （遗忘）
MIB-PROS-001   （前瞻）
MIB-SELF-001   （自我认知）
MIB-CAUSAL-001 （因果）
MIB-X-001      （跨维度综合）
```

---

# 24. 世界模拟器（World Simulator）

世界模拟器掌握评测环境的隐藏真实基准（Ground Truth）：

```text
世界真实状态
虚拟时钟
工具底层状态
实体内部状态
环境状态演化
任务成功/失败判据
随机数种子
```

智能体无法直接读取隐藏的世界真值，只能通过执行交互观察到的结果来进行认知。

示例：

```text
智能体调用 deploy()
→ 模拟器基于当前真实状态求值
→ 返回 startup_error 错误
```

这确保了 MIB 评测的是对客观现实的行为响应，而非局限于自然语言的文字相似度。

---

# 25. 虚拟时钟（Virtual Time）

MIB 支持虚拟时钟推进机制，能够在不发生真实物理等待的前提下，模拟跨越数天、数周、数月甚至数年的长周期时间演变。

虚拟时钟支撑以下能力的评测：

```text
信息陈旧度演变
长期承诺兑现
有效期限推理
遗忘衰减曲线
长周期状态更新
定时维护调度
```

智能体仅能通过正常的交互接口感知时间变化。

---

# 26. Agent Adapter 适配器

核心 Agent 适配接口保持极简设计：

```typescript
interface MIBAgent {
  reset(run: RunContext): Promise<void>;
  observe(input: Observation): Promise<void>;
  respond(input: AgentInput): Promise<AgentOutput>;
  act(task: Task): Promise<ActionResult>;
}
```

智能体内部如何沉淀记忆、生成摘要、结构化巩固、检索召回、推理决策或调用内部工具，MIB 不做任何限制。

---

# 27. 观测数据与输入格式

观测数据类型包括用户消息、工具调用返回、环境事件、文档材料、传感器读数、系统反馈、系统通知与时间推进事件。

示例：

```json
{
  "id": "obs-123",
  "type": "user_message",
  "timestamp": "2026-08-19T01:00:00Z",
  "actor": "alice",
  "content": "我的时区是 UTC+8。"
}
```

MIB 明确区分三类数据：当前即时输入、预期依赖过往记忆调取的线索、以及隐藏的环境基准真值。

---

# 28. 可选 Memory Adapter 诊断接口

具备开放能力的记忆系统可选择性暴露内部接口：

```typescript
interface MIBMemoryAdapter {
  snapshot(): Promise<MemorySnapshot>;
  inspect(query?: MemoryInspectionQuery): Promise<MemoryRecord[]>;
  delete(ref: MemoryRef): Promise<void>;
  restore(snapshot: MemorySnapshot): Promise<void>;
  metrics(): Promise<MemoryMetrics>;
}
```

可选扩展包括 `mask`（遮蔽）、`clone`（克隆）、`export`（导出）、`traceInfluence`（影响追踪）以及 `retrieveTrace`（检索轨迹追溯）。

黑盒系统在不实现该接口的情况下依然可以正常参加常规评测。

---

# 29. 消融控制器（Ablation Controller）

支持的消融控制手段（按干预精度从高到低排序）：

```text
1. 精准记录删除 / 遮蔽（exact record deletion/masking）
2. 记忆快照分支重置（memory snapshot branching）
3. 过滤历史事件后克隆记忆状态（cloned memory with filtered past）
4. 排除特定事件后从头重放（replay excluding selected events）
5. 黑盒场景端到端重构执行（black-box scenario reconstruction）
```

评测报告必须披露所使用的消融方法，因消融手段的控制精度会直接影响因果推断的严格程度。

---

# 30. 基准对照线（Baselines）

MIB 设置以下标准对照线：

```text
Agent + 参评记忆系统（Agent + Memory）
Agent + 全量可见上下文（Agent + Full Relevant Context）
Agent + 无记忆系统（Agent + No Memory）
```

“全量上下文”对照线有助于厘清是记忆系统出现缺陷，还是基座模型本身缺乏推理能力；“无记忆”对照线则确立了仅凭当前上下文信息所能达到的性能下界。

---

# 31. 多层评测器体系（Evaluator Hierarchy）

评测判定优先级由高到低依次为：

```text
1. 确定性规则评测器（Deterministic evaluator）
2. 环境状态评测器（World-state evaluator）
3. 结构化语义约束评测器（Structured semantic constraints）
4. 行为轨迹评测器（Trajectory evaluator）
5. LLM 裁判评测器（LLM judge）
```

LLM 裁判仅作为兜底辅助手段，不作为首选的真实判定基准。

确定性判定示例：

```text
预期时区 = "+01:00"
选定认证方式 = "session"
严禁调用已废弃接口
承诺触发条件已满足
```

环境状态判定示例包括服务是否真实部署成功、数据库目标是否正确配置、提醒是否成功送达、是否避免了已知有害动作等。

结构化自然语言约束可明确指定 `must_include`、`must_not_include` 以及允许的不确定性表述。

轨迹评测可检查智能体在行动前是否执行了前置条件校验、在迁移技能前是否参考了已知反例等。

---

# 32. LLM 裁判规范（LLM Judge Policy）

当必须引入 LLM 裁判时：

1. 必须公开裁判大模型的具体版本；
2. 温度（temperature）参数应设为 0 或极低值以保证确定性；
3. 必须使用结构化评分细则（Rubric）；
4. 可采用多重抽样评判求均值；
5. 榜单关键分数应附带置信区间；
6. 任何情况下，确定性的环境客观真值判定均高于裁判模型的主观意见。

---

# 33. MIB 主得分体系

默认加权计算方式：

\[
MIB = \sum_i w_i s_i
\]

其中各维度得分 $s_i \in [0,100]$，且 $\sum w_i = 1$。

v1 推荐权重配置：

```text
保留与检索（Retention & Retrieval）       0.12
时序记忆（Temporal Memory）               0.13
认识状态记忆（Epistemic Memory）          0.15
经验记忆（Experience Memory）             0.15
技能学习与迁移（Skill Learning & Transfer） 0.15
选择性遗忘（Selective Forgetting）        0.10
前瞻与自我记忆（Prospective & Self Memory） 0.08
因果记忆效应（Causal Memory Impact）       0.12
```

发布综合得分时必须同时列出各子维度的明细得分。

---

# 34. 安全与病态防范惩罚（Guardrail Penalties）

对于严重的记忆病态缺陷，应设置有上限的显式扣分机制，避免其被平均分掩盖。

典型违规模式：

```text
凭空捏造高置信度虚假记忆
陈旧记忆屡次导致破坏性操作
记忆引发虚假权限幻觉
私有隐藏记忆发生越权泄露
灾难性实体身份混淆
```

惩罚细则必须保持透明并纳入版本化管理。

---

# 35. 评测能力卡片（Capability Card）

标准评估输出报告示例：

```text
Memory Intelligence Benchmark（记忆智能基准报告）
────────────────────────────────────────

系统信息
  智能体：    Example Agent + Memory X
  基座模型：  Model Y
  参赛赛道：  赛道 A —— 记忆系统
  评测规模：  MIB-M

MIB 综合得分
  78.6 / 100

能力维度剖面
  保留与检索（Retention & Retrieval）        91
  时序记忆（Temporal Memory）              84
  认识状态记忆（Epistemic Memory）         62
  经验记忆（Experience Memory）            81
  技能学习与迁移（Skill Learning & Transfer）74
  选择性遗忘（Selective Forgetting）        69
  前瞻与自我记忆（Prospective & Self Memory） 76
  因果记忆效应（Causal Memory Impact）     82

因果分析指标
  记忆收益（Memory Benefit）              +28.4%
  记忆损害（Memory Harm）                   5.2%
  净记忆增益（Net Memory Gain）           +23.2%
  已知错误重现率（Known Error Recurrence）  11.0%
  负迁移率（Negative Transfer）             8.0%
  陈旧记忆采纳率（Stale Memory Adoption）   14.0%
```

---

# 36. 系统效率指标

系统开销与效率指标独立于记忆智能得分进行统计与呈现。

推荐统计项：

```text
单有效事件写入次数（writes / meaningful event）
千事件存储字节占用（storage bytes / 1k events）
检索延迟 p50 / p95（retrieval latency）
端到端任务总耗时（end-to-end task latency）
单任务上下文注入 Token 量（tokens injected / task）
记忆形成阶段消耗的大模型 Token 数
检索召回阶段消耗的大模型 Token 数
千事件综合成本估算（cost / 1k events）
写入放大倍数（write amplification）
长期维护与整理开销（maintenance cost）
```

能力表现与资源成本属于不同维度的度量。

---

# 37. 可复现性保障

每次基准运行均应完整记录以下元数据：

```text
场景定义版本
场景随机种子
世界模拟器版本
智能体版本
大模型版本
Prompt 哈希
记忆系统版本
工具集版本
裁判模型版本
运行时间戳
```

针对非确定性系统，MIB 要求进行多轮重复运行，并给出均值、中位数、标准差及置信区间。

---

# 38. 防刷榜机制（Anti-Gaming）

基准必须预先防范针对评测特性的针对性优化与作弊行为。

防御手段包括：

```text
隐藏场景实例化生成
未来探针延迟采样
实体名称与数值随机化
语义同义改写
多模板交叉组合
动态注入干扰噪音
环境状态随机扰动
未公开的反例测试
配对因果消融验证
```

适配器接口严禁向智能体透传任何隐藏的标签或真值。

---

# 39. 记忆投毒与对抗鲁棒性

MIB 包含对抗性与有害记忆的测试用例：

```text
陈旧错误事实干扰
记忆中夹带恶意指令
已废弃失效的操作流程
不可信信源提供的内容
跨情境越权声称具备效力的技能
虚假的自传体经历声明
重复摘要引发的虚假放大
```

系统应能够在善用有效记忆的同时，坚决避免对记忆内容的盲从。

---

# 40. 隐私安全与数据隔离边界

后续 MIB Profile 可扩展测试记忆是否在跨用户、跨会话、跨工作区、跨角色、跨 Agent 或跨私有/公开边界时发生越权泄露。

隐私安全性应当作为专门的 Safety Profile 或独立得分进行列报，严禁混入基础检索得分中。

---

# 41. 跨智能体记忆协同（Cross-Agent Memory）

未来场景可支持评测跨 Agent 经验共享：

```text
Agent A 的经验轨迹
→ 沉淀为共享 / 导入记忆
→ 供 Agent B 消费
```

核心检验点：

```text
Agent B 能否有效从 A 的经验中汲取技能？
Agent B 是否清晰保留了该经验的信源出处？
Agent B 是否避免了将 A 的经历误认作自身经历？
Agent B 是否避免了越权继承 A 的操作权限？
```

---

# 42. 多模态记忆（Multimodal Memory）

MIB 具有模态中立性。输入观测类型未来可平滑扩展至文本、图像、音频、视频、屏幕截屏、传感器流与空间轨迹数据。

无论模态如何变化，评测的核心逻辑始终如一：

```text
观察到了什么？
发生了什么？
学到了什么？
应该如何影响未来的决策与行为？
```

---

# 43. MIB 与 KIP 的关系澄清

MIB 与 KIP 属于职责明确分离的两个项目：

```text
KIP 协议符合性
  关注：
  实现是否严格遵循了 KIP 协议的交互语义与规范？

MIB
  关注：
  智能体所展现出的记忆智能水平到底有多高？
```

基于 KIP 的实现如果在记忆管理上表现不佳，在 MIB 上同样可能得低分；非 KIP 系统只要行为优秀，在 MIB 上完全可以夺得高分。这种评测的独立性是刻意设计的。

原生支持 KIP 的适配器可以更便捷地导出 KQL/KML/META、BELIEF、HISTORY、证据链、经验胶囊与技能快照等高级诊断数据，但这些并非参与 MIB 基础评测的强制要求。

---

# 44. 跨维度综合场景

最具评测价值的往往是融汇多项能力的综合场景。

示例：

```text
用户提出偏好
→ 随后更正了偏好
→ 经历长周期的无关干扰信息
→ 未来行动决策依赖于最新偏好
→ 历史追溯提问考察最初的偏好
→ 触发关键记忆消融重放
```

该场景同时检验了保留检索、时序演进、认识纠错、行动引导、历史留存及因果效应。

MIB 不应演变为孤立细碎微型测试的简单拼盘。

---

# 45. 难度度量模型

场景的客观难度由以下可控参数决定：

```text
时序时间跨度
干扰项总数
交互实体数量
多跳关联深度
信源歧义程度
冲突复杂度
经验轨迹长度
技能抽象跨度
反例区分难度
提问探针的隐式程度
```

难度等级应当基于受控属性量化生成，而非仅凭主观标签标注。

---

# 46. 失败模式分类体系（Failure Taxonomy）

MIB 针对失败案例进行结构化归因分类：

```text
记忆形成遗漏（formation miss）
检索召回失败（retrieval miss）
实体匹配错误（identity mismatch）
采纳陈旧过时记忆（stale-memory adoption）
信源混淆归错（source confusion）
纠错信息丢失（correction loss）
对未知妄加确定（false certainty）
经验轨迹断裂（trajectory collapse）
技能未能成功迁移（Skill non-transfer）
发生负迁移（negative transfer）
忽略已知反例（counterexample neglect）
承诺未能触发兑现（commitment miss）
自我认知漂移（self-model drift）
虚假记忆幻觉（memory hallucination）
无关噪音干扰（irrelevant-memory interference）
权限界限混淆（authority confusion）
```

这使得评测基准能够切实为工程研发优化提供精准诊断，而不仅仅用于排名。

---

# 47. 记忆链路端到端诊断

当接入可选诊断适配器时，MIB 可对记忆全生命周期的各阶段进行分段定位：

```text
信息是否被观测到了？
信息是否被成功写入存储？
信息是否完成了必要的结构化转换？
信息是否被长期稳固保留？
信息在理论上是否可被索引检索？
信息在实际中是否被成功召回？
召回的信息是否影响了智能体的决策？
该影响是否产生了正确的行为结果？
```

诊断分析链路：

```text
观测（Observe） → 存储（Store） → 保留（Retain） → 检索（Retrieve） → 影响（Influence） → 结果（Outcome）
```

不同环节的失败对应着完全不同的工程改进方向。

---

# 48. 黑盒智能体的因果评测方案

对于完全黑盒的智能体系统，依然可以通过对照重放来完成严格的因果评估：

```text
运行 A： 供给全量历史
运行 B： 供给剔除了关键相关片段的历史
运行 C： 供给剔除了无关片段的历史
运行 D： 供给额外注入了陈旧/误导陷阱的历史
```

这确保了 MIB 评测在任何情况下都能保持真正的架构中立性。

---

# 49. 领域 Profile 规划

未来可拓展的垂直领域 Profile 包括：

```text
MIB-Assistant（通用个人助理）
MIB-Coding（软件工程与代码研发）
MIB-Research（科学探索与学术研究）
MIB-Enterprise（企业知识管理与业务协同）
MIB-Companion（长效情感陪伴）
MIB-Robotics（具身智能与机器人控制）
MIB-Multimodal（多模态感知理解）
```

领域 Profile 可增设专属任务套件，但跨系统横向对比仍依赖统一的 MIB-Core 核心基准。

---

# 50. MIB v0.1 参考发布范围

首个落地版本保持精简聚焦：

```text
MIB-Recall（检索与保留）
MIB-Time（时序记忆）
MIB-Belief（认识与信念记忆）
MIB-Experience（经验记忆）
MIB-Skill（技能学习）
MIB-Causal（因果效应验证）
```

这六大套件已足以将简单的存储检索与深度的时序、认识、经验、技能以及因果可用记忆明确区分开来。

v0.1 的目标规模约为 60 个标准场景模板：

```text
检索与保留（Recall）      10
时序记忆（Time）          10
认识状态（Belief）        10
经验记忆（Experience）     8
技能学习（Skill）          8
因果效应（Causal）         8
跨维度综合（Cross-suite）  6
─────────────────────────────
总计                      60
```

每个模板均支持多个隐藏的随机化实例化变体。

---

# 51. 规范与机器可读产物

MIB 规范与实现仓库包含以下核心组成：

```text
MIB-Architecture.md（架构设计总则）

schemas/
  mib-scenario.schema.json（场景 Schema）
  mib-run.schema.json（运行记录 Schema）
  mib-observation.schema.json（观测数据 Schema）
  mib-agent-output.schema.json（智能体输出 Schema）
  mib-report.schema.json（评测报告 Schema）
  mib-capability-card.schema.json（能力卡片 Schema）

adapters/
  MIB-Agent-Adapter.md（Agent 适配器规范）
  MIB-Memory-Adapter.md（Memory 诊断适配器规范）

scenarios/
  recall/
  time/
  epistemic/
  experience/
  skill/
  causal/

runner/
  reference implementation（参考 Runner 实现）

evaluators/
  deterministic/（确定性评测器）
  world-state/（环境状态评测器）
  semantic/（结构化语义评测器）
  trajectory/（执行轨迹评测器）

leaderboard/
  policy.md（排行榜治理规范）
```

---

# 52. 评测运行产物（Run Artifact）

每次基准评测运行都必须生成一份机器可读的结构化报告产物，包含：

```text
参评系统身份与版本
参赛赛道
评测规模
套件版本
运行环境配置
随机数种子清单
场景级逐项得分
维度综合得分
因果度量指标
资源效率指标
运行告警日志
裁判模型元数据
```

该产物应具备独立审计与校验能力。

---

# 53. 排行榜公正性准则

申请加入官方排行榜的提交必须满足：提供可复现的适配器、明确声明基座模型与记忆系统版本、声明外部依赖服务、锁定环境配置、提供完整运行产物并通过隐藏评测集的自动化验证。

对于商业闭源系统，评测服务可在沙箱环境中托管运行提交的适配器，而无需向参赛方透露隐藏场景的内容。

---

# 54. 版本演进与治理

MIB 采用严格的版本控制规范：

```text
MIB 0.1
MIB 0.2
MIB 1.0
```

未定义明确归一化方案的前提下，不同主版本的得分严禁直接进行横向比较。

公开治理机制涵盖场景准入、权重调整、裁判演进、排行榜规则、防数据污染、废弃场景淘汰、安全漏洞披露与申诉仲裁流程。

---

# 55. MIB 赋能的研究课题

MIB 既是公信力排行榜，更是深入探索记忆智能前沿的科研工具。

典型研究问题：

```text
结构化情景记忆能否提升技能的跨领域迁移效果？
时序记忆建模能否有效降低执行陈旧动作的错误率？
文本摘要机制在提升检索率的同时，是否显著削弱了信源归属精度？
知识图谱记忆是否有助于复杂多跳关联推理？
选择性遗忘机制在多大程度上能够提升最终决策动作的质量？
在何种条件下，过往记忆更容易引发负迁移？
大模型基座升级后，记忆系统带来的净增益有多少能够得以保持？
记忆系统的性能收益与资源成本之间的帕累托最优前沿在哪里？
```

---

# 56. 能力与效率的帕累托前沿

MIB 倡导采用多维帕累托分析呈现系统表现：

```text
MIB 综合得分 vs 资源成本
MIB 综合得分 vs 响应延迟
因果记忆收益 vs 存储空间
技能迁移成功率 vs 记忆写入开销
```

避免使用简单的单一成本折算分数掩盖架构之间的核心权衡。

---

# 57. 最低限度记忆智能体判定

一个具备**最低限度记忆智能**的智能体应当能够做到：

```text
记住关键事实
更新已改变的事实
保留重要历史脉络
避免将未知信息断言为假
准确记住信源发言主体
能够从部分实际经验中学习
避免重复发生已知教训的失败
在未来决策中利用好相关过往信息
在合适时机忽略无关历史噪音
```

而一个**高水平记忆智能体**还应进一步具备：

```text
习得可泛化迁移的技能
敏锐辨识并利用反例
稳固兑现前瞻承诺
维持清晰一致的自我能力认知
有效抵御陈旧与投毒记忆
完整维护证据链与信源溯源
在操作层面实现精准的选择性遗忘
在对照实验中展现出强劲的因果记忆收益
```

---

# 58. 架构设计不变量（Architectural Invariants）

1. **检索召回不等于记忆智能。**
2. **静态存储不等于具备功能的认知记忆。**
3. **未来探针绝不能在记忆形成阶段泄漏。**
4. **相关记忆必须能够因果性地提升未来表现。**
5. **无关记忆对系统表现的影响应接近于零。**
6. **系统必须具备抵御有害或陈旧记忆的能力。**
7. **未知状态绝不能被强行断言为确定性的假。**
8. **认知纠错绝不能粗暴破坏对历史事实的理解。**
9. **当前状态与历史状态必须能够被分别独立测试。**
10. **信源存在分歧时，来源归属至关重要。**
11. **多次重复生成的摘要不能构成相互独立的证据源。**
12. **孤立事件召回与完整经验轨迹召回存在本质区别。**
13. **单次成功的经验不能直接等同于通用技能。**
14. **技能迁移测试必须包含适用性边界检验。**
15. **负迁移必须可被量化检测。**
16. **遗忘并不必然等同于物理删除。**
17. **前瞻记忆是记忆智能不可或缺的组成部分。**
18. **自我认知记忆绝不能虚构出系统未被授予的权限。**
19. **能力表现与资源效率是相互独立的度量轴。**
20. **配对因果消融是高置信度记忆评测的核心支柱。**
21. **MIB 必须始终保持架构中立。**
22. **KIP 协议符合性与 MIB 记忆智能得分彼此独立。**
23. **确定性与环境状态评测优先于大模型主观裁判。**
24. **隐藏随机化评测是保障排行榜权威性的必要条件。**
25. **评测结果应当能够深入诊断系统失败模式，而非单纯输出排名。**

---

# 59. MIB 核心原则总结

MIB 的精髓可以凝练为一句话：

> **MIB 评测的不是智能体记住了多少，而是它能否智能地运用记忆。**

更精确地表达：

> **评估记忆系统的优劣，不在于它能检索出多少过往信息，而在于过往经历中正确的部分能否以正确的方式改变未来的决策。**

这就是 MIB 的架构立论之本。

---

# 附录 A —— 概念模型图

```text
                过往世界（PAST）
                     │
                     ▼
            ┌─────────────────┐
            │   观测输入      │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   记忆形成      │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   记忆状态      │
            └────────┬────────┘
                     │
            ┌────────┴────────┐
            │                 │
            ▼                 ▼
        记忆巩固          记忆修正
            │                 │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   回忆检索      │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   未来决策      │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   行为执行      │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   环境产出      │
            └────────┬────────┘
                     │
                     └───────────────↺
```

MIB 评测的是整条认知闭环，而非其中的单一环节。

---

# 附录 B —— 能力卡片示例

```text
MIB — Memory Intelligence Benchmark
════════════════════════════════════════

系统概览
  智能体：    Example Agent
  记忆系统：  Memory X
  基座模型：  Model Y
  参赛赛道：  赛道 A —— 记忆系统
  评测规模：  MIB-M

MIB 综合得分
  78.6 / 100

能力维度明细
  保留与检索（Retention & Retrieval）        91
  时序记忆（Temporal Memory）              84
  认识状态记忆（Epistemic Memory）         62
  经验记忆（Experience Memory）            81
  技能学习（Skill Learning）               74
  选择性遗忘（Selective Forgetting）        69
  前瞻与自我记忆（Prospective & Self Memory） 76
  因果记忆效应（Causal Memory Impact）     82

因果分析指标
  记忆收益（Memory Benefit）              +28.4%
  记忆损害（Memory Harm）                   5.2%
  净记忆增益（Net Memory Gain）           +23.2%
  负迁移率（Negative Transfer）             8.0%
  已知错误重现率（Known Error Recurrence）  11.0%
```

---

# 附录 C —— 推荐配套规范清单

建议依照以下顺序阅读相关技术规范：

```text
1. MIB-Scenario-Model.md（场景模型规范）
2. mib-scenario.schema.json（场景 Schema）
3. MIB-Agent-Adapter.md（Agent 适配器协议）
4. MIB-Scoring.md（计分与统计方法）
5. mib-report.schema.json（评测报告 Schema）
6. MIB-v0.1-Test-Plan.md（v0.1 测试与校准计划）
7. 官方标准场景包（Canonical Scenario Pack）
8. 参考 Runner 实现（Reference Runner）
```

首期实现里程碑应优先攻克：

```text
场景生命周期执行
未来探针严格隔离
黑盒 Agent 适配接入
世界模拟器交互
确定性计分逻辑
基于重放的对照消融
能力卡片自动生成
```

为后续构建公共评测排行榜奠定扎实基础。
