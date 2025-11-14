#!/bin/bash
# Simple agent generation - run amplihack for each scenario

echo "Generating 50 goal-seeking agents..."
count=0

for scenario in docs/scenarios/*.md; do
    # Skip templates
    if [[ "$scenario" == *"TEMPLATE"* ]] || [[ "$scenario" == *"SCALING_PLAN"* ]]; then
        continue
    fi

    name=$(basename "$scenario" .md)
    # Truncate name to 42 chars max (leaving room for "-agent" suffix = 48 total, under 50 limit)
    name="${name:0:42}"
    count=$((count + 1))

    echo ""
    echo "[$count/50] $name"

    uvx --from git+https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding amplihack new --file "$scenario" --output "src/agents/${name}-agent"
done

echo ""
echo "Complete! Generated $count agents in src/agents/"
