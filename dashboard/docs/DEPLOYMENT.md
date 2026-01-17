# Dashboard Deployment Guide

This guide covers deploying the Analytics Dashboard to Azure Static Web Apps and connecting it to the AzureHayMaker orchestrator.

## Prerequisites

Before deploying, ensure you have:

1. **Azure Subscription** with permissions to create resources
2. **Azure CLI** installed and configured (`az login`)
3. **Node.js 20+** and npm 10+ installed
4. **GitHub Repository** with the AzureHayMaker code
5. **AzureHayMaker Orchestrator** already deployed and running

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│  Azure Static Web App (Frontend)            │
│  - React Dashboard                          │
│  - Azure AD B2C Authentication             │
│  - CDN Distribution                         │
└─────────────────────────────────────────────┘
                    │
                    │ HTTPS / WebSocket
                    ▼
┌─────────────────────────────────────────────┐
│  Azure Container Apps (Backend)             │
│  - FastAPI Orchestrator Server             │
│  - WebSocket /ws/metrics endpoint          │
│  - REST API endpoints                       │
└─────────────────────────────────────────────┘
```

## Option 1: Automated Deployment (GitHub Actions)

### Step 1: Configure GitHub Secrets

Add these secrets to your GitHub repository:

```bash
# Azure Static Web Apps deployment token
AZURE_STATIC_WEB_APPS_API_TOKEN

# Optional: Azure credentials for other resources
AZURE_CREDENTIALS
```

### Step 2: Enable GitHub Actions Workflow

The repository includes a pre-configured workflow at `.github/workflows/dashboard-deploy.yml`:

```yaml
name: Deploy Dashboard

on:
  push:
    branches: [main]
    paths:
      - 'dashboard/**'
      - '.github/workflows/dashboard-deploy.yml'
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: dashboard/package-lock.json

      - name: Install dependencies
        working-directory: dashboard
        run: npm ci

      - name: Run tests
        working-directory: dashboard
        run: npm test

      - name: Build dashboard
        working-directory: dashboard
        run: npm run build
        env:
          VITE_API_BASE_URL: ${{ secrets.VITE_API_BASE_URL }}
          VITE_WS_URL: ${{ secrets.VITE_WS_URL }}

      - name: Deploy to Azure Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: 'upload'
          app_location: 'dashboard'
          output_location: 'dist'
```

### Step 3: Trigger Deployment

Push changes to the `main` branch:

```bash
git add .
git commit -m "Deploy dashboard"
git push origin main
```

GitHub Actions will automatically:
1. Install dependencies
2. Run tests
3. Build the dashboard
4. Deploy to Azure Static Web Apps

## Option 2: Manual Deployment (Azure CLI)

### Step 1: Create Azure Static Web App

```bash
# Set variables
RESOURCE_GROUP="haymaker-rg"
LOCATION="westus2"
APP_NAME="haymaker-dashboard"
GITHUB_REPO="https://github.com/rysweet/AzureHayMaker"
BRANCH="main"

# Create Static Web App
az staticwebapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --source $GITHUB_REPO \
  --location $LOCATION \
  --branch $BRANCH \
  --app-location "dashboard" \
  --output-location "dist" \
  --login-with-github
```

### Step 2: Configure Environment Variables

```bash
# Set build-time environment variables
az staticwebapp appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --setting-names \
    VITE_API_BASE_URL="https://your-orchestrator.azurecontainerapps.io" \
    VITE_WS_URL="wss://your-orchestrator.azurecontainerapps.io/ws/metrics"
```

### Step 3: Verify Deployment

```bash
# Get the Static Web App URL
az staticwebapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "defaultHostname" \
  --output tsv
```

Open the URL in your browser to verify the dashboard is running.

## Option 3: Local Build and Manual Upload

### Step 1: Build Dashboard Locally

```bash
cd dashboard

# Install dependencies
npm install

# Create production build
npm run build
```

### Step 2: Deploy Using Azure CLI

```bash
# Zip the dist directory
cd dist
zip -r ../dashboard-dist.zip .
cd ..

# Upload to Azure Static Web Apps
az staticwebapp environment set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --source dashboard-dist.zip
```

## Post-Deployment Configuration

### 1. Configure Custom Domain (Optional)

```bash
# Add custom domain
az staticwebapp hostname set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname "dashboard.yourdomain.com"
```

### 2. Configure Azure AD B2C Authentication

#### Create Azure AD B2C Application

```bash
# Create app registration
az ad app create \
  --display-name "HayMaker Dashboard" \
  --sign-in-audience "AzureADMyOrg" \
  --web-redirect-uris "https://$APP_NAME.azurestaticapps.net/.auth/login/aad/callback"
