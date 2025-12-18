# Azure Container Apps (Webhook Receiver) – 24/7 Quick Start

## Ziel
Den PayPal Webhook Receiver **24/7** mit einer öffentlichen HTTPS‑URL betreiben, damit Revenue Events zuverlässig erfasst werden können (ohne Reporting‑API Rechte).

## Endpoints
- `GET /health`
- `POST /paypal/webhook`
- `GET /stats`

## Voraussetzungen
- Azure CLI (`az`) installiert
- Login: `az login`

## Secrets / Env Vars
Required (LIVE Verification):
- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_WEBHOOK_ID`

Optional (durable Storage):
- `AZURE_STORAGE_CONNECTION_STRING`
- `PAYPAL_EVENTS_CONTAINER` (default: `paypal-events`)
- `PAYPAL_EVENTS_PREFIX` (default: `events`)

## Deploy (ein Befehl)
Das Script baut das Image per `az acr build`, pusht es nach ACR und erstellt/updated die Container App.

### Option A: Secrets als Env Vars setzen (empfohlen)
PowerShell:
```powershell
$env:PAYPAL_CLIENT_ID = "..."
$env:PAYPAL_CLIENT_SECRET = "..."
$env:PAYPAL_WEBHOOK_ID = "..."

# Optional:
# $env:AZURE_STORAGE_CONNECTION_STRING = "..."
# $env:PAYPAL_EVENTS_CONTAINER = "paypal-events"
# $env:PAYPAL_EVENTS_PREFIX = "events"

.\azure\aca_deploy.ps1
```

### Option B: Secrets als Parameter übergeben
```powershell
.\azure\aca_deploy.ps1 -PayPalClientId "..." -PayPalClientSecret "..." -PayPalWebhookId "..."
```

Nach dem Deploy zeigt das Script die URLs aus:
- `https://<fqdn>/health`
- `https://<fqdn>/paypal/webhook`
- `https://<fqdn>/stats`

## PayPal Webhook URL
Im PayPal Developer Dashboard die Webhook URL auf folgendes setzen:
- `https://<fqdn>/paypal/webhook`

## Storage Setup (optional)
Wenn du Blob Storage nutzen willst:
```powershell
.\azure\storage_setup.ps1
```
Dann `AZURE_STORAGE_CONNECTION_STRING` ins Deploy reinreichen (Env var oder Parameter).
