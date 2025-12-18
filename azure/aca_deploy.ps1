param(
  [string]$ResourceGroup = "mega-ultra-paypal-rg",
  [string]$Location = "switzerlandnorth",
  [string]$AcrName = "megaultpaypalacr",
  [string]$EnvironmentName = "mega-ultra-aca-env",
  [string]$AppName = "mega-ultra-paypal-webhook",
  [string]$ImageRepo = "mega-ultra-paypal-webhook",
  [string]$ImageTag = "1",
  [int]$TargetPort = 8080,

  # Secrets (Default: aus Umgebungsvariablen lesen)
  [string]$PayPalClientId = $env:PAYPAL_CLIENT_ID,
  [string]$PayPalClientSecret = $env:PAYPAL_CLIENT_SECRET,
  [string]$PayPalWebhookId = $env:PAYPAL_WEBHOOK_ID,

  # Optional: Azure Blob Storage (durable Events)
  [string]$AzureStorageConnectionString = $env:AZURE_STORAGE_CONNECTION_STRING,
  [string]$PayPalEventsContainer = $env:PAYPAL_EVENTS_CONTAINER,
  [string]$PayPalEventsPrefix = $env:PAYPAL_EVENTS_PREFIX
)

$ErrorActionPreference = "Stop"

function Require-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Missing prerequisite: '$name' not found in PATH."
  }
}

Require-Command az

# Container Apps CLI extension (oft nötig)
try {
  az extension add --name containerapp --only-show-errors | Out-Null
} catch {
  # ok wenn schon installiert
}

# Login Check (keine perfekte Methode; wir versuchen eine harmlose Abfrage)
try {
  az account show --only-show-errors | Out-Null
} catch {
  Write-Host "Not logged in. Running: az login" -ForegroundColor Yellow
  az login | Out-Null
}

Write-Host "== Resource Group ==" -ForegroundColor Cyan
az group create --name $ResourceGroup --location $Location --only-show-errors | Out-Null

Write-Host "== Azure Container Registry (ACR) ==" -ForegroundColor Cyan
$acrExists = $false
try {
  az acr show --name $AcrName --resource-group $ResourceGroup --only-show-errors | Out-Null
  $acrExists = $true
} catch {}

if (-not $acrExists) {
  az acr create --name $AcrName --resource-group $ResourceGroup --location $Location --sku Basic --admin-enabled true --only-show-errors | Out-Null
}

$loginServer = az acr show --name $AcrName --resource-group $ResourceGroup --query loginServer -o tsv
$imageFull = "$loginServer/${ImageRepo}:$ImageTag"

Write-Host "== Build & Push Image via az acr build ==" -ForegroundColor Cyan
# Aus dem Projektroot bauen, weil Dockerfile.webhook dort liegt
Push-Location "$(Split-Path -Parent $PSScriptRoot)"
try {
  az acr build --registry $AcrName --image "${ImageRepo}:$ImageTag" --file "Dockerfile.webhook" . --only-show-errors | Out-Null
} finally {
  Pop-Location
}

Write-Host "== Container Apps Environment ==" -ForegroundColor Cyan
$envExists = $false
try {
  az containerapp env show --name $EnvironmentName --resource-group $ResourceGroup --only-show-errors | Out-Null
  $envExists = $true
} catch {}

if (-not $envExists) {
  az containerapp env create --name $EnvironmentName --resource-group $ResourceGroup --location $Location --only-show-errors | Out-Null
}

Write-Host "== Registry credentials (ACR admin) ==" -ForegroundColor Cyan
$acrCred = az acr credential show --name $AcrName --resource-group $ResourceGroup | ConvertFrom-Json
$acrUser = $acrCred.username
$acrPass = $acrCred.passwords[0].value

Write-Host "== Container App (Create or Update) ==" -ForegroundColor Cyan
$appExists = $false
try {
  az containerapp show --name $AppName --resource-group $ResourceGroup --only-show-errors | Out-Null
  $appExists = $true
} catch {}

if (-not $appExists) {
  az containerapp create `
    --name $AppName `
    --resource-group $ResourceGroup `
    --environment $EnvironmentName `
    --image $imageFull `
    --ingress external `
    --target-port $TargetPort `
    --min-replicas 1 `
    --max-replicas 3 `
    --cpu 0.5 `
    --memory 1Gi `
    --registry-server $loginServer `
    --registry-username $acrUser `
    --registry-password $acrPass `
    --env-vars PORT=$TargetPort `
    --only-show-errors | Out-Null
} else {
  az containerapp update `
    --name $AppName `
    --resource-group $ResourceGroup `
    --image $imageFull `
    --registry-server $loginServer `
    --registry-username $acrUser `
    --registry-password $acrPass `
    --set-env-vars PORT=$TargetPort `
    --only-show-errors | Out-Null
}

Write-Host "== Secrets & Env Vars ==" -ForegroundColor Cyan
if (-not $PayPalClientId -or -not $PayPalClientSecret -or -not $PayPalWebhookId) {
  Write-Host "Missing PayPal secrets. Provide params or set env vars: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_WEBHOOK_ID" -ForegroundColor Yellow
  Write-Host "Skipping secret set/update." -ForegroundColor Yellow
} else {
  az containerapp secret set --name $AppName --resource-group $ResourceGroup `
    --secrets `
      PAYPAL_CLIENT_ID=$PayPalClientId `
      PAYPAL_CLIENT_SECRET=$PayPalClientSecret `
      PAYPAL_WEBHOOK_ID=$PayPalWebhookId `
    --only-show-errors | Out-Null

  $envVars = @(
    "PAYPAL_CLIENT_ID=secretref:PAYPAL_CLIENT_ID",
    "PAYPAL_CLIENT_SECRET=secretref:PAYPAL_CLIENT_SECRET",
    "PAYPAL_WEBHOOK_ID=secretref:PAYPAL_WEBHOOK_ID"
  )

  if ($AzureStorageConnectionString) {
    az containerapp secret set --name $AppName --resource-group $ResourceGroup --secrets AZURE_STORAGE_CONNECTION_STRING=$AzureStorageConnectionString --only-show-errors | Out-Null
    $envVars += "AZURE_STORAGE_CONNECTION_STRING=secretref:AZURE_STORAGE_CONNECTION_STRING"
  }
  if ($PayPalEventsContainer) { $envVars += "PAYPAL_EVENTS_CONTAINER=$PayPalEventsContainer" }
  if ($PayPalEventsPrefix) { $envVars += "PAYPAL_EVENTS_PREFIX=$PayPalEventsPrefix" }

  az containerapp update --name $AppName --resource-group $ResourceGroup --set-env-vars $envVars --only-show-errors | Out-Null
}

Write-Host "== Output URL ==" -ForegroundColor Cyan
$fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
$baseUrl = "https://$fqdn"
Write-Host "App URL: $baseUrl" -ForegroundColor Green
Write-Host "Health:  $baseUrl/health" -ForegroundColor Green
Write-Host "Webhook: $baseUrl/paypal/webhook" -ForegroundColor Green
Write-Host "Stats:   $baseUrl/stats" -ForegroundColor Green

Write-Host "== Health Check ==" -ForegroundColor Cyan
try {
  $resp = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing -TimeoutSec 30
  Write-Host "Health status: $($resp.StatusCode)" -ForegroundColor Green
} catch {
  Write-Host "Health check failed (container may still be starting). Try again in ~60s." -ForegroundColor Yellow
  Write-Host $_.Exception.Message -ForegroundColor Yellow
}
