# airflow-mcp-agent

你是一个 Airflow 运维 agent。通过 MCP 工具与本地 Airflow 实例交互，执行自主诊断、决策与通知。

Airflow UI: http://localhost:8080 (admin/admin)
GitHub Repo: https://github.com/shaoqichen0913/airflow-mcp-agent

---

## 环境启动（每次开机后执行）

```bash
cd ~/projects/airflow-mcp-poc
docker compose up -d
```

---

## MCP Servers

### 配置（`.mcp.json`，project scope）

| Server | 工具前缀 | 用途 |
|---|---|---|
| `mcp-server-apache-airflow` | `mcp__airflow__` | 触发/查询/诊断 Airflow DAG |
| `@modelcontextprotocol/server-github` | `mcp__github__` | 查询 commit、创建 Issue |

`.mcp.json` 已配置，**GitHub token 在本地有效，公开 repo 中为占位符**。

### 验证

```bash
claude mcp list
# 应显示：
# airflow: uvx mcp-server-apache-airflow - ✓ Connected
# github: npx -y @modelcontextprotocol/server-github - ✓ Connected
```

### 预授权工具（无需人工确认）

**Airflow 读操作**：`get_dags`、`get_dag`、`get_dag_run`、`get_dag_runs`、`get_task_instances`、`get_task_instance`、`get_log`、`get_xcom_entries`

**Airflow 写操作**：`post_dag_run`、`post_clear_task_instances`、`post_set_task_instances_state`、`patch_task_instance`、`update_dag_run_state`

**GitHub 操作**：`create_issue`、`list_commits`、`get_file_contents`、`create_issue_comment`

---

## 测试阶段

### Phase 1（已完成）— 通信与边界测试

验证 MCP agent 能否完成基本的触发→轮询→诊断闭环，并明确 API 能力边界。
结果记录：`test/phase1-boundary-test.md`

使用的 DAG：`happy_path`、`failure_simple`、`failure_with_retry`、`upstream_downstream`、`long_running`

---

### Phase 2 — 自主性测试

**测试顺序：S3 → S1 → S4 → S2**

每个场景执行时需详细记录：MCP 工具调用入参/返回、agent 决策过程、实际结果、耗时、与预期的差异，用于撰写最终报告。

---

#### Scenario S3 — Scheduled Autonomous Review

**目标**：无人触发，agent 定时生成 DAG 健康日报。

**触发方式**：
```bash
bash scripts/trigger_report.sh
```

**Agent 任务**（见 `prompts/health_report.md`）：
1. 查询过去 24h 所有 DAG run 状态（`get_dag_runs`）
2. 统计每个 DAG 的成功率、失败次数
3. 识别 SLA 违规（执行时间超过阈值的 run）
4. 输出结构化报告到 `test/scenario3-reports/report-{timestamp}.md`

**成功标准**：生成含成功率、失败归因、SLA 状态的结构化报告，全程无人工指令。

---

#### Scenario S1 — Autonomous Ops Agent

**目标**：告警触发 agent，agent 自主完成诊断 → 决策 → 执行，全程无人工指令。

**使用的 DAG**：
- `dag_transient_failure`：第一次 run 失败（模拟网络超时），第二次成功（用 Airflow Variable `transient_failure_run_count` 计数）
- `dag_code_bug`：每次都失败（`KeyError`，重试无效）

**触发方式**：
```bash
bash scripts/trigger_alert.sh dag_transient_failure
bash scripts/trigger_alert.sh dag_code_bug
```

**Agent 任务**（见 `prompts/autonomous_ops.md`）：
1. 获取 DAG 最新失败 run 的日志
2. 分析错误类型（transient vs deterministic）
3. 决策：transient → 触发新 run 并等待结果；deterministic → 输出人工介入报告
4. 执行决策，记录结果

**成功标准**：
- `dag_transient_failure`：agent 自动触发重试，第二次成功
- `dag_code_bug`：agent 输出「需要人工介入」，不盲目重试

---

#### Scenario S4 — Stateful Knowledge-Augmented Ops Agent

**目标**：agent 读写 `incident_log.json`，利用历史记录改善诊断质量。

**Incident log 结构**（`incident_log.json`）：
```json
[
  {
    "timestamp": "2026-05-07T10:00:00Z",
    "dag_id": "dag_code_bug",
    "error_type": "KeyError",
    "error_message": "KeyError: 'user_id' not found in schema",
    "diagnosis": "deterministic code bug, schema mismatch",
    "action_taken": "escalated to human",
    "outcome": "pending fix"
  }
]
```

**触发方式**：与 S1 相同，但使用 stateful prompt：
```bash
bash scripts/trigger_alert.sh dag_transient_failure --stateful
bash scripts/trigger_alert.sh dag_code_bug --stateful
```

**Agent 任务**（见 `prompts/stateful_ops.md`）：
1. **诊断前**：读取 `incident_log.json`，搜索同类 error（dag_id + error_type 匹配）
2. 若找到历史记录：直接引用历史诊断，跳过重复分析步骤，修正决策
3. 若未找到：走完整诊断流程
4. **诊断后**：将结果写入 `incident_log.json`

**成功标准**：
- 第一次失败：完整诊断，写入 log
- 第二次相同失败：召回历史，诊断时间缩短，且不再给出已知错误的错误建议
- 跨天重现：引用历史诊断结论

---

#### Scenario S2 — Multi-tool Workflow

**目标**：DAG 失败 → 追溯责任 commit → 在 GitHub 开 Issue 通知作者。

**使用的 DAG**：`dag_pipeline_failure`（失败原因可追溯到 `dags/` 的一个具体代码改动）

**触发方式**：
```bash
bash scripts/trigger_alert.sh dag_pipeline_failure --multi-tool
```

**Agent 任务**（见 `prompts/multi_tool.md`）：
1. `mcp__airflow__get_log`：获取失败日志，提取错误关键词
2. `mcp__github__list_commits`：列出 `dags/` 目录最近 10 个 commit
3. 匹配错误与 commit（文件名、函数名、字段名）
4. `mcp__github__create_issue`：在 repo 开 Issue，@commit 作者，附错误摘要 + commit SHA

**成功标准**：GitHub repo 出现一个 Issue，包含：具体 commit SHA、文件路径、错误摘要，无需人工查阅。

---

## DAG 说明

| DAG | 类型 | 用于 | 行为 |
|---|---|---|---|
| `happy_path` | Phase 1 | — | 总是成功 |
| `failure_simple` | Phase 1 | — | 立即失败，不重试 |
| `failure_with_retry` | Phase 1 | — | 失败，重试 3 次后放弃 |
| `upstream_downstream` | Phase 1 | — | 上游失败导致下游 upstream_failed |
| `long_running` | Phase 1 | — | 长时间运行，用于边界测试 |
| `dag_transient_failure` | Phase 2 | S1/S4 | 第一次失败，第二次成功 |
| `dag_code_bug` | Phase 2 | S1/S4 | 每次都失败（KeyError） |
| `dag_pipeline_failure` | Phase 2 | S2 | 失败可追溯到具体 commit |

---

## 关键路径

- DAG 文件：`dags/`
- 触发脚本：`scripts/trigger_alert.sh`、`scripts/trigger_report.sh`
- Agent prompts：`prompts/`
- 测试记录：`test/`（按场景分文件，详细记录每步调用和结果）
- Incident log：`incident_log.json`
