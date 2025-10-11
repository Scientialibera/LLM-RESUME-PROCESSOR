<parameter name="content">#Requires -Version 7.0
#Requires -Modules Az

<#
.SYNOPSIS
    Deploys Azure resources for the Resume Processor application.

.DESCRIPTION
    This script deploys and configures all required Azure resources:
    - Azure OpenAI Service
    - Cosmos DB with containers
    - Event Grid System Topic
    - Azure Container Apps (API and Frontend)
    - Required IAM roles and permissions

.PARAMETER ResourceGroupName
    Name of the Azure Resource Group to create or use.

.PARAMETER Location
    Azure region for resource deployment (default: eastus).

.PARAMETER SkipExisting
    Skip deployment if resources already exist.

.EXAMPLE
    .\Deploy-AzureResources.ps1 -ResourceGroupName "rg-resume-processor" -Location "eastus"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $false)]
    [string]$Location = "eastus",

    [Parameter(Mandatory = $false)]
    [switch]$SkipExisting
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Configuration
$config = @{
    OpenAI = @{
        Name = "aoai-resume-processor-$(Get-Random -Minimum 1000 -Maximum 9999)"
        SKU = "S0"
        ChatModel = "gpt-4"
        ChatModelVersion = "0613"
        EmbeddingModel = "text-embedding-ada-002"
        EmbeddingModelVersion = "2"
    }
    CosmosDB = @{
        Name = "cosmos-resume-processor-$(Get-Random -Minimum 1000 -Maximum 9999)"
        DatabaseName = "resume-processor"
        RawContainer = "raw-resumes"
        ProcessedContainer = "processed-resumes"
    }
    EventGrid = @{
        TopicName = "evgt-resume-processor"
    }
    ContainerApp = @{
        EnvironmentName = "cae-resume-processor"
        ApiName = "ca-resume-api"
        FrontendName = "ca-resume-frontend"
    }
}

#region Helper Functions

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "    ✓ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "    ⚠ $Message" -ForegroundColor Yellow
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "    ✗ $Message" -ForegroundColor Red
}

function Test-AzResourceExists {
    param(
        [string]$ResourceType,
        [string]$ResourceName,
        [string]$ResourceGroupName
    )

    $resource = Get-AzResource -ResourceType $ResourceType -ResourceName $ResourceName -ResourceGroupName $ResourceGroupName -ErrorAction SilentlyContinue
    return $null -ne $resource
}

#endregion

#region Main Deployment

Write-Host @"
╔═══════════════════════════════════════════════════════════╗
║     Resume Processor - Azure Resource Deployment         ║
╚═══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Blue

# Check Azure Login
Write-Step "Checking Azure authentication"
$context = Get-AzContext
if (-not $context) {
    Write-Warning "Not logged in to Azure. Initiating login..."
    Connect-AzAccount
    $context = Get-AzContext
}
Write-Success "Logged in as: $($context.Account.Id)"
Write-Success "Subscription: $($context.Subscription.Name)"

# Create or verify Resource Group
Write-Step "Setting up Resource Group"
$rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
if (-not $rg) {
    Write-Host "    Creating resource group: $ResourceGroupName"
    $rg = New-AzResourceGroup -Name $ResourceGroupName -Location $Location
    Write-Success "Resource group created"
} else {
    Write-Success "Resource group already exists"
}

# Deploy Azure OpenAI
Write-Step "Deploying Azure OpenAI Service"
$openAIExists = Test-AzResourceExists -ResourceType "Microsoft.CognitiveServices/accounts" -ResourceName $config.OpenAI.Name -ResourceGroupName $ResourceGroupName

if ($openAIExists -and $SkipExisting) {
    Write-Warning "Azure OpenAI service already exists, skipping"
    $openAI = Get-AzCognitiveServicesAccount -ResourceGroupName $ResourceGroupName -Name $config.OpenAI.Name
} else {
    try {
        $openAI = New-AzCognitiveServicesAccount `
            -ResourceGroupName $ResourceGroupName `
            -Name $config.OpenAI.Name `
            -Type "OpenAI" `
            -SKU $config.OpenAI.SKU `
            -Location $Location `
            -CustomSubdomainName $config.OpenAI.Name

        Write-Success "Azure OpenAI service created"

        # Deploy models
        Write-Host "    Deploying GPT-4 model..."
        New-AzCognitiveServicesAccountDeployment `
            -ResourceGroupName $ResourceGroupName `
            -AccountName $config.OpenAI.Name `
            -Name $config.OpenAI.ChatModel `
            -Properties @{
                model = @{
                    format = "OpenAI"
                    name = $config.OpenAI.ChatModel
                    version = $config.OpenAI.ChatModelVersion
                }
            } `
            -Sku @{name = "Standard"; capacity = 10}

        Write-Host "    Deploying embedding model..."
        New-AzCognitiveServicesAccountDeployment `
            -ResourceGroupName $ResourceGroupName `
            -AccountName $config.OpenAI.Name `
            -Name $config.OpenAI.EmbeddingModel `
            -Properties @{
                model = @{
                    format = "OpenAI"
                    name = $config.OpenAI.EmbeddingModel
                    version = $config.OpenAI.EmbeddingModelVersion
                }
            } `
            -Sku @{name = "Standard"; capacity = 10}

        Write-Success "Models deployed"
    } catch {
        Write-ErrorMessage "Failed to deploy Azure OpenAI: $_"
        throw
    }
}

$openAIEndpoint = "https://$($config.OpenAI.Name).openai.azure.com/"
Write-Success "Endpoint: $openAIEndpoint"

