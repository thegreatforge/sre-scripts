#!/bin/bash

# Set the URL of the Vault server
VAULT_ADDR=https://vault.example.com

# Authenticate with Vault
vault login -address=$VAULT_ADDR

mkdir "./dump"
cd "./dump"

# List all secrets engines
vault secrets list -address=$VAULT_ADDR

# Define a function to download secrets recursively
download_secrets() {
  # List all secrets in the current engine
  secrets=$(vault list -address=$VAULT_ADDR $1)
  # Loop through all secrets and download them
  for secret in $secrets; do
    # Check if the current secret is a directory or a leaf node
    if vault kv list -address=$VAULT_ADDR "$1/$secret" 2>/dev/null; then
      # Current secret is a directory, recurse into it
      download_secrets "$1/$secret"
    else
      # Current secret is a leaf node, download it
      mkdir -p "$1"
      vault read -address=$VAULT_ADDR -format=json "$1/$secret" > "$1/$secret.json"
    fi
  done
}

# Loop through all secrets engines and download all secrets recursively
for engine in $(vault secrets list -address=$VAULT_ADDR | awk '{print $1}'); do
  download_secrets $engine
done

# Log out of Vault
vault logout

