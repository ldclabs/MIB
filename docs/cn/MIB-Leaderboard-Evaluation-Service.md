# MIB 排行榜与评测服务规范

**版本：** 0.5.0  
**状态：** 参考评测服务原型规范

---

## 1. 架构目标

评测服务将隐藏评测执行器封装为常驻持久化服务，具备以下标准链路：

```text
提交注册中心（Submission Registry）
        ↓
评测周期注册中心（Evaluation Cycle Registry）
        ↓
已签名的评测任务清单（Signed Evaluation Job）
        ↓
按执行后端路由的 Worker 队列（Backend-routed Worker Queue）
        ↓
隐藏黑盒评测执行（Hidden Evaluation）
        ↓
已签名的结果认证证明（Signed Result Attestation）
        ↓
排行榜数据库（Leaderboard Database）
        ↓
配对系统统计学显著性对比（Paired System Comparison）
```

该服务在架构上完全独立于各家记忆系统的内部细节。任何受测系统依然仅通过标准 MIB Agent Adapter 接入参评。

---

## 2. 持久化数据模型

SQLite 参考数据库维护四大核心实体对象：

```text
Submission  （提交记录）
Cycle       （评测周期）
Job         （评测任务）
Result      （评测结果）
```

### 提交记录（Submission）

绑定全局唯一的提交 ID，包含：

```text
Agent Adapter 配置规范
规范文件哈希摘要（Spec digest）
系统显示名称
所有者标识
参评赛道（Track）
当前状态
可选的适配器能力描述符
```

在 Worker 启动执行前，系统会重新计算原始提交规范的哈希摘要并严格比对，彻底杜绝参赛方在入队后静默替换二进制或配置文件的作弊行为。

### 评测周期（Evaluation Cycle）

评测周期绑定：

```text
周期唯一 ID（Cycle ID）
评测 Profile
私有隐藏评测数据存储目录（Private Evaluation Store）
数据存储目录哈希摘要
Profile 哈希摘要
面向公众的安全评测清单
活跃 / 已退役状态（Active / Retired）
```

**唯有在相同评测周期下生成的评测结果，才具备直接在排行榜上横向排名的资格。**

激活新周期将自动使同一 Profile 下的前序活跃周期退役归档。

### 评测任务（Evaluation Job）

Job 并非单纯的可变队列行记录。在入队时，服务会生成一份**不可变的签名清单（Manifest）**，包含：

```text
任务唯一 ID（Job ID）
提交 ID（Submission ID）
提交规范哈希摘要
周期 ID（Cycle ID）
Profile ID
私有存储哈希摘要
Profile 哈希摘要
Scenario Schema 哈希摘要
Report Schema 哈希摘要
指定执行后端（Execution backend）
Runner 版本
创建时间戳
防重放随机数（Nonce）
```

该清单使用专属的 **Ed25519 Job 签名私钥** 进行数字签名。Worker 在启动隐藏评测前，必须先行校验该签名及所有绑定的产物哈希。

### 评测结果（Result）

评测成功后固化入库：

```text
综合主得分（MIB Score）
95% 置信区间
内部完整报告路径 + 哈希摘要
公开脱敏报告路径 + 哈希摘要
服务结果证明签名（Service Result Attestation）
Ed25519 数字签名
```

---

## 3. 密钥隔离体系

服务由唯一的**服务根私钥（Root Secret）**通过派生函数生成相互隔离的专用密码学材料：

```text
根私钥 (Root Secret)
   ├── HMAC 评测实例随机种子派生密钥
   ├── HMAC 公开报告脱敏密钥
   ├── Ed25519 任务清单签名密钥
   └── Ed25519 评测结果证明签名密钥
```

根私钥通过环境变量注入，严禁写入数据库或明文报告中。

生产环境部署应当接入 KMS/HSM 硬件安全模块或专业密钥管理系统，避免直接使用进程环境变量。

---

## 4. 公开可验证签名

