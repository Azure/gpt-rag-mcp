"""Application-owned Cosmos catalog. No provisioning or business-row ingestion."""

import math
import struct

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from .contracts import Metadata, NL2SQLError, Source, SourcesResult, SourceSummary


def clean_document(document):
    return {k: v for k, v in document.items() if not k.startswith("_")}


def float32_vector(vector, dimensions):
    if len(vector) != dimensions or not all(math.isfinite(x) for x in vector):
        raise NL2SQLError("EMBEDDING_INVALID: embedding dimensions or values are invalid")
    try:
        return list(struct.unpack(f"<{dimensions}f", struct.pack(f"<{dimensions}f", *vector)))
    except (OverflowError, struct.error) as exc:
        raise NL2SQLError("EMBEDDING_INVALID: vector cannot be represented as float32") from exc


class Catalog:
    def __init__(self, sources, metadata, settings):
        self.sources = sources
        self.metadata = metadata
        self.settings = settings

    async def source(self, source_id):
        try:
            document = await self.sources.read_item(source_id, partition_key=source_id)
        except CosmosResourceNotFoundError as exc:
            raise NL2SQLError("SOURCE_NOT_APPROVED: source is unavailable") from exc
        source = Source.model_validate(clean_document(document))
        if not source.enabled:
            raise NL2SQLError("SOURCE_NOT_APPROVED: source is disabled")
        return source

    async def list_sources(self):
        summaries = []
        async for doc in self.sources.query_items(
            query="SELECT TOP 101 * FROM c WHERE c.enabled = @enabled",
            parameters=[{"name": "@enabled", "value": True}],
        ):
            source = Source.model_validate(clean_document(doc))
            summaries.append(
                SourceSummary(
                    source_id=source.source_id,
                    name=source.name,
                    description=source.description,
                    metadata_version=source.metadata_version,
                )
            )
        if len(summaries) > 100:
            raise NL2SQLError("SOURCE_LIMIT: approved source listing exceeds 100")
        return SourcesResult(sources=sorted(summaries, key=lambda s: s.source_id))

    def parameters(self, source):
        return [
            {"name": "@source", "value": source.source_id},
            {"name": "@version", "value": source.metadata_version},
        ]

    async def retrieve(self, source, embedding):
        vector = float32_vector(embedding, self.settings.MCP_EMBEDDING_DIMENSIONS)
        docs = self.metadata.query_items(
            query=(
                "SELECT TOP @k c.id, c.source_id, c.metadata_version, c.kind, c.content, "
                "c.object_name, c.related_objects FROM c "
                "WHERE c.source_id = @source AND c.metadata_version = @version "
                "ORDER BY VectorDistance(c.embedding, @embedding)"
            ),
            parameters=self.parameters(source)
            + [
                {"name": "@k", "value": self.settings.MCP_METADATA_TOP_K},
                {"name": "@embedding", "value": vector},
            ],
            partition_key=source.source_id,
        )
        records = [Metadata.model_validate(clean_document(d)) async for d in docs]
        if not records:
            raise NL2SQLError("METADATA_MISSING: active version has no matching metadata")
        approved = set(source.allowed_objects)
        # Expand schema and related/FK context to a fixed point, never silently drop relationships.
        needed = set()
        for record in records:
            needed.update(record.related_objects)
            if record.object_name:
                needed.add(record.object_name)
        expanded = set()
        while needed - expanded:
            obj = sorted(needed - expanded)[0]
            if obj not in approved:
                raise NL2SQLError("METADATA_UNAPPROVED: related object is not approved")
            schema_docs = self.metadata.query_items(
                query=(
                    "SELECT TOP 257 * FROM c WHERE c.source_id = @source "
                    "AND c.metadata_version = @version AND c.kind = @kind "
                    "AND c.object_name = @object"
                ),
                parameters=self.parameters(source)
                + [{"name": "@kind", "value": "schema"}, {"name": "@object", "value": obj}],
                partition_key=source.source_id,
            )
            schemas = [Metadata.model_validate(clean_document(d)) async for d in schema_docs]
            if not schemas:
                raise NL2SQLError("METADATA_CONTEXT_MISSING: related object schema is missing")
            expanded.add(obj)
            for record in schemas:
                needed.update(record.related_objects)
                if record.id not in {r.id for r in records}:
                    records.append(record)
            if len(records) > 256 or sum(len(r.content) for r in records) > 64000:
                raise NL2SQLError("METADATA_CONTEXT_LIMIT: complete context exceeds safety limit")
        if not expanded:
            raise NL2SQLError("METADATA_CONTEXT_MISSING: retrieval must identify approved objects")
        for record in records:
            if (
                record.source_id != source.source_id
                or record.metadata_version != source.metadata_version
            ):
                raise NL2SQLError("METADATA_INVALID: source/version mismatch")
            if record.object_name and record.object_name not in approved:
                raise NL2SQLError("METADATA_UNAPPROVED: object is not approved")
        if sum(len(r.content) for r in records) > 64000:
            raise NL2SQLError("METADATA_CONTEXT_LIMIT: complete context exceeds safety limit")
        return records, expanded
