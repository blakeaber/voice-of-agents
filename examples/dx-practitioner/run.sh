#!/usr/bin/env bash
# DX Practitioner example: quickstart → run → seed-eval
# The full research → eval bridge workflow
# Cost: ~$0.08 with haiku | Time: 10-15 minutes
# Requires: ANTHROPIC_API_KEY

set -e

echo "=== DX Practitioner Research → Eval Bridge Example ==="
echo ""

# Step 1: Validate config
echo "[1/4] Validating research config..."
voa research validate-config research-config.yaml

# Step 2: Run cost estimate
echo ""
echo "[2/4] Cost estimate (use --model-haiku for low cost):"
voa research run research-config.yaml --dry-run --model-haiku

echo ""
echo "Press Enter to run the research pipeline, or Ctrl+C to abort."
read

# Step 3: Run research pipeline
echo ""
echo "[3/4] Running research pipeline (Stages 1 + 2 for persona seeding)..."
voa research run research-config.yaml --model-haiku --stage personas

# Step 4: Seed eval from research personas
echo ""
echo "[4/4] Seeding eval pipeline from research personas..."
SESSION_FILE=$(ls -t research-sessions/*.yaml 2>/dev/null | head -1)

if [ -z "$SESSION_FILE" ]; then
    echo "No session file found. Make sure the pipeline completed Stage 2."
    exit 1
fi

echo "Using session: $SESSION_FILE"
voa research seed-eval "$SESSION_FILE" --output data/personas/ --starting-id 100

echo ""
echo "=== Bridge Complete ==="
echo ""
echo "What just happened:"
echo "  1. Ran synthetic research with DX practitioner personas"
echo "  2. Identified behavioral archetypes: adopters, abandoners, skeptics"
echo "  3. Converted research sidecars to canonical eval Personas"
echo "  4. Wrote DRAFT Personas to data/personas/"
echo ""
echo "Next steps:"
echo "  1. Read data/personas/BRIDGE-WORKFLOW.md"
echo "  2. Review the DRAFT personas — they reflect the research archetypes"
echo "  3. Promote to 'validated' after a real user confirms the archetype"
echo "  4. Run your eval suite with the new personas:"
echo "     voa eval run --personas data/personas/"
