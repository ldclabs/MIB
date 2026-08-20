# MIB 隐藏评测基础设施工程说明

**适用范围：** 隐藏黑盒评测基础设施、延迟采样探针机制、外部智能体传输协议与提交沙箱隔离。

隐藏黑盒评测层将场景包执行引擎升级为**具备严格防泄密边界的评测服务**，能够在绝对不泄露隐藏题库与客观判决真值的前提下，安全调度并评测外部长期记忆智能体。

---

## 1. 系统拓扑

```text
私有隐藏评测存储库（Private Evaluation Store）
        ↓
HMAC 隐藏实例确定性生成器（HMAC Hidden Instance Generator）
        ↓
延迟采样探针机制（late / hidden_late Probe Sampling）
        ↓
外部智能体适配器（External Agent Adapter）
   ├── stdio JSONL 通道
   └── HTTP JSON 通道
        ↓
提交沙箱隔离系统（Submission Sandbox）
        ↓
评测执行 / 配对消融 / Bootstrap 统计推断
        ↓
内部完整报告（Internal Report）
        ↓
公开脱敏报告（Public Redacted Report）
        ↓
离线重算核验（verify-score）
```

---

## 2. 私有评测存储库（Private Evaluation Store）

评测端专属的隐藏题库独立存放于公开代码库之外。

参考结构目录：

```text
private-eval-store-demo/
├── manifest.private.json
└── templates/
    ├── hidden/
    └── holdout/
```

支持两类可见性级别：
- **`hidden_eval`（隐藏评测集）：** 所属能力大类与测试原理可公开披露；
- **`private_holdout`（私有保留集）：** 结构组成、生成器算法、裁判真值与探针变体完全保密。

通过命令 `mib public-eval-manifest` 可自动派生出不含私有路径与保留集细节的安全公开清单。

---

## 3. 基于 HMAC 的确定性隐藏实例生成

隐藏测试实例由以下派生算法确定性生成：

```text
HMAC-SHA256(
  evaluator_key,
  cycle_id + template_id + instance_index
)
```

真实生成随机种子绝对不得传递给智能体或暴露在公开报告中。

公开报告仅展示模糊化的不透明别名，例如：

```text
hs_dcd0faa610141950
```

核心特性：
- 相同的评测密钥 + 周期 ID + 模板 ID + 实例索引 $\rightarrow$ 逐字节完全可复现；
- 评测周期轮换 $\rightarrow$ 自动生成全新的一组隐藏实例；
- 参赛方无法反推真实的生成种子。

---

## 4. 延迟采样探针机制（late / hidden_late）

探针可声明多个面向智能体的同义输入句式变体：

```json
{
  "extensions": {
    "mib.probe_sampling": {
      "input_variants": [
        {"content": "我现在处于哪个时区？"},
        {"content": "为我安排会议应使用哪个时区？"}
      ]
    }
  }
}
```

Runner 仅在**探针实际触发的瞬间**才确定性采样具体提问。采样种子严格由场景实例、重复轮次与探针 ID 派生，且刻意**不包含消融条件标签**。因此全量组与各消融变体将接收到完全相同的提问词面。

`hidden_late` 进一步支持将变体候选集合本身完全置于私有存储中。

---

## 5. 外部 stdio Agent 适配器

标准 stdio 交互协议：

```text
stdin  → 每行一条 JSON 请求
stdout → 每行一条 JSON 响应
stderr → 仅限输出本地诊断日志
```

核心支持操作：`describe`、`reset`、`observe`、`respond`、`act`、`close`。

冒烟测试指令：

```bash
PYTHONPATH=src python -m mib_runner.cli agent-smoke-test \
  --submission examples/submissions/reference-stdio.json
```

---

## 6. 外部 HTTP Agent 适配器

标准 REST 端点：

```text
GET  /mib-agent/v0.1/describe
POST /mib-agent/v0.1/reset
POST /mib-agent/v0.1/observe
POST /mib-agent/v0.1/respond
POST /mib-agent/v0.1/act
POST /mib-agent/v0.1/close
```

启动本地 HTTP 参考测试桩并测试：

```bash
python examples/agents/http_reference_agent.py --port 8765

PYTHONPATH=src python -m mib_runner.cli agent-smoke-test \
  --submission examples/submissions/reference-http.json
```

---

## 7. 提交沙箱隔离系统（Submission Sandbox）

在具备非特权用户命名空间支持的 Linux 宿主机上，本地沙箱提供：
- User / Mount / Network 命名空间强隔离；
- 系统资源配额限制；
- 干净的白名单环境变量；
- 临时工作目录与代码暂存（Staging）；
- **私有评测路径物理遮蔽（私有挂载命名空间下通过 tmpfs 覆盖隐藏）**；
- 进程组级彻底回收与清理。

报告中如实记录实际隔离生效状态：

```json
{
  "submission_sandbox": {
    "transport": "stdio",
    "network_isolated": true,
    "filesystem_isolated": true,
    "warnings": []
  }
}
```

---

## 8. 提交代码工作区暂存（Staging）

由于评测服务私有目录对子进程物理不可见，参赛提交所需的代码首先被拷贝至隔离的临时工作区中执行。评测端的私有题目文件绝不会被暂存或挂载给智能体。

---

## 9. 隐藏黑盒评测 CLI 命令

```bash
export MIB_EVAL_KEY='replace-with-evaluator-secret'

PYTHONPATH=src python -m mib_runner.cli evaluate-hidden \
  private-eval-store-demo \
  --profile profiles/MIB-Core-0.1-Hidden-M4-Demo.json \
  --submission examples/submissions/reference-stdio.json \
  --schema schemas/mib-scenario.schema.json \
  --report-schema schemas/mib-report.schema.json \
  --cycle cycle-2026-08 \
  --bootstrap-resamples 200 \
  --output-internal internal-report.json \
  --output-public public-report.json \
  --card capability-card.md
```

---

## 10. 内部完整报告 vs 公开脱敏报告

- **内部报告（Internal Report）：** 完整保留私有模板 ID、生成种子、真实文件路径等调试排障信息；
- **公开报告（Public Report）：** 彻底剥离单次运行详细流水、私有种子、私有文件路径与消融内部 ID，仅保留聚合得分、模糊化模板别名、维度得分、因果指标、Bootstrap 置信区间与沙箱隔离记录。

公开报告完全满足以下离线重算核验：

```bash
mib verify-score public-report.json
```

---

## 11. 安全与防泄密边界总结

智能体仅能接收到：
- 属于公开可见范围的环境观测（Observation）
- 虚拟时钟时间戳
- 当前探针的任务目标与即时约束
- 可用工具的接口 Schema

智能体**绝对无法接触到**：私有模板定义、裁判真值（Oracle）、评测器配置、能力维度权重、消融与相关性内部标签、隐藏世界真值、实例生成种子与私有探针句式集合。
