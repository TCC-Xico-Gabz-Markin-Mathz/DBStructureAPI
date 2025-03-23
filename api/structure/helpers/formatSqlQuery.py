import re


def format_sql_query(query: str) -> str:
    query = re.sub(r"^[\s\S]*?SELECT", "SELECT", query)

    query = query.replace("\n", " ")
    query = query.replace("```;", "")

    query = re.sub(r"\s+", " ", query).strip()

    query = query + ";\n"

    return query
