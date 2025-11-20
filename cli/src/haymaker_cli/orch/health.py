"""Health check implementations for orchestrator CLI commands.

This module provides comprehensive health checking for Azure Container Apps,
including app status, endpoint connectivity, replica health, and HTTP endpoint checks.
All checks run asynchronously with configurable timeouts.

Public API:
    - check_container_app_status: Basic app status check
    - check_endpoint_connectivity: DNS and TCP connectivity check
    - check_replica_health: Replica health verification
    - check_http_health_endpoint: Deep HTTP health endpoint check
    - run_health_checks: Run all checks in parallel

Example:
    >>> import asyncio
    >>> from haymaker_cli.orch import ContainerAppsClient
    >>> from haymaker_cli.orch.health import run_health_checks
    >>> client = ContainerAppsClient("sub-id", "rg")
    >>> results = asyncio.run(run_health_checks(client, deep=True))  # doctest: +SKIP
    >>> print(results[0]["status"])  # doctest: +SKIP
    'PASS'
"""

import asyncio
import socket
from datetime import datetime
from typing import Any

import httpx

from haymaker_cli.orch.client import ContainerAppsClient
from haymaker_cli.orch.models import ApiError, NetworkError


async def check_container_app_status(
    client: ContainerAppsClient,
    app_name: str,
    timeout: int = 10,
) -> dict[str, Any]:
    """Check Container App provisioning and running status.

    Verifies that the app is provisioned successfully and in running state.
    This is the most basic health check.

    Args:
        client: Container Apps client
        app_name: Container app name
        timeout: Timeout in seconds (default: 10)

    Returns:
        Health check result with keys:
            - check_name: "Container App Status"
            - status: "PASS", "WARN", or "FAIL"
            - message: Status message
            - details: Additional status details
            - suggestions: List of actionable suggestions

    Example:
        >>> import asyncio
        >>> from haymaker_cli.orch import ContainerAppsClient
        >>> client = ContainerAppsClient("sub-id", "rg")
        >>> result = asyncio.run(
        ...     check_container_app_status(client, "my-app")
        ... )  # doctest: +SKIP
        >>> result["check_name"]  # doctest: +SKIP
        'Container App Status'
    """
    try:
        # Get app info with timeout
        app = await asyncio.wait_for(
            client.get_container_app(app_name),
            timeout=timeout,
        )

        # Check provisioning state
        if app.provisioning_state == "Succeeded":
            if app.running_status == "Running":
                return {
                    "check_name": "Container App Status",
                    "status": "PASS",
                    "message": "App is running",
                    "details": {
                        "provisioning_state": app.provisioning_state,
                        "running_status": app.running_status,
                        "location": app.location,
                    },
                    "suggestions": [],
                }
            else:
                return {
                    "check_name": "Container App Status",
                    "status": "WARN",
                    "message": f"App provisioned but not running: {app.running_status}",
                    "details": {
                        "provisioning_state": app.provisioning_state,
                        "running_status": app.running_status or "Unknown",
                    },
                    "suggestions": [
                        "Check if app was manually stopped",
                        "Review scaling configuration",
                        "Check container logs for errors",
                    ],
                }
        elif app.provisioning_state == "Failed":
            return {
                "check_name": "Container App Status",
                "status": "FAIL",
                "message": "App provisioning failed",
                "details": {
                    "provisioning_state": app.provisioning_state,
                },
                "suggestions": [
                    "Check container logs for startup errors",
                    "Verify container image is accessible",
                    "Review resource limits and quotas",
                    "Check Azure portal for detailed error messages",
                ],
            }
        else:
            return {
                "check_name": "Container App Status",
                "status": "WARN",
                "message": f"App in intermediate state: {app.provisioning_state}",
                "details": {
                    "provisioning_state": app.provisioning_state,
                    "running_status": app.running_status or "Unknown",
                },
                "suggestions": [
                    "Wait for provisioning to complete",
                    "Check Azure portal for deployment progress",
                ],
            }

    except asyncio.TimeoutError:
        return {
            "check_name": "Container App Status",
            "status": "FAIL",
            "message": f"Timeout after {timeout}s",
            "details": {"timeout": timeout},
            "suggestions": [
                "Check Azure service status",
                "Verify network connectivity to Azure",
                "Try increasing timeout value",
            ],
        }
    except (NetworkError, ApiError) as e:
        return {
            "check_name": "Container App Status",
            "status": "FAIL",
            "message": str(e),
            "details": getattr(e, "details", {}),
            "suggestions": [
                "Verify Azure credentials are configured",
                "Check subscription ID and resource group",
                "Ensure container app exists",
            ],
        }
    except Exception as e:
        return {
            "check_name": "Container App Status",
            "status": "FAIL",
            "message": f"Unexpected error: {e}",
            "details": {"error_type": type(e).__name__},
            "suggestions": [
                "Check error message for details",
                "Verify Azure SDK is installed correctly",
            ],
        }


