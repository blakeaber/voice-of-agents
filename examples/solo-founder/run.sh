#!/usr/bin/env bash
# Solo founder example: quickstart → run → decision-report
# Cost: ~$0.08 with haiku | Time: ~5-10 minutes
# Requires: ANTHROPIC_API_KEY

set -e

echo "=== Solo Founder Research Example ==="
echo "Running: AI tool abandonment research with Haiku (low cost)"
echo ""

# Option A: Use the pre-written config
echo "Validating config..."
voa research validate-config research-config.yaml

echo ""
echo "Estimated run cost:"
voa research run research-config.yaml --dry-run --model-haiku

echo ""
echo "Running pipeline (this will take 5-10 minutes)..."
voa research run research-config.yaml --model-haiku

echo ""
echo "Listing completed sessions..."
voa research list-sessions

echo ""
echo "Session complete. Check research-sessions/ for your YAML and DECISION-REPORT.md"
echo ""
echo "Next steps:"
echo "  1. Read DECISION-REPORT.md — this is what you act on"
echo "  2. Read SYNTHETIC-DATA-NOTICE.md — these are the 3 questions to ask real users"
echo "  3. Book 3 user calls and use the validate_with questions"
