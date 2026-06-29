#!/usr/bin/env bash
#
# Blake Analysis Pipeline Orchestrator
# Thin wrapper ensuring uv-managed environment is always used.
#
# Usage:
#   ./scripts/run_pipeline.sh [options]
#
# Options are passed directly to run_all.py (e.g., --quick, --skip-download)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🔧 Blake Analysis Pipeline"
echo "=========================="

# Ensure uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies if needed
echo "📦 Syncing dependencies..."
uv sync --quiet

# Run the pipeline
echo "🚀 Launching analysis pipeline..."
uv run python run_all.py "$@"

echo "✅ Pipeline complete. Results in: analysis_output/"