async def check_endpoint_connectivity(
    endpoint: str,
    timeout: int = 10,
) -> dict[str, Any]:
    """Check DNS resolution and TCP connectivity to endpoint.

    Performs basic network connectivity checks without making HTTP requests.
    Verifies that the endpoint can be resolved and a TCP connection can be established.

    Args:
        endpoint: Endpoint URL or hostname (e.g., "https://my-app.azurecontainerapps.io")
        timeout: Timeout in seconds (default: 10)

    Returns:
        Health check result

    Example:
        >>> import asyncio
        >>> result = asyncio.run(
        ...     check_endpoint_connectivity("https://example.com")
        ... )  # doctest: +SKIP
        >>> result["check_name"]  # doctest: +SKIP
        'Endpoint Connectivity'
    """
    try:
        # Parse endpoint
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            # Extract hostname from URL
            from urllib.parse import urlparse
            parsed = urlparse(endpoint)
            hostname = parsed.hostname or parsed.netloc
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        else:
            # Assume it's just a hostname
            hostname = endpoint
            port = 443

        if not hostname:
            return {
                "check_name": "Endpoint Connectivity",
                "status": "FAIL",
                "message": "Invalid endpoint format",
                "details": {"endpoint": endpoint},
                "suggestions": [
                    "Provide a valid URL or hostname",
                    "Check endpoint configuration",
                ],
            }

        # DNS resolution
        try:
            loop = asyncio.get_event_loop()
            addresses = await asyncio.wait_for(
                loop.getaddrinfo(hostname, port, family=socket.AF_INET, type=socket.SOCK_STREAM),
                timeout=timeout / 2,
            )
            ip_address = addresses[0][4][0] if addresses else None
        except asyncio.TimeoutError:
            return {
                "check_name": "Endpoint Connectivity",
                "status": "FAIL",
                "message": f"DNS resolution timeout for {hostname}",
                "details": {"hostname": hostname, "timeout": timeout},
                "suggestions": [
                    "Check DNS configuration",
                    "Verify hostname is correct",
                    "Check network connectivity",
                ],
            }
        except socket.gaierror as e:
            return {
                "check_name": "Endpoint Connectivity",
                "status": "FAIL",
                "message": f"DNS resolution failed: {e}",
                "details": {"hostname": hostname},
                "suggestions": [
                    "Verify hostname is correct",
                    "Check if container app has external ingress enabled",
                    "Ensure DNS records are properly configured",
                ],
            }

        # TCP connectivity
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port),
                timeout=timeout / 2,
            )
            writer.close()
            await writer.wait_closed()

            return {
                "check_name": "Endpoint Connectivity",
                "status": "PASS",
                "message": f"DNS and TCP connection successful",
                "details": {
                    "hostname": hostname,
                    "ip_address": ip_address or "unknown",
                    "port": port,
                },
                "suggestions": [],
            }

        except asyncio.TimeoutError:
            return {
                "check_name": "Endpoint Connectivity",
                "status": "FAIL",
                "message": f"TCP connection timeout to {hostname}:{port}",
                "details": {
                    "hostname": hostname,
                    "port": port,
                    "timeout": timeout,
                },
                "suggestions": [
                    "Check if ingress is enabled",
                    "Verify firewall rules",
                    "Ensure container is listening on correct port",
                ],
            }
        except (ConnectionRefusedError, OSError) as e:
            return {
                "check_name": "Endpoint Connectivity",
                "status": "FAIL",
                "message": f"TCP connection failed: {e}",
                "details": {
                    "hostname": hostname,
                    "port": port,
                },
                "suggestions": [
                    "Check if ingress is enabled",
                    "Verify container is running",
                    "Ensure container is listening on correct port",
                ],
            }

    except Exception as e:
        return {
            "check_name": "Endpoint Connectivity",
            "status": "FAIL",
            "message": f"Unexpected error: {e}",
            "details": {"error_type": type(e).__name__},
            "suggestions": [
                "Check error message for details",
                "Verify endpoint format is correct",
            ],
        }


