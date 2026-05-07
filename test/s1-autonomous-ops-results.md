# S1 Autonomous Ops — Test Results

**Date:** 2026-05-07  
**Agent:** Claude (claude-sonnet-4-6)  
**Environment:** Airflow 2.9.3 (Docker), MCP via airflow-proxy.py on port 8081

---

## Test A: dag_transient_failure

- **Run 1:** `manual__2026-05-07T15:09:11.769824+00:00`, state: `failed`
  - Task: `sync_data` (PythonOperator), duration: 0.41s
  - Error: `ConnectionError: External API timeout: failed to reach data-service after 3 retries`
- **Classification:** TRANSIENT
  - Rationale: `ConnectionError` is an infrastructure/network failure, not a code defect.
    DAG source confirms simulated transience — the task uses an Airflow Variable counter
    (`transient_failure_run_count`) that causes a failure on the first run (count=0) and
    succeeds on the second run (count=1). Pattern matches real-world intermittent API timeouts.
- **Decision:** Trigger retry (Run 2)
- **Run 2:** `manual__2026-05-07T15:09:36.913373+00:00`, state: `success`
  - Task `sync_data` completed: "Data sync complete. 142 records processed."
  - Duration: ~1.06s
- **Outcome:** SUCCESS — transient failure resolved on retry as expected

---

## Test B: dag_code_bug

- **Run:** `manual__2026-05-07T15:09:11.832144+00:00`, state: `failed`
  - Task: `process_records` (PythonOperator), duration: 0.34s
  - Error: `KeyError: 'user_id'`
  - Traceback location: `dag_code_bug.py`, line 9: `required_field = schema_dict["user_id"]`
- **Classification:** DETERMINISTIC
  - Rationale: `KeyError` is a code defect. The schema is hardcoded as
    `["username", "email", "created_at"]` but the code immediately attempts to access
    `schema_dict["user_id"]`, which is not present. This will fail on every run without
    exception — no amount of retrying will change the outcome.
- **Decision:** Escalate — no retry

### Escalation Report

- **Error type:** `KeyError` — dictionary key lookup failure
- **Root cause:** Schema mismatch. `process_records()` constructs `schema_dict` from a
  hardcoded list `["username", "email", "created_at"]` (fields: username→0, email→1,
  created_at→2), then immediately accesses `schema_dict["user_id"]` on line 9. The key
  `user_id` does not exist in the schema definition and was never added. This is likely
  either a field renamed during a refactor (e.g., `user_id` → `username`) or a copy-paste
  error where the wrong schema list was used.
- **Affected file:** `/opt/airflow/dags/dag_code_bug.py`, line 9
- **Recommended fix (two options):**
  1. **If `user_id` should be in the schema:** Add `"user_id"` to the schema list:
     `schema = ["user_id", "username", "email", "created_at"]`
  2. **If the code should use `username`:** Change the lookup to use the correct key:
     `required_field = schema_dict["username"]`
- **Retry recommended:** NO — will fail deterministically on every attempt until code is fixed
- **Urgency:** Medium — DAG produces no output data until fixed; downstream consumers of
  processed records are blocked

---

## Decision Trace

| Step | Action | Tool Used | Result |
|------|--------|-----------|--------|
| 1 | Unpause both DAGs | REST PATCH | Both unpaused |
| 2 | Trigger Test A Run 1 | REST POST dagRuns | queued → failed (2s) |
| 3 | Trigger Test B Run 1 | REST POST dagRuns | queued → failed (2s) |
| 4 | Get task instances (A) | mcp__airflow__get_task_instances | `sync_data` failed |
| 5 | Get task instances (B) | mcp__airflow__get_task_instances | `process_records` failed |
| 6 | Get logs (A) | mcp__airflow__get_log | ConnectionError identified |
| 7 | Get logs (B) | mcp__airflow__get_log | KeyError identified |
| 8 | Classify A as TRANSIENT | Agent analysis | DAG source confirmed |
| 9 | Classify B as DETERMINISTIC | Agent analysis | Code defect confirmed |
| 10 | Trigger Test A Run 2 | REST POST dagRuns | queued → success (2s) |
| 11 | Escalate Test B | Report generated | No retry |

---

## Timing

- **Test A total:** ~27s (Run 1 trigger → Run 2 success, including analysis time)
  - Run 1 execution: ~2s (failed)
  - Analysis + retry decision: ~25s
  - Run 2 execution: ~2s (success)
- **Test B total:** ~2s (trigger → failed, classified during parallel analysis)
- **Both tests ran concurrently** for initial trigger and log collection

---

## Infrastructure Note

The `airflow-mcp-server` MCP tool `mcp__airflow__post_dag_run` returned HTTP 400
(`Property is read-only - 'dag_id'`) due to a known incompatibility: the MCP server sends
`dag_id` in the request body, but Airflow 2.x treats it as read-only (path parameter only).
DAG run triggers were performed via direct REST API as a workaround. All subsequent
polling and log retrieval used MCP tools (`mcp__airflow__get_dag_run`,
`mcp__airflow__get_task_instances`, `mcp__airflow__get_log`) successfully.

**Proxy status:** `airflow-proxy.py` was created and started during this session at
`http://localhost:8081`. The `.mcp.json` in this repo uses `mcp-server-apache-airflow`
with direct Basic Auth (not the proxy-based `airflow-mcp-server`), so the proxy is not
required for this MCP configuration.
