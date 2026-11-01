"""App Configuration (agent-lz) bootstrap with managed identity only."""

import json
import os
import re
from uuid import UUID

from azure.appconfiguration.aio import AzureAppConfigurationClient
from pydantic import BaseModel, Field, HttpUrl, model_validator


class Settings(BaseModel):
    MCP_AUTH_TENANT_ID: UUID
    MCP_AUTH_AUDIENCE: UUID
    MCP_AUTH_RESOURCE_SCOPE: str
    MCP_ALLOWED_CLIENT_IDS: list[UUID]
    MCP_SQL_SECRET_NAMES: list[str] = Field(default_factory=list)
    MCP_COSMOS_ENDPOINT: HttpUrl
    MCP_COSMOS_DATABASE: str = Field(min_length=1)
    MCP_SOURCES_CONTAINER: str = "mcp-sources"
    MCP_METADATA_CONTAINER: str = "mcp-nl2sql-metadata"
    MCP_EMBEDDING_DIMENSIONS: int = Field(default=3072, ge=1, le=65536)
    MCP_QUERY_TIMEOUT_SECONDS: int = Field(default=75, ge=1, le=75)
    MCP_METADATA_TOP_K: int = Field(default=8, ge=1, le=32)
    AI_FOUNDRY_OPENAI_ENDPOINT: HttpUrl
    CHAT_DEPLOYMENT_NAME: str = Field(min_length=1)
    EMBEDDING_DEPLOYMENT_NAME: str = Field(min_length=1)
    KEY_VAULT_ENDPOINT: HttpUrl | None = None
    MCP_SERVER_URL: HttpUrl | None = None

    @model_validator(mode="after")
    def secure_urls(self):
        if self.MCP_AUTH_RESOURCE_SCOPE != f"api://{self.MCP_AUTH_AUDIENCE}/.default":
            raise ValueError("Resource scope must target the dedicated MCP audience")
        for name in ("MCP_COSMOS_ENDPOINT", "AI_FOUNDRY_OPENAI_ENDPOINT", "KEY_VAULT_ENDPOINT"):
            url = getattr(self, name)
            if url and (url.scheme != "https" or url.username or url.password):
                raise ValueError("Provider endpoints require HTTPS without credentials")
        url = self.MCP_SERVER_URL
        if url and (
            url.scheme != "https"
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path != "/mcp"
        ):
            raise ValueError("MCP_SERVER_URL must be the public HTTPS /mcp endpoint")

        if any(not re.fullmatch(r"[A-Za-z0-9-]{1,127}", n) for n in self.MCP_SQL_SECRET_NAMES):
            raise ValueError("SQL secret names must be Key Vault reference names")
        endpoint_path = self.AI_FOUNDRY_OPENAI_ENDPOINT.path
        if endpoint_path not in (None, "/"):
            raise ValueError("AI_FOUNDRY_OPENAI_ENDPOINT must be the platform endpoint root")
        return self

    @property
    def issuer(self):
        return f"https://login.microsoftonline.com/{self.MCP_AUTH_TENANT_ID}/v2.0"

    @property
    def resource_url(self):
        if self.MCP_SERVER_URL:
            return str(self.MCP_SERVER_URL)
        hostname = os.getenv("CONTAINER_APP_HOSTNAME")
        return f"https://{hostname}/mcp" if hostname else "http://localhost:8080/mcp"


async def load_settings(credential) -> Settings:
    endpoint = os.environ.get("APP_CONFIG_ENDPOINT", "")
    if not re.fullmatch(r"https://[A-Za-z0-9-]+\.azconfig\.io", endpoint):
        raise ValueError("APP_CONFIG_ENDPOINT must be an HTTPS App Configuration endpoint")
    async with AzureAppConfigurationClient(endpoint, credential) as client:
        values = {}
        async for item in client.list_configuration_settings(label_filter="agent-lz"):
            if item.key in Settings.model_fields:
                # Secrets are never accepted as plaintext configuration values.
                if item.content_type and "keyvaultref" in item.content_type:
                    raise ValueError("Runtime configuration fields must not contain secret values")
                values[item.key] = item.value
        for name in ("MCP_ALLOWED_CLIENT_IDS", "MCP_SQL_SECRET_NAMES"):
            if name in values:
                values[name] = json.loads(values[name])
        return Settings.model_validate(values)