```

#### Configure Static Web App Authentication

Create `staticwebapp.config.json` in the dashboard root:

```json
{
  "auth": {
    "identityProviders": {
      "azureActiveDirectory": {
        "userDetailsClaim": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "registration": {
          "openIdIssuer": "https://login.microsoftonline.com/<tenant-id>/v2.0",
          "clientIdSettingName": "AAD_CLIENT_ID",
          "clientSecretSettingName": "AAD_CLIENT_SECRET"
        }
      }
    }
  },
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["authenticated"]
    }
  ],
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/images/*.{png,jpg,gif}", "/css/*"]
  },
  "responseOverrides": {
    "401": {
      "redirect": "/.auth/login/aad",
      "statusCode": 302
    }
  }
}
```

#### Set Authentication Secrets

```bash
# Set AAD credentials
az staticwebapp appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --setting-names \
    AAD_CLIENT_ID="<your-client-id>" \
    AAD_CLIENT_SECRET="<your-client-secret>"
```

### 3. Configure CORS on Orchestrator

Update your orchestrator's FastAPI application to allow the Static Web App origin:

```python
# In src/azure_haymaker/orchestrator/app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://haymaker-dashboard.azurestaticapps.net",
        "http://localhost:5173",  # For development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy the orchestrator after making CORS changes.

### 4. Configure WebSocket Support

Ensure your orchestrator's Container App allows WebSocket connections:

```bash
# Enable WebSocket on Container App
az containerapp update \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --enable-websockets
```

## Monitoring and Maintenance

### View Deployment Logs

```bash
# View recent deployments
az staticwebapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

# View environment details
az staticwebapp environment show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP
```

### Application Insights Integration

Enable Application Insights for monitoring:

```bash
# Create Application Insights
az monitor app-insights component create \
  --app haymaker-dashboard-insights \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app haymaker-dashboard-insights \
  --resource-group $RESOURCE_GROUP \
  --query "instrumentationKey" \
  --output tsv)

# Add to Static Web App settings
az staticwebapp appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --setting-names \
    APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=$INSTRUMENTATION_KEY"
```

### Update Dashboard

For updates:

```bash
# Option 1: Push to GitHub (automatic deployment)
git push origin main

# Option 2: Manual build and deploy
cd dashboard
npm run build
# Follow manual upload steps above
```

## Rollback

### Rollback to Previous Deployment

```bash
# List deployments
az staticwebapp environment list \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

# Rollback to specific deployment
az staticwebapp environment restore \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment-id <environment-id>
```

## Troubleshooting

### Build Failures

Check GitHub Actions logs or local build output:

```bash
# Local build with verbose output
npm run build -- --debug
```

### Runtime Errors

1. **Check Browser Console**: Look for JavaScript errors
2. **Verify Environment Variables**: Ensure API URLs are correct
3. **Check Network Tab**: Look for failed API requests
4. **Review CORS**: Verify orchestrator allows dashboard origin

### WebSocket Connection Issues

```bash
# Test WebSocket endpoint
wscat -c wss://your-orchestrator.azurecontainerapps.io/ws/metrics

# Check Container App logs
az containerapp logs show \
  --name haymaker-orchestrator \
  --resource-group $RESOURCE_GROUP \
  --follow
```

## Security Considerations

1. **Always use HTTPS** - Never deploy without SSL/TLS
2. **Enable Authentication** - Use Azure AD B2C or similar
3. **Rotate Secrets Regularly** - Update client secrets periodically
4. **Monitor Access Logs** - Review Application Insights for suspicious activity
5. **Limit CORS Origins** - Only allow specific dashboard domains

## Cost Optimization

Azure Static Web Apps pricing:
- **Free Tier**: 100 GB bandwidth/month, 2 custom domains
- **Standard Tier**: $9/month, 100 GB included, then $0.20/GB

Recommended for production:
- Start with Free tier for development/staging
- Use Standard tier for production with custom domain
- Monitor bandwidth usage in Azure Portal

## Support and Resources

- [Azure Static Web Apps Documentation](https://docs.microsoft.com/en-us/azure/static-web-apps/)
- [Azure Container Apps Documentation](https://docs.microsoft.com/en-us/azure/container-apps/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Project Issues](https://github.com/rysweet/AzureHayMaker/issues)

## Next Steps

After deployment:
1. Test all dashboard features
2. Configure monitoring and alerts
3. Set up backup and disaster recovery
4. Document custom configurations
5. Train team on dashboard usage
