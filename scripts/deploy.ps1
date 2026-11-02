# Deploy only to an existing platform-owned Container App. Every native exit is checked.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Native {
    param([string]$Command, [string[]]$Arguments)
    $result = & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Native command failed: $Command ($LASTEXITCODE)" }
    return $result
}

function Get-ConfigValue {
    param([string]$Key)
    $value = Invoke-Native az @(
        'appconfig', 'kv', 'show', '--endpoint', $script:Endpoint,
        '--key', $Key, '--label', 'agent-lz', '--auth-mode', 'login',
        '--query', 'value', '-o', 'tsv'
    )
    if ([string]::IsNullOrWhiteSpace($value)) { throw "Missing App Configuration key: $Key" }
    return $value.Trim()
}

$Endpoint = $env:APP_CONFIG_ENDPOINT
if ([string]::IsNullOrWhiteSpace($Endpoint)) {
    $Endpoint = Invoke-Native azd @('env', 'get-value', 'APP_CONFIG_ENDPOINT')
}
$Endpoint = $Endpoint.Trim().TrimEnd('/')
if ($Endpoint -notmatch '^https://[a-zA-Z0-9-]+\.azconfig\.io$') {
    throw 'APP_CONFIG_ENDPOINT must be an HTTPS App Configuration endpoint'
}
$null = Invoke-Native az @('account', 'show')
$Registry = Get-ConfigValue 'CONTAINER_REGISTRY_NAME'
$LoginServer = Get-ConfigValue 'CONTAINER_REGISTRY_LOGIN_SERVER'
$RegistryId = Get-ConfigValue 'CONTAINER_REGISTRY_RESOURCE_ID'
$ResourceGroup = Get-ConfigValue 'AZURE_APP_RESOURCE_GROUP'
$AppName = Get-ConfigValue 'MCP_APP_NAME'
if ($RegistryId -notmatch '^/subscriptions/([a-fA-F0-9-]{36})/resourceGroups/([^/]+)/providers/Microsoft\.ContainerRegistry/registries/([^/]+)$') {
    throw 'CONTAINER_REGISTRY_RESOURCE_ID must identify the exact provisioned ACR'
}
$RegistrySubscription = $Matches[1]
$RegistryGroup = $Matches[2]
if ($Matches[3] -ine $Registry) { throw 'Registry ID/name mismatch' }
$ActualLoginServer = (Invoke-Native az @('acr', 'show', '--ids', $RegistryId, '--query', 'loginServer', '-o', 'tsv')).Trim()
if ($ActualLoginServer -ine $LoginServer) { throw 'Registry ID/login server mismatch' }
# Assert existence before any build/push. Never provision or infer a replacement app.
$App = Invoke-Native az @('containerapp', 'show', '--name', $AppName, '--resource-group', $ResourceGroup, '-o', 'json')
$App = ($App -join "`n") | ConvertFrom-Json
$Identity = $App.identity
if (-not $Identity) { throw 'MCP app must have a managed identity' }
$ClientIds = @()
if ($Identity.type -like '*UserAssigned*') {
    foreach ($Assignment in $Identity.userAssignedIdentities.PSObject.Properties) {
        # Resolve the app's exact UAI resource ID; never inherit operator AZURE_CLIENT_ID.
        $ClientIds += (Invoke-Native az @('identity', 'show', '--ids', $Assignment.Name, '--query', 'clientId', '-o', 'tsv')).Trim()
    }
}
$BoundClientId = $env:MCP_APP_CLIENT_ID
$SelectedClientId = $null
if ($ClientIds.Count -gt 0) {
    if ($BoundClientId) {
        if ($BoundClientId -notin $ClientIds) { throw 'MCP_APP_CLIENT_ID is not assigned to the MCP app' }
        $SelectedClientId = $BoundClientId
    } elseif ($ClientIds.Count -eq 1) {
        $SelectedClientId = $ClientIds[0]
    } else { throw 'Multiple MCP UAIs require bound MCP_APP_CLIENT_ID' }
    if ($SelectedClientId -notmatch '^[a-fA-F0-9-]{36}$') { throw 'Invalid MCP UAI client ID' }
} elseif ($Identity.type -notlike '*SystemAssigned*' -or $BoundClientId) {
    throw 'MCP app has no usable managed identity or binding does not match'
}
$Commit = (Invoke-Native git @('rev-parse', 'HEAD')).Trim()
if ($Commit -notmatch '^[a-f0-9]{40}$') { throw 'Invalid Git commit' }
$Repository = 'agent-lz/mcp'
$Tag = "${Repository}:$Commit"
$Image = "$LoginServer/$Tag"
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $null = Invoke-Native az @('acr', 'login', '--name', $Registry, '--resource-group', $RegistryGroup, '--subscription', $RegistrySubscription)
    Invoke-Native docker @('build', '--platform', 'linux/amd64', '-t', $Image, '.')
    Invoke-Native docker @('push', $Image)
} else {
    Invoke-Native az @('acr', 'build', '--registry', $Registry, '--resource-group', $RegistryGroup, '--subscription', $RegistrySubscription, '--image', $Tag, '--file', 'Dockerfile', '.')
}
$Digest = (Invoke-Native az @(
    'acr', 'manifest', 'show-metadata', $Image, '--subscription', $RegistrySubscription,
    '--query', 'digest', '-o', 'tsv'
)).Trim()
if ($Digest -notmatch '^sha256:[a-f0-9]{64}$') { throw 'Registry did not return an immutable digest' }
$UpdateArguments = @(
    'containerapp', 'update', '--name', $AppName, '--resource-group', $ResourceGroup,
    '--image', "$LoginServer/$Repository@$Digest",
    '--set-env-vars', "APP_CONFIG_ENDPOINT=$Endpoint"
)
if ($SelectedClientId) {
    $UpdateArguments += "AZURE_CLIENT_ID=$SelectedClientId"
} else {
    $UpdateArguments += @('--remove-env-vars', 'AZURE_CLIENT_ID')
}
Invoke-Native az $UpdateArguments
Invoke-Native az @('containerapp', 'ingress', 'update', '--name', $AppName, '--resource-group', $ResourceGroup, '--target-port', '8080')
