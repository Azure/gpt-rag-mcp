import jwt
import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock

from server import create_app
from tools.nl2sql.contracts import QueryResult, SourcesResult


async def test_valid_application_token(signing):
    access = await signing.verifier.verify_token(signing.token())
    assert access.client_id == signing.claims["azp"]
    assert access.scopes == ["MCP.Invoke"]


@pytest.mark.parametrize(
    "updates",
    [
        {"aud": "api://wrong"},
        {"iss": "https://wrong.example"},
        {"tid": "40000000-0000-0000-0000-000000000004"},
        {"exp": 0},
        {"ver": "1.0"},
        {"roles": []},
        {"roles": "MCP.Invoke"},
        {"azp": "40000000-0000-0000-0000-000000000004"},
        {"scp": "MCP.Invoke"},
        {"nbf": 9999999999},
        {"aud": ["20000000-0000-0000-0000-000000000002"]},
    ],
)
async def test_claim_denials(signing, updates):
    assert await signing.verifier.verify_token(signing.token(**updates)) is None


async def test_signature_algorithm_missing_claims_and_jwks_failure(signing):
    assert (
        await signing.verifier.verify_token(
            jwt.encode(signing.claims, "untrusted-secret" * 3, algorithm="HS256")
        )
        is None
    )
    claims = {k: v for k, v in signing.claims.items() if k != "exp"}
    assert await signing.verifier.verify_token(jwt.encode(claims, signing.key, "RS256")) is None
    assert await signing.verifier.verify_token("not-a-token") is None
    signing.jwks.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError("offline")
    assert await signing.verifier.verify_token(signing.token()) is None


async def test_empty_allowlist_starts_but_denies(settings, signing):
    settings.MCP_ALLOWED_CLIENT_IDS = []
    assert await signing.verifier.verify_token(signing.token()) is None
    with TestClient(create_app(AsyncMock(), settings, signing.verifier)) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.post("/mcp").status_code == 401
        assert (
            client.post("/mcp", headers={"Authorization": f"Bearer {signing.token()}"}).status_code
            == 401
        )


def test_real_sdk_http_discovery_and_structured_output(settings, signing):
    service = AsyncMock()
    service.list_sources.return_value = SourcesResult(sources=[])
    service.query.return_value = QueryResult(
        source_id="synthetic",
        query_id="test-id",
        metadata_version="v1",
        columns=[],
        rows=[],
        row_count=0,
    )
    with TestClient(create_app(service, settings, signing.verifier)) as client:
        assert client.get("/healthz").status_code == 200
        for path in ("/", "/sse", "/mcp/sse"):
            assert client.get(path).status_code == 404
        denial = client.post("/mcp")
        assert denial.status_code == 401
        assert "resource_metadata=" in denial.headers["www-authenticate"]
        assert (
            client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {},
                },
            ).status_code
            == 401
        )
        metadata = client.get("/.well-known/oauth-protected-resource/mcp").json()
        assert metadata["resource"] == "http://localhost:8080/mcp"
        assert metadata["authorization_servers"] == [settings.issuer]
        headers = {
            "Authorization": f"Bearer {signing.token()}",
            "Accept": "application/json, text/event-stream",
        }

        def rpc(method, params=None, id=1):
            response = client.post(
                "/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": id,
                    "method": method,
                    "params": params or {},
                },
            )
            assert response.status_code == 200, response.text
            assert "mcp-session-id" not in response.headers
            return response.json()

        initialized = rpc(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "local-test", "version": "1"},
            },
        )
        assert initialized["result"]["serverInfo"]["version"] == "1.0.0"
        tools = rpc("tools/list")["result"]["tools"]
        assert {t["name"] for t in tools} == {"nl2sql.list_sources", "nl2sql.query"}
        query = next(t for t in tools if t["name"] == "nl2sql.query")
        assert query["inputSchema"]["required"] == ["source_id", "question"]
        assert query["inputSchema"]["properties"]["question"]["maxLength"] == 4000
        assert "rows" in query["outputSchema"]["properties"]
        assert rpc("tools/call", {"name": "nl2sql.list_sources"})["result"][
            "structuredContent"
        ] == {
            "schema_version": 1,
            "sources": [],
        }
        result = rpc(
            "tools/call",
            {
                "name": "nl2sql.query",
                "arguments": {"source_id": "synthetic", "question": "count?"},
            },
        )["result"]
        assert result["structuredContent"]["row_count"] == 0
        for arguments in (
            {"source_id": "../bad", "question": "count"},
            {"source_id": "synthetic", "question": "x" * 4001},
            {"source_id": "synthetic", "question": "  "},
        ):
            result = rpc("tools/call", {"name": "nl2sql.query", "arguments": arguments})["result"]
            assert result["isError"] is True
        assert service.query.await_count == 1
        assert client.post("/mcp", headers=headers, content="x" * 16385).status_code == 413


async def test_official_sdk_client_and_server_locally(settings, signing):
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    service = AsyncMock()
    service.list_sources.return_value = SourcesResult(sources=[])
    app = create_app(service, settings, signing.verifier)
    async with app.router.lifespan_context(app):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            base_url="http://localhost:8080",
            headers={"Authorization": f"Bearer {signing.token()}"},
        ) as http:
            async with streamable_http_client(
                "http://localhost:8080/mcp", http_client=http
            ) as streams:
                async with ClientSession(*streams) as session:
                    initialized = await session.initialize()
                    assert initialized.server_info.name == "agent-app-mcp"
                    tools = await session.list_tools()
                    assert len(tools.tools) == 2
                    result = await session.call_tool("nl2sql.list_sources", {})
                    assert result.structured_content == {"schema_version": 1, "sources": []}


def test_oauth_metadata_uses_parent_endpoint(settings, signing):
    from tools.nl2sql.config import Settings

    configured = Settings.model_validate(
        settings.model_dump() | {"MCP_SERVER_URL": "https://synthetic-mcp.example.com/mcp"}
    )
    with TestClient(create_app(AsyncMock(), configured, signing.verifier)) as client:
        document = client.get("/.well-known/oauth-protected-resource/mcp").json()
        assert document["resource"] == "https://synthetic-mcp.example.com/mcp"
        assert (
            client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            ).status_code
            == 401
        )
