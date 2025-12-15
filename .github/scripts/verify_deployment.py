#!/usr/bin/env python3
"""GitHub Actions script for deployment verification

This script wraps the DeploymentVerifier to verify deployment health.

Usage:
    python verify_deployment.py \\
        --subscription-id <sub-id> \\
        --resource-group <rg> \\
        --container-app <app-name> \\
        --orchestrator-url <url>
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path so we can import azure_haymaker
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from azure_haymaker.orchestrator.deployment_verifier import (
    APIEndpointError,
    ContainerHealthError,
    DeploymentVerifier,
    RBACPermissionError,
)


def main():
    """Main entry point for deployment verification script"""
    parser = argparse.ArgumentParser(description="Verify deployment health for Container App")
    parser.add_argument("--subscription-id", required=True, help="Azure subscription ID")
    parser.add_argument("--resource-group", required=True, help="Resource group name")
    parser.add_argument("--container-app", required=True, help="Container app name")
    parser.add_argument("--orchestrator-url", required=True, help="Orchestrator base URL")
    parser.add_argument(
        "--wait-ready",
        action="store_true",
        help="Wait for container to become ready",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Overall timeout in seconds (default: 300)",
    )

    args = parser.parse_args()

    print(f"Starting deployment verification for '{args.container_app}'")
    print(f"Orchestrator URL: {args.orchestrator_url}")
    print(f"Resource Group: {args.resource_group}")

    try:
        # Create verifier
        verifier = DeploymentVerifier(
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            orchestrator_url=args.orchestrator_url,
            timeout_seconds=args.timeout,
        )

        # Verify container health
        print("\n1. Checking container health...")
        verifier.check_container_health(
            container_app_name=args.container_app, wait_ready=args.wait_ready
        )
        print("   ✓ Container is healthy")

        # Verify API endpoints
        print("\n2. Verifying API endpoints...")
        api_endpoints = [
            "/api/status",
            "/api/resources",
        ]

        for endpoint in api_endpoints:
            try:
                verifier.verify_api_endpoint(endpoint, max_retries=3)
                print(f"   ✓ {endpoint} is accessible")
            except APIEndpointError as e:
                print(f"   ✗ {endpoint} failed: {e}")
                raise

        # Generate verification report
        print("\n3. Generating verification report...")
        report = verifier.generate_verification_report(
            container_app_name=args.container_app,
            api_endpoints=api_endpoints,
        )

        print(f"\n{'=' * 60}")
        print("DEPLOYMENT VERIFICATION REPORT")
        print(f"{'=' * 60}")
        print(f"Container App: {report['container_app_name']}")
        print(f"Verification Time: {report['verification_time']}")
        print(f"Checks Passed: {report['checks_passed']}")
        print(f"Checks Failed: {report['checks_failed']}")
        print(f"\nOverall Status: {'✓ SUCCESS' if report['results']['success'] else '✗ FAILED'}")
        print(f"{'=' * 60}\n")

        # Export report for GitHub Actions
        report_file = Path("/tmp/verification-report.json")
        report_file.write_text(json.dumps(report, indent=2))
        print(f"Report saved to: {report_file}")

        if not report["results"]["success"]:
            print("\n✗ Deployment verification failed!")
            return 1

        print("\n✓ Deployment verification completed successfully!")
        return 0

    except ContainerHealthError as e:
        print(f"\n✗ Container health check failed: {e}", file=sys.stderr)
        print("Please check container logs for errors:", file=sys.stderr)
        print(
            f"  az containerapp logs show -n {args.container_app} -g {args.resource_group}",
            file=sys.stderr,
        )
        return 1

    except APIEndpointError as e:
        print(f"\n✗ API endpoint verification failed: {e}", file=sys.stderr)
        print("Please check:", file=sys.stderr)
        print("  1. Container app is running", file=sys.stderr)
        print("  2. API endpoints are implemented", file=sys.stderr)
        print("  3. Network connectivity is working", file=sys.stderr)
        return 1

    except RBACPermissionError as e:
        print(f"\n✗ RBAC permission check failed: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
