# MIB 评测服务工程说明

**适用范围：** 排行榜 / 评测服务（Leaderboard / Evaluation Service）

MIB 评测服务将隐藏评测执行器封装为常驻服务，提供外部智能体注册、评测任务冻结与签名、隐藏周期评测执行、结果认证证明出具、排行榜维护以及基于配对统计学的系统显著性对比等能力。

---

## 1. 整体架构

```text
提交注册中心（Submission Registry）
        ↓
当前激活的隐藏评测周期（Active Hidden Evaluation Cycle）
        ↓
已签名的 Ed25519 任务清单（Job Manifest）
        ↓
按后端路由的 Worker 队列（Backend-routed Worker Queue）
        ↓
沙箱化外部智能体（Sandboxed External Agent）
        ↓
MIB 隐藏黑盒评测执行（MIB Hidden Evaluation）
        ↓
内部完整报告 + 公开脱敏报告（Internal + Public Reports）
        ↓
Ed25519 评测结果证明（Result Attestation）
        ↓
SQLite 排行榜数据库（SQLite Leaderboard）
        ↓
配对系统统计学显著性比对（Paired System Comparison）
```

Runner 执行引擎、场景包调度器与隐藏评测器已完整内置并全部通过回归测试。

---

## 2. 核心系统能力

- SQLite 提交 / 周期 / 任务 / 结果持久化注册表；
- 评测周期的受控激活与生命周期隔离；
- 不可变任务清单（Job Manifest），密码学绑定提交、存储、Profile、Scenario Schema 与 Report Schema 哈希摘要；
- Ed25519 任务清单数字签名；
- 基于 HMAC 密钥在评测端确定性具象化隐藏实例；
- 单任务常驻 stdio Agent 进程，各条件执行前通过全新 `run_id` 显式重置隔离；
- 按后端类型路由 Worker（已实现并测试 `local_namespace`；保留 OCI 与 microVM 路由标识）；
- 公开脱敏报告与内部完整报告产物存储库；
- Ed25519 服务级结果认证证明（Result Attestation）；
- 第三方无需服务私钥即可公开核验证明签名；
- 评测周期级作用域的官方排行榜；
- 配对分层 Bootstrap 系统显著性比对；
- 本地 HTTP 服务 API；
- 单节点队列 Worker 崩溃自动恢复管理。

完整信任模型与服务规范请参阅 [MIB-Leaderboard-Evaluation-Service.md](../MIB-Leaderboard-Evaluation-Service.md)。

---

## 平台前置条件

评测服务通过参考提交沙箱执行参赛方提供的 stdio 提交，其隔离能力依赖 Linux 非特权
用户 / 挂载 / 网络命名空间（`unshare`）。因此所有会拉起提交进程的命令——
`register-submission`（除非指定 `--no-smoke`）、`worker-once` 以及
`POST /worker/once` 接口——要求运行环境满足：

```text
Linux
可用的非特权 user / mount / network 命名空间
PATH 中存在 `unshare`
```

macOS 与 Windows 上不存在上述命名空间隔离，地址空间限额也无法生效，禁止在这些平台上
执行上述命令：未隔离的提交进程将获得完整的宿主机网络与文件系统可见性。其余服务命令
（`init`、`register-cycle`、`activate-cycle`、`enqueue`、`job`、`jobs`、`leaderboard`、
`compare`、`verify-result`、`verify-attestation-file`、`serve`）不拉起提交进程，跨平台可用；
`mib` 的 `validate`、`run`、`run-pack`、`benchmark`、`capability-card`、`verify-score`
同样跨平台可用。

---

## 3. 环境安装

```bash
python -m pip install --no-build-isolation -e .
```

依赖组件：

```text
jsonschema >= 4.18
cryptography >= 46
```

---

## 4. 服务配置

参考开发配置文件位于：

```text
examples/service/service-config.json
```