async def check_replica_health(
    client: ContainerAppsClient,
    app_name: str,
    timeout: int = 10,
) -> dict[str, Any]:
    """Check replica health across all active revisions.

    Verifies that replicas are running and healthy. Checks all active revisions
    and aggregates replica status.

    Args:
        client: Container Apps client
        app_name: Container app name
        timeout: Timeout in seconds (default: 10)

    Returns:
        Health check result

    Example:
        >>> import asyncio
        >>> from haymaker_cli.orch import ContainerAppsClient
        >>> client = ContainerAppsClient("sub-id", "rg")
        >>> result = asyncio.run(
        ...     check_replica_health(client, "my-app")
        ... )  # doctest: +SKIP
        >>> result["check_name"]  # doctest: +SKIP
        'Replica Health'
    """
    try:
        # Get revisions with timeout
        revisions = await asyncio.wait_for(
            client.list_revisions(app_name),
            timeout=timeout / 2,
        )

        active_revisions = [r for r in revisions if r.active]

        if not active_revisions:
            return {
                "check_name": "Replica Health",
                "status": "WARN",
                "message": "No active revisions found",
                "details": {
                    "total_revisions": len(revisions),
                    "active_revisions": 0,
                },
                "suggestions": [
                    "Check if app has been deployed",
                    "Verify revision mode configuration",
                ],
            }

        # Count replicas across all active revisions
        total_replicas = 0
        healthy_replicas = 0
        revision_details = []

        # Use remaining timeout for replica checks
        remaining_timeout = timeout / 2

        for revision in active_revisions:
            try:
                replicas = await asyncio.wait_for(
                    client.list_replicas(app_name, revision.name),
                    timeout=remaining_timeout / len(active_revisions),
                )

                total_replicas += len(replicas)
                healthy_count = sum(1 for r in replicas if r.running_state == "Running")
                healthy_replicas += healthy_count

                revision_details.append({
                    "revision": revision.name,
                    "total": len(replicas),
                    "healthy": healthy_count,
                })

            except asyncio.TimeoutError:
                # Skip this revision on timeout
                revision_details.append({
                    "revision": revision.name,
                    "error": "timeout",
                })
                continue
            except Exception as e:
                # Skip this revision on error
                revision_details.append({
                    "revision": revision.name,
                    "error": str(e),
                })
                continue

        # Determine health status
        if total_replicas == 0:
            return {
                "check_name": "Replica Health",
                "status": "FAIL",
                "message": "No replicas found",
                "details": {
                    "active_revisions": len(active_revisions),
                    "total_replicas": 0,
                },
                "suggestions": [
                    "Scale up the app (min_replicas may be 0)",
                    "Check for recent deployment failures",
                    "Review container logs",
                ],
            }
        elif healthy_replicas == total_replicas:
            return {
                "check_name": "Replica Health",
                "status": "PASS",
                "message": f"All {total_replicas} replicas healthy",
                "details": {
                    "active_revisions": len(active_revisions),
                    "total_replicas": total_replicas,
                    "healthy_replicas": healthy_replicas,
                },
                "suggestions": [],
            }
        elif healthy_replicas > 0:
            return {
                "check_name": "Replica Health",
                "status": "WARN",
                "message": f"Only {healthy_replicas}/{total_replicas} replicas healthy",
                "details": {
                    "active_revisions": len(active_revisions),
                    "total_replicas": total_replicas,
                    "healthy_replicas": healthy_replicas,
                    "revisions": revision_details,
                },
                "suggestions": [
                    "Check container logs for errors",
                    "Review health probe configuration",
                    "Consider restarting unhealthy replicas",
                ],
            }
        else:
            return {
                "check_name": "Replica Health",
                "status": "FAIL",
                "message": "No healthy replicas",
                "details": {
                    "active_revisions": len(active_revisions),
                    "total_replicas": total_replicas,
                    "healthy_replicas": 0,
                    "revisions": revision_details,
                },
                "suggestions": [
                    "Check container logs for runtime errors",
                    "Verify dependencies (databases, services) are accessible",
                    "Review health probe configuration",
                    "Consider rolling back to previous revision",
                ],
            }

    except asyncio.TimeoutError:
        return {
            "check_name": "Replica Health",
            "status": "FAIL",
            "message": f"Timeout after {timeout}s",
            "details": {"timeout": timeout},
            "suggestions": [
                "Check Azure service status",
                "Try increasing timeout value",
            ],
        }
    except (NetworkError, ApiError) as e:
        return {
            "check_name": "Replica Health",
            "status": "FAIL",
            "message": str(e),
            "details": getattr(e, "details", {}),
            "suggestions": [
                "Verify Azure credentials",
                "Check network connectivity",
            ],
        }
    except Exception as e:
        return {
            "check_name": "Replica Health",
            "status": "FAIL",
            "message": f"Unexpected error: {e}",
            "details": {"error_type": type(e).__name__},
            "suggestions": [
                "Check error message for details",
            ],
        }


