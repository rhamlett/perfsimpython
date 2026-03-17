# Azure Deployment Guide

Deploy Performance Problem Simulator to Azure App Service using GitHub Actions with OIDC authentication.

## Overview

This guide walks you through deploying the Performance Problem Simulator to Azure App Service using GitHub Actions with OpenID Connect (OIDC) authentication. OIDC eliminates the need to store credentials as secrets.

### Prerequisites

- Azure subscription with permissions to create resources
- Azure AD/Entra ID permissions to create App Registrations
- GitHub account
- Azure CLI installed (optional, for CLI method)

### What You'll Create

| Resource | Purpose |
|----------|---------|
| Azure App Service | Hosts the Performance Problem Simulator application |
| Azure AD App Registration | Identity for GitHub Actions OIDC |
| Federated Credential | Links GitHub repo to Azure AD |
| Role Assignment | Grants deployment permissions |

## Step 1: Create Azure App Service

### Option A: Azure Portal

1. **Navigate to App Services**
   - Go to [Azure Portal](https://portal.azure.com)
   - Search for "App Services" and select it
   - Click **+ Create**

2. **Configure Basics**

   | Setting | Value |
   |---------|-------|
   | Subscription | Your subscription |
   | Resource Group | Create new or use existing |
   | Name | `your-app-name` (must be globally unique) |
   | Publish | Code |
   | Runtime stack | Select your application's runtime |
   | Operating System | Windows or Linux (as appropriate for your runtime) |
   | Region | Your preferred region |

3. **Configure App Service Plan**

   | Setting | Recommendation |
   |---------|---------------|
   | SKU | **Basic B1** or higher |

   > ⚠️ **Important:** The Free (F1) tier does not support WebSockets which are required for real-time SignalR dashboard updates.

4. **Review and Create** - Click through to create the resource

### Option B: Azure CLI

```bash
# Login to Azure
az login

# Set variables
RESOURCE_GROUP="your-resource-group"
APP_NAME="your-app-name"
LOCATION="eastus"
APP_SERVICE_PLAN="your-app-plan"
RUNTIME="your-runtime"  # e.g., "dotnet:8", "node:20-lts", "python:3.11"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service Plan (B1 for WebSocket support)
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku B1

# Create Web App with your runtime
az webapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --runtime $RUNTIME
```

### Enable WebSockets

After creation, enable WebSockets for SignalR real-time communication:

1. Go to your App Service → **Configuration** → **General settings**
2. Set **Web sockets** to **On**
3. Click **Save**

Or via CLI:

```bash
az webapp config set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --web-sockets-enabled true
```

## Step 2: Create Azure AD App Registration

GitHub Actions uses OpenID Connect (OIDC) to authenticate with Azure without storing credentials.

### Create the App Registration

1. **Navigate to App Registrations**
   - Go to [Azure Portal](https://portal.azure.com)
   - Search for "App registrations" and select it
   - Click **+ New registration**

2. **Configure Registration**

   | Setting | Value |
   |---------|-------|
   | Name | `github-your-app-deploy` (descriptive name for your deployment identity) |
   | Supported account types | Accounts in this organizational directory only |
   | Redirect URI | Leave empty |

3. **Click Register**

### Record the IDs

From the **Overview** page, copy these values (you'll need them for GitHub secrets):

| Value | GitHub Secret Name |
|-------|-------------------|
| Application (client) ID | `AZURE_CLIENT_ID` |
| Directory (tenant) ID | `AZURE_TENANT_ID` |

### Get Subscription ID

1. Go to **Subscriptions** in the Azure Portal
2. Select your subscription
3. Copy the **Subscription ID** → This is `AZURE_SUBSCRIPTION_ID`

## Step 3: Configure Federated Credentials

Federated credentials allow GitHub Actions to authenticate without storing secrets.

1. **Navigate to your App Registration**
   - Go to **Certificates & secrets**
   - Select **Federated credentials** tab
   - Click **+ Add credential**

2. **Configure the Credential**

   | Setting | Value |
   |---------|-------|
   | Federated credential scenario | **GitHub Actions deploying Azure resources** |
   | Organization | Your GitHub username or organization |
   | Repository | Your repository name |
   | Entity type | **Branch** |
   | GitHub branch name | `main` |
   | Name | `github-main-branch` |

3. **Click Add**

> 💡 **Note:** If you also want to deploy from pull requests or other branches, add additional federated credentials with the appropriate entity type.

## Step 4: Grant Azure Permissions

The App Registration needs permission to deploy to your App Service.

### Assign Contributor Role

1. **Navigate to your App Service**
   - Go to **Access control (IAM)**
   - Click **+ Add** → **Add role assignment**

2. **Configure Role Assignment**

   | Setting | Value |
   |---------|-------|
   | Role | **Contributor** |
   | Assign access to | User, group, or service principal |
   | Members | Search for your App Registration name |

3. **Click Review + assign**

## Step 5: Configure GitHub Secrets

### Fork or Clone the Repository

1. **Fork the Repository**
   - Go to the Performance Problem Simulator repository for your stack
   - Click **Fork** to create your own copy

### Add GitHub Secrets

1. **Navigate to Repository Settings**
   - Go to your repository on GitHub
   - Click **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**

2. **Add the Following Secrets**

   | Secret Name | Value | Description |
   |-------------|-------|-------------|
   | AZURE_CLIENT_ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | App Registration Client ID |
   | AZURE_TENANT_ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | Azure AD Directory/Tenant ID |
   | AZURE_SUBSCRIPTION_ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | Azure Subscription ID |

> 💡 **No Client Secret Needed:** OIDC federated credentials eliminate the need to store a client secret. The three IDs above are sufficient.

### Update Workflow (if needed)

Update `.github/workflows/deploy.yml` with your App Service name and runtime version:

```yaml
env:
  AZURE_WEBAPP_NAME: your-app-service-name  # Your App Service name
  # Add any runtime-specific version variables as needed
```

## Step 6: Deploy

### Automatic Deployment

Deployment triggers automatically when you push to the `main` branch:

```bash
git add .
git commit -m "Your changes"
git push origin main
```

### Manual Deployment

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **Deploy to Azure App Service**
4. Click **Run workflow** → **Run workflow**

### Verify Deployment

1. **Open the App URL**: `https://<your-app-name>.azurewebsites.net`
2. **Verify Dashboard**: Real-time metrics should update via SignalR, status should show "Connected"
3. **Test Health Endpoint**:
   ```bash
   curl https://<your-app-name>.azurewebsites.net/api/health
   ```

## Optional Configuration

You can customize the application behavior using Azure App Service environment variables.

### Health Probe Rate

Control how often the server sends health probes to measure request latency. All probes are routed through the Azure frontend to capture realistic end-to-end latency.

| Variable Name | Description | Default |
|---------------|-------------|---------|
| `HEALTH_PROBE_RATE` | Probe interval in milliseconds. Minimum 100ms. | `200` |

```bash
# Slow down probes if CLR profiler shows overlapping requests
az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --settings HEALTH_PROBE_RATE=400
```

### Idle Timeout

When the application is idle (no dashboard connections or load test requests), health probes are automatically suspended to reduce unnecessary network traffic to Azure's frontend and Application Insights telemetry.

| Variable Name | Description | Default |
|---------------|-------------|---------|
| `IDLE_TIMEOUT_MINUTES` | Minutes of inactivity before suspending health probes. Activity resumes automatically when the dashboard is opened or any request is received. | `20` |

```bash
# Extend idle timeout to 30 minutes
az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --settings IDLE_TIMEOUT_MINUTES=30
```

### Custom Page Footer

Set a custom footer message that appears on all pages. The footer supports HTML, allowing you to include links.

| Variable Name | Description |
|---------------|-------------|
| `PAGE_FOOTER` | HTML content for the footer's second line. If not set, only the app description and build info are shown. |

**Example Value:**
```
Created by <a href="https://yoursite.com">Your Team</a> for training purposes
```

**Setting via Azure CLI:**
```bash
az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP \
  --settings 'PAGE_FOOTER=Created by <a href="https://yoursite.com">Your Team</a> for training purposes'
```

**Setting via Azure Portal:**
1. Navigate to your App Service in the Azure Portal
2. Go to **Settings** → **Environment variables**
3. Click **+ Add**
4. Set Name: `PAGE_FOOTER`
5. Set Value: Your HTML footer content
6. Click **Apply**, then **Confirm**

## Troubleshooting

### SignalR Connection Fails

**Symptoms:** Dashboard shows "Disconnected", charts don't update in real-time

**Solutions:**
- Ensure WebSockets are enabled in App Service Configuration
- Upgrade from Free tier to Basic or higher
- Check if ARR Affinity is enabled (Settings → Configuration → General settings)

### OIDC Authentication Fails

**Symptoms:** GitHub Actions fails at "Login to Azure" step

**Check:**
- Verify all three secrets are set correctly
- Confirm federated credential subject matches your repo/branch: `repo:USERNAME/REPO:ref:refs/heads/main`
- Ensure App Registration has Contributor role on the App Service

### Application Crashes on Startup

**Symptoms:** App shows "Application Error" or doesn't respond

**Check:**
- View Log stream in Azure Portal (App Service → Log stream)
- Enable Application Logging under App Service → App Service Logs
- Verify runtime version matches your application's requirements
- Check for missing configuration or environment variables

### View Logs

```bash
# Stream live logs
az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP

# View deployment logs
az webapp log deployment show --name $APP_NAME --resource-group $RESOURCE_GROUP
```

## Quick Reference - CLI One-Liner

Complete setup script (customize variables at top):

```bash
# Full setup (customize variables at top)
RESOURCE_GROUP="your-resource-group"
APP_NAME="your-app-name"
LOCATION="eastus"
RUNTIME="your-runtime"  # e.g., "dotnet:8", "node:20-lts", "python:3.11"
GITHUB_REPO="YOUR_USERNAME/YOUR_REPO"

# Create resources
az group create -n $RESOURCE_GROUP -l $LOCATION
az appservice plan create -n "${APP_NAME}-plan" -g $RESOURCE_GROUP -l $LOCATION --sku B1
az webapp create -n $APP_NAME -g $RESOURCE_GROUP -p "${APP_NAME}-plan" --runtime $RUNTIME
az webapp config set -n $APP_NAME -g $RESOURCE_GROUP --web-sockets-enabled true

# Create App Registration and get IDs
APP_ID=$(az ad app create --display-name "github-${APP_NAME}-deploy" --query appId -o tsv)
az ad sp create --id $APP_ID
TENANT_ID=$(az account show --query tenantId -o tsv)
SUB_ID=$(az account show --query id -o tsv)

# Create federated credential
az ad app federated-credential create --id $APP_ID --parameters "{
  \"name\": \"github-main-branch\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:${GITHUB_REPO}:ref:refs/heads/main\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}"

# Assign permissions
APP_SERVICE_ID=$(az webapp show -n $APP_NAME -g $RESOURCE_GROUP --query id -o tsv)
az role assignment create --assignee $APP_ID --role Contributor --scope $APP_SERVICE_ID

# Output secrets for GitHub
echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID=$SUB_ID"
```
