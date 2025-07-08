import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call

# Add the src directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tools import sql_postgres
from utils import Config
from utils.security import validate_sql

class TestSqlPostgres(unittest.TestCase):

    @patch('psycopg2.connect')
    @patch('utils.Config.DATABASE_URL', 'postgresql://user:pass@host:port/db')
    def test_get_connection_with_database_url(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = sql_postgres.get_connection()
        mock_connect.assert_called_once_with('postgresql://user:pass@host:port/db')
        self.assertEqual(conn, mock_conn)

    @patch('psycopg2.connect')
    @patch('utils.Config.DATABASE_URL', None)
    def test_get_connection_no_database_url(self, mock_connect):
        with self.assertRaisesRegex(ValueError, "DATABASE_URL environment variable not set"):
            sql_postgres.get_connection()
        mock_connect.assert_not_called()

    @patch('psycopg2.connect')
    def test_get_connection_with_credentials(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = sql_postgres.get_connection_with_credentials('host', 'db', 'user', 'pass', 5432)
        mock_connect.assert_called_once_with(
            host='host', database='db', user='user', password='pass', port=5432
        )
        self.assertEqual(conn, mock_conn)

    @patch('psycopg2.connect')
    @patch('utils.Config.POSTGRES_HOST', 'localhost')
    @patch('utils.Config.POSTGRES_DB', 'testdb')
    @patch('utils.Config.POSTGRES_USER', 'testuser')
    @patch('utils.Config.POSTGRES_PASSWORD', 'testpass')
    @patch('utils.Config.POSTGRES_PORT', 5432)
    @patch('utils.Config.validate_required_env_vars')
    def test_get_connection_from_env_credentials_success(self, mock_validate_env_vars, mock_connect):
        mock_validate_env_vars.return_value = (True, [])
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = sql_postgres.get_connection_from_env_credentials()
        mock_validate_env_vars.assert_called_once_with(
            ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
        )
        mock_connect.assert_called_once_with(
            host='localhost', database='testdb', user='testuser', password='testpass', port=5432
        )
        self.assertEqual(conn, mock_conn)

    @patch('psycopg2.connect')
    @patch('utils.Config.validate_required_env_vars')
    def test_get_connection_from_env_credentials_missing_vars(self, mock_validate_env_vars, mock_connect):
        mock_validate_env_vars.return_value = (False, ['POSTGRES_HOST'])
        
        with self.assertRaisesRegex(ValueError, "Missing required PostgreSQL environment variables: POSTGRES_HOST"):
            sql_postgres.get_connection_from_env_credentials()
        mock_validate_env_vars.assert_called_once_with(
            ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
        )
        mock_connect.assert_not_called()

    @patch('psycopg2.connect')
    def test_get_schema(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchall.side_effect = [
            [('users',), ('products',)], # First fetchall for table names
            # Second fetchall for create statements (one for each table)
        ]
        mock_cursor.fetchone.side_effect = [
            ('CREATE TABLE users (id INTEGER, name VARCHAR(255));',),
            ('CREATE TABLE products (id INTEGER, name VARCHAR(255), price NUMERIC(10,2));',)
        ]

        conn = mock_conn # Use the mocked connection directly
        schema = sql_postgres.get_schema(conn)

        expected_schema = (
            "CREATE TABLE users (id INTEGER, name VARCHAR(255));\n"
            "CREATE TABLE products (id INTEGER, name VARCHAR(255), price NUMERIC(10,2));"
        )
        self.assertEqual(schema, expected_schema)
        mock_cursor.execute.assert_has_calls([
            call("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """),
            call("""
                SELECT
                    'CREATE TABLE ' || table_name || ' (' ||
                    string_agg(
                        column_name || ' ' ||
                        CASE
                            WHEN data_type = 'character varying' THEN 'VARCHAR(' || character_maximum_length || ')'
                            WHEN data_type = 'character' THEN 'CHAR(' || character_maximum_length || ')'
                            WHEN data_type = 'numeric' THEN 'NUMERIC(' || numeric_precision || ',' || numeric_scale || ')'
                            WHEN data_type = 'integer' THEN 'INTEGER'
                            WHEN data_type = 'bigint' THEN 'BIGINT'
                            WHEN data_type = 'smallint' THEN 'SMALLINT'
                            WHEN data_type = 'boolean' THEN 'BOOLEAN'
                            WHEN data_type = 'text' THEN 'TEXT'
                            WHEN data_type = 'timestamp without time zone' THEN 'TIMESTAMP'
                            WHEN data_type = 'timestamp with time zone' THEN 'TIMESTAMPTZ'
                            WHEN data_type = 'date' THEN 'DATE'
                            WHEN data_type = 'time without time zone' THEN 'TIME'
                            WHEN data_type = 'uuid' THEN 'UUID'
                            ELSE UPPER(data_type)
                        END ||
                        CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                        ', '
                        ORDER BY ordinal_position
                    ) || ');' as create_statement
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                GROUP BY table_name;
            """, ('users', )),
            call("""
                SELECT
                    'CREATE TABLE ' || table_name || ' (' ||
                    string_agg(
                        column_name || ' ' ||
                        CASE
                            WHEN data_type = 'character varying' THEN 'VARCHAR(' || character_maximum_length || ')'
                            WHEN data_type = 'character' THEN 'CHAR(' || character_maximum_length || ')'
                            WHEN data_type = 'numeric' THEN 'NUMERIC(' || numeric_precision || ',' || numeric_scale || ')'
                            WHEN data_type = 'integer' THEN 'INTEGER'
                            WHEN data_type = 'bigint' THEN 'BIGINT'
                            WHEN data_type = 'smallint' THEN 'SMALLINT'
                            WHEN data_type = 'boolean' THEN 'BOOLEAN'
                            WHEN data_type = 'text' THEN 'TEXT'
                            WHEN data_type = 'timestamp without time zone' THEN 'TIMESTAMP'
                            WHEN data_type = 'timestamp with time zone' THEN 'TIMESTAMPTZ'
                            WHEN data_type = 'date' THEN 'DATE'
                            WHEN data_type = 'time without time zone' THEN 'TIME'
                            WHEN data_type = 'uuid' THEN 'UUID'
                            ELSE UPPER(data_type)
                        END ||
                        CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                        ', '
                        ORDER BY ordinal_position
                    ) || ');' as create_statement
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                GROUP BY table_name;
            """, ('products', ))
        ])
        mock_cursor.close.assert_called_once()

    @patch('tools.sql_postgres.validate_sql')
    def test_run_sql_valid_select(self, mock_validate_sql):
        mock_validate_sql.return_value = (True, "SQL statement appears valid")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'Alice'), (2, 'Bob')]

        run_sql_func = sql_postgres.run_sql(mock_conn)
        result = run_sql_func("SELECT id, name FROM users;")

        self.assertIn("```", result)
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)
        mock_validate_sql.assert_called_once_with("SELECT id, name FROM users") # Removed semicolon
        mock_cursor.execute.assert_called_once_with("SELECT id, name FROM users") # Removed semicolon
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()

    @patch('tools.sql_postgres.validate_sql')
    def test_run_sql_invalid_statement(self, mock_validate_sql):
        mock_validate_sql.return_value = (False, "SQL injection detected")
        mock_conn = MagicMock()
        
        run_sql_func = sql_postgres.run_sql(mock_conn)
        result = run_sql_func("DROP TABLE users;")

        self.assertEqual(result, "SQL validation failed: SQL injection detected")
        mock_validate_sql.assert_called_once_with("DROP TABLE users") # Removed semicolon
        mock_conn.cursor.assert_not_called()

    @patch('tools.sql_postgres.validate_sql')
    def test_run_sql_dml_with_select_append(self, mock_validate_sql):
        mock_validate_sql.side_effect = [(True, ""), (True, "")] # For DML and appended SELECT
        mock_conn = MagicMock()
        
        # Create and configure individual cursor mocks
        mock_cursor_insert = MagicMock()
        mock_cursor_insert.description = None # No description for DML
        mock_cursor_insert.fetchall.return_value = []

        mock_cursor_select = MagicMock()
        mock_cursor_select.description = [('id',), ('name',)]
        mock_cursor_select.fetchall.return_value = [(1, 'NewUser')]

        # Configure mock_conn.cursor to return these pre-configured mocks
        mock_conn.cursor.side_effect = [mock_cursor_insert, mock_cursor_select]

        run_sql_func = sql_postgres.run_sql(mock_conn)
        result = run_sql_func("INSERT INTO users (name) VALUES ('NewUser'); SELECT * FROM users;")

        self.assertIn("```", result)
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("NewUser", result)
        
        mock_validate_sql.assert_has_calls([
            call("INSERT INTO users (name) VALUES ('NewUser')"),
            call("SELECT * FROM users")
        ])
        self.assertEqual(mock_conn.commit.call_count, 2) # Expect commit to be called twice
        
        # Assert that cursor.close() was called on both returned mocks
        self.assertEqual(mock_conn.cursor.call_count, 2)
        for cursor_mock in mock_conn.cursor.side_effect:
            cursor_mock.close.assert_called_once()

    @patch('tools.sql_postgres.validate_sql')
    def test_run_sql_error_during_execution(self, mock_validate_sql):
        mock_validate_sql.return_value = (True, "SQL statement appears valid")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.execute.side_effect = Exception("Database error")

        run_sql_func = sql_postgres.run_sql(mock_conn)
        result = run_sql_func("SELECT * FROM non_existent_table;")

        self.assertEqual(result, "SQL Error: Database error")
        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_parse_sql(self):
        self.assertEqual(sql_postgres.parse_sql("SELECT 1; SELECT 2;"), ["SELECT 1", "SELECT 2"])
        self.assertEqual(sql_postgres.parse_sql("INSERT INTO users (name) VALUES ('test');"), ["INSERT INTO users (name) VALUES ('test')"])
        self.assertEqual(sql_postgres.parse_sql(""), [])
        self.assertEqual(sql_postgres.parse_sql("  SELECT 1  ;  "), ["SELECT 1"])

    def test_format_run_sql_result_as_md(self):
        # Test with list of dicts
        data = [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
        result = sql_postgres.format_run_sql_result_as_md(data)
        self.assertIn("```", result)
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)

        # Test with empty list
        result = sql_postgres.format_run_sql_result_as_md([])
        self.assertEqual(result, "```\n-\n``` (No results or an empty set was returned)")

        # Test with non-dict list (e.g., raw rows)
        data_raw = [(1, 'Alice'), (2, 'Bob')]
        result = sql_postgres.format_run_sql_result_as_md(data_raw)
        self.assertIn("```\n[(1, 'Alice'), (2, 'Bob')]\n```", result)

        # Test with single string (error message or simple result)
        result = sql_postgres.format_run_sql_result_as_md("SQL executed successfully.")
        self.assertEqual(result, "```\nSQL executed successfully.\n```\n") # Added newline

if __name__ == '__main__':
    unittest.main()