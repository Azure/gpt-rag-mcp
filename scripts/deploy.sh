#!/usr/bin/env bash
# -------------------------------------------------------------------------
# deploy.sh — validate APP_CONFIG_ENDPOINT, load App Config (label=gpt-rag), then build & push
# -------------------------------------------------------------------------

set -euo pipefail

# Toggle DEBUG for verbose output
DEBUG=${DEBUG:-false}
if [[ "$DEBUG" == "true" ]]; then
  set -x
fi

# colors
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # no color

echo
# First, check shell environment
if [[ -n "${APP_CONFIG_ENDPOINT:-}" ]]; then
  echo -e "${GREEN}✅ Using APP_CONFIG_ENDPOINT from environment: ${APP_CONFIG_ENDPOINT}${NC}"
else
  echo -e "${BLUE}🔍 Fetching APP_CONFIG_ENDPOINT from azd env…${NC}"
  envValues="$(azd env get-values 2>/dev/null || true)"
  APP_CONFIG_ENDPOINT="$(echo "$envValues" \
    | grep -i '^APP_CONFIG_ENDPOINT=' \
    | cut -d '=' -f2- \
    | tr -d '"' \
    | tr -d '[:space:]' || true)"
fi

if [[ -z "${APP_CONFIG_ENDPOINT:-}" ]]; then
  echo -e "${YELLOW}⚠️  Missing APP_CONFIG_ENDPOINT.${NC}"
  echo -e "  • ${BLUE}Set it with:${NC} azd env set APP_CONFIG_ENDPOINT <your-endpoint>"
  echo -e "  • ${BLUE}Or export in shell:${NC} export APP_CONFIG_ENDPOINT=<your-endpoint> before running this script."
  exit 1
fi

echo -e "${GREEN}✅ APP_CONFIG_ENDPOINT: ${APP_CONFIG_ENDPOINT}${NC}"
echo

# derive App Configuration name from endpoint
configName="${APP_CONFIG_ENDPOINT#https://}"
configName="${configName%.azconfig.io}"
if [[ -z "$configName" ]]; then
  echo -e "${YELLOW}⚠️  Could not parse config name from endpoint '${APP_CONFIG_ENDPOINT}'.${NC}"
  exit 1
fi
echo -e "${GREEN}✅ App Configuration name: ${configName}${NC}"
echo

echo -e "${BLUE}🔐 Checking Azure CLI login and subscription…${NC}"
if ! az account show >/dev/null 2>&1; then
  echo -e "${YELLOW}⚠️  Not logged in. Please run 'az login'.${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Azure CLI is logged in.${NC}"
echo

# label for your configuration keys
label="gpt-rag"

echo -e "${GREEN}⚙️ Loading App Configuration settings (label=${label})…${NC}"
echo

# helper to fetch a key (with label) from App Configuration via az CLI
get_config_value() {
  key="$1"
  echo -e "${BLUE}🛠️  Retrieving '$key' (label=${label}) from App Configuration…${NC}" >&2
  val="$(az appconfig kv show \
    --name "$configName" \
    --key "$key" \
    --label "$label" \
    --auth-mode login \
    --query value -o tsv 2>&1)" || status=$?
  if [[ -z "${val// /}" ]]; then
    echo -e "${YELLOW}⚠️  Failed to retrieve key '$key'. CLI output: $val${NC}" >&2
    return 1
  fi
  echo "$val"
}

# fetch required settings
containerRegistryName=""
containerRegistryLoginServer=""
resourceGroupName=""
mcpApp=""
missing_keys=()

if ! containerRegistryName="$(get_config_value "CONTAINER_REGISTRY_NAME")"; then
  missing_keys+=("CONTAINER_REGISTRY_NAME")
fi
if ! containerRegistryLoginServer="$(get_config_value "CONTAINER_REGISTRY_LOGIN_SERVER")"; then
  missing_keys+=("CONTAINER_REGISTRY_LOGIN_SERVER")
fi
if ! resourceGroupName="$(get_config_value "AZURE_RESOURCE_GROUP")"; then
  missing_keys+=("AZURE_RESOURCE_GROUP")
fi
if ! mcpApp="$(get_config_value "MCP_APP_NAME")"; then
  missing_keys+=("MCP_APP_NAME")
fi

if [[ ${#missing_keys[@]} -gt 0 ]]; then
  echo -e "${YELLOW}⚠️  Missing or invalid App Config keys: ${missing_keys[*]}${NC}"
  exit 1
fi

echo -e "${GREEN}✅ All App Configuration values retrieved:${NC}"
echo "   containerRegistryName = $containerRegistryName"
echo "   containerRegistryLoginServer = $containerRegistryLoginServer"
echo "   resourceGroupName = $resourceGroupName"
echo "   mcpApp = $mcpApp"
echo

echo -e "${GREEN}🔐 Logging into ACR (${containerRegistryName})…${NC}"
az acr login --name "${containerRegistryName}"
echo -e "${GREEN}✅ Logged into ACR.${NC}"
echo

echo -e "${BLUE}🛢️ Defining tag…${NC}"
tag="${tag:-$(git rev-parse --short HEAD)}"
echo -e "${GREEN}✅ tag set to: ${tag}${NC}"
echo

echo -e "${GREEN}🛠️  Building Docker image…${NC}"
docker build \
  --platform linux/amd64 \
  -t "${containerRegistryLoginServer}/azure-gpt-rag/mcp:${tag}" \
  .

echo
echo -e "${GREEN}📤 Pushing image…${NC}"
docker push "${containerRegistryLoginServer}/azure-gpt-rag/mcp:${tag}"
echo -e "${GREEN}✅ Image pushed.${NC}"

echo
echo -e "${GREEN}🔄 Updating container app…${NC}"
az containerapp update \
  --name "${mcpApp}" \
  --resource-group "${resourceGroupName}" \
  --image "${containerRegistryLoginServer}/azure-gpt-rag/mcp:${tag}"
echo -e "${GREEN}✅ Container app updated.${NC}"
