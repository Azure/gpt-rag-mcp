"""Read-only reference guard plus fail-closed T-SQL AST and scoped object validation."""

import sqlglot
import sqlparse
from sqlglot import exp
from sqlglot.optimizer.scope import Scope, traverse_scope
from sqlparse import tokens as T

from .contracts import NL2SQLError

FORBIDDEN = {
    "ALTER",
    "BACKUP",
    "BEGIN",
    "COMMIT",
    "CREATE",
    "DELETE",
    "DENY",
    "DROP",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "INSERT",
    "MERGE",
    "RESTORE",
    "REVOKE",
    "ROLLBACK",
    "TRUNCATE",
    "UPDATE",
    "USE",
    "WAITFOR",
    "INTO",
    "OPENQUERY",
    "OPENROWSET",
    "OPENDATASOURCE",
    "DBCC",
    "RECONFIGURE",
    "SHUTDOWN",
}


def validate_sql(sql: str, approved_objects: set[str]) -> str:
    """Accept one SELECT/CTE over explicitly approved, two-part local objects only."""
    if not sql or len(sql) > 16000:
        raise NL2SQLError("SQL_INVALID: SQL must be nonempty and bounded")
    try:
        statements = sqlparse.parse(sql)
        if len(statements) != 1 or statements[0].get_type() != "SELECT":
            raise ValueError("Not a single SELECT")
        for token in statements[0].flatten():
            if token.is_whitespace or token.ttype in T.Comment or token.ttype in T.Literal.String:
                continue
            if token.normalized.upper() in FORBIDDEN:
                raise ValueError("Forbidden keyword")
        trees = sqlglot.parse(sql, read="tsql", error_level=sqlglot.ErrorLevel.RAISE)
        if len(trees) != 1 or not isinstance(trees[0], (exp.Select, exp.Union)):
            raise ValueError("Not a SELECT AST")
        tree = trees[0]
        denied = (
            exp.DDL,
            exp.DML,
            exp.Into,
            exp.Command,
            exp.Anonymous,
            exp.Parameter,
            exp.Var,
            exp.Lock,
            exp.Hint,
            exp.NextValueFor,
        )
        for node in tree.walk():
            if isinstance(node, denied):
                raise ValueError("Unsafe SQL node")
            if isinstance(node, exp.Dot) and isinstance(node.expression, exp.Func):
                raise ValueError("User-defined function")
        scopes = list(traverse_scope(tree))
        if not scopes:
            raise ValueError("Unresolved SQL scopes")
        for scope in scopes:
            for _, (_, reference) in scope.selected_sources.items():
                if isinstance(reference, Scope):
                    continue  # CTE/subquery resolves through its own validated scope.
                if not isinstance(reference, exp.Table):
                    raise ValueError("Unsafe source")
                if (
                    not isinstance(reference.this, exp.Identifier)
                    or not reference.db
                    or reference.catalog
                    or reference.args.get("hints")
                    or reference.args.get("version")
                    or len(reference.parts) != 2
                    or any(not isinstance(p, exp.Identifier) for p in reference.parts)
                ):
                    raise ValueError("Unsafe table reference")
                name = f"{reference.db}.{reference.name}"
                if name not in approved_objects:
                    raise ValueError("Unapproved object")
        # Reject unscoped table nodes (e.g. unsupported parser constructions).
        scoped_tables = {id(t) for s in scopes for t in s.tables}
        if any(id(t) not in scoped_tables for t in tree.find_all(exp.Table)):
            raise ValueError("Unresolved table")
    except (
        sqlglot.errors.SqlglotError,
        ValueError,
        KeyError,
        sqlparse.exceptions.SQLParseError,
    ) as exc:
        raise NL2SQLError(
            "SQL_REJECTED: require one read-only SELECT over approved local objects"
        ) from exc
    return sql
