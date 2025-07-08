from tabulate import tabulate


def get_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    schema_statements = []

    for table_name_tuple in tables:
        name = table_name_tuple[0]
        if name == 'sqlite_sequence':
            continue

        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?;",
            (name, ))
        create_statement_tuple = cursor.fetchone()
        if create_statement_tuple:
            schema_statements.append(create_statement_tuple[0])
    return "\n".join(schema_statements)


def run_sql(conn):

    def inner(sql_statements: str):
        column_names = []
        rows = []
        parsed_sql_list = parse_sql(str(sql_statements))
        for sql_statement in parsed_sql_list:
            if not sql_statement.strip():
                continue
            cursor = conn.cursor()
            print("RUNNING SQL:")
            print(sql_statement)
            cursor.execute(sql_statement)
            if cursor.description:
                column_names = [
                    description[0] for description in cursor.description
                ]
                rows = cursor.fetchall()
            else:
                column_names = []
                rows = []
            conn.commit()
            print("DONE")
        if column_names and rows:
            return format_run_sql_result_as_md(
                [dict(zip(column_names, row)) for row in rows])
        elif rows:
            return format_run_sql_result_as_md(rows)
        else:
            return "SQL statement(s) executed successfully. No data returned."

    return inner


def parse_sql(assistant_response: str):
    all_statements = []
    statements = assistant_response.split(';')
    cleaned_statements = [stmt.strip() for stmt in statements if stmt.strip()]
    all_statements.extend(cleaned_statements)
    return all_statements


def format_run_sql_result_as_md(sql_results):
    if sql_results and isinstance(sql_results, list) and isinstance(
            sql_results[0], dict):
        headers = list(sql_results[0].keys())
        values = [list(row.values()) for row in sql_results]
        return "```\n" + tabulate(values, headers=headers,
                                  tablefmt="orgtbl") + "\n```\n"
    elif sql_results:  # If it's not a list of dicts, but still some result
        return "```\n" + str(sql_results) + "\n```\n"
    else:
        return "```\n-\n``` (No results or an empty set was returned)"
