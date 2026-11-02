"""Deployment checks use process-local shell function mocks: never Azure/image publication."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PS = shutil.which("pwsh") or shutil.which("powershell")
BASH = shutil.which("bash")
FAIL_SCENARIOS = {
    "empty",
    "bad-registry-id",
    "registry-mismatch",
    "multi",
    "wrong-bound",
    "no-identity",
}


def assert_binding(calls, scenario):
    assert all("AZURE_RESOURCE_GROUP" not in c for c in calls)
    app_calls = [c for c in calls if "az containerapp" in c]
    assert all("--resource-group application-rg" in c for c in app_calls)
    registry_calls = [
        c for c in calls if c.startswith("az acr login") or c.startswith("az acr build")
    ]
    assert all("--resource-group registry-rg" in c for c in registry_calls)
    assert all("--subscription 00000000-0000-0000-0000-000000000001" in c for c in registry_calls)
    update = next(c for c in calls if c.startswith("az containerapp update"))
    assert "99999999-9999-9999-9999-999999999999" not in update
    if scenario == "system":
        assert "--remove-env-vars AZURE_CLIENT_ID" in update
        assert "AZURE_CLIENT_ID=" not in update
    else:
        selected = (
            "22222222-2222-2222-2222-222222222222"
            if scenario == "multi-bound"
            else "11111111-1111-1111-1111-111111111111"
        )
        assert f"AZURE_CLIENT_ID={selected}" in update
    assert any(
        "--target-port 8080" in c for c in calls if c.startswith("az containerapp ingress update")
    )


@pytest.mark.skipif(not PS, reason="PowerShell not available")
@pytest.mark.parametrize(
    "failure,scenario",
    [
        ("", "local"),
        ("", "cloud"),
        ("", "bootstrap"),
        ("account show", "local"),
        ("appconfig", "local"),
        ("containerapp show", "local"),
        ("git", "local"),
        ("acr login", "local"),
        ("docker build", "local"),
        ("docker push", "local"),
        ("acr build", "cloud"),
        ("manifest", "local"),
        ("containerapp update", "local"),
        ("azd", "bootstrap"),
        ("", "empty"),
        ("acr show", "local"),
        ("identity show", "local"),
        ("containerapp ingress update", "local"),
        ("", "system"),
        ("", "bound"),
        ("", "multi-bound"),
        ("", "multi"),
        ("", "wrong-bound"),
        ("", "no-identity"),
        ("", "bad-registry-id"),
        ("", "registry-mismatch"),
    ],
)
def test_powershell_native_failures_and_digest(failure, scenario):
    result = subprocess.run(
        [
            PS,
            "-NoProfile",
            "-File",
            str(ROOT / "tests" / "deploy_mocks.ps1"),
            "-Failure",
            failure,
            "-Scenario",
            scenario,
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["failed"] == bool(failure or scenario in FAIL_SCENARIOS), result.stdout
    updates = [c for c in report["calls"] if c.startswith("az containerapp update")]
    if not failure and scenario not in FAIL_SCENARIOS:
        assert len(updates) == 1
        assert "agent-lz/mcp@sha256:" in updates[0]
        assert "--set-env-vars APP_CONFIG_ENDPOINT=https://example.azconfig.io" in updates[0]
        assert all("--label agent-lz" in c for c in report["calls"] if "appconfig" in c)
        assert_binding(report["calls"], scenario)
    elif failure not in ("containerapp update", "containerapp ingress update"):
        assert not updates


BASH_MOCKS = r"""
set -euo pipefail
az() {
  printf 'CALL az %s\n' "$*" >&2
  if [[ -n "$FAILURE" && "$*" == *"$FAILURE"* ]]; then return 17; fi
  case "$1 $2" in
    'appconfig kv')
      while [[ "$1" != '--key' ]]; do shift; done
      case "$2" in
        CONTAINER_REGISTRY_NAME) echo mockregistry;;
        CONTAINER_REGISTRY_LOGIN_SERVER) echo mockregistry.azurecr.io;;
        CONTAINER_REGISTRY_RESOURCE_ID)
          if [[ "$SCENARIO" == bad-registry-id ]]; then echo /wrong/registry; else
            echo /subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/registry-rg/providers/Microsoft.ContainerRegistry/registries/mockregistry
          fi;;
        AZURE_RESOURCE_GROUP) return 99;;
        AZURE_APP_RESOURCE_GROUP) echo application-rg;;
        MCP_APP_NAME) [[ "$SCENARIO" != empty ]] && echo synthetic-mcp || :;;
      esac;;
    'acr show')
      if [[ "$SCENARIO" == registry-mismatch ]]; then echo wrong.azurecr.io; else echo mockregistry.azurecr.io; fi;;
    'identity show')
      if [[ "$*" == *'/exact/app/uai2'* ]]; then echo 22222222-2222-2222-2222-222222222222; else
        echo 11111111-1111-1111-1111-111111111111; fi;;
    'containerapp show')
      if [[ "$*" == *'keys(identity.userAssignedIdentities)'* ]]; then
        echo /exact/app/uai1
        [[ "$SCENARIO" != multi* ]] || echo /exact/app/uai2
      elif [[ "$SCENARIO" == system ]]; then echo SystemAssigned
      elif [[ "$SCENARIO" == no-identity ]]; then echo None
      else echo 'SystemAssigned, UserAssigned'; fi;;
    'acr manifest') printf 'sha256:%064d\n' 0;;
    *) echo 'mock success';;
  esac
}
azd() {
  printf 'CALL azd %s\n' "$*" >&2
  [[ "$FAILURE" != azd ]] || return 17
  echo https://example.azconfig.io
}
git() {
  printf 'CALL git %s\n' "$*" >&2
  [[ "$FAILURE" != git ]] || return 17
  printf '%040d\n' 0
}
docker() {
  printf 'CALL docker %s\n' "$*" >&2
  [[ "$FAILURE" != "docker $1" ]] || return 17
  echo 'mock success'
}
command() {
  if [[ "$1" == -v && "$2" == docker ]]; then
    [[ "$SCENARIO" != cloud ]] || return 1
    echo 'mock docker'; return 0
  fi
  builtin command "$@"
}
export -f az azd git docker command
exec bash scripts/deploy.sh
"""


@pytest.mark.skipif(not BASH, reason="Bash not available")
@pytest.mark.parametrize(
    "failure,scenario",
    [
        ("", "local"),
        ("", "cloud"),
        ("", "bootstrap"),
        ("account show", "local"),
        ("appconfig", "local"),
        ("containerapp show", "local"),
        ("git", "local"),
        ("acr login", "local"),
        ("docker build", "local"),
        ("docker push", "local"),
        ("acr build", "cloud"),
        ("manifest", "local"),
        ("containerapp update", "local"),
        ("azd", "bootstrap"),
        ("", "empty"),
        ("acr show", "local"),
        ("identity show", "local"),
        ("containerapp ingress update", "local"),
        ("", "system"),
        ("", "bound"),
        ("", "multi-bound"),
        ("", "multi"),
        ("", "wrong-bound"),
        ("", "no-identity"),
        ("", "bad-registry-id"),
        ("", "registry-mismatch"),
    ],
)
def test_bash_native_failures_and_digest(failure, scenario):
    env = os.environ | {
        "FAILURE": failure,
        "SCENARIO": scenario,
        "APP_CONFIG_ENDPOINT": "" if scenario == "bootstrap" else "https://example.azconfig.io",
        "AZURE_CLIENT_ID": "99999999-9999-9999-9999-999999999999",
        "MCP_APP_CLIENT_ID": {
            "bound": "11111111-1111-1111-1111-111111111111",
            "multi-bound": "22222222-2222-2222-2222-222222222222",
            "wrong-bound": "99999999-9999-9999-9999-999999999999",
        }.get(scenario, ""),
    }
    result = subprocess.run(
        [BASH, "-c", BASH_MOCKS],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    failed = bool(failure or scenario in FAIL_SCENARIOS)
    assert (result.returncode != 0) == failed, result.stderr
    updates = [c for c in result.stderr.splitlines() if c.startswith("CALL az containerapp update")]
    if not failed:
        assert len(updates) == 1
        assert "agent-lz/mcp@sha256:" in updates[0]
        assert "--set-env-vars APP_CONFIG_ENDPOINT=https://example.azconfig.io" in updates[0]
        assert all("--label agent-lz" in c for c in result.stderr.splitlines() if "appconfig" in c)
        assert_binding(
            [c.removeprefix("CALL ") for c in result.stderr.splitlines() if c.startswith("CALL ")],
            scenario,
        )
    elif failure not in ("containerapp update", "containerapp ingress update"):
        assert not updates


def test_container_and_azd_static_contract():
    docker = (ROOT / "Dockerfile").read_text()
    assert "python:3.12-slim" in docker
    assert "uv sync --frozen --no-dev" in docker
    assert "msodbcsql18" in docker and "USER 10001" in docker
    assert "COPY . ." not in docker
    assert '"server:app"' in docker
    yaml = (ROOT / "azure.yaml").read_text()
    assert "infra:" not in yaml
    assert "preprovision:" in yaml
    assert "scripts/deploy.sh" in yaml and "scripts/deploy.ps1" in yaml


def test_distributable_lock_has_public_artifact_urls():
    import tomllib

    current = tomllib.loads((ROOT / "uv.lock").read_text())
    assert next(p["version"] for p in current["package"] if p["name"] == "mcp") == "2.3.0"
    for package in current["package"]:
        if "registry" not in package["source"]:
            continue
        assert package["source"]["registry"] == "https://pypi.org/simple"
        for artifact in package.get("wheels", []) + (
            [package["sdist"]] if "sdist" in package else []
        ):
            assert artifact["url"].startswith("https://files.pythonhosted.org/packages/")
