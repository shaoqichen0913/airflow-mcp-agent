# Airflow MCP POC

你是一个 Airflow 运维 agent。通过 MCP 工具与本地 Airflow 实例交互，完成以下测试场景。

Airflow UI: http://localhost:8080 (admin/admin)

---

## 环境启动（每次开机后执行）

```bash
cd ~/projects/airflow-mcp-poc
docker compose up -d
```

### MCP server

使用 `mcp-server-apache-airflow`（yangkyeongmo），原生支持 Airflow 2.x + Basic Auth，无需代理。

配置在 `.mcp.json`（project scope）：

```json
{
  "mcpServers": {
    "airflow": {
      "command": "uvx",
      "args": ["mcp-server-apache-airflow"],
      "env": {
        "AIRFLOW_HOST": "http://localhost:8080",
        "AIRFLOW_USERNAME": "admin",
        "AIRFLOW_PASSWORD": "admin"
      }
    }
  }
}
```

### 验证 MCP server 已加载
```bash
claude mcp list  # 应显示 airflow: ✓ Connected
```
新会话启动后，MCP tools 应以 `mcp__airflow__` 前缀出现。

---

## 场景 1：Happy Path

1. 列出所有 DAG，确认 `happy_path` 存在且未暂停
2. 触发 `happy_path` DAG run
3. 每隔 5 秒轮询运行状态，直到 state 变为 `success` 或 `failed`
4. 输出最终状态和耗时

---

## 场景 2：简单失败 + 日志诊断

1. 触发 `failure_simple` DAG run
2. 轮询直到状态为 `failed`
3. 获取失败 task 的日志
4. 分析：错误类型是什么？根因是什么？是否值得重试？

---

## 场景 3：重试耗尽归因

1. 触发 `failure_with_retry` DAG run
2. 轮询状态，同时观察 `try_number` 字段变化（从 1 到 4）
3. 每次重试完成后读取该次的日志
4. 分析：三次重试的错误根因是否一致？建议人工介入还是继续重试？

---

## 场景 4：上游失败 + 下游 skipped 追溯

1. 触发 `upstream_downstream` DAG run
2. 轮询直到 DAG run 状态为 `failed`
3. 枚举该 run 下所有 task instances 的状态
4. 分析：哪个 task 失败了？哪个 task 被 skipped？为什么 task_c 没有执行？
5. 给出依赖链的完整解释

---

## 场景 5：诊断边界显式测试

1. 触发 `long_running` DAG run
2. 等待 task 进入 `running` 状态（约 10 秒内）
3. 查询 task instance 的详细信息
4. 尝试通过 MCP 工具获取任务进度或 worker 资源信息
5. 明确输出两部分：
   - **我能看到的**：通过 Airflow REST API 获取到的信息
   - **我看不到的**：MCP/REST API 无法提供的信息（进度、CPU/内存、是否真在推进）
   - **建议**：如果怀疑任务卡死，应该去哪里查（worker 日志、Celery queue、K8s pod events）
