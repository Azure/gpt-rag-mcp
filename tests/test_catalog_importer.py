from unittest.mock import AsyncMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from pydantic import ValidationError

from conftest import Container
from tools.nl2sql.catalog import Catalog, float32_vector
from tools.nl2sql.contracts import NL2SQLError
from tools.nl2sql.importer import ImportFile, import_metadata


async def test_vector_filters_and_complete_relationships(settings, source, import_json):
    container = Container(import_json["records"])
    catalog = Catalog(Container(), container, settings)
    records, objects = await catalog.retrieve(source, [0.1, 0.2, 0.3])
    assert objects == {"dbo.Products", "dbo.Categories"}
    assert {r.id for r in records} == {"products", "categories", "count-example"}
    for call in container.calls:
        params = {p["name"]: p["value"] for p in call["parameters"]}
        assert call["partition_key"] == source.source_id
        assert params["@source"] == source.source_id
        assert params["@version"] == source.metadata_version
    vector_call = container.calls[0]
    assert "TOP @k" in vector_call["query"]
    assert "VectorDistance(c.embedding, @embedding)" in vector_call["query"]
    assert {p["name"]: p["value"] for p in vector_call["parameters"]}["@k"] == 8


async def test_missing_related_schema_fails(settings, source, import_json):
    catalog = Catalog(Container(), Container([import_json["records"][0]]), settings)
    with pytest.raises(NL2SQLError, match="CONTEXT_MISSING"):
        await catalog.retrieve(source, [0.1, 0.2, 0.3])


@pytest.mark.parametrize("vector", [[1.0], [1.0, float("nan"), 0], [1e100, 0, 0]])
def test_embedding_validation(vector):
    with pytest.raises(NL2SQLError):
        float32_vector(vector, 3)


async def test_activation_after_all_writes_and_conditional_update(import_json):
    data = ImportFile.model_validate(import_json)
    sources = Container()
    sources.read_item = AsyncMock(return_value={"_etag": "previous", "metadata_version": "old"})
    metadata = Container()
    models = AsyncMock()
    models.embed.return_value = [0.1, 0.2, 0.3]

    async def activate(*args, **kwargs):
        assert metadata.create_item.await_count == 3
        assert kwargs["etag"] == "previous"
        assert kwargs["match_condition"].name == "IfNotModified"

    sources.replace_item.side_effect = activate
    version = await import_metadata(data, sources, metadata, models, 3)
    assert version.startswith("catalog-v1-")
    assert sources.replace_item.call_args.args[1]["metadata_version"] == version
    for call in metadata.create_item.call_args_list:
        assert call.args[0]["metadata_version"] == version
        assert call.args[0]["source_id"] == "synthetic"


async def test_partial_import_never_activates_or_modifies_old_version(import_json):
    data = ImportFile.model_validate(import_json)
    sources = Container()
    sources.read_item = AsyncMock(return_value={"_etag": "old", "metadata_version": "old"})
    metadata = Container()
    metadata.create_item.side_effect = [None, RuntimeError("mock write failure")]
    models = AsyncMock()
    models.embed.return_value = [0, 0, 1]
    with pytest.raises(RuntimeError):
        await import_metadata(data, sources, metadata, models, 3)
    sources.replace_item.assert_not_awaited()
    sources.create_item.assert_not_awaited()
    assert all(c.args[0]["metadata_version"] != "old" for c in metadata.create_item.call_args_list)


async def test_new_source_creation_and_conflict_fail_closed(import_json):
    sources, metadata, models = Container(), Container(), AsyncMock()
    sources.read_item = AsyncMock(side_effect=CosmosResourceNotFoundError())
    models.embed.return_value = [0, 0, 1]
    await import_metadata(ImportFile.model_validate(import_json), sources, metadata, models, 3)
    sources.create_item.assert_awaited_once()
    sources.replace_item.assert_not_awaited()
    sources.read_item = AsyncMock(return_value={"_etag": "old"})
    sources.replace_item.side_effect = RuntimeError("CAS conflict")
    with pytest.raises(RuntimeError):
        await import_metadata(ImportFile.model_validate(import_json), sources, metadata, models, 3)


def test_import_requires_all_approved_schemas(import_json):
    import_json["records"] = import_json["records"][:1]
    with pytest.raises(ValidationError):
        ImportFile.model_validate(import_json)
