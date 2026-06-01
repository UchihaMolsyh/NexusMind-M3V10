"""
SQL Database — SQLite database operations.
"""
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam


class SQLManager:
    """Manage SQLite databases."""

    def __init__(self):
        self.connections: Dict[str, str] = {}  # name -> path

    def get_connection(self, db_name: str) -> sqlite3.Connection:
        from config import DATA_DIR
        if db_name not in self.connections:
            db_path = DATA_DIR / f"{db_name}.db"
            self.connections[db_name] = str(db_path)
        return sqlite3.connect(self.connections[db_name])

    def query(self, db_name: str, sql: str, params: tuple = ()) -> Dict[str, Any]:
        conn = self.get_connection(db_name)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(sql, params)
            sql_upper = sql.strip().upper()

            if sql_upper.startswith("SELECT") or sql_upper.startswith("PRAGMA") or sql_upper.startswith("WITH"):
                rows = cursor.fetchall()
                columns = [d[0] for d in cursor.description] if cursor.description else []
                data = [dict(r) for r in rows]
                conn.close()
                return {
                    "columns": columns,
                    "rows": data,
                    "count": len(data),
                    "success": True,
                }
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return {
                    "affected_rows": affected,
                    "success": True,
                    "operation": sql_upper.split()[0] if sql_upper else "UNKNOWN",
                }
        except Exception as e:
            conn.close()
            return {"error": str(e), "success": False, "sql": sql}

    def list_tables(self, db_name: str) -> List[str]:
        result = self.query(db_name, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        if result.get("success"):
            return [r["name"] for r in result.get("rows", [])]
        return []

    def table_schema(self, db_name: str, table: str) -> Dict:
        result = self.query(db_name, f"PRAGMA table_info({table})")
        return result


sql_manager = SQLManager()


@registry.tool(
    name="sql_query",
    description="Execute SQL queries on SQLite databases. Supports SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, etc.",
    category="Database",
    parameters=[
        ToolParam("database", "string", "Database name (creates if not exists)"),
        ToolParam("query", "string", "SQL query to execute"),
        ToolParam("action", "string", "Action: query, tables, schema", required=False, default="query"),
        ToolParam("table", "string", "Table name (for schema action)", required=False, default=""),
    ],
)
def sql_query(database: str, query: str = "", action: str = "query", table: str = ""):
    if action == "tables":
        tables = sql_manager.list_tables(database)
        return {"database": database, "tables": tables, "count": len(tables)}
    elif action == "schema":
        if not table:
            return {"error": "Table name required for schema action"}
        return sql_manager.table_schema(database, table)
    else:
        if not query.strip():
            return {"error": "No SQL query provided"}
        return sql_manager.query(database, query)
