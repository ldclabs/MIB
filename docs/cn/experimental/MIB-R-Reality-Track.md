# MIB-R —— 现实任务评测轨（Reality Track）

## 记忆智能基准（MIB）面向真实外部任务环境的评测规范

[ [English](../../experimental/MIB-R-Reality-Track.md) | 简体中文 ]

**版本：** 0.1-draft  
**状态：** 原型规范 / `MIB-Transfer-Intelligence.md` 配套规范  
**评测 Profile：** `MIB-R-0.1-Dev` —— **非官方基准（not official）**

---

# 0. 规范目标

MIB-Core 是一个受到严格控制的人工合成因果实验室。它在评测方完全掌控的理想环境中，确证了记忆干预对未来行为决策的改变效力。但它自身无法确证的是：这种记忆智能在与复杂的真实任务碰撞时能否依然存续。

MIB-R 核心追问：

> 过去经历能否因果性地改善在共享可验证程序性支持的真实保留测试任务上的表现？

MIB-R **绝不是** MIB-Core 的替代品，它也不是一个通用的智能体性能基准。它的核心贡献不在于任务本身——市面上已有大量包含真实任务的基准。它的核心贡献在于：所有的执行条件保持严格成对配对，唯有记忆状态发生变化。

---

# 1. 核心不可变原则

## 1.1 与 MIB-Core 严格解耦

MIB-R 拥有专用的 Profile ID、专用的结果族（`reality`）以及独立的排行榜界面。排行榜查询**严禁（MUST NOT）**生成跨结果族混合排名的榜单，跨结果族的成对配对对比将被直接拒绝，而非进行模糊近似。

## 1.2 不设立官方统一总分

在 v0.1-Dev 版本中，刻意不设立官方统一的 MIB-R Score。上游各个基准的分值量纲互不兼容，过早在单一算术平均值下掩盖各领域的具体行为，会彻底抹杀该评测轨本应产出的诊断信息。若未来的规范拟引入总分，必须显式定义并说明其归一化规则。

## 1.3 原型阶段定位

`MIB-R-0.1-Dev` 属于原型设计。通过 §9 中的验收准则并不意味着它成为官方基准，**严禁（MUST NOT）**进行此类误导性宣传。

## 1.4 迁移图谱纯属评测方私密

现实迁移图谱（Reality Transfer Graph）在官方评测期间**严禁（MUST NOT）**对参赛者公开。在面对多次反复提交时，迁移图谱极易遭受自适应的逆向工程破解。

## 1.5 严禁未授权重新分发第三方数据

MIB 仅存储上游任务的标识符、不可变版本号和内容哈希摘要。在版权许可不允许再分发的情况下，MIB 仅保留 ID、摘要和本地配置指引。

---

# 2. 实验结构设计

```text
阶段 A —— 经验获取（Experience acquisition）
    训练任务（Train Task）
        ↓
    Agent 在真实环境中执行操作
        ↓
    动作轨迹（Trajectory）
        ↓
    校验器判决结果（Verifier result）
        ↓
    经验 / 技能形成（Experience / Skill formation）

阶段 B —— 保留测试迁移（Held-out transfer）
    相关的测试任务（Related Test Task）
        ↓
    相同的基座 Agent / 模型 / 工具集
        ↓
    记忆条件发生变化
        ↓
    校验器打分（Verifier score）
```

获取阶段属于真实演练：Agent 尝试解决训练任务，校验器进行判决，判决结果——以及失败时由审核者给出的修正反馈——作为观察事件回传给 Agent。正是这一过程将记忆塑造成真正的“亲历经验（Experience）”，而非单纯的文本资料堆砌。

---

# 3. 配对测试条件

```text
no_memory                    完全不经历训练任务获取阶段
natural_memory               经历完整的训练获取；代表实际部署行为
relevant_ability_ablated     经历训练获取，但剔除了对当前被测能力的支撑部分
irrelevant_ability_ablated   经历训练获取，但剔除了等量与目标任务无关的过往经历
wrong_ability_injected       经历完整训练获取，并注入合理但错误的过度泛化经验

可选配置：
oracle_skill                 扣留自然支撑，将标准的真值产物放入记忆库中
oracle_routing               扣留自然支撑，在任务执行时刻将标准真值产物推送至上下文
```

所有测试条件**必须（MUST）**在以下维度保持严格配对：

```text
相同的源任务集
相同的目标任务
相同的运行环境版本
相同的 Agent
相同的基座模型
相同的工具集
相同的超时时限
在支持的情况下保持相同的任务随机种子
相同的校验器
```

彼此之间仅允许记忆或知识演化状态发生改变。这是 MIB 特有的核心贡献。

## 3.1 无关对照组必须保持绝对无关

一条迁移边声明两组任务集：

```text
source_task_ids   支撑该关系所指能力的任务集
causal_task_ids   目标任务正确答案所实际依赖的全部训练任务集
```

在正向迁移边上，二者通常重合。但在**拟真（near-match）**边上，二者截然不同：被指明的某项能力恰恰是必须被*扣留*的，而目标任务依然依赖于其他正确管辖它的知识。无关对照组仅从 `causal_task_ids` 之外的任务中抽样，确保“无关”绝不会隐蔽地变成“关键支柱”。

