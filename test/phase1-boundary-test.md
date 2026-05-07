# Phase 1：通信与边界测试

**测试日期**：2026-05-07  
**测试目标**：验证 Airflow MCP agent 能否通过 REST API 完成基本的 DAG 触发、状态轮询、日志诊断，并明确 API 的能力边界。  
**MCP Server**：`mcp-server-apache-airflow`（yangkyeongmo），原生支持 Airflow 2.x Basic Auth  
**Airflow 版本**：2.9.3（Docker Compose）

---

## 环境说明

- 5 个测试 DAG 均为手动触发（`schedule_interval=null`），无调度周期
- 所有 DAG 在测试开始时均处于 `is_active=true`、`is_paused=false` 状态
- 测试并行执行：5 个 subagent 同时触发各自的 DAG

---

## 场景 1：Happy Path

**DAG**：`happy_path`  
**目标**：验证正常流程下的触发→轮询→成功

| 字段 | 值 |
|---|---|
| DAG Run ID | `manual__2026-05-07T09:56:27.844396+00:00` |
| 最终状态 | **success** |
| start_date | 2026-05-07 09:56:28.597 UTC |
| end_date | 2026-05-07 09:56:31.749 UTC |
| 执行耗时 | **3.15 秒** |
| 触发到完成 | ~4 秒（含调度延迟） |

**结论**：DAG 一次性成功，调度延迟极低，Happy Path 验证通过。

---

## 场景 2：简单失败 + 日志诊断

**DAG**：`failure_simple`  
**目标**：触发已知失败 DAG，通过日志定位根因

| 字段 | 值 |
|---|---|
| 失败 Task | `fail_task`（PythonOperator） |
| 最终状态 | **failed** |
| 执行耗时 | ~0.14 秒（瞬间失败） |
| 重试次数 | 0（`max_tries=0`） |

**错误信息**：
```
ValueError: Simulated failure: upstream data source unavailable
  File "/opt/airflow/dags/failure_simple.py", line 6, in run_task
```

**根因**：`run_task` 函数硬编码 `raise ValueError(...)`，是 POC 的刻意设计，非真实上游问题。

**是否值得重试**：否。确定性失败（deterministic failure），代码不修改则每次结果相同，需修复 DAG 代码后重新触发。

---

## 场景 3：重试耗尽归因

**DAG**：`failure_with_retry`  
**目标**：观察重试过程，分析多次重试的错误一致性

| 字段 | 值 |
|---|---|
| Task | `flaky_task`（PythonOperator） |
| 最终状态 | **failed** |
| 配置重试次数 | 3（共执行 4 次） |
| 总耗时 | ~17 秒 |
| 重试间隔 | ~5-6 秒 |

**各次重试情况**：

| 尝试 | 时间戳 (UTC) | 错误 | 结果 |
|---|---|---|---|
| 1/4 | 21:40:36.897 | ConnectionError | up_for_retry |
| 2/4 | 21:40:42.777 | ConnectionError | up_for_retry |
| 3/4 | 21:40:48.003 | ConnectionError | up_for_retry |
| 4/4 | 21:40:53.339 | ConnectionError | **failed** |

**错误信息**（4 次完全一致）：
```
ConnectionError: External API timeout: connection refused after 30s
  File "/opt/airflow/dags/failure_with_retry.py", line 8, in run_task
```

**根因**：外部 API 持续不可达（connection refused），非瞬时抖动，所有重试错误 100% 一致。

**建议**：立即人工介入。检查外部 API 是否在线、网络连通性、认证配置。服务恢复后手动 clear 重跑。不建议继续自动重试（应区分 `ConnectionError` 与 `TimeoutError`，前者不应重试）。

---

## 场景 4：上游失败 + 下游 upstream_failed 追溯

**DAG**：`upstream_downstream`  
**目标**：追溯依赖链，理解上游失败对下游的影响

