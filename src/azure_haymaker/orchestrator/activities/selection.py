"""Scenario selection activity for Azure HayMaker orchestrator.

This module contains the activity function for selecting random scenarios
for execution based on simulation size.

Design Pattern: Activity Function
- Stateless operation
- Can be retried
- Returns selected scenarios
"""

import logging
from typing import Any

from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.orchestrator_app import app
from azure_haymaker.orchestrator.scenario_selector import select_scenarios

logger = logging.getLogger(__name__)


@app.activity_trigger(input_name="input_data")
async def select_scenarios_activity(input_data: Any) -> dict[str, Any]:
    """Activity: Select random scenarios for execution.

    Randomly selects N scenarios based on simulation_size configuration.
    Size mappings:
    - small: 5 scenarios
    - medium: 15 scenarios
    - large: 30 scenarios

    Args:
        input_data: Not used (activity receives None)

    Returns:
        Dictionary with selected scenarios:
        {
            "scenarios": [
                {
                    "scenario_name": str,
                    "technology_area": str,
                    "scenario_doc_path": str
                }
            ]
        }
    """
    try:
        logger.info("Activity: select_scenarios - Starting")
        config = await load_config()
        # Get simulation size from config
        sim_size = config.simulation_size
        scenarios = select_scenarios(sim_size)
        logger.info(f"Activity: select_scenarios - Selected {len(scenarios)} scenarios")
        return {
            "scenarios": [
                {
                    "scenario_name": s.scenario_name,
                    "technology_area": s.technology_area,
                    "scenario_doc_path": s.scenario_doc_path,
                    "agent_path": s.agent_path,
                }
                for s in scenarios
            ]
        }
    except Exception as e:
        logger.error(f"Activity: select_scenarios - Failed: {str(e)}", exc_info=True)
        return {"scenarios": []}