该配置中的相对路径以配置文件自身所在目录为基准解析：五个 Schema 条目指向仓库
`schemas/` 目录，运行期状态写入仓库根目录下的 `service/state/` 与 `service/artifacts/`。
这两个运行期目录已被 gitignore，首次使用时自动创建。`mib-service` 的 `--config` 默认值为
`service/service-config.json`，全新克隆的仓库中并不存在该文件，因此需显式传入
`--config examples/service/service-config.json`，或将该文件复制到自有部署位置。

通过环境变量注入服务根私钥：

```bash
export MIB_SERVICE_ROOT_SECRET='use-a-real-secret-manager-in-production'
```

根私钥用于派生隐藏实例生成、报告脱敏、任务签名与结果签名的独立密钥，服务数据库严禁明文持久化根私钥。

---

## 5. 初始化与服务身份核验

```bash
mib-service --config examples/service/service-config.json init
```

执行后输出公开 Ed25519 公钥及 `key_id`，用于通过可信发布渠道锚定可信公钥。

---

## 6. 注册 Agent 提交规范

```bash
mib-service --config examples/service/service-config.json register-submission \
  examples/submissions/reference-stdio.json \
  --name 'Reference Fixture'
```

同时内置一个刻意无记忆的测试桩：

```text
examples/submissions/no-memory-stdio.json
```

仅用于校验排行榜对记忆系统的区分度。

---

## 7. 注册并激活隐藏评测周期

```bash
mib-service --config examples/service/service-config.json register-cycle \
  cycle-m5-demo-001 \
  --store fixtures/private-eval-store-demo \
  --profile profiles/MIB-Core-0.1-Hidden-M4-Demo.json \
  --activate
```

---

## 8. 任务入队与 Worker 执行

```bash
mib-service --config examples/service/service-config.json enqueue mib-reference-fixture-stdio
mib-service --config examples/service/service-config.json worker-once
```

任务在入队时被数字签名。Worker 在执行前若发现 Submission、私有题库或 Profile 配置与签名清单不一致，将拒绝执行。

---

## 9. 查看排行榜

```bash
mib-service --config examples/service/service-config.json leaderboard
```

---

## 10. 配对显著性比对

```bash
mib-service --config examples/service/service-config.json compare \
  result_A result_B \
  --resamples 5000
```

在相同隐藏评测周期下，服务对两系统在同一模糊化场景实例上的表现进行严格配对 Bootstrap 重采样。

---

## 11. 校验评测结果与签名

服务端内部核验：

```bash
mib-service --config examples/service/service-config.json verify-result result_xxx
```

第三方完全公开离线核验（无需服务密钥）：

```bash
mib-service verify-attestation-file \
  service/artifacts/job_xxx/result-attestation.json \
  --public-report service/artifacts/job_xxx/public.report.json \
  --expected-key-id ed25519:...
```

---

## 12. HTTP 服务 API 接口

```bash
mib-service --config examples/service/service-config.json serve \
  --host 127.0.0.1 \
  --port 8088
```

参考端点：

```text
GET  /health
GET  /submissions
GET  /cycles
GET  /jobs
GET  /leaderboard
POST /submissions
POST /jobs
POST /worker/once
POST /compare
```

---

## 13. 执行后端就绪状态

```text
local_namespace   已完整实现并测试通过
oci_command       已预留路由协议接口
microvm_command   已预留路由协议接口
```

当前参考环境未安装 Docker / Podman / Firecracker，因此不声明已完成 OCI 或 microVM 的实机验证。

---

## 14. 自动化回归测试

```bash
PYTHONPATH=src python -m pytest tests -q
```

其中需要拉起沙箱提交进程的服务测试在非 Linux 宿主机上会自动跳过。

---

## 15. 安全边界说明

结果签名属于**服务级证明（Service Attestation）**，证明该结果确由指定公钥背书且紧密绑定报告哈希，不代表底层硬件 TEE 证明。
