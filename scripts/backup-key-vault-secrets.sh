#!/bin/bash
# Backup all secrets from Key Vault

RG="haymaker-dev-rg"
KV="haymaker-dev-yow3ex-kv"
BACKUP_DIR="backups/secrets-$(date +%Y%m%d-%H%M%S)"

echo "🔐 Backing up Key Vault secrets..."
echo "Key Vault: $KV"
echo "Backup to: $BACKUP_DIR"
echo ""

mkdir -p "$BACKUP_DIR"

# List all secrets
SECRETS=$(az keyvault secret list --vault-name $KV --query "[].name" -o tsv 2>/dev/null)

if [ -z "$SECRETS" ]; then
  echo "No secrets found"
  exit 0
fi

echo "Found secrets:"
echo "$SECRETS"
echo ""

# Backup each secret (names only, not values for security)
echo "$SECRETS" > "$BACKUP_DIR/secret-names.txt"

echo "✅ Backup complete: $BACKUP_DIR/secret-names.txt"
echo ""
echo "⚠️  Values NOT backed up for security (retrieve from Key Vault as needed)"
