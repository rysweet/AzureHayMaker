#!/usr/bin/env python3
"""GitHub Actions script for secret injection

This script wraps the SecretInjectionHandler to inject secrets from Key Vault
into the container app with RBAC propagation wait.

Usage:
    python inject_secrets.py \\
        --subscription-id <sub-id> \\
        --resource-group <rg> \\
        --container-app <app-name> \\
        --keyvault <kv-name> \\
        --principal-id <principal-id>
"""

import argparse
import sys
from pathlib import Path

# Add src to path so we can import azure_haymaker
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from azure_haymaker.orchestrator.secret_injection_handler import (
    RBACPropagationError,
    SecretInjectionError,
    SecretInjectionHandler,
)


def main():
    """Main entry point for secret injection script"""
    parser = argparse.ArgumentParser(description="Inject secrets from Key Vault to Container App")
    parser.add_argument("--subscription-id", required=True, help="Azure subscription ID")
    parser.add_argument("--resource-group", required=True, help="Resource group name")
    parser.add_argument("--container-app", required=True, help="Container app name")
    parser.add_argument("--keyvault", required=True, help="Key Vault name")
    parser.add_argument("--principal-id", required=True, help="Managed identity principal ID")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retry attempts (default: 5)",
    )
    parser.add_argument(
        "--initial-backoff",
        type=int,
        default=10,
        help="Initial backoff delay in seconds (default: 10)",
    )

    args = parser.parse_args()

    print(f"Starting secret injection for container app '{args.container_app}'")
    print(f"Key Vault: {args.keyvault}")
    print(f"Resource Group: {args.resource_group}")

    try:
        # Create handler
        handler = SecretInjectionHandler(
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
            max_retries=args.max_retries,
            initial_backoff_seconds=args.initial_backoff,
        )

        # Wait for RBAC propagation
        print("\nWaiting for RBAC propagation (this may take several minutes)...")
        handler.wait_for_rbac_propagation(
            keyvault_name=args.keyvault,
            identity_principal_id=args.principal_id,
        )
        print("RBAC propagation complete!")

        # Inject secrets
        print("\nInjecting secrets to container app...")
        # Note: Container Apps secret names must be lowercase
        secrets = [
            {
                "name": "anthropic-api-key",  # Secret name (lowercase required)
                "keyvault_secret": "anthropic-api-key",  # Key Vault secret name
            },
        ]

        handler.inject_secrets_to_container_app(
            container_app_name=args.container_app,
            keyvault_name=args.keyvault,
            secrets=secrets,
        )

        print("\n✓ Secret injection completed successfully!")
        return 0

    except RBACPropagationError as e:
        print(f"\n✗ RBAC propagation timeout: {e}", file=sys.stderr)
        print(
            "The role assignment may not have propagated yet. Please check:",
            file=sys.stderr,
        )
        print(
            "  1. Verify managed identity has 'Key Vault Secrets User' role",
            file=sys.stderr,
        )
        print(f"  2. Check principal ID: {args.principal_id}", file=sys.stderr)
        print("  3. Wait a few minutes and retry", file=sys.stderr)
        return 1

    except SecretInjectionError as e:
        print(f"\n✗ Secret injection failed: {e}", file=sys.stderr)
        print(
            "Please check container app configuration and permissions.",
            file=sys.stderr,
        )
        return 1

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
