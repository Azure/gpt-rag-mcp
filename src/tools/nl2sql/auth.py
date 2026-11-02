"""Entra application-token verifier plugged into the official MCP auth middleware."""

import asyncio
import logging

import jwt
from mcp.server.auth.provider import AccessToken

logger = logging.getLogger(__name__)


class EntraVerifier:
    def __init__(self, settings, jwks=None):
        self.settings = settings
        self.jwks = jwks or jwt.PyJWKClient(
            f"https://login.microsoftonline.com/{settings.MCP_AUTH_TENANT_ID}/discovery/v2.0/keys",
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        if len(token) > 16384:
            return None
        try:
            key = await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=str(self.settings.MCP_AUTH_AUDIENCE),
                issuer=self.settings.issuer,
                options={
                    "require": ["exp", "iss", "aud", "azp", "roles", "ver", "tid"],
                    "strict_aud": True,
                },
            )
            roles = claims["roles"]
            if (
                claims["ver"] != "2.0"
                or claims["tid"] != str(self.settings.MCP_AUTH_TENANT_ID)
                or claims["azp"] not in {str(x) for x in self.settings.MCP_ALLOWED_CLIENT_IDS}
                or not isinstance(roles, list)
                or "MCP.Invoke" not in roles
                or "scp" in claims  # No delegated user-token authority.
            ):
                return None
            return AccessToken(
                token=token,
                client_id=claims["azp"],
                scopes=["MCP.Invoke"],
                expires_at=claims["exp"],
                claims={"iss": claims["iss"]},
            )
        except (jwt.PyJWTError, OSError, ValueError, TypeError):
            logger.info("MCP token denied")  # Never log tokens/claims/JWKS exception bodies.
            return None
