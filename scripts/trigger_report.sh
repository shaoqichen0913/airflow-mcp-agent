#!/bin/bash
# Simulates a cron job: generates daily DAG health report via Claude agent
# Usage: bash scripts/trigger_report.sh

set -euo pipefail

DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="test/scenario3-reports"
OUTPUT_FILE="$OUTPUT_DIR/report-$DATE.md"

# Resolve paths relative to the project root (directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PROMPT_TEMPLATE="$PROJECT_ROOT/prompts/health_report.md"
OUTPUT_DIR_ABS="$PROJECT_ROOT/$OUTPUT_DIR"
OUTPUT_FILE_ABS="$PROJECT_ROOT/$OUTPUT_FILE"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR_ABS"

# Read the prompt template and substitute {{DATE}} with today's date
PROMPT=$(sed "s/{{DATE}}/$DATE/g" "$PROMPT_TEMPLATE")

# Append output file instruction so the agent knows where to save
PROMPT="$PROMPT

Your output file for this run is: $OUTPUT_FILE_ABS
Write the final markdown report to that file using the Write tool."

echo "Generating DAG health report for $DATE ..."
echo "Output: $OUTPUT_FILE_ABS"
echo ""

# Invoke Claude agent with the rendered prompt
claude -p "$PROMPT" 2>&1

echo ""
echo "Report saved to $OUTPUT_FILE_ABS"
