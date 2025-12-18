#!/usr/bin/env python3
"""Demo: haymaker kw list-workers --run-id kw-250569d9"""

import json
from pathlib import Path

run_id = "kw-250569d9"
state_file = Path.home() / ".azure_haymaker" / "deployments" / f"{run_id}.json"

print(f"📋 Knowledge Workers - Run ID: {run_id}")
print("=" * 70)

with open(state_file) as f:
    state = json.load(f)

print(f"\nDeployment: {state['name']}")
print(f"Status: {state['status']}")
print(f"Phase: {state['phase']}")
print(f"Started: {state['started_at']}")
print(f"\n{'Worker ID':<30} {'Department':<15} {'Endpoint':<15}")
print("-" * 70)

# List workers from directory
workers_dir = Path.home() / ".azure_haymaker" / "workers" / run_id
if workers_dir.exists():
    for worker_file in sorted(workers_dir.glob("*.json")):
        with open(worker_file) as f:
            worker = json.load(f)
            print(
                f"{worker['worker_id']:<30} {worker['department']:<15} {worker.get('endpoint_type', 'N/A'):<15}"
            )

print(f"\nTotal Workers: {state['worker_count']}")
