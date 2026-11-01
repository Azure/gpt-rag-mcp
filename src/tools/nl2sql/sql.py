"""ODBC execution: connection/cursor/execute/fetch/cleanup owned by one bounded worker."""

import asyncio
import base64
import datetime as dt
import decimal
import math
import struct
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pyodbc

from .contracts import Column, NL2SQLError, QueryResult

MAX_ROWS = 1000
MAX_BYTES = 262144
SQL_TIMEOUT = 30
TYPES = {
    str: "string",
    int: "integer",
    float: "float",
    bool: "boolean",
    decimal.Decimal: "decimal-string",
    dt.date: "date-iso",
    dt.datetime: "datetime-iso",
    dt.time: "time-iso",
    bytes: "binary-base64",
    bytearray: "binary-base64",
    uuid.UUID: "uuid-string",
}


def encode(value):
    if value is None:
        return None
    if isinstance(value, decimal.Decimal):
        if not value.is_finite():
            raise NL2SQLError("RESULT_TYPE: nonfinite decimal")
        return str(value)
    if isinstance(value, (dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, uuid.UUID):
        return str(value)
    if type(value) not in (str, int, float, bool):
        raise NL2SQLError("RESULT_TYPE: unsupported SQL value type")
    if isinstance(value, float) and not math.isfinite(value):
        raise NL2SQLError("RESULT_TYPE: nonfinite float")
    return value


def check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise NL2SQLError("SQL_TIMEOUT: execution exceeded 30 seconds")


def serialize(cursor, source, query_id, deadline=None):
    if not cursor.description:
        raise NL2SQLError("RESULT_TYPE: query did not produce columns")
    columns = []
    for desc in cursor.description:
        logical_type = TYPES.get(desc[1])
        if not logical_type:
            raise NL2SQLError("RESULT_TYPE: unsupported SQL column type")
        columns.append(Column(name=desc[0], type=logical_type))
    result = QueryResult(
        source_id=source.source_id,
        query_id=query_id,
        metadata_version=source.metadata_version,
        columns=columns,
        rows=[],
        row_count=0,
    )
    if len(result.model_dump_json().encode("utf-8")) > MAX_BYTES:
        raise NL2SQLError("RESULT_BYTES: columns exceed 256 KiB")
    # Fetch one row at a time so large result sets are never accumulated before enforcement.
    while True:
        check_deadline(deadline)
        row = cursor.fetchone()
        check_deadline(deadline)
        if row is None:
            break
        if result.row_count == MAX_ROWS:
            raise NL2SQLError("RESULT_ROWS: result exceeds 1000 rows")
        if len(row) != len(columns):
            raise NL2SQLError("RESULT_TYPE: column/row arity mismatch")
        result.rows.append([encode(v) for v in row])
        result.row_count += 1
        if len(result.model_dump_json().encode("utf-8")) > MAX_BYTES:
            raise NL2SQLError("RESULT_BYTES: result exceeds 256 KiB")
    return result


def odbc_value(value):
    """Brace-escape operator-controlled ODBC values to prevent connection-string injection."""
    return "{" + value.replace("}", "}}") + "}"


class SQLExecutor:
    def __init__(self, credential, vault=None, connect=pyodbc.connect, secret_names=()):
        self.credential = credential
        self.vault = vault
        self.connect = connect
        self.secret_names = frozenset(secret_names)
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nl2sql")
        self.slots = asyncio.Semaphore(4)

    async def execute(self, source, sql, query_id):
        password = None
        if source.authentication == "sql_password":
            if source.password_secret_name not in self.secret_names:
                raise NL2SQLError("SQL_AUTH_CONFIG: SQL secret reference is not approved")
            if self.vault is None:
                raise NL2SQLError("SQL_AUTH_CONFIG: SQL password source requires Key Vault")
            password = (await self.vault.get_secret(source.password_secret_name)).value
            if not password:
                raise NL2SQLError("SQL_AUTH_CONFIG: Key Vault secret is empty")
        await self.slots.acquire()
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self.pool, self._worker, source, sql, query_id, password)

        def completed(f):
            self.slots.release()
            # Consume late exceptions without logging sensitive ODBC error payloads.
            if not f.cancelled():
                f.exception()

        future.add_done_callback(completed)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=SQL_TIMEOUT)
        except TimeoutError:
            # The worker retains ownership until driver timeout and its finally cleanup.
            raise NL2SQLError("SQL_TIMEOUT: execution exceeded 30 seconds") from None

    def _worker(self, source, sql, query_id, password):
        connection = cursor = None
        deadline = time.monotonic() + SQL_TIMEOUT
        try:
            connection_string = (
                "Driver={ODBC Driver 18 for SQL Server};"
                f"Server={odbc_value(source.sql_server + ',1433')};"
                f"Database={odbc_value(source.sql_database)};"
                "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            )
            kwargs = {"autocommit": True}
            if source.authentication == "managed_identity":
                if not source.sql_server.casefold().endswith(".database.windows.net"):
                    raise NL2SQLError(
                        "SQL_AUTH_CONFIG: managed identity requires Azure SQL hostname"
                    )
                token = self.credential.get_token("https://database.windows.net/.default")
                raw = token.token.encode("utf-16-le")
                kwargs["attrs_before"] = {1256: struct.pack(f"<I{len(raw)}s", len(raw), raw)}
            else:
                connection_string += (
                    f"UID={odbc_value(source.sql_username)};PWD={odbc_value(password)};"
                )
            check_deadline(deadline)
            kwargs["timeout"] = max(1, int(deadline - time.monotonic()))
            connection = self.connect(connection_string, **kwargs)
            check_deadline(deadline)
            connection.timeout = max(1, int(deadline - time.monotonic()))
            cursor = connection.cursor()
            cursor.execute(sql)
            return serialize(cursor, source, query_id, deadline)
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                if connection is not None:
                    connection.close()

    async def close(self):
        # Shutdown waits for workers, without closing in-use ODBC handles from another thread.
        await asyncio.to_thread(self.pool.shutdown, wait=True)
