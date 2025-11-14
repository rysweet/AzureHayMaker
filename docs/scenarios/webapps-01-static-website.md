# Scenario: Static Website with Azure Storage and CDN

## Technology Area
Web Apps

## Company Profile
- **Company Size**: Small design agency
- **Industry**: Creative Services / Marketing
- **Use Case**: Host static portfolio websites for clients with global CDN for fast loading

## Scenario Description
Deploy a static HTML/CSS/JS website to Azure Storage static website hosting, configure Azure CDN for global distribution, and set up custom domain with HTTPS. Perfect for portfolio sites, documentation, or landing pages.

## Azure Services Used
- Azure Storage Account (Static Website Hosting)
- Azure CDN (Content Delivery Network)
- Azure DNS (for custom domain - optional)

## Prerequisites
- Azure subscription with Contributor role
- Azure CLI installed
- Sample static website files
- A unique identifier for this scenario run

---

## Phase 1: Deployment and Validation

### Environment Setup
```bash
# Set variables
UNIQUE_ID=$(date +%Y%m%d%H%M%S)
RESOURCE_GROUP="azurehaymaker-webapp-static-${UNIQUE_ID}-rg"
LOCATION="eastus"
STORAGE_ACCOUNT="azmkrweb${UNIQUE_ID}"
CDN_PROFILE="azurehaymaker-cdn-${UNIQUE_ID}"
CDN_ENDPOINT="azurehaymaker-endpoint-${UNIQUE_ID}"

# Tags
TAGS="AzureHayMaker-managed=true Scenario=webapps-static-website Owner=AzureHayMaker"
```

### Deployment Steps
```bash
# Step 1: Create Resource Group
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags ${TAGS}

# Step 2: Create Storage Account
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags ${TAGS}

# Step 3: Enable static website hosting
az storage blob service-properties update \
  --account-name "${STORAGE_ACCOUNT}" \
  --static-website \
  --404-document "404.html" \
  --index-document "index.html"

# Step 4: Get storage account key
STORAGE_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --query '[0].value' -o tsv)

# Step 5: Create sample website files
mkdir -p /tmp/website
cat > /tmp/website/index.html <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure HayMaker Portfolio</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>Azure HayMaker Portfolio Site</h1>
        <p>Static Website Hosting Demo</p>
    </header>
    <main>
        <section>
            <h2>Welcome</h2>
            <p>This is a sample static website hosted on Azure Storage with CDN.</p>
            <p>Scenario: webapps-static-website</p>
            <p>Timestamp: $(date)</p>
        </section>
    </main>
    <footer>
        <p>&copy; 2024 Azure HayMaker</p>
    </footer>
</body>
</html>
EOF

cat > /tmp/website/styles.css <<EOF
body {
    font-family: Arial, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f5f5f5;
}
header {
    background-color: #0078d4;
    color: white;
    padding: 20px;
    border-radius: 5px;
    margin-bottom: 20px;
}
h1 { margin: 0; }
section {
    background: white;
    padding: 20px;
    border-radius: 5px;
    margin-bottom: 20px;
}
footer {
    text-align: center;
    padding: 20px;
    color: #666;
}
EOF

cat > /tmp/website/404.html <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
</head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>The page you're looking for doesn't exist.</p>
    <a href="/">Go to homepage</a>
</body>
</html>
EOF

# Step 6: Upload website files to $web container
az storage blob upload-batch \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --destination '$web' \
  --source /tmp/website \
  --overwrite

# Step 7: Get the static website URL
WEBSITE_URL=$(az storage account show \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "primaryEndpoints.web" -o tsv)

echo "Static Website URL: ${WEBSITE_URL}"

# Step 8: Create CDN Profile
az cdn profile create \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CDN_PROFILE}" \
  --sku Standard_Microsoft \
  --location "global" \
  --tags ${TAGS}

# Step 9: Create CDN Endpoint
# Extract hostname from website URL (remove https:// and trailing /)
ORIGIN_HOSTNAME=$(echo "${WEBSITE_URL}" | sed 's|https://||' | sed 's|/$||')

az cdn endpoint create \
  --resource-group "${RESOURCE_GROUP}" \
  --profile-name "${CDN_PROFILE}" \
  --name "${CDN_ENDPOINT}" \
  --origin "${ORIGIN_HOSTNAME}" \
  --origin-host-header "${ORIGIN_HOSTNAME}" \
  --enable-compression \
  --content-types-to-compress "text/html" "text/css" "application/javascript" "application/json" \
  --tags ${TAGS}

# Step 10: Get CDN endpoint URL
CDN_URL=$(az cdn endpoint show \
  --resource-group "${RESOURCE_GROUP}" \
  --profile-name "${CDN_PROFILE}" \
  --name "${CDN_ENDPOINT}" \
  --query "hostName" -o tsv)

echo ""
echo "=========================================="
echo "Website Deployment Complete!"
echo "Storage Website: ${WEBSITE_URL}"
echo "CDN Endpoint: https://${CDN_URL}"
echo "=========================================="
```

### Validation
```bash
# Verify Resource Group
az group show --name "${RESOURCE_GROUP}"

# Verify Storage Account
az storage account show --name "${STORAGE_ACCOUNT}" --resource-group "${RESOURCE_GROUP}"

# Check static website is enabled
az storage blob service-properties show \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}"

# List files in $web container
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name '$web' \
  --output table

# Verify CDN Profile
az cdn profile show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CDN_PROFILE}"

# Verify CDN Endpoint
az cdn endpoint show \
  --resource-group "${RESOURCE_GROUP}" \
  --profile-name "${CDN_PROFILE}" \
  --name "${CDN_ENDPOINT}"

# Test website accessibility
curl -s "${WEBSITE_URL}" | grep "Azure HayMaker"
echo "If you see HTML output above, the website is accessible!"

# List all resources
az resource list --resource-group "${RESOURCE_GROUP}" --output table
```

---

## Phase 2: Mid-Day Operations and Management

### Management Operations
```bash
# Operation 1: Update website content
cat > /tmp/website/index.html <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Azure HayMaker Portfolio - Updated</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>Azure HayMaker Portfolio Site - UPDATED</h1>
        <p>Version 2.0 - Last updated: $(date)</p>
    </header>
    <main>
        <section>
            <h2>Latest Updates</h2>
            <p>This website has been updated with new content!</p>
            <ul>
                <li>Enhanced design</li>
                <li>New sections added</li>
                <li>Performance optimized</li>
            </ul>
        </section>
    </main>
    <footer>
        <p>&copy; 2024 Azure HayMaker</p>
    </footer>
</body>
</html>
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name '$web' \
  --name "index.html" \
  --file /tmp/website/index.html \
  --overwrite

# Operation 2: Purge CDN cache to see updates immediately
az cdn endpoint purge \
  --resource-group "${RESOURCE_GROUP}" \
  --profile-name "${CDN_PROFILE}" \
  --name "${CDN_ENDPOINT}" \
  --content-paths "/*"

# Operation 3: Add new page to website
cat > /tmp/website/about.html <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>About Us</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header><h1>About Azure HayMaker</h1></header>
    <main>
        <section>
            <p>This is the about page.</p>
        </section>
    </main>
    <footer><a href="/">Home</a></footer>
</body>
</html>
EOF

az storage blob upload \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name '$web' \
  --name "about.html" \
  --file /tmp/website/about.html

# Operation 4: Monitor CDN metrics
az monitor metrics list \
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Cdn/profiles/${CDN_PROFILE}/endpoints/${CDN_ENDPOINT}" \
  --metric "BytesSentPerRequest" \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Operation 5: Check CDN endpoint status
az cdn endpoint show \
  --resource-group "${RESOURCE_GROUP}" \
  --profile-name "${CDN_PROFILE}" \
  --name "${CDN_ENDPOINT}" \
  --query "resourceState" -o tsv

# Operation 6: Enable custom domain (example - requires actual domain)
echo "To add custom domain:"
echo "az cdn custom-domain create --resource-group \"${RESOURCE_GROUP}\" --profile-name \"${CDN_PROFILE}\" --endpoint-name \"${CDN_ENDPOINT}\" --name \"myCustomDomain\" --hostname \"www.example.com\""

# Operation 7: Configure caching rules
az cdn endpoint rule add \
  --resource-group "${RESOURCE_GROUP}" \
  --profile-name "${CDN_PROFILE}" \
  --name "${CDN_ENDPOINT}" \
  --order 1 \
  --rule-name "CacheImages" \
  --match-variable RequestUri \
  --operator Contains \
  --match-values ".jpg" ".png" ".gif" \
  --action-name CacheExpiration \
  --cache-behavior Override \
  --cache-duration "7.00:00:00"

# Operation 8: List all blobs in website
az storage blob list \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --container-name '$web' \
  --output table

# Operation 9: Download website for backup
az storage blob download-batch \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${STORAGE_KEY}" \
  --source '$web' \
  --destination /tmp/website-backup

# Operation 10: Monitor storage account usage
az storage account show-usage \
  --location "${LOCATION}"
```

