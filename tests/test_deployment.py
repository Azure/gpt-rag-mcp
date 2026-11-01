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
    assert report["failed"] == bool(failure or scenario == "empty"), result.stdout
    updates = [c for c in report["calls"] if c.startswith("az containerapp update")]
    if not failure and scenario != "empty":
        assert len(updates) == 1
        assert "agent-lz/mcp@sha256:" in updates[0]
        assert "--set-env-vars APP_CONFIG_ENDPOINT=https://example.azconfig.io" in updates[0]
        assert all("--label agent-lz" in c for c in report["calls"] if "appconfig" in c)
    elif failure != "containerapp update":
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
        AZURE_RESOURCE_GROUP) echo synthetic-rg;;
        MCP_APP_NAME) [[ "$SCENARIO" != empty ]] && echo synthetic-mcp || :;;
      esac;;
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
    ],
)
def test_bash_native_failures_and_digest(failure, scenario):
    env = os.environ | {
        "FAILURE": failure,
        "SCENARIO": scenario,
        "APP_CONFIG_ENDPOINT": "" if scenario == "bootstrap" else "https://example.azconfig.io",
    }
    result = subprocess.run(
        [BASH, "-c", BASH_MOCKS],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    failed = bool(failure or scenario == "empty")
    assert (result.returncode != 0) == failed, result.stderr
    updates = [c for c in result.stderr.splitlines() if c.startswith("CALL az containerapp update")]
    if not failed:
        assert len(updates) == 1
        assert "agent-lz/mcp@sha256:" in updates[0]
        assert "--set-env-vars APP_CONFIG_ENDPOINT=https://example.azconfig.io" in updates[0]
        assert all("--label agent-lz" in c for c in result.stderr.splitlines() if "appconfig" in c)
    elif failure != "containerapp update":
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
