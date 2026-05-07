# Scenario 2 — Multi-Tool Workflow: Investigation Report

**Date**: 2026-05-07  
**Agent**: Airflow MCP + GitHub CLI  
**Total elapsed**: ~4 minutes (including proxy startup and DAG unpausing)

---

## 1. Failed Run Details

| Field | Value |
|-------|-------|
| DAG ID | `dag_pipeline_failure` |
| Run ID | `manual__2026-05-07T15:09:14.580823+00:00` |
| State | `failed` |
| Start | `2026-05-07T15:09:51.561462+00:00` |
| End | `2026-05-07T15:09:53.292148+00:00` |
| Duration | ~1.7 seconds |

### Task Instance States

| Task ID | State | Try # |
|---------|-------|-------|
| `validate_schema` | success | 1 |
| `process_data` | **failed** | 1 |

---

## 2. Error Keywords

- **Error type**: `KeyError`
- **Missing key**: `'event_timestamp'`
- **Location**: `dags/dag_pipeline_failure.py`, line 15, function `process_data`
- **Full exception**:

```
KeyError: 'event_timestamp'

File "/opt/airflow/dags/dag_pipeline_failure.py", line 15, in process_data
    ts = record["event_timestamp"]  # BUG: field was renamed to 'ts' in this commit
         ~~~~~~^^^^^^^^^^^^^^^^^^^
```

The `validate_schema` task succeeded because it only prints a hardcoded string — it does not actually inspect the record structure at runtime. The real schema mismatch only surfaces when `process_data` tries to read a key that no longer exists.

---

## 3. Matched Commit

| Field | Value |
|-------|-------|
| Short SHA | `ebdc95cd` |
| Full SHA | `ebdc95cdb3dea4a2b7d08591c65ea263ce2ddff0` |
| Author | Shaoqi Chen <shaoqichen0913@gmail.com> |
| Date | 2026-05-07T14:53:20Z |
| Message | `refactor: rename event_timestamp to ts in pipeline schema` |

### What the commit changed

```diff
-        {"event_timestamp": "2026-05-07T10:00:00Z", "user_id": "u123", "action_type": "click"},
-        {"event_timestamp": "2026-05-07T10:01:00Z", "user_id": "u456", "action_type": "view"},
+        {"ts": "2026-05-07T10:00:00Z", "user_id": "u123", "action_type": "click"},
+        {"ts": "2026-05-07T10:01:00Z", "user_id": "u456", "action_type": "view"},
```

**What was missed**: Line 15 still reads `record["event_timestamp"]` — the dict-access was not updated to match the renamed key.

---

## 4. Root Cause Analysis

Commit `ebdc95cd` performed a partial rename: the sample record dictionaries were updated (`event_timestamp` → `ts`), but the corresponding read on line 15 was left untouched. This is a classic **partial schema rename** defect.

Contributing factor: `validate_schema` is a no-op validator — it prints a static message without inspecting actual record fields. A real schema validator would have caught this mismatch before `process_data` was reached.

---

## 5. GitHub Issue

- **URL**: https://github.com/shaoqichen0913/airflow-mcp-agent/issues/1
- **Title**: `[Pipeline Failure] dag_pipeline_failure: KeyError 'event_timestamp'`
- **Contents**: Failed run ID, failed task + traceback, suspected commit (SHA + message + diff), root cause analysis, recommended fix with code snippet, assignee suggestion

---

## 6. Recommended Fix

In `dags/dag_pipeline_failure.py`, line 15:

```python
# Before (broken)
ts = record["event_timestamp"]

# After (fixed)
ts = record["ts"]
```

Also update `validate_schema()` to document the current schema accurately:

```python
# Before
print("Schema validation passed. Fields: event_timestamp, user_id, action_type")

# After
print("Schema validation passed. Fields: ts, user_id, action_type")
```

---

## 7. Tool Chain Used

1. `mcp__airflow__post_dag_run` → triggered DAG (via REST API fallback due to MCP tool parameter constraint)
2. `mcp__airflow__get_dag_run` → polled state until `failed`
3. `mcp__airflow__get_task_instances` → identified `process_data` as the failed task
4. `mcp__airflow__get_log` → extracted full traceback with `KeyError: 'event_timestamp'`
5. `gh api repos/.../commits` → listed last 10 commits to `dags/` path
6. `gh api repos/.../commits/ebdc95cd` → confirmed diff and author
7. `gh issue create` → opened GitHub Issue #1 with full investigation report
