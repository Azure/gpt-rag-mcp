from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from starlette.testclient import TestClient

import server
from tools.nl2sql.models import Models


async def test_official_async_model_adapter_selected_deployments(settings, monkeypatch):
    import tools.nl2sql.models as module

    client = AsyncMock()
    client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0, 0, 1])]
    )
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="SELECT 1"))]
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(module, "AsyncOpenAI", factory)
    monkeypatch.setattr(module, "get_bearer_token_provider", Mock(return_value="mock-provider"))
    models = Models(settings, object())
    assert factory.call_args.kwargs["base_url"] == "https://example.openai.azure.com/openai/v1/"
    assert factory.call_args.kwargs["api_key"] == "mock-provider"
    assert await models.embed("approved schema") == [0, 0, 1]
    assert client.embeddings.create.call_args.kwargs["model"] == "embedding"
    assert client.embeddings.create.call_args.kwargs["dimensions"] == 3
    assert await models.generate("question", None, [], {"dbo.Products"}) == "SELECT 1"
    assert client.chat.completions.create.call_args.kwargs["model"] == "generation"
    await models.close()
    client.close.assert_awaited_once()


def test_production_lifespan_with_mock_azure_boundaries(settings, monkeypatch):
    settings.MCP_ALLOWED_CLIENT_IDS = []
    credential, cosmos = AsyncMock(), AsyncMock()
    credential.__aenter__.return_value = credential
    cosmos.__aenter__.return_value = cosmos
    cosmos.get_database_client = Mock()
    sync_credential = Mock()
    models = AsyncMock()
    sql = AsyncMock()
    monkeypatch.setattr(server, "ManagedIdentityCredential", Mock(return_value=credential))
    monkeypatch.setattr(server, "SyncManagedIdentityCredential", Mock(return_value=sync_credential))
    monkeypatch.setattr(server, "CosmosClient", Mock(return_value=cosmos))
    monkeypatch.setattr(server, "Models", Mock(return_value=models))
    monkeypatch.setattr(server, "SQLExecutor", Mock(return_value=sql))
    monkeypatch.setattr(server, "load_settings", AsyncMock(return_value=settings))
    with TestClient(server.Runtime(lifespan=server.lifespan)) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert (
            client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                },
            ).status_code
            == 401
        )
        assert client.get("/.well-known/oauth-protected-resource/mcp").status_code == 200
    models.close.assert_awaited_once()
    sql.close.assert_awaited_once()
    sync_credential.close.assert_called_once()