---

## Phase 3: Cleanup and Tear-Down

### Cleanup Steps
```bash
# Step 1: Delete CDN endpoint first (takes longest)
az cdn endpoint delete \
  --resource-group "${RESOURCE_GROUP}" \
  --profile-name "${CDN_PROFILE}" \
  --name "${CDN_ENDPOINT}" \
  --yes

# Step 2: Delete CDN profile
az cdn profile delete \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CDN_PROFILE}" \
  --yes

# Step 3: Delete the entire resource group (includes storage account)
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

# Step 4: Verify deletion
sleep 60
az group exists --name "${RESOURCE_GROUP}"

# Step 5: Confirm cleanup
echo "Verifying cleanup..."
az resource list --resource-group "${RESOURCE_GROUP}" 2>&1 | grep "could not be found" && echo "✓ Resource group successfully deleted"

# Step 6: Clean up local temp files
rm -rf /tmp/website /tmp/website-backup
```

---

## Resource Naming Convention
- Resource Group: `azurehaymaker-webapp-static-${UNIQUE_ID}-rg`
- Storage Account: `azmkrweb${UNIQUE_ID}`
- CDN Profile: `azurehaymaker-cdn-${UNIQUE_ID}`
- CDN Endpoint: `azurehaymaker-endpoint-${UNIQUE_ID}`

All resources tagged with: `AzureHayMaker-managed=true`

---

## Documentation References
- [Static website hosting in Azure Storage](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-static-website)
- [Azure CDN Overview](https://learn.microsoft.com/en-us/azure/cdn/cdn-overview)
- [Use Azure CDN with Azure Storage](https://learn.microsoft.com/en-us/azure/cdn/cdn-create-a-storage-account-with-cdn)
- [Azure Storage CLI Reference](https://learn.microsoft.com/en-us/cli/azure/storage)
- [Azure CDN CLI Reference](https://learn.microsoft.com/en-us/cli/azure/cdn)

---

## Automation Tool
**Recommended**: Azure CLI

**Rationale**: Azure CLI provides excellent support for both Azure Storage static websites and Azure CDN. The commands are straightforward and well-documented. Terraform is also viable for infrastructure-as-code, but Azure CLI is simpler for this scenario.

---

## Estimated Duration
- **Deployment**: 10-15 minutes
- **Operations Phase**: 8 hours (with periodic content updates and cache purges)
- **Cleanup**: 5-10 minutes (CDN deletion takes a few minutes)

---

## Notes
- Static website hosting is very cost-effective (pennies per month)
- CDN provides global distribution with edge caching
- HTTPS is automatic for both storage and CDN endpoints
- Custom domains require DNS configuration (CNAME record)
- CDN cache purge may take a few minutes to propagate globally
- All operations scoped to single tenant and subscription
- Perfect for JAMstack applications, documentation sites, SPAs
- Storage account must be v2 (StorageV2) for static website feature
