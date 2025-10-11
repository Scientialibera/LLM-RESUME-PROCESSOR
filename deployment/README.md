# Deployment Guide

This directory contains deployment scripts and configurations for the Resume Processor application.

## Prerequisites

1. **Azure Subscription**: Active Azure subscription with permissions to create resources
2. **PowerShell 7+**: [Download here](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell)
3. **Azure PowerShell Module**: Install with `Install-Module -Name Az -AllowClobber`
4. **Azure CLI** (optional): For additional configuration

## Quick Deploy

### Step 1: Login to Azure

```powershell
Connect-AzAccount
```

Select your subscription:

```powershell
Set-AzContext -SubscriptionId "your-subscription-id"
```

### Step 2: Run Deployment Script

```powershell
.\Deploy-AzureResources.ps1 -ResourceGroupName "rg-resume-processor" -Location "eastus"
```

#### Parameters

- **ResourceGroupName** (required): Name of the resource group to create or use
- **Location** (optional): Azure region (default: eastus)
- **SkipExisting** (optional): Skip resources that already exist

#### Example with all parameters:

```powershell
.\Deploy-AzureResources.ps1 `
  -ResourceGroupName "rg-resume-prod" `
  -Location "westus2" `
  -SkipExisting
```

### Step 3: Verify Deployment

The script will output a summary of deployed resources:

```
╔═══════════════════════════════════════════════════════════╗
║              Deployment Configuration                      ║
╚═══════════════════════════════════════════════════════════╝

Azure OpenAI:
  Name:       your-resource
  Endpoint:   https://your-resource.openai.azure.com/
  ...
```

## Post-Deployment Configuration

### Configure Managed Identity

Grant your deployment identity (App Service or Container App) access to resources:

```powershell
# Get the identity of your API
$apiIdentity = (az webapp identity show --name your-api-name --resource-group rg-resume-processor --query principalId -o tsv)

# Grant Cosmos DB access
az cosmosdb sql role assignment create \
  --account-name cosmos-resume-processor-xxxx \
  --resource-group rg-resume-processor \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --principal-id $apiIdentity \
  --scope "/"

# Grant OpenAI access
az role assignment create \
  --assignee $apiIdentity \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/{subscription-id}/resourceGroups/rg-resume-processor/providers/Microsoft.CognitiveServices/accounts/aoai-resume-processor-xxxx"
```

### Configure Event Grid Webhook

1. Deploy your API first
2. Get the webhook URL: `https://your-api.azurecontainerapps.io/api/v1/webhooks/eventgrid`
3. Create the subscription:

```powershell
az eventgrid system-topic event-subscription create \
  --name resume-processor-sub \
  --resource-group rg-resume-processor \
  --system-topic-name evgt-resume-processor \
  --endpoint "https://your-api.azurecontainerapps.io/api/v1/webhooks/eventgrid" \
  --endpoint-type webhook \
  --included-event-types "Microsoft.DocumentDB.DatabaseAccountsDataEvent"
```

## Resource Pricing Estimates

Based on typical usage (100 resumes/day):

| Resource | Tier | Est. Monthly Cost |
|----------|------|-------------------|
| Azure OpenAI | Standard | $50-100 |
| Cosmos DB | Provisioned (400 RU/s) | $24 |
| Event Grid | Pay-as-you-go | $0.60 |
| Container Apps | Consumption | $5-20 |
| **Total** | | **~$80-145/month** |

To reduce costs:
- Use Cosmos DB free tier (if available)
- Optimize OpenAI token usage
- Use reserved capacity for predictable workloads

## Troubleshooting

### Issue: PowerShell Az module not found

```powershell
Install-Module -Name Az -AllowClobber -Scope CurrentUser
```

### Issue: Insufficient permissions

Ensure your account has:
- Contributor role on subscription
- User Access Administrator (for RBAC assignments)

### Issue: OpenAI model deployment failed

Some regions have limited model availability. Try:
- Use `eastus` or `swedencentral` regions
- Check [model availability](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)

### Issue: Cosmos DB creation failed

You may have hit account limits. Check:
- Maximum Cosmos DB accounts per subscription
- Region availability

## Clean Up Resources

To delete all deployed resources:

```powershell
Remove-AzResourceGroup -Name "rg-resume-processor" -Force
```

**Warning**: This will delete all resources in the resource group permanently.

## Next Steps

1. Configure your `.env` file with the endpoints from deployment output
2. Deploy your backend API
3. Deploy your frontend
4. Configure Event Grid webhook
5. Test the end-to-end flow

For more information, see the main [README.md](../README.md).
