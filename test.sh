#!/bin/bash
# Quick test runner script

set -e  # Exit on error

cd "$(dirname "$0")"

echo "Running test suite..."
echo ""

python3 -m pytest spooler/tests/ -v --tb=short "$@"

echo ""
echo "✅ All tests passed!"