采用 Ed25519 算法生成公开可验证的非对称数字签名，保障结果防篡改：

```json
{
  "scheme": "ed25519",
  "context": "mib-service-result-attestation/v1",
  "payload_digest": "sha256:...",
  "signature": "...",
  "public_key": "...",
  "key_id": "ed25519:..."
}
```

任何第三方在无需获取服务端私钥的前提下，均可使用公开公钥完成数学签名的离线核验。

可信度建立在通过官方仓库或域名信任链锚定官方 MIB Evaluation Service 公钥或 `key_id` 的基础之上。

---

## 5. 服务级证明（Service Attestation） vs 硬件级证明

当前 Result 对象明确界定为**服务级证明（service_attestation）**：

> 官方 MIB 评测服务基于密码学签名正式背书：该 Result 确系由签名的 Job 清单与所列报告摘要真实执行产出。

该证明**不代表**：

```text
硬件安全证明（Hardware attestation）
可信执行环境证明（TEE attestation）
机密计算证明（Confidential-computing proof）
MicroVM 启动度量证明（MicroVM measurement proof）
```

未来演进的高级后端可将上述底层证明扩展放入 `backend_evidence` 字段中，无需破坏顶层 Result 数据模型。

---

## 6. 执行后端路由机制

任务清单支持声明多种执行后端：

```text
local_namespace   本地沙箱命名空间
oci_command       OCI 容器沙箱
microvm_command   MicroVM 微虚拟机沙箱
```

参考 Worker 默认实现基于提交沙箱的 `local_namespace` 后端。

队列支持后端路由分发：Worker 仅认领与自身后端类型匹配的任务。这允许未来平滑接入 OCI 容器或 Firecracker microVM 集群 Worker，复用统一的注册表与任务协议。

---

## 7. 常驻 stdio 智能体进程模式

在服务化环境下，若为每个场景条件反复冷启动子进程会带来不必要的系统开销。

服务支持常驻 stdio 传输通道：

```text
单次评测任务（Job）对应单个沙箱化的 Agent Host 常驻进程
        ↓
使用隔离的 run_id 命名空间区分多次运行
        ↓
在全量条件与各消融变体执行前显式下发重置（reset）
```

在保障认知状态完全隔离的前提下，避免重复拉起进程。整个场景包评测完毕后统一回收进程。

---

## 8. Worker 崩溃恢复机制

Worker 将任务状态流转为：`queued → running`。

管理后台提供恢复指令：

```text
recover-running
```

能够自动重置因 Worker 异常崩溃而滞留在 `running` 状态的任务。分布式生产环境应进一步升级为租约过期（Lease Expiry）、心跳探活与幂等提交机制。

---

## 9. 隐藏评测全流程

```text
接收签名 Job
   ↓ 校验 Ed25519 签名
核验 Submission 哈希摘要
核验 Store 题库哈希摘要
核验 Profile 配置哈希摘要
   ↓
基于 HMAC 密钥确定性具象化场景实例
   ↓
在沙箱环境中驱动外部 Agent
   ↓
执行全量及配对消融实验
   ↓
执行模板与维度分层聚合
   ↓
计算 Bootstrap 统计置信区间
   ↓
输出内部完整报告（Internal Report）
   ↓
基于公开规则执行数据脱敏
   ↓
执行离线 verify-score 重算校验
```

只有当脱敏后的公开报告通过完整的得分重算核验时，Result 才被正式提交固化入库。

---

## 10. 结果证明签名（Result Attestation）

签名的 Result Attestation 紧密绑定：

```text
Result ID
Job ID
Job Manifest 哈希摘要
Submission ID
Cycle ID
Profile ID
MIB Score 综合得分
公开报告 SHA-256 摘要
内部报告 SHA-256 摘要
执行后端类型
后端执行证据
评测启动与完成时间戳
```

评测结束后若篡改任一份报告的任何字节，均会导致校验彻底失效。

---

## 11. 排行榜排名语义

