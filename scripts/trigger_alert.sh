#!/bin/bash
# Usage: bash scripts/trigger_alert.sh <dag_id> [--stateful] [--multi-tool]

set -euo pipefail

DAG_ID="${1:-}"
MODE="${2:-}"

if [[ -z "$DAG_ID" ]]; then
  echo "Error: DAG_ID is required." >&2
  echo "Usage: bash scripts/trigger_alert.sh <dag_id> [--stateful] [--multi-tool]" >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

case "$MODE" in
  --stateful)
    PROMPT_FILE="$PROJECT_ROOT/prompts/stateful_ops.md"
    ;;
  --multi-tool)
    PROMPT_FILE="$PROJECT_ROOT/prompts/multi_tool.md"
    ;;
  *)
    PROMPT_FILE="$PROJECT_ROOT/prompts/autonomous_ops.md"
    ;;
esac

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Error: prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

PROMPT_TEMPLATE="$(cat "$PROMPT_FILE")"
PROMPT="${PROMPT_TEMPLATE//\{\{DAG_ID\}\}/$DAG_ID}"

mkdir -p "$PROJECT_ROOT/test/scenario-runs"
LOG_FILE="$PROJECT_ROOT/test/scenario-runs/alert-${DAG_ID}-$(date +%Y%m%d-%H%M%S).log"

claude -p "$PROMPT" 2>&1 | tee "$LOG_FILE"

echo ""
echo "Log saved to: $LOG_FILE"