当现存的非关键任务数量少于相关消融所扣留的任务量时，这两个条件在规模和内容上均会产生失衡。此时报告会发出 `reality.ablation_magnitude_mismatch` 警告，绝不将弱对照粉饰为纯净对照。

---

# 4. 现实迁移图谱（Reality Transfer Graph）

由评测方私密维护的任务与能力关联图谱：

```text
训练任务-17 ──支撑──►  能力-A
训练任务-29 ──支撑──►  能力-A

能力-A ──适用于──► 测试任务-42

能力-A ──拟真但不适用──► 测试任务-51

能力-A + 能力-B ──组合支撑──► 测试任务-77
```

核心构成要素：

```text
任务节点（Task nodes）
能力节点（Ability nodes）
支撑边（Support edges）
不适用边（Non-applicability edges）
组合边（Composition edges）
```

每条边承载与 `MIB-Transfer-Intelligence.md` 完全相同的关系分类法，使得正向距离阶梯 `D0`–`D3` 与负向对照组在两个评测轨中具有完全等价的语义。

## 4.1 引用消解

公开发布的数据包仅携带：

```json
{
  "transfer_graph": {
    "private_ref": "graph.evaluator.json",
    "digest": "sha256:..."
  }
}
```

该引用路径相对于数据包根目录进行消解；若配置了环境变量 `MIB_REALITY_GRAPH_ROOT`，则优先基于该路径消解，使得公开数据包能够引用仅存在于评测方私有环境中的图谱文件。摘要不匹配属于严重错误：静默修改图谱将导致所有成对配对的比较基准发生偏移。

---

# 5. 现实任务清单（Reality Task Manifest）

```json
{
  "task_id": "external:benchmark:task-42",
  "source_benchmark": "example-benchmark",
  "source_revision": "immutable-revision-or-digest",
  "content_digest": "sha256:...",
  "verifier": "upstream"
}
```

适配器将 `task_id` 解析为任务实际内容并校验其摘要。环境版本的微小漂移将直接报错中断，防止其悄然改变对比基准。

---

# 6. 现实任务适配器（Reality Task Adapter）

```python
class RealityTaskAdapter(Protocol):
    def describe(self) -> dict: ...
    def load_task(self, task_ref: dict) -> dict: ...
    def run_task(self, task, agent, *, run_id, seed, request_id) -> dict: ...
    def normalize_score(self, result: dict) -> float: ...
    def collect_trajectory(self, result: dict) -> list[dict]: ...
```

参考实现采用同步调用风格，与 `types.py` 中的进程内 Agent Adapter 保持一致。基于 HTTP 或容器化的适配器可在其传输层边界采用异步实现，而不违背该接口契约。

适配器还须提供 `feedback(task, result, *, score)` 方法：产出校验器判决，并在失败时产出审核者修正意见。这正是阶段 A 转化为记忆经验的源泉。

---

# 7. 诊断指标体系

仅用于深度诊断：

```text
条件得分                  每个配对条件各产出一个分值
自然迁移收益              natural_memory - no_memory
相关消融差值              natural_memory - relevant_ability_ablated
无关记忆稳定性            1 - |natural_memory - irrelevant_ability_ablated|
记忆危害                  max(0, natural_memory - wrong_ability_injected)
真值技能收益              oracle_skill - no_memory
真值路由收益              oracle_routing - no_memory

负迁移率
受支持迁移成功率
拟真抵抗度
未支持记忆中立度

按距离等级划分的迁移收益
按业务领域划分的迁移收益

工具调用 / 交互轮次 / 延迟 / 成本差异
```

所有差值指标均为**带符号数值**。对于存在过度泛化倾向的系统，移除它本不该使用的记忆反而会*提升*其表现；取绝对值会彻底掩盖 MIB-R 设立的核心发现。

置信区间采用任务级别的配对 Bootstrap 分析，保留每个目标任务完整的条件集合。

---

# 8. 负向对照组

仅包含正向迁移的基准无法区分“真正能提供帮助的系统”与“盲目滥用经验停不下来的系统”。因此 MIB-R 强制要求包含：

```text
受支持迁移（Supported Transfer）
拟真不适用（Near-Match Non-Applicable）
未支持全新任务（Unsupported Novel）
陈旧废弃能力（Stale Ability）
有害错误能力（Harmful Ability）
组合式能力（Compositional Ability）
```

一套优良的记忆系统，不仅要在存在支持时展现出辅助效果，更要在缺乏支持或不适用时保持克制中立。毫无记忆的系统在记忆中立度上得满分而在迁移上得零分；过度泛化的系统在迁移上得高分而在适用边界上彻底溃败。孤立看待任何单一指标均毫无意义。

---

# 9. 真实有效性校准

在正式接纳一条现实迁移边之前：

```text
训练阶段的能力支撑
        ↓
真值技能 + 真值路由
        ↓
必须在目标测试任务上带来可衡量的性能提升
```

