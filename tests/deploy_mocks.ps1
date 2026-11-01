# Local behavioral harness. Function mocks cannot call Azure/Docker/Git executables.
param([string]$Failure = '', [string]$Scenario = 'local')
$ErrorActionPreference = 'Stop'
$global:Calls = [System.Collections.Generic.List[string]]::new()

function global:az {
    $global:Calls.Add("az $($args -join ' ')")
    $global:LASTEXITCODE = 0
    if ($Failure -and ($args -join ' ') -like "*$Failure*") {
        $global:LASTEXITCODE = 17
        return 'native failure'
    }
    if ($args[0] -eq 'appconfig') {
        $key = $args[[Array]::IndexOf($args, '--key') + 1]
        if ($Scenario -eq 'empty' -and $key -eq 'MCP_APP_NAME') { return '' }
        switch ($key) {
            'CONTAINER_REGISTRY_NAME' { return 'mockregistry' }
            'CONTAINER_REGISTRY_LOGIN_SERVER' { return 'mockregistry.azurecr.io' }
            'CONTAINER_REGISTRY_RESOURCE_ID' {
                if ($Scenario -eq 'bad-registry-id') { return '/wrong/registry' }
                return '/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/registry-rg/providers/Microsoft.ContainerRegistry/registries/mockregistry'
            }
            'AZURE_RESOURCE_GROUP' { throw 'Foundry group must never be consumed' }
            'AZURE_APP_RESOURCE_GROUP' { return 'application-rg' }
            'MCP_APP_NAME' { return 'synthetic-mcp' }
        }
    }
    if ($args[0] -eq 'acr' -and $args[1] -eq 'show') {
        if ($Scenario -eq 'registry-mismatch') { return 'wrong.azurecr.io' }
        return 'mockregistry.azurecr.io'
    }
    if ($args[0] -eq 'containerapp' -and $args[1] -eq 'show') {
        $identity = @{ type = 'SystemAssigned, UserAssigned'; userAssignedIdentities = @{ '/exact/app/uai1' = @{} } }
        if ($Scenario -eq 'system') { $identity = @{ type = 'SystemAssigned' } }
        if ($Scenario -eq 'no-identity') { $identity = @{ type = 'None' } }
        if ($Scenario -like 'multi*') { $identity.userAssignedIdentities['/exact/app/uai2'] = @{} }
        return (@{ identity = $identity } | ConvertTo-Json -Depth 5 -Compress)
    }
    if ($args[0] -eq 'identity') {
        if ($args -contains '/exact/app/uai2') { return '22222222-2222-2222-2222-222222222222' }
        return '11111111-1111-1111-1111-111111111111'
    }
    if ($args[0] -eq 'acr' -and $args[1] -eq 'manifest') { return "sha256:$('b' * 64)" }
    return 'mock success'
}
function global:azd {
    $global:Calls.Add("azd $($args -join ' ')")
    $global:LASTEXITCODE = 0
    if ($Failure -eq 'azd') { $global:LASTEXITCODE = 17; return 'native failure' }
    return 'https://example.azconfig.io'
}
function global:git {
    $global:Calls.Add("git $($args -join ' ')")
    $global:LASTEXITCODE = 0
    if ($Failure -eq 'git') { $global:LASTEXITCODE = 17; return 'native failure' }
    return ('a' * 40)
}
function global:docker {
    $global:Calls.Add("docker $($args -join ' ')")
    $global:LASTEXITCODE = 0
    if ($Failure -eq "docker $($args[0])") { $global:LASTEXITCODE = 17; return 'native failure' }
    return 'mock success'
}
function global:Get-Command {
    param([string]$Name, $ErrorAction)
    if ($Name -eq 'docker') {
        if ($Scenario -eq 'cloud') { return $null }
        return 'mock docker'
    }
    throw 'Unexpected command discovery'
}
$env:APP_CONFIG_ENDPOINT = 'https://example.azconfig.io'
$env:AZURE_CLIENT_ID = '99999999-9999-9999-9999-999999999999'
$env:MCP_APP_CLIENT_ID = ''
if ($Scenario -eq 'bound') { $env:MCP_APP_CLIENT_ID = '11111111-1111-1111-1111-111111111111' }
if ($Scenario -eq 'multi-bound') { $env:MCP_APP_CLIENT_ID = '22222222-2222-2222-2222-222222222222' }
if ($Scenario -eq 'wrong-bound') { $env:MCP_APP_CLIENT_ID = $env:AZURE_CLIENT_ID }
if ($Scenario -eq 'bootstrap') { $env:APP_CONFIG_ENDPOINT = '' }
$failed = $false
try { & "$PSScriptRoot/../scripts/deploy.ps1" | Out-Null } catch { $failed = $true }
Write-Output (@{ failed = $failed; calls = @($global:Calls) } | ConvertTo-Json -Depth 4 -Compress)
