# MIB v0.1 校准框架与基线套件说明

本模块为 36 个官方 `MIB-Core-0.1` 隐藏评测集（Hidden Eval）与私有保留集（Private Holdout）场景模板提供评测端实证校准机制。

---

## 1. 核心功能

```text
B0 — 完全无记忆基线（No Memory）
B1 — 完美可见历史测试桩基线（Full Visible History Fixture）
B2 — 简单词法检索基线（Simple Lexical Retrieval / RAG）
B3 — 结构化/智能体高级记忆基线（Structured / Agentic Memory）
        ↓
生成模板校准卡片（Template Calibration Cards）
        ↓
FC / NM / MDI 核心指标
MGC_B2 / MGC_B3 记忆差距弥合率
基线间区分跨度（Baseline separation）
因果干预敏感性（Causal sensitivity）
无关记忆稳定性（Irrelevant stability）
        ↓
输出准入通过 / 待修订 / 需重新设计处置队列
```

核心源码实现位于：

```text
src/mib_runner/calibration.py
src/mib_runner/calibration_baselines.py
src/mib_runner/calibration_cli.py
```

---

## 2. 关键状态边界声明

内置的 B0~B3 实现属于**确定性参考测试桩（Reference Fixtures）**。

其主要价值在于：
- 验证校准调度流水线逻辑闭环；
- 提前探测无记忆作弊与信息泄漏；
- 检验简单关键词检索能否轻易解题；
- 检验消融重放的因果敏感性；
- 产出清晰的场景修订优化清单。

上述测试桩**不足以直接作为正式榜单发布的最终校准凭证**，因为 B1 尚未接入赛道 A 统一绑定的外部固定大模型。

因此生成的报告中显式声明：

```text
release_calibration_eligible = false
```

---

## 3. 官方私有题库包

校准框架不重复内置官方评测模板的具体定义，执行时需指向私有存储目录：

```text
MIB-v0.1-Official-Canonical-Pack-PRIVATE/
```

该私有目录绝对严禁对外公开发布。

---

## 4. 运行参考校准

```bash
./run-reference-calibration.sh /path/to/MIB-v0.1-Official-Canonical-Pack-PRIVATE
```

或直接调用 Python CLI：

```bash
PYTHONPATH=src python -m mib_runner.calibration_cli \
  /path/to/private-pack \
  --schema schemas/mib-scenario.schema.json \
  --profile profiles/MIB-Core-0.1.json \
  --seeds 101,202,303,404 \
  --bootstrap-resamples 2000 \
  --output-json examples/calibration/calibration.json \
  --output-md examples/calibration/calibration.md \
  --output-csv examples/calibration/calibration.csv
```

---

## 5. 将测试桩 B1 替换为真实固定模型 Agent

```bash
mib-calibrate ... \
  --baseline-override B1=my_eval_package:FixedModelFullContextAgent
```

替换后的 Agent 通过标准 MIB Agent Adapter 接口交互，并需如实声明其校准角色。

---

## 6. 参考运行统计

参考基准运行配置：
- 36 个官方模板
- 每个模板生成 4 个具象化隐藏实例
- 4 套全量基线条件
- 1 轮 B3 因果消融重放
- 每模板基线统计量执行 2000 次 Bootstrap 重采样

执行运行总场次：
- B0~B3 全量运行：576 场
- B3 因果消融运行：684 场
- **总计：1260 场**

---

## 7. 自动化测试

```bash
PYTHONPATH=src pytest -q
```

预期通过结果：

```text
32 passed
```