async def check_http_health_endpoint(
    endpoint: str,
    path: str = "/health",
    timeout: int = 10,
) -> dict[str, Any]:
    """Check HTTP health endpoint with deep validation.

    Makes an actual HTTP request to the health endpoint and validates the response.
    This is the most comprehensive check but also the most invasive.

    Args:
        endpoint: Base endpoint URL (e.g., "https://my-app.azurecontainerapps.io")
        path: Health endpoint path (default: "/health")
        timeout: Timeout in seconds (default: 10)

    Returns:
        Health check result

    Example:
        >>> import asyncio
        >>> result = asyncio.run(
        ...     check_http_health_endpoint("https://example.com")
        ... )  # doctest: +SKIP
        >>> result["check_name"]  # doctest: +SKIP
        'HTTP Health Endpoint'
    """
    try:
        # Build full URL
        if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
            endpoint = f"https://{endpoint}"

        url = f"{endpoint.rstrip('/')}/{path.lstrip('/')}"

        # Make HTTP request
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            start_time = datetime.now()
            response = await client.get(url)
            elapsed = (datetime.now() - start_time).total_seconds()

            # Check response status
            if 200 <= response.status_code < 300:
                return {
                    "check_name": "HTTP Health Endpoint",
                    "status": "PASS",
                    "message": f"HTTP {response.status_code} OK",
                    "details": {
                        "url": url,
                        "status_code": response.status_code,
                        "response_time_ms": int(elapsed * 1000),
                    },
                    "suggestions": [],
                }
            elif 400 <= response.status_code < 500:
                return {
                    "check_name": "HTTP Health Endpoint",
                    "status": "FAIL",
                    "message": f"HTTP {response.status_code} client error",
                    "details": {
                        "url": url,
                        "status_code": response.status_code,
                    },
                    "suggestions": [
                        f"Health endpoint {path} may not exist",
                        "Verify health endpoint path is correct",
                        "Check if authentication is required",
                    ],
                }
            elif 500 <= response.status_code < 600:
                return {
                    "check_name": "HTTP Health Endpoint",
                    "status": "FAIL",
                    "message": f"HTTP {response.status_code} server error",
                    "details": {
                        "url": url,
                        "status_code": response.status_code,
                    },
                    "suggestions": [
                        "Check container logs for errors",
                        "Verify dependencies are accessible",
                        "Review application configuration",
                    ],
                }
            else:
                return {
                    "check_name": "HTTP Health Endpoint",
                    "status": "WARN",
                    "message": f"HTTP {response.status_code} unexpected status",
                    "details": {
                        "url": url,
                        "status_code": response.status_code,
                    },
                    "suggestions": [
                        "Review response status code",
                        "Check application logs",
                    ],
                }

    except httpx.TimeoutException:
        return {
            "check_name": "HTTP Health Endpoint",
            "status": "FAIL",
            "message": f"HTTP request timeout after {timeout}s",
            "details": {
                "url": url if 'url' in locals() else endpoint,
                "timeout": timeout,
            },
            "suggestions": [
                "Check if container is responding slowly",
                "Verify dependencies are accessible",
                "Consider increasing timeout",
            ],
        }
    except httpx.ConnectError as e:
        return {
            "check_name": "HTTP Health Endpoint",
            "status": "FAIL",
            "message": f"Connection failed: {e}",
            "details": {
                "url": url if 'url' in locals() else endpoint,
            },
            "suggestions": [
                "Check if ingress is enabled",
                "Verify container is running",
                "Ensure container is listening on correct port",
            ],
        }
    except httpx.HTTPError as e:
        return {
            "check_name": "HTTP Health Endpoint",
            "status": "FAIL",
            "message": f"HTTP error: {e}",
            "details": {
                "url": url if 'url' in locals() else endpoint,
            },
            "suggestions": [
                "Check error message for details",
                "Verify endpoint is accessible",
            ],
        }
    except Exception as e:
        return {
            "check_name": "HTTP Health Endpoint",
            "status": "FAIL",
            "message": f"Unexpected error: {e}",
            "details": {
                "error_type": type(e).__name__,
            },
            "suggestions": [
                "Check error message for details",
                "Verify endpoint format is correct",
            ],
        }


