import os

def save_sql_query_to_file(query_name: str, sql_statement: str):
    # Define the file path
    file_path = f"{query_name}.sql"
    
    # Write the SQL statement to the file
    with open(file_path, 'w') as file:
        file.write(sql_statement)
    
    return f"SQL query saved as {file_path}."