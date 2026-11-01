"""Bounded orchestration over injectable Azure/SQL adapters."""

import asyncio
import logging
import uuid

from .contracts import NL2SQLError
from .sql_validation import validate_sql

logger = logging.getLogger(__name__)


class Service:
    def __init__(self, catalog, models, sql, settings):
        self.catalog, self.models, self.sql, self.settings = catalog, models, sql, settings

    async def list_sources(self):
        try:
            async with asyncio.timeout(self.settings.MCP_QUERY_TIMEOUT_SECONDS):
                return await self.catalog.list_sources()
        except NL2SQLError:
            raise
        except TimeoutError:
            raise NL2SQLError("QUERY_TIMEOUT: overall deadline exceeded") from None
        except Exception as exc:
            logger.warning("Source catalog failure (%s)", type(exc).__name__)
            raise NL2SQLError("CATALOG_FAILED: approved source catalog is unavailable") from None

    async def query(self, source_id, question):
        try:
            async with asyncio.timeout(self.settings.MCP_QUERY_TIMEOUT_SECONDS):
                source = await self.catalog.source(source_id)
                embedding = await self.models.embed(question)
                records, objects = await self.catalog.retrieve(source, embedding)
                sql = await self.models.generate(question, source, records, objects)
                validate_sql(sql, objects)
                # Recheck operator revocation/version replacement before SQL execution.
                current = await self.catalog.source(source_id)
                if current != source:
                    raise NL2SQLError("SOURCE_CHANGED: source changed during query; retry")
                return await self.sql.execute(source, sql, str(uuid.uuid4()))
        except NL2SQLError:
            raise
        except TimeoutError:
            raise NL2SQLError("QUERY_TIMEOUT: overall deadline exceeded") from None
        except Exception as exc:
            # SDK tool errors are safe; never forward/log model/SQL/provider exception text.
            logger.warning("NL2SQL provider failure (%s)", type(exc).__name__)
            raise NL2SQLError("PROVIDER_FAILED: metadata, model or SQL operation failed") from None
