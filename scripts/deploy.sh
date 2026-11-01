#!/usr/bin/env bash
# Deploy only to an existing platform-owned Container App.
set -euo pipefail
cd "$(dirname "$0")/.."

APP_CONFIG_ENDPOINT="${APP_CONFIG_ENDPOINT:-$(azd env get-value APP_CONFIG_ENDPOINT)}"
APP_CONFIG_ENDPOINT="${APP_CONFIG_ENDPOINT%/}"
[[ "$APP_CONFIG_ENDPOINT" =~ ^https://[a-zA-Z0-9-]+\.azconfig\.io$ ]] || {
  echo "APP_CONFIG_ENDPOINT must be an HTTPS App Configuration endpoint" >&2; exit 1;
}
az account show
get_config_value() {
  local value
  value="$(az appconfig kv show --endpoint "$APP_CONFIG_ENDPOINT" --key "$1" \
    --label agent-lz --auth-mode login --query value -o tsv)" || return $?
  [[ -n "${value//[[:space:]]/}" ]] || { echo "Missing App Configuration key: $1" >&2; return 1; }
  printf '%s' "$value"
}
registry="$(get_config_value CONTAINER_REGISTRY_NAME)"
login_server="$(get_config_value CONTAINER_REGISTRY_LOGIN_SERVER)"
resource_group="$(get_config_value AZURE_RESOURCE_GROUP)"
app_name="$(get_config_value MCP_APP_NAME)"
az containerapp show --name "$app_name" --resource-group "$resource_group"
commit="$(git rev-parse HEAD)"
[[ "$commit" =~ ^[a-f0-9]{40}$ ]] || { echo "Invalid Git commit" >&2; exit 1; }
repository="agent-lz/mcp"
tag="$repository:$commit"
image="$login_server/$tag"
if command -v docker; then
  az acr login --name "$registry"
  docker build --platform linux/amd64 -t "$image" .
  docker push "$image"
else
  az acr build --registry "$registry" --image "$tag" --file Dockerfile .
fi
digest="$(az acr manifest show-metadata --registry "$registry" --name "$tag" --query digest -o tsv)"
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]] || { echo "Registry did not return an immutable digest" >&2; exit 1; }
az containerapp update --name "$app_name" --resource-group "$resource_group" \
  --image "$login_server/$repository@$digest" --set-env-vars "APP_CONFIG_ENDPOINT=$APP_CONFIG_ENDPOINT"