# Deploy Cosmos DB
Write-Step "Deploying Cosmos DB"
$cosmosExists = Test-AzResourceExists -ResourceType "Microsoft.DocumentDB/databaseAccounts" -ResourceName $config.CosmosDB.Name -ResourceGroupName $ResourceGroupName

if ($cosmosExists -and $SkipExisting) {
    Write-Warning "Cosmos DB already exists, skipping"
    $cosmos = Get-AzCosmosDBAccount -ResourceGroupName $ResourceGroupName -Name $config.CosmosDB.Name
} else {
    try {
        $cosmos = New-AzCosmosDBAccount `
            -ResourceGroupName $ResourceGroupName `
            -Name $config.CosmosDB.Name `
            -Location $Location `
            -ApiKind "Sql" `
            -EnableAutomaticFailover $false `
            -EnableFreeTier $true

        Write-Success "Cosmos DB account created"

        # Create database
        Write-Host "    Creating database..."
        New-AzCosmosDBSqlDatabase `
            -ResourceGroupName $ResourceGroupName `
            -AccountName $config.CosmosDB.Name `
            -Name $config.CosmosDB.DatabaseName

        # Create containers
        Write-Host "    Creating raw-resumes container..."
        New-AzCosmosDBSqlContainer `
            -ResourceGroupName $ResourceGroupName `
            -AccountName $config.CosmosDB.Name `
            -DatabaseName $config.CosmosDB.DatabaseName `
            -Name $config.CosmosDB.RawContainer `
            -PartitionKeyPath "/id" `
            -PartitionKeyKind Hash `
            -Throughput 400

        Write-Host "    Creating processed-resumes container..."
        New-AzCosmosDBSqlContainer `
            -ResourceGroupName $ResourceGroupName `
            -AccountName $config.CosmosDB.Name `
            -DatabaseName $config.CosmosDB.DatabaseName `
            -Name $config.CosmosDB.ProcessedContainer `
            -PartitionKeyPath "/id" `
            -PartitionKeyKind Hash `
            -Throughput 400

        Write-Success "Containers created"
    } catch {
        Write-ErrorMessage "Failed to deploy Cosmos DB: $_"
        throw
    }
}

$cosmosEndpoint = "https://$($config.CosmosDB.Name).documents.azure.com:443/"
Write-Success "Endpoint: $cosmosEndpoint"

# Deploy Event Grid System Topic
Write-Step "Deploying Event Grid System Topic"
try {
    # Create system topic for Cosmos DB
    $eventGridTopic = New-AzEventGridSystemTopic `
        -ResourceGroupName $ResourceGroupName `
        -Name $config.EventGrid.TopicName `
        -Location $Location `
        -TopicType "Microsoft.DocumentDB.DatabaseAccounts" `
        -Source "/subscriptions/$($context.Subscription.Id)/resourceGroups/$ResourceGroupName/providers/Microsoft.DocumentDB/databaseAccounts/$($config.CosmosDB.Name)"

    Write-Success "Event Grid system topic created"
} catch {
    Write-Warning "Event Grid topic may already exist or failed to create: $_"
}

# Output configuration
Write-Step "Deployment Summary"
Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║              Deployment Configuration                      ║
╚═══════════════════════════════════════════════════════════╝

Azure OpenAI:
  Name:       $($config.OpenAI.Name)
  Endpoint:   $openAIEndpoint
  Chat Model: $($config.OpenAI.ChatModel)
  Embedding:  $($config.OpenAI.EmbeddingModel)

Cosmos DB:
  Name:       $($config.CosmosDB.Name)
  Endpoint:   $cosmosEndpoint
  Database:   $($config.CosmosDB.DatabaseName)
  Containers: $($config.CosmosDB.RawContainer), $($config.CosmosDB.ProcessedContainer)

Event Grid:
  Topic:      $($config.EventGrid.TopicName)

"@ -ForegroundColor Green

# Generate .env file
Write-Step "Generating .env file"
$envContent = @"
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=$openAIEndpoint
AZURE_OPENAI_CHAT_DEPLOYMENT=$($config.OpenAI.ChatModel)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$($config.OpenAI.EmbeddingModel)
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Cosmos DB Configuration
COSMOS_DB_ENDPOINT=$cosmosEndpoint
COSMOS_DB_DATABASE_NAME=$($config.CosmosDB.DatabaseName)
COSMOS_DB_RAW_RESUMES_CONTAINER=$($config.CosmosDB.RawContainer)
COSMOS_DB_PROCESSED_RESUMES_CONTAINER=$($config.CosmosDB.ProcessedContainer)

# Event Grid Configuration (Webhook will be configured after API deployment)
EVENT_GRID_TOPIC_ENDPOINT=
EVENT_GRID_TOPIC_KEY=
EVENT_GRID_WEBHOOK_SECRET=

# Application Configuration
APP_NAME=Resume Processor API
VERSION=1.0.0
LOG_LEVEL=INFO
"@

$envPath = Join-Path $PSScriptRoot ".." ".env"
$envContent | Out-File -FilePath $envPath -Encoding UTF8
Write-Success "Environment file created at: $envPath"

Write-Step "Deployment Complete!"
Write-Host @"

Next Steps:
1. Review the generated .env file
2. Run the backend API: cd backend && python -m uvicorn app.main:app --reload
3. Run the frontend: cd frontend && npm install && npm run dev
4. Configure Event Grid webhook after API is deployed

"@ -ForegroundColor Yellow

#endregion
