#!/bin/bash
set -e

# Generate goal-seeking agents for all Azure HayMaker scenarios
# Uses the amplihack Goal Agent Generator mechanism

echo "🤖 Azure HayMaker: Generating 50 Goal-Seeking Agents"
echo "======================================================="
echo ""

# Create agents directory if it doesn't exist
mkdir -p src/agents

# Counter for progress
total_scenarios=$(find docs/scenarios -name "*.md" -not -name "SCALING_PLAN.md" -not -name "SCENARIO_TEMPLATE.md" | wc -l | tr -d ' ')
current=0

echo "Found ${total_scenarios} scenarios to process"
echo ""

# Iterate through all scenario files
for scenario_file in docs/scenarios/*.md; do
    # Skip template and scaling plan files
    if [[ "$scenario_file" == *"SCALING_PLAN.md" ]] || [[ "$scenario_file" == *"SCENARIO_TEMPLATE.md" ]]; then
        echo "⏭️  Skipping: $(basename "$scenario_file")"
        continue
    fi

    current=$((current + 1))

    # Extract scenario name without extension
    scenario_name=$(basename "$scenario_file" .md)

    # Create agent directory name
    agent_dir="src/agents/${scenario_name}-agent"

    echo "[$current/$total_scenarios] Generating agent for: $scenario_name"

    # Generate the agent using amplihack
    if amplihack new --file "$scenario_file" --output "$agent_dir" 2>&1; then
        echo "  ✅ Agent created: $agent_dir"
    else
        echo "  ❌ Failed to create agent: $agent_dir"
    fi
    echo ""
done

echo ""
echo "======================================================="
echo "🎉 Complete! Generated ${total_scenarios} goal-seeking agents"
echo "======================================================="
echo ""
echo "Agents are located in: src/agents/"
echo ""
echo "To run an agent:"
echo "  cd src/agents/<scenario-name>-agent/<bundle-name>"
echo "  python main.py"
