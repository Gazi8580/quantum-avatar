param(
  [string]$ResourceGroup = "mega-ultra-paypal-rg",
  [string]$Location = "switzerlandnorth",
  [string]$StorageAccount = "megaultpaypal" ,
  [string]$Container = "paypal-events"
)

# Creates a Storage Account + container for durable webhook event storage.
# Prereq: az login

az group create --name $ResourceGroup --location $Location

az storage account create \
  --name $StorageAccount \
  --resource-group $ResourceGroup \
  --location $Location \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false

$connectionString = az storage account show-connection-string --name $StorageAccount --resource-group $ResourceGroup --query connectionString -o tsv

az storage container create --name $Container --connection-string $connectionString

"AZURE_STORAGE_CONNECTION_STRING=$connectionString"
