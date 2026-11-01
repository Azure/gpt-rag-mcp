"""Thin official MCPServer composition. No import-time Azure calls."""

import asyncio
import os
from contextlib import AsyncExitStack, asynccontextmanager

from azure.cosmos.aio import CosmosClient
from azure.identity import ManagedIdentityCredential as SyncManagedIdentityCredential
from azure.identity.aio import ManagedIdentityCredential
from azure.keyvault.secrets.aio import SecretClient
from mcp.server import MCPServer
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from starlette.applications import Starlette
from starlette.responses import JSONResponse

from tools.nl2sql.auth import EntraVerifier
from tools.nl2sql.catalog import Catalog
from tools.nl2sql.config import load_settings
from tools.nl2sql.contracts import NL2SQLError, QueryResult, Question, SourceId, SourcesResult
from tools.nl2sql.models import Models
from tools.nl2sql.service import Service
from tools.nl2sql.sql import SQLExecutor


def create_app(service, settings, verifier=None):
    """Compose injectable adapters with real SDK auth, schemas, transport, and liveness."""
    server = MCPServer(
        "agent-app-mcp",
        version="1.0.0",
        token_verifier=verifier or EntraVerifier(settings),
        auth=AuthSettings(
            issuer_url=settings.issuer,
            resource_server_url=settings.resource_url,
            required_scopes=["MCP.Invoke"],
            validate_token_resource=False,
        ),
    )
    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

    @server.tool(name="nl2sql.list_sources", structured_output=True, annotations=annotations)
    async def list_sources() -> SourcesResult:
        """List enabled, operator-approved SQL sources; never return connection or credential data."""
        try:
            return await service.list_sources()
        except NL2SQLError as exc:
            raise ToolError(str(exc)) from None

    @server.tool(name="nl2sql.query", structured_output=True, annotations=annotations)
    async def query(source_id: SourceId, question: Question) -> QueryResult:
        """Query an approved Azure SQL/SQL Server source using bounded read-only NL2SQL."""
        if not question.strip():
            raise ToolError("INPUT_INVALID: question must not be blank")
        try:
            return await service.query(source_id, question)
        except NL2SQLError as exc:
            raise ToolError(str(exc)) from None

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(_request):
        return JSONResponse({"status": "ok"})

    return server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        max_request_body_size=16384,
        host="0.0.0.0",
    )


@asynccontextmanager
async def lifespan(app):
    async with AsyncExitStack() as stack:
        credential = await stack.enter_async_context(
            ManagedIdentityCredential(client_id=os.getenv("AZURE_CLIENT_ID"))
        )
        settings = await load_settings(credential)
        cosmos = await stack.enter_async_context(
            CosmosClient(str(settings.MCP_COSMOS_ENDPOINT), credential=credential)
        )
        database = cosmos.get_database_client(settings.MCP_COSMOS_DATABASE)
        models = Models(settings, credential)
        stack.push_async_callback(models.close)
        sync_credential = SyncManagedIdentityCredential(client_id=os.getenv("AZURE_CLIENT_ID"))
        stack.push_async_callback(asyncio.to_thread, sync_credential.close)
        vault = None
        if settings.KEY_VAULT_ENDPOINT:
            vault = await stack.enter_async_context(
                SecretClient(str(settings.KEY_VAULT_ENDPOINT), credential)
            )
        sql = SQLExecutor(sync_credential, vault, secret_names=settings.MCP_SQL_SECRET_NAMES)
        stack.push_async_callback(sql.close)
        service = Service(
            Catalog(
                database.get_container_client(settings.MCP_SOURCES_CONTAINER),
                database.get_container_client(settings.MCP_METADATA_CONTAINER),
                settings,
            ),
            models,
            sql,
            settings,
        )
        sdk_app = create_app(service, settings)
        await stack.enter_async_context(sdk_app.router.lifespan_context(sdk_app))
        app.state.sdk_app = sdk_app
        yield


class Runtime(Starlette):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await super().__call__(scope, receive, send)
        else:
            await self.state.sdk_app(scope, receive, send)


app = Runtime(lifespan=lifespan)
