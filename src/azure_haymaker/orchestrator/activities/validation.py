"""Validation activity for Azure HayMaker orchestrator.

This module contains the activity function for validating environment
prerequisites before scenario execution.

Checks:
- Azure credentials validity
- Anthropic API access
- Azure CLI availability
- Key Vault access
- Service Bus connectivity

Design Pattern: Activity Function
- Stateless operation
- Can be retried
- Returns structured result
"""

import logging
from typing import Any

from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.orchestrator_app import app
from azure_haymaker.orchestrator.validation import validate_environment

logger = logging.getLogger(__name__)


@app.activity_trigger(input_name="input_data")
async def validate_environment_activity(input_data: Any) -> dict[str, Any]:
    """Activity: Validate environment prerequisites.

    Checks:
    - Azure credentials validity
    - Anthropic API access
    - Azure CLI availability
    - Key Vault access
    - Service Bus connectivity

    Args:
        input_data: Not used (activity receives None)

    Returns:
        Dictionary with validation results:
        {
            "overall_passed": bool,
            "results": [
                {"check": "azure_credentials", "passed": bool, "error": str}
            ]
        }
    """
    try:
        logger.info("Activity: validate_environment - Starting")
        config = await load_config()
        result = await validate_environment(config)
        logger.info("Activity: validate_environment - Completed")
        return {
            "overall_passed": result.overall_passed,
            "results": [r.model_dump() for r in result.results],
        }
    except Exception as e:
        logger.error(f"Activity: validate_environment - Failed: {str(e)}", exc_info=True)
        return {
            "overall_passed": False,
            "results": [
                {
                    "check": "validation",
                    "passed": False,
                    "error": str(e),
                }
            ],
        }
