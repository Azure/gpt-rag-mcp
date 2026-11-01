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
$ResourceGroup = Get-ConfigValue 'AZURE_RESOURCE_GROUP'
$AppName = Get-ConfigValue 'MCP_APP_NAME'
# Assert existence before any build/push. Never provision or infer a replacement app.
$null = Invoke-Native az @('containerapp', 'show', '--name', $AppName, '--resource-group', $ResourceGroup)
$Commit = (Invoke-Native git @('rev-parse', 'HEAD')).Trim()
if ($Commit -notmatch '^[a-f0-9]{40}$') { throw 'Invalid Git commit' }
$Repository = 'agent-lz/mcp'
$Tag = "${Repository}:$Commit"
$Image = "$LoginServer/$Tag"
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $null = Invoke-Native az @('acr', 'login', '--name', $Registry)
    Invoke-Native docker @('build', '--platform', 'linux/amd64', '-t', $Image, '.')
    Invoke-Native docker @('push', $Image)
} else {
    Invoke-Native az @('acr', 'build', '--registry', $Registry, '--image', $Tag, '--file', 'Dockerfile', '.')
}
$Digest = (Invoke-Native az @(
    'acr', 'manifest', 'show-metadata', '--registry', $Registry, '--name', $Tag,
    '--query', 'digest', '-o', 'tsv'
)).Trim()
if ($Digest -notmatch '^sha256:[a-f0-9]{64}$') { throw 'Registry did not return an immutable digest' }
Invoke-Native az @(
    'containerapp', 'update', '--name', $AppName, '--resource-group', $ResourceGroup,
    '--image', "$LoginServer/$Repository@$Digest",
    '--set-env-vars', "APP_CONFIG_ENDPOINT=$Endpoint"
)
