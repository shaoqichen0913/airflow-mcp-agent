# airflow-mcp-agent

A POC demonstrating AI agents operating Apache Airflow autonomously via MCP (Model Context Protocol).

## Context

This repo accompanies the Airflow MCP agent write-up. It is not a production-ready agent runtime; it is a reproducible local POC with the DAGs, prompts, trigger scripts, incident memory, and test records used to evaluate whether an AI agent can close a narrow Airflow failure-response loop.

## What this tests

Can an AI agent — given only a DAG ID and an alert — diagnose failures, decide whether to retry or escalate, and act on that decision **after the initial trigger, without step-by-step human guidance**?

Four progressive scenarios:

| Scenario | What it tests |
|---|---|
| **S1** Autonomous Ops | Agent receives an alert and self-diagnoses: retry vs. human escalation |
| **S2** Multi-tool Workflow | DAG failure → trace to commit → open GitHub Issue notifying the author |
| **S3** Scheduled Review | Agent simulates a scheduled daily DAG health report |
| **S4** Stateful Agent | Same as S1, but agent recalls past incidents — tests whether historical context improves decisions |

## Stack

| Layer | Tool |
|---|---|
| Orchestrator | Apache Airflow 2.9.3 (Docker Compose) |
| MCP Server | [mcp-server-apache-airflow](https://github.com/yangkyeongmo/mcp-server-apache-airflow) |
| Agent | Claude Code (claude.ai/code) |
| Notifications | GitHub Issues (S2) |

Airflow does not currently have an official MCP server. This POC uses one community implementation, `mcp-server-apache-airflow`, tested against Airflow 2.9.3 with Basic Auth. Some early test notes mention a previous proxy-based MCP setup; the current repo config in `.mcp.json` uses `mcp-server-apache-airflow` directly.

## Prerequisites

- Docker + Docker Compose
- [Claude Code](https://claude.ai/code)
- `uvx` (via `pip install uv`)
- GitHub CLI (`gh`) — for S2 only
- GitHub PAT with `repo` scope — for S2 only

## Quickstart

```bash
# 1. Start Airflow
docker compose up -d

# 2. Verify Airflow UI
open http://localhost:8080  # admin / admin

# 3. Open project in Claude Code
cd airflow-mcp-agent
claude
```

Claude Code will auto-load the MCP server via `.mcp.json`. Run `claude mcp list` to confirm `airflow: ✓ Connected`.

## Repository structure

```
airflow-mcp-agent/
├── dags/                    # Airflow DAG files
│   ├── happy_path.py
│   ├── failure_simple.py
│   ├── failure_with_retry.py
│   ├── upstream_downstream.py
│   ├── long_running.py
│   ├── dag_transient_failure.py   # S1/S4: fails first run, succeeds on retry
│   ├── dag_code_bug.py            # S1/S4: deterministic failure, needs human fix
│   └── dag_pipeline_failure.py   # S2: failure traceable to a commit
├── scripts/
│   ├── trigger_alert.sh           # Simulates PagerDuty alert → triggers agent (S1/S4)
│   └── trigger_report.sh          # Simulates cron → triggers agent report (S3)
├── prompts/
│   ├── autonomous_ops.md          # Agent prompt for S1
│   ├── stateful_ops.md            # Agent prompt for S4
│   ├── health_report.md           # Agent prompt for S3
│   └── multi_tool.md              # Agent prompt for S2
├── test/
│   ├── phase1-boundary-test.md    # Phase 1 results (stateless MCP boundary tests)
│   ├── scenario3-reports/         # Generated health reports
│   └── ...                        # Per-scenario test records
├── incident_log.json              # Operational memory for S4
├── docker-compose.yml
├── .mcp.json                      # MCP server config (Airflow local)
└── CLAUDE.md                      # Agent instructions
```

## Running the scenarios

### S1 — Autonomous Ops
```bash
bash scripts/trigger_alert.sh dag_transient_failure  # should auto-retry
bash scripts/trigger_alert.sh dag_code_bug           # should escalate
```

### S2 — Multi-tool Workflow
Requires a GitHub PAT with `repo` scope set in `.mcp.json`:
```bash
bash scripts/trigger_alert.sh dag_pipeline_failure --multi-tool
# Agent will open a GitHub Issue in this repo
```

### S3 — Scheduled Review
```bash
bash scripts/trigger_report.sh
# Output written to test/scenario3-reports/
```

### S4 — Stateful Agent
Run S1 first to populate `incident_log.json`, then run the same alerts again and observe whether the agent recalls history:
```bash
bash scripts/trigger_alert.sh dag_transient_failure --stateful
bash scripts/trigger_alert.sh dag_code_bug --stateful
```

## Test results

See `test/` directory for detailed records of each scenario run, including MCP tool call inputs/outputs, agent decision traces, and timing data.

Phase 1 (boundary/communication tests) complete: [`test/phase1-boundary-test.md`](test/phase1-boundary-test.md)