若真值技能仍无法改善目标任务的表现，说明该迁移边缺乏实证支撑，绝不可作为正向迁移基准案例。`minimum_effect` 门槛在完成先行测试校准后针对各个外部基准分别确定。

切勿假设人工标注的能力只要听起来合理就一定有效。参考领域中声明的每一项约定规范均经过严格检验，确认其具有决定性因果支撑：省略该项规范必然会导致答案出错。

---

# 10. 报告呈现与公开脱敏

推荐的公开结果发布策略：

```text
即时公开项：
  整体领域得分
  聚合层面的迁移指标
  聚合层面的距离画像
  密码学认证签名

延期公开 / 严格保密项：
  单个任务的具体得分
  单项具体能力的得分
  具体的支撑关联
  具体的错误技能失误细节
```

公开呈现版本会剔除逐任务明细行、逐关系明细块，图谱摘要中除计数和哈希外全部剥离。在托管评测服务周期内，建议进一步缩减逐任务的公开反馈粒度。

## 10.1 结果认证签名（Attestation）

MIB-R 结果签名将现实数据包摘要、评测方私有迁移图谱摘要、环境适配器身份、测试条件集合以及内部和公开两份报告的哈希进行强绑定。签名**不包含综合分**：MIB-R 没有官方统一总分，在签名中臆造总分会违背避免混合排名的隔离初衷。其签名上下文与核心评测服务严格隔离，确保现实轨签名绝无法被伪造回放为 MIB-Core 官方得分。

---

# 11. 领域选型考量

首批接入 MIB-R 的候选业务领域应当具备：

```text
确定性或极高质素的客观校验器
可控的运行耗时
清晰明确的程序性复用价值
较低的外部数据版权许可复杂度
```

算法编程或受控的网络检索任务是理想的首选起点。在 Reality 抽象层稳定成熟之前，尽量避免直接从需要完整容器集群编排的 SWE-Bench 级规模起步。

`MIB-R-0.1-Dev` 的核心宗旨是验证迁移干预方法学，而非追求任务的表面声望。

---

# 12. 参考领域实现 —— 分类账编码（Ledger Codes）

`reality/MIB-R-Demo-LedgerCodes/` 附带了一个确定性的算法推理领域：包含 23 个训练获取任务和 12 个保留测试任务，配备本地确定性校验器，完整覆盖 `D0`–`D3` 以及拟真和未支持对照组。

四项隐式规则支配着编码计算，它们不会出现在任务提示中，只能通过失败后的修正反馈习得：

```text
A1  在执行计算前必须归一化标识符
A2  标准族编码采用模 97 计算
A3  历史遗留族保持模 100 计算          （A2 的适用边界）
A4  前导的 CK 是校验标识符，不是数值项
```

完全未学得任何约定的系统无法生成有效编码，必须明确弃权说明，从而使未支持对照成为纯粹的中立度测量而非靠猜测蒙对。若系统将 A2 规则滥用到其适用边界之外，会在遗留族记录上给出自信的错误答案，从而使拟真对照成为精准的陷阱。

该领域属于**参考领域实现**，而非外部真实基准，不分发任何第三方版权数据。它的存在是为了确保本方法学在开源代码库中具备可复现性。真实的生态现实效度（ecological validity）依赖于后续通过相同适配器契约接入真实的外部上游基准。

---

# 13. 执行命令范例

```bash
mib reality-benchmark reality/MIB-R-Demo-LedgerCodes/pack.json   --profile profiles/MIB-R-0.1-Dev.json   --pack-schema schemas/mib-reality-pack.schema.json   --agent mib_runner.experimental.reality_fixtures:RuleLearningRealityAgent   --bootstrap-resamples 2000   --output-report reality-internal.json   --output-public reality-public.json   --output-attestation reality-attestation.json   --card reality-card.md
```

`--submission` 参数可通过与核心隐藏评测相同的沙箱隔离传输协议运行外部 Agent 提交。

---

# 14. 原型验收检查清单

```text
[x] 一个真实的领域适配器
[x] >= 20 个训练获取任务
[x] >= 10 个保留测试任务
[x] 评测方私有的现实迁移图谱
[x] 受支持 + 拟真 + 未支持关联类型
[x] 外部校验器无缝集成
[x] 自然 / 无记忆 / 相关消融 / 无关消融对照组
[x] 成对配对执行
[x] 结果数字签名认证
[x] 公开报告脱敏处理
[x] 绝不与 MIB-Core 混合排名
```

满足上述各项并不意味着 MIB-R 成为官方基准。后续工作仍侧重于提升生态效度：接入真实的外部基准、理顺版权授权，并在真实基座模型上进行实证的边有效性校准。

---

# 15. 三层体系最终定位

```text
MIB-Core
────────────────────────────────────
过往经历中的哪些部分
正确参与了未来的认知与行为计算？

MIB 迁移诊断（Transfer Diagnostics）
────────────────────────────────────
过往经历是如何一步步
沉淀转化为未来行动能力的？

MIB-R
────────────────────────────────────
同一种记忆智能在真实的
外部任务世界中能否依然存续？
```

> 记忆的真正智能，不在于记得更多，而在于让正确的过往——且唯有正确的过往——塑造未来。
