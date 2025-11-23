"""Test Azure Functions discovery in function_app.py.

This test verifies that all 17 functions are properly defined in function_app.py.
"""

import re
from pathlib import Path


def test_function_count():
    """Test that all 17 Azure Functions are defined."""
    # Read function_app.py
    function_app_path = Path(__file__).parent.parent / "src" / "function_app.py"
    content = function_app_path.read_text()

    # Find all function definitions that have @app decorators
    # Pattern: @app.something followed by function definition
    pattern = r"@app\.\w+.*?\n(?:@app\.\w+.*?\n)*(?:async )?def (\w+)\("
    matches = re.findall(pattern, content)

    # Expected functions (17 total)
    expected_functions = {
        # Timer trigger (1)
        "haymaker_timer",
        # Orchestrator (1)
        "orchestrate_haymaker_run",
        # Activities (8)
        "validate_environment_activity",
        "select_scenarios_activity",
        "create_service_principal_activity",
        "deploy_container_app_activity",
        "check_agent_status_activity",
        "verify_cleanup_activity",
        "force_cleanup_activity",
        "generate_report_activity",
        # HTTP APIs (7)
        "execute_scenario",
        "get_execution_status",
        "list_agents",
        "get_agent_logs",
        "get_metrics",
        "list_resources",
        "get_resource",
    }

    discovered_functions = set(matches)

    # Verify all expected functions are discovered
    missing_functions = expected_functions - discovered_functions
    extra_functions = discovered_functions - expected_functions

    print(f"\nFunction Discovery Report:")
    print(f"Expected: {len(expected_functions)} functions")
    print(f"Discovered: {len(discovered_functions)} functions")
    print(f"Discovered functions: {sorted(discovered_functions)}")

    if missing_functions:
        print(f"\n❌ Missing functions: {sorted(missing_functions)}")

    if extra_functions:
        print(f"\n⚠️  Extra functions: {sorted(extra_functions)}")

    if not missing_functions and not extra_functions:
        print("\n✅ All 17 functions discovered successfully!")

    # Test assertions
    assert len(discovered_functions) == 17, (
        f"Expected 17 functions, found {len(discovered_functions)}. "
        f"Missing: {missing_functions}, Extra: {extra_functions}"
    )
    assert missing_functions == set(), f"Missing functions: {missing_functions}"
    assert extra_functions == set(), f"Extra functions: {extra_functions}"


def test_function_categories():
    """Test that functions are categorized correctly."""
    # Verify function counts by category
    timer_triggers = ["haymaker_timer"]
    orchestrators = ["orchestrate_haymaker_run"]
    activities = [
        "validate_environment_activity",
        "select_scenarios_activity",
        "create_service_principal_activity",
        "deploy_container_app_activity",
        "check_agent_status_activity",
        "verify_cleanup_activity",
        "force_cleanup_activity",
        "generate_report_activity",
    ]
    http_apis = [
        "execute_scenario",
        "get_execution_status",
        "list_agents",
        "get_agent_logs",
        "get_metrics",
        "list_resources",
        "get_resource",
    ]

    print("\nFunction Categories:")
    print(f"  Timer Triggers: {len(timer_triggers)}")
    print(f"  Orchestrators: {len(orchestrators)}")
    print(f"  Activities: {len(activities)}")
    print(f"  HTTP APIs: {len(http_apis)}")
    print(f"  Total: {len(timer_triggers) + len(orchestrators) + len(activities) + len(http_apis)}")

    assert len(timer_triggers) == 1
    assert len(orchestrators) == 1
    assert len(activities) == 8
    assert len(http_apis) == 7
    assert len(timer_triggers) + len(orchestrators) + len(activities) + len(http_apis) == 17


def test_http_api_routes():
    """Test that all HTTP API routes are properly defined."""
    # Read function_app.py
    function_app_path = Path(__file__).parent.parent / "src" / "function_app.py"
    content = function_app_path.read_text()

    # Expected routes
    expected_routes = {
        "execute": "POST",
        "executions/{execution_id}": "GET",
        "agents": "GET",
        "agents/{agent_id}/logs": "GET",
        "metrics": "GET",
        "resources": "GET",
        "resources/{resource_id}": "GET",
    }

    # Find all @app.route decorators
    route_pattern = r'@app\.route\(route="([^"]+)",\s*methods=\["(\w+)"\]'
    routes = re.findall(route_pattern, content)

    found_routes = {route: method for route, method in routes}

    print("\nHTTP API Routes:")
    for route, method in sorted(found_routes.items()):
        print(f"  {method:6s} /api/{route}")

    # Verify all expected routes are present
    missing_routes = set(expected_routes.keys()) - set(found_routes.keys())
    extra_routes = set(found_routes.keys()) - set(expected_routes.keys())

    if missing_routes:
        print(f"\n❌ Missing routes: {sorted(missing_routes)}")

    if extra_routes:
        print(f"\n⚠️  Extra routes: {sorted(extra_routes)}")

    if not missing_routes and not extra_routes:
        print("\n✅ All 7 HTTP API routes defined correctly!")

    assert len(found_routes) == 7, f"Expected 7 routes, found {len(found_routes)}"
    assert missing_routes == set(), f"Missing routes: {missing_routes}"

    # Verify methods match
    for route, method in expected_routes.items():
        assert found_routes[route] == method, f"Route {route} expected {method}, got {found_routes[route]}"


if __name__ == "__main__":
    test_function_count()
    test_function_categories()
    test_http_api_routes()
    print("\n✅ All tests passed!")
