import psycopg2
from tabulate import tabulate

from utils import get_logger, Config, validate_sql

# Initialize logger
logger = get_logger(__name__)


def get_connection():
    """Get PostgreSQL connection using DATABASE_URL from config"""
    database_url = Config.DATABASE_URL
    if not database_url:
        logger.error("DATABASE_URL is not set in environment variables")
        raise ValueError("DATABASE_URL environment variable not set")

    logger.info("Creating PostgreSQL connection using DATABASE_URL")
    return psycopg2.connect(database_url)


def get_connection_with_credentials(host, database, username, password, port=5432):
    """Get PostgreSQL connection using individual credentials"""
    logger.info(f"Creating PostgreSQL connection to {host}:{port}/{database}")
    return psycopg2.connect(
        host=host,
        database=database,
        user=username,
        password=password,
        port=port
    )


def get_connection_from_env_credentials():
    """Get PostgreSQL connection using individual environment variables from config"""
    logger.info(f"Creating PostgreSQL connection to {Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}")
    
    # Check if required credentials are set
    required_vars = ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    is_valid, missing_vars = Config.validate_required_env_vars(required_vars)
    
    if not is_valid:
        error_msg = f"Missing required PostgreSQL environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    return psycopg2.connect(
        host=Config.POSTGRES_HOST,
        database=Config.POSTGRES_DB,
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        port=Config.POSTGRES_PORT
    )


def get_schema(conn):
    """
    Get PostgreSQL database schema as CREATE TABLE statements.
    
    Args:
        conn: PostgreSQL database connection
        
    Returns:
        String containing CREATE TABLE statements for all tables
    """
    logger.info("Retrieving database schema")
    cursor = conn.cursor()

    try:
        # Get all user tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        logger.info(f"Found {len(tables)} tables in database")
        schema_statements = []

        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            logger.debug(f"Getting schema for table: {table_name}")

            # Get CREATE TABLE statement equivalent for PostgreSQL
            cursor.execute(
                """
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
            """, (table_name, ))

            create_statement_tuple = cursor.fetchone()
            if create_statement_tuple:
                schema_statements.append(create_statement_tuple[0])

        return "\n".join(schema_statements)
    except Exception as e:
        logger.error(f"Error retrieving database schema: {e}", exc_info=True)
        return f"Error retrieving database schema: {e}"
    finally:
        cursor.close()


def run_sql(conn):
    """
    Returns a function that executes SQL statements against the provided connection.
    
    Args:
        conn: PostgreSQL database connection
        
    Returns:
        Function that executes SQL statements
    """
    def inner(sql_statements: str):
        """
        Execute SQL statements against the database.
        
        Args:
            sql_statements: String containing one or more SQL statements
            
        Returns:
            Formatted results or error message
        """
        logger.info("Executing SQL statements")
        logger.debug(f"SQL statements: {sql_statements}")
        
        column_names = []
        rows = []
        parsed_sql_list = parse_sql(str(sql_statements))

        for sql_statement in parsed_sql_list:
            if not sql_statement.strip():
                continue

            # Validate SQL for security
            is_valid, reason = validate_sql(sql_statement)
            if not is_valid:
                logger.warning(f"SQL validation failed: {reason}")
                return f"SQL validation failed: {reason}"

            cursor = conn.cursor()
            logger.info(f"Running SQL: {sql_statement}")

            try:
                cursor.execute(sql_statement)

                if cursor.description:
                    column_names = [
                        description[0] for description in cursor.description
                    ]
                    rows = cursor.fetchall()
                    logger.info(f"Query returned {len(rows)} rows")
                else:
                    column_names = []
                    rows = []
                    logger.info("Query executed successfully (no rows returned)")

                conn.commit()
                logger.debug("Transaction committed")

            except Exception as e:
                conn.rollback()
                error_msg = f"SQL Error: {e}"
                logger.error(error_msg, exc_info=True)
                return error_msg
            finally:
                cursor.close()

        # Format and return results
        if column_names and rows:
            result = format_run_sql_result_as_md(
                [dict(zip(column_names, row)) for row in rows])
            logger.debug(f"Formatted result: {result}")
            return result
        elif rows:
            result = format_run_sql_result_as_md(rows)
            logger.debug(f"Formatted result: {result}")
            return result
        else:
            return "SQL statement(s) executed successfully. No data returned."

    return inner


def parse_sql(assistant_response: str):
    """
    Parse SQL statements from a string.
    
    Args:
        assistant_response: String containing one or more SQL statements
        
    Returns:
        List of SQL statements
    """
    logger.debug(f"Parsing SQL statements from: {assistant_response}")
    all_statements = []
    statements = assistant_response.split(';')
    cleaned_statements = [stmt.strip() for stmt in statements if stmt.strip()]
    all_statements.extend(cleaned_statements)
    logger.debug(f"Parsed {len(all_statements)} SQL statements")
    return all_statements


def format_run_sql_result_as_md(sql_results):
    """
    Format SQL results as markdown.
    
    Args:
        sql_results: SQL query results
        
    Returns:
        Markdown-formatted string
    """
    logger.debug("Formatting SQL results as markdown")
    try:
        if sql_results and isinstance(sql_results, list) and isinstance(sql_results[0], dict):
            headers = list(sql_results[0].keys())
            values = [list(row.values()) for row in sql_results]
            return "```\n" + tabulate(values, headers=headers, tablefmt="orgtbl") + "\n```\n"
        elif sql_results:
            return "```\n" + str(sql_results) + "\n```\n"
        else:
            return "```\n-\n``` (No results or an empty set was returned)"
    except Exception as e:
        logger.error(f"Error formatting SQL results: {e}", exc_info=True)
        return f"Error formatting results: {e}"