async def run_health_checks(
    client: ContainerAppsClient,
    app_name: str,
    deep: bool = False,
    timeout: int = 30,
    health_path: str = "/health",
) -> list[dict[str, Any]]:
    """Run all health checks in parallel.

    Executes multiple health checks concurrently for faster results.
    Basic checks always run; deep checks (HTTP endpoint) are optional.

    Args:
        client: Container Apps client
        app_name: Container app name
        deep: Run deep checks including HTTP endpoint (default: False)
        timeout: Total timeout in seconds for all checks (default: 30)
        health_path: Path for HTTP health endpoint (default: "/health")

    Returns:
        List of health check results, one per check

    Example:
        >>> import asyncio
        >>> from haymaker_cli.orch import ContainerAppsClient
        >>> client = ContainerAppsClient("sub-id", "rg")
        >>> results = asyncio.run(
        ...     run_health_checks(client, "my-app", deep=True)
        ... )  # doctest: +SKIP
        >>> len(results) >= 3  # doctest: +SKIP
        True
    """
    # Calculate per-check timeout
    num_basic_checks = 3
    num_deep_checks = 1 if deep else 0
    total_checks = num_basic_checks + num_deep_checks
    check_timeout = timeout / total_checks

    # Build list of checks to run
    checks = [
        check_container_app_status(client, app_name, timeout=check_timeout),
        check_replica_health(client, app_name, timeout=check_timeout),
    ]

    # Get endpoint for connectivity and HTTP checks
    try:
        app = await asyncio.wait_for(
            client.get_container_app(app_name),
            timeout=check_timeout,
        )
        endpoint = app.latest_revision_fqdn
    except Exception:
        # If we can't get the app, endpoint checks will fail gracefully
        endpoint = None

    if endpoint:
        checks.append(
            check_endpoint_connectivity(f"https://{endpoint}", timeout=check_timeout)
        )

        # Add deep HTTP check if requested
        if deep:
            checks.append(
                check_http_health_endpoint(
                    f"https://{endpoint}",
                    path=health_path,
                    timeout=check_timeout,
                )
            )
    else:
        # Add a check result indicating endpoint is not available
        async def _failed_endpoint_check():
            return {
                "check_name": "Endpoint Connectivity",
                "status": "FAIL",
                "message": "Could not determine endpoint",
                "details": {},
                "suggestions": [
                    "Check if ingress is enabled",
                    "Verify app is deployed",
                ],
            }
        checks.append(_failed_endpoint_check())

    # Run all checks in parallel
    results = await asyncio.gather(*checks, return_exceptions=True)

    # Convert exceptions to failure results
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({
                "check_name": f"Check {i+1}",
                "status": "FAIL",
                "message": f"Check failed: {result}",
                "details": {"error_type": type(result).__name__},
                "suggestions": ["Check error message for details"],
            })
        else:
            final_results.append(result)

    return final_results


__all__ = [
    "check_container_app_status",
    "check_endpoint_connectivity",
    "check_replica_health",
    "check_http_health_endpoint",
    "run_health_checks",
]
