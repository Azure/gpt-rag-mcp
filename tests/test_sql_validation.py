import pytest

from tools.nl2sql.contracts import NL2SQLError
from tools.nl2sql.sql_validation import validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT TOP (1000) * FROM dbo.Products",
        "SELECT p.Name FROM [dbo].[Products] p JOIN dbo.Categories c ON c.CategoryId=p.CategoryId",
        "WITH x AS (SELECT * FROM dbo.Products) SELECT * FROM x",
        "SELECT COUNT(*) FROM dbo.Products WHERE Name = 'DROP TABLE x; OPENQUERY'",
        "SELECT * FROM dbo.Products WHERE CategoryId IN (SELECT CategoryId FROM dbo.Categories)",
        "SELECT 1 AS constant",
    ],
)
def test_read_only(sql):
    assert validate_sql(sql, {"dbo.Products", "dbo.Categories"}) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "SELECT 1; SELECT 2",
        "DROP TABLE dbo.Products",
        "DELETE FROM dbo.Products",
        "WITH x AS (SELECT * FROM dbo.Products) DELETE FROM x",
        "SELECT * INTO dbo.NewTable FROM dbo.Products",
        "SELECT * FROM OPENQUERY(remote, 'SELECT 1')",
        "SELECT * FROM OPENROWSET('SQLNCLI', 'secret', 'SELECT 1')",
        "SELECT * FROM OPENDATASOURCE('SQLNCLI', 'secret').db.dbo.Products",
        "SELECT * FROM server.db.dbo.Products",
        "SELECT * FROM db.dbo.Products",
        "SELECT * FROM Products",
        "SELECT * FROM dbo.Unapproved",
        "SELECT * FROM #temp",
        "SELECT * FROM @table",
        "SELECT * FROM dbo.SomeFunction()",
        "SELECT dbo.SomeFunction(1)",
        "SELECT NEXT VALUE FOR dbo.Sequence",
        "SELECT * FROM dbo.Products WITH (NOLOCK)",
        "SELECT * FROM dbo.Products FOR SYSTEM_TIME ALL",
        "SELECT * FROM dbo.Products; WAITFOR DELAY '00:00:01'",
        "SELECT * FROM dbo.Products WHERE EXISTS (SELECT 1 FROM dbo.Secret)",
        "WITH x AS (SELECT * FROM dbo.Secret) SELECT * FROM x",
        "SELECT * FROM [dbo.Products]",
        "SELECT * FROM dbo.Products p CROSS APPLY dbo.Unsafe(p.Name)",
        "SELECT * FROM dbo.Products OPTION (MAXDOP 0)",
        "EXEC('SELECT 1')",
        "SELECT * FROM dbo.products",
    ],
)
def test_reject_unsafe_sql(sql):
    with pytest.raises(NL2SQLError, match="SQL_(REJECTED|INVALID)"):
        validate_sql(sql, {"dbo.Products", "dbo.Categories"})
