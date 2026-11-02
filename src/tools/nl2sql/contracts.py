"""Bounded, strict data contracts. Source metadata is operator-approved, not caller authority."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SourceId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]
Question = Annotated[str, Field(min_length=1, max_length=4000)]
ObjectName = Annotated[
    str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$", max_length=257)
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(StrictModel):
    id: SourceId
    source_id: SourceId
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(max_length=2000)
    enabled: bool
    metadata_version: SourceId
    sql_server: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
    sql_database: str = Field(min_length=1, max_length=128)
    allowed_objects: list[ObjectName] = Field(min_length=1, max_length=256)
    authentication: Literal["managed_identity", "sql_password"]
    sql_username: str | None = Field(default=None, min_length=1, max_length=128)
    password_secret_name: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{1,127}$")

    @model_validator(mode="after")
    def consistent(self):
        if self.id != self.source_id:
            raise ValueError("Source ID must match partition key")
        if len({s.casefold() for s in self.allowed_objects}) != len(self.allowed_objects):
            raise ValueError("Duplicate approved objects")
        if self.authentication == "sql_password":
            if not self.sql_username or not self.password_secret_name:
                raise ValueError("Password sources require username and Key Vault secret name")
        elif self.sql_username or self.password_secret_name:
            raise ValueError("Managed identity sources must not declare password fields")
        if re.search(r"[\x00-\x1f]", self.sql_database + (self.sql_username or "")):
            raise ValueError("Control characters are not allowed")
        return self


class Metadata(StrictModel):
    id: SourceId
    source_id: SourceId
    metadata_version: SourceId
    kind: Literal["schema", "example"]
    content: str = Field(min_length=1, max_length=16000)
    object_name: ObjectName | None = None
    related_objects: list[ObjectName] = Field(default_factory=list, max_length=256)
    embedding: list[float] = Field(default_factory=list, max_length=65536)


class SourceSummary(StrictModel):
    source_id: SourceId
    name: str
    description: str
    metadata_version: str


class SourcesResult(StrictModel):
    schema_version: Literal[1] = 1
    sources: list[SourceSummary]


class Column(StrictModel):
    name: str
    type: Literal[
        "string",
        "integer",
        "float",
        "boolean",
        "decimal-string",
        "date-iso",
        "datetime-iso",
        "time-iso",
        "binary-base64",
        "uuid-string",
    ]


class QueryResult(StrictModel):
    schema_version: Literal[1] = 1
    source_id: SourceId
    query_id: str
    metadata_version: str
    columns: list[Column]
    rows: list[list[str | int | float | bool | None]]
    row_count: int = Field(ge=0, le=1000)


class NL2SQLError(Exception):
    """Safe actionable error code/message, never SQL or provider payloads."""