| Task | State | 耗时 |
|---|---|---|
| task_a | **success** | 0.118s |
| task_b | **failed** | 0.072s |
| task_c | **upstream_failed** | 0s（未执行） |

**task_b 失败原因**：
```
RuntimeError: task_b: Transformation failed — schema mismatch in column 'event_ts'
  File "/opt/airflow/dags/upstream_downstream.py", line 9, in task_b_fn
```

**依赖链分析**：
```
task_a ──► task_b ──► task_c
(success)  (failed)   (upstream_failed，未被调度)
```

task_c 未执行的原因：默认触发规则 `trigger_rule=ALL_SUCCESS`，task_b 失败后调度器直接将 task_c 置为 `upstream_failed`，从未派发给 worker（`try_number=0`，`pid=null`）。

**修复建议**：
1. 修复 `event_ts` 列的 schema 映射逻辑
2. 从 task_b 开始 clear 重跑即可，task_a 无需重跑

---

## 场景 5：诊断边界显式测试

**DAG**：`long_running`  
**目标**：明确 Airflow REST API / MCP 的信息边界

### 我能看到的（API 可提供）

| 信息 | 获取方式 |
|---|---|
| task 状态（queued/running/failed/success） | `get_task_instance` |
| start_date、已运行时长 | `get_task_instance` |
| 运行 worker 的 hostname | `get_task_instance.hostname` |
| Worker 进程 PID | `get_task_instance.pid` |
| 日志内容（已写入部分，支持增量拉取） | `get_log` + continuation_token |
| XCom 数据（若 task 主动写入） | `get_xcom_entries` |
| 历史 run 的 duration（用于判断是否异常耗时） | `get_dag_runs` |
| 调度器最后决策时间 | `get_dag_run.last_scheduling_decision` |

### 我看不到的（API 不提供）

| 信息 | 原因 |
|---|---|
| 任务内部执行进度（%） | 无 progress 字段，除非代码主动写 XCom |
| Worker CPU/内存/I/O 使用率 | API 只暴露控制平面，不暴露数据平面 |
| 任务是否真在推进（vs 卡死） | `state=running` 无法区分执行中和卡死 |
| Celery 队列积压情况 | 需 Celery Flower 或命令行 |
| K8s Pod 事件（OOMKill、Eviction 等） | 需 kubectl |
| 网络 I/O 和外部依赖状态 | 需 lsof/strace |

### 怀疑任务卡死时的排查路径

1. 通过 `get_task_instance` 获取 `hostname` 和 `pid`
2. `docker logs airflow-worker -f`（本环境为 Docker Compose）
3. `celery inspect active`（若使用 CeleryExecutor）
4. `ps/top -p <pid>` → `lsof -p <pid>` 查网络连接
5. 确认卡死后通过 `patch_task_instance(state=failed)` 终止，再重新触发

---

## 总结

| 场景 | 结论 |
|---|---|
| 1 Happy Path | MCP 触发→轮询→成功链路完全可用 |
| 2 简单失败 | 日志诊断能力完整，根因可定位到代码行 |
| 3 重试耗尽 | try_number 变化可追踪，多次日志可对比 |
| 4 依赖追溯 | task instance 状态枚举完整，upstream_failed 可追溯 |
| 5 边界测试 | API 提供控制平面信息，进度/资源需基础设施层工具 |

**整体结论**：Airflow MCP agent 能够完成标准的运维操作（触发、轮询、诊断、日志分析），但对于"任务是否真的在正常推进"这类深度可观测性问题，需要结合 worker 层工具才能回答。

---

## 遗留问题与修复

测试过程中发现并修复了一个代理兼容性 bug：  
原 `airflow-proxy.py` 转发 `POST /dags/*/dagRuns` 时未过滤 body 中的 `dag_id` 字段，Airflow 2.9.3 将其视为 read-only 并返回 HTTP 400。已在代理层添加过滤逻辑。

**注**：后续已切换至 `mcp-server-apache-airflow`（yangkyeongmo），原生支持 Airflow 2.x Basic Auth，不再需要代理。
