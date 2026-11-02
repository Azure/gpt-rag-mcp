import asyncio
import datetime as dt
import decimal
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from tools.nl2sql.contracts import NL2SQLError
from tools.nl2sql.sql import SQLExecutor, odbc_value, serialize


class Cursor:
    def __init__(self, types, rows):
        self.description = [(f"c{i}", t) for i, t in enumerate(types)]
        self.rows = iter(rows)
        self.threads = []
        self.closed = False
        self.started = threading.Event()
        self.finish = threading.Event()
        self.block = False

    def execute(self, sql):
        self.threads.append(threading.get_ident())
        self.started.set()
        if self.block:
            assert self.finish.wait(5), "test failed to unblock worker"

    def fetchone(self):
        self.threads.append(threading.get_ident())
        return next(self.rows, None)

    def close(self):
        self.threads.append(threading.get_ident())
        self.closed = True


class Connection:
    def __init__(self, cursor):
        self.handle = cursor
        self.closed = False
        self.threads = []

    def cursor(self):
        self.threads.append(threading.get_ident())
        return self.handle

    def close(self):
        self.threads.append(threading.get_ident())
        self.closed = True


def test_exact_serialization(source):
    result = serialize(
        Cursor(
            [decimal.Decimal, dt.date, dt.datetime, dt.time, bytes, str, int, float, bool],
            [
                [
                    decimal.Decimal("1234567890.12345678901234567890"),
                    dt.date(2026, 1, 2),
                    dt.datetime(2026, 1, 2, 3, 4, 5),
                    dt.time(3, 4),
                    b"\x00\xff",
                    None,
                    2,
                    1.5,
                    True,
                ]
            ],
        ),
        source,
        "id",
    )
    assert result.rows == [
        [
            "1234567890.12345678901234567890",
            "2026-01-02",
            "2026-01-02T03:04:05",
            "03:04:00",
            "AP8=",
            None,
            2,
            1.5,
            True,
        ]
    ]
    assert [c.type for c in result.columns][:5] == [
        "decimal-string",
        "date-iso",
        "datetime-iso",
        "time-iso",
        "binary-base64",
    ]
    assert "sql" not in result.model_dump()


@pytest.mark.parametrize(
    "types,rows,code",
    [
        ([str], [["x"]] * 1001, "RESULT_ROWS"),
        ([str], [["x" * 262144]], "RESULT_BYTES"),
        ([object], [[object()]], "RESULT_TYPE"),
        ([float], [[float("nan")]], "RESULT_TYPE"),
        ([str], [[object()]], "RESULT_TYPE"),
        ([str], [[1, 2]], "RESULT_TYPE"),
    ],
)
def test_result_limits(types, rows, code, source):
    with pytest.raises(NL2SQLError, match=code):
        serialize(Cursor(types, rows), source, "id")


def test_exact_row_boundary(source):
    assert serialize(Cursor([int], [[1]] * 1000), source, "id").row_count == 1000


async def test_one_worker_owns_all_handles_and_tls(source):
    cursor = Cursor([int], [[1]])
    connection = Connection(cursor)
    threads = []
    credential = Mock()
    credential.get_token.return_value = SimpleNamespace(token="synthetic-token")

    def connect(connection_string, **kwargs):
        threads.append(threading.get_ident())
        assert "Encrypt=yes;TrustServerCertificate=no;" in connection_string
        assert "ODBC Driver 18 for SQL Server" in connection_string
        assert kwargs["attrs_before"][1256][4:] == "synthetic-token".encode("utf-16-le")
        assert kwargs["autocommit"] is True
        return connection

    executor = SQLExecutor(credential, connect=connect)
    try:
        result = await executor.execute(source, "SELECT 1", "id")
        assert result.row_count == 1
        assert cursor.closed and connection.closed
        assert len(set(threads + cursor.threads + connection.threads)) == 1
        assert threads[0] != threading.get_ident()
    finally:
        await executor.close()


async def test_timeout_does_not_close_in_use_handles(source, monkeypatch):
    import tools.nl2sql.sql as module

    monkeypatch.setattr(module, "SQL_TIMEOUT", 0.05)
    cursor = Cursor([int], [[1]])
    cursor.block = True
    connection = Connection(cursor)
    credential = Mock()
    credential.get_token.return_value = SimpleNamespace(token="token")
    executor = SQLExecutor(credential, connect=lambda *a, **kw: connection)
    try:
        with pytest.raises(NL2SQLError, match="SQL_TIMEOUT"):
            await executor.execute(source, "SELECT 1", "id")
        assert cursor.started.is_set()
        assert not cursor.closed and not connection.closed
        assert executor.slots._value == 3
        cursor.finish.set()
        await executor.close()
        await asyncio.sleep(0)
        assert cursor.closed and connection.closed
        assert executor.slots._value == 4
    finally:
        cursor.finish.set()
        await executor.close()


async def test_execution_failure_cleans_both_handles(source):
    cursor = Cursor([int], [])
    cursor.execute = Mock(side_effect=RuntimeError("private SQL text"))
    connection = Connection(cursor)
    credential = Mock()
    credential.get_token.return_value = SimpleNamespace(token="token")
    executor = SQLExecutor(credential, connect=lambda *a, **kw: connection)
    try:
        with pytest.raises(RuntimeError):
            await executor.execute(source, "SELECT 1", "id")
        assert cursor.closed and connection.closed
    finally:
        await executor.close()


async def test_password_secret_allowlist_and_escaping(source):
    source.authentication = "sql_password"
    source.sql_username = "read-only"
    source.password_secret_name = "approved-password"
    vault = AsyncMock()
    vault.get_secret.return_value = SimpleNamespace(value="a};UID=other;{")
    connect = Mock(return_value=Connection(Cursor([int], [[1]])))
    executor = SQLExecutor(Mock(), vault, connect)
    try:
        with pytest.raises(NL2SQLError, match="not approved"):
            await executor.execute(source, "SELECT 1", "id")
        vault.get_secret.assert_not_awaited()
        executor.secret_names = {"approved-password"}
        await executor.execute(source, "SELECT 1", "id")
        assert "PWD={a}};UID=other;{};" in connect.call_args.args[0]
        assert "attrs_before" not in connect.call_args.kwargs
    finally:
        await executor.close()
    assert odbc_value("x};Encrypt=no;") == "{x}};Encrypt=no;}"
