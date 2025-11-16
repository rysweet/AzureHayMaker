"""Test configuration and fixtures for Azure HayMaker tests.

This conftest.py is loaded before any tests run and sets up the test environment.

Note: Azure Durable Functions decorators in orchestrator.py are only needed for
production runtime. Tests can run without them since we mock the activity functions.
"""

import contextlib

# Ensure azure.durable_functions is available for orchestrator module import
# The module may not be found due to namespace package conflicts between system and venv
with contextlib.suppress(ImportError):
    import azure.durable_functions  # noqa: F401
