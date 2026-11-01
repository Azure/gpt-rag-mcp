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
registry_id="$(get_config_value CONTAINER_REGISTRY_RESOURCE_ID)"
resource_group="$(get_config_value AZURE_APP_RESOURCE_GROUP)"
app_name="$(get_config_value MCP_APP_NAME)"
[[ "$registry_id" =~ ^/subscriptions/([a-fA-F0-9-]{36})/resourceGroups/([^/]+)/providers/Microsoft\.ContainerRegistry/registries/([^/]+)$ ]] || {
  echo "CONTAINER_REGISTRY_RESOURCE_ID must identify the exact provisioned ACR" >&2; exit 1;
}
registry_subscription="${BASH_REMATCH[1]}"
registry_group="${BASH_REMATCH[2]}"
[[ "${BASH_REMATCH[3],,}" == "${registry,,}" ]] || { echo "Registry ID/name mismatch" >&2; exit 1; }
actual_login_server="$(az acr show --ids "$registry_id" --query loginServer -o tsv)"
[[ "${actual_login_server,,}" == "${login_server,,}" ]] || { echo "Registry ID/login server mismatch" >&2; exit 1; }
identity_type="$(az containerapp show --name "$app_name" --resource-group "$resource_group" --query identity.type -o tsv)"
client_ids=()
if [[ "$identity_type" == *UserAssigned* ]]; then
  assignments="$(az containerapp show --name "$app_name" --resource-group "$resource_group" \
    --query 'keys(identity.userAssignedIdentities)' -o tsv)"
  while IFS= read -r assignment; do
    [[ -n "$assignment" ]] || continue
    client_ids+=("$(az identity show --ids "$assignment" --query clientId -o tsv)")
  done <<< "$assignments"
fi
selected_client_id=""
bound_client_id="${MCP_APP_CLIENT_ID:-}"
if [[ ${#client_ids[@]} -gt 0 ]]; then
  if [[ -n "$bound_client_id" ]]; then
    for client_id in "${client_ids[@]}"; do
      [[ "${client_id,,}" != "${bound_client_id,,}" ]] || selected_client_id="$client_id"
    done
    [[ -n "$selected_client_id" ]] || { echo "MCP_APP_CLIENT_ID is not assigned to the MCP app" >&2; exit 1; }
  elif [[ ${#client_ids[@]} -eq 1 ]]; then
    selected_client_id="${client_ids[0]}"
  else
    echo "Multiple MCP UAIs require bound MCP_APP_CLIENT_ID" >&2; exit 1
  fi
  [[ "$selected_client_id" =~ ^[a-fA-F0-9-]{36}$ ]] || { echo "Invalid MCP UAI client ID" >&2; exit 1; }
elif [[ "$identity_type" != *SystemAssigned* || -n "$bound_client_id" ]]; then
  echo "MCP app has no usable managed identity or binding does not match" >&2; exit 1
fi
commit="$(git rev-parse HEAD)"
[[ "$commit" =~ ^[a-f0-9]{40}$ ]] || { echo "Invalid Git commit" >&2; exit 1; }
repository="agent-lz/mcp"
tag="$repository:$commit"
image="$login_server/$tag"
if command -v docker; then
  az acr login --name "$registry" --resource-group "$registry_group" --subscription "$registry_subscription"
  docker build --platform linux/amd64 -t "$image" .
  docker push "$image"
else
  az acr build --registry "$registry" --resource-group "$registry_group" \
    --subscription "$registry_subscription" --image "$tag" --file Dockerfile .
fi
digest="$(az acr manifest show-metadata "$image" --subscription "$registry_subscription" --query digest -o tsv)"
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]] || { echo "Registry did not return an immutable digest" >&2; exit 1; }
update_args=(containerapp update --name "$app_name" --resource-group "$resource_group"
  --image "$login_server/$repository@$digest" --set-env-vars "APP_CONFIG_ENDPOINT=$APP_CONFIG_ENDPOINT")
if [[ -n "$selected_client_id" ]]; then
  update_args+=("AZURE_CLIENT_ID=$selected_client_id")
else
  update_args+=(--remove-env-vars AZURE_CLIENT_ID)
fi
az "${update_args[@]}"
az containerapp ingress update --name "$app_name" --resource-group "$resource_group" --target-port 8080