官方排行榜规则：

> 选取每个 Submission 在当前激活的评测周期（Cycle）内**最新的一次成功 Result**；

排序规则：

```text
按 MIB Score 降序排列
```

每条排行榜条目必须完整展示：

```text
综合主得分 (MIB Score)
95% 置信区间
Result ID
公开报告下载链接
Result Attestation 数字签名
```

不同评测周期的得分严禁混排。

---

## 12. 配对系统统计学显著性比对

简单的排名高低不等于具备统计学显著性差异。

当两个系统在同一个隐藏评测周期下完成评测时，其公开报告保留了能够一一对应的模糊化场景实例别名（Alias）。

服务支持执行**配对分层 Bootstrap**：

```text
模板层（Template）
  ↓
配对实例层（Paired Instance）
```

在严格共享相同隐藏实例的前提下分析两系统差异。输出包括：

```text
MIB Score 综合分差值
配对 95% 置信区间
配对模板总数
配对实例总数
各能力维度分差
统计显著性判定标识（statistically_distinguishable）
```

当综合分差值的 95% 置信区间包含 0 时，官方明确标明“统计上无显著差异”。

---

## 13. HTTP 服务 API 接口

参考端点设计：

```text
GET  /health              健康检查
GET  /submissions         查询提交列表
GET  /cycles              查询评测周期列表
GET  /jobs                查询任务列表
GET  /jobs/{job_id}       查询单任务详情
GET  /leaderboard         获取当前榜单

POST /submissions         注册新提交
POST /jobs                任务入队
POST /worker/once         单步触发 Worker 执行
POST /compare             比对两个评测结果的显著性
```

参考 API 专为本地开发与内网基础设施设计，生产环境需增补多租户认证鉴权、限流与对象存储直传能力。

---

## 14. 命令行工具（CLI）

```bash
# 初始化评测数据库与密钥体系
mib-service init

# 注册新的 Agent 提交规范
mib-service register-submission submission.json

# 注册并激活新的评测周期
mib-service register-cycle cycle-2026-08 \
  --store /private/mib-eval-store \
  --profile MIB-Core-0.1.json \
  --activate

# 任务入队并触发 Worker
mib-service enqueue my-agent
mib-service worker-once

# 查看当前周期排行榜
mib-service leaderboard

# 校验本地结果与签名
mib-service verify-result result_xxx

# 对比两个系统结果的显著性
mib-service compare result_A result_B \
  --resamples 5000
```

第三方无需服务密钥即可完全公开核验签名：

```bash
mib-service verify-attestation-file \
  result-attestation.json \
  --public-report public.report.json \
  --expected-key-id ed25519:...
```

---

## 15. 完整信任链条

```text
可信 MIB 服务公钥
        ↓
已签名的 Job 清单（Job Manifest）
        ↓
不可变的 Submission / 题库 / Profile 哈希摘要
        ↓
隐藏评测周期受控执行
        ↓
沙箱环境驱动 Agent
        ↓
可重算核验的公开报告（Public Report）
        ↓
报告 SHA-256 摘要
        ↓
已签名的结果证明（Result Attestation）
        ↓
排行榜官方条目
```

该信任链并不宣称评测题目完美无瑕，但它在数学上严格证明了：**发布的每一个得分条目究竟是由哪份基准定义、哪个评测周期和哪台认证服务真实执行产出的。**

---

## 16. 生产化演进规划

当前原型在迈向大规模多租户生产环境时需增补：

```text
多租户账号与鉴权体系
云端对象存储（S3/GCS）集成
KMS/HSM 密钥托管
分布式 Worker 租约心跳与自动重试
OCI 容器隔离后端落地
MicroVM 微虚拟机硬隔离后端落地
HTTP 提交的网络沙箱策略管控
多节点分布式任务队列
API 调用限流与提交配额
官方规范场景包的签名分发
公钥定期轮换机制
面向公众的现代化排行榜 Web 前端
```
