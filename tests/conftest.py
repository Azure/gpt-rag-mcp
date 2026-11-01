import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from tools.nl2sql.auth import EntraVerifier
from tools.nl2sql.config import Settings
from tools.nl2sql.contracts import Source

TENANT = "10000000-0000-0000-0000-000000000001"
AUDIENCE = "20000000-0000-0000-0000-000000000002"
CLIENT = "30000000-0000-0000-0000-000000000003"


@pytest.fixture
def settings():
    return Settings(
        MCP_AUTH_TENANT_ID=TENANT,
        MCP_AUTH_AUDIENCE=AUDIENCE,
        MCP_AUTH_RESOURCE_SCOPE=f"api://{AUDIENCE}/.default",
        MCP_ALLOWED_CLIENT_IDS=[CLIENT],
        MCP_COSMOS_ENDPOINT="https://example.documents.azure.com",
        MCP_COSMOS_DATABASE="application",
        MCP_EMBEDDING_DIMENSIONS=3,
        AI_FOUNDRY_OPENAI_ENDPOINT="https://example.openai.azure.com",
        CHAT_DEPLOYMENT_NAME="generation",
        EMBEDDING_DEPLOYMENT_NAME="embedding",
    )


@pytest.fixture
def import_json():
    return json.loads(
        (Path(__file__).parents[1] / "samples" / "approved-synthetic.json").read_text()
    )


@pytest.fixture
def source(import_json):
    return Source.model_validate(import_json["source"])


@pytest.fixture
def signing(settings):
    import time

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = Mock()
    jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
    verifier = EntraVerifier(settings, jwks)
    claims = {
        "iss": settings.issuer,
        "aud": AUDIENCE,
        "tid": TENANT,
        "ver": "2.0",
        "azp": CLIENT,
        "roles": ["MCP.Invoke"],
        "exp": int(time.time()) + 600,
    }

    def token(**updates):
        return jwt.encode(claims | updates, key, algorithm="RS256", headers={"kid": "test"})

    return SimpleNamespace(key=key, jwks=jwks, verifier=verifier, claims=claims, token=token)


class Container:
    def __init__(self, documents=()):
        self.documents = list(documents)
        self.calls = []
        self.create_item = AsyncMock()
        self.replace_item = AsyncMock()

    def query_items(self, **kwargs):
        self.calls.append(kwargs)

        async def iterator():
            params = {p["name"]: p["value"] for p in kwargs.get("parameters", [])}
            for doc in self.documents:
                if "@object" in params:
                    if doc.get("kind") != "schema":
                        continue
                    if (doc.get("object_name") or "") != params["@object"]:
                        continue
                yield doc

        return iterator()
