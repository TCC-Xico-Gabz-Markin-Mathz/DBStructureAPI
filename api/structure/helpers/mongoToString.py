def convert_db_structure_to_string(db_structure):
    result = []

    for table in db_structure["tables"]:
        table_name = table["table_name"]
        columns_str = []

        for column in table["columns"]:
            column_name = column["name"]
            column_type = column["type"]
            is_nullable = "não nulo" if not column["is_nullable"] else "nulo"
            is_primary_key = "chave primária" if column["is_primary_key"] else ""
            is_foreign_key = ""

            if column["is_foreign_key"]:
                is_foreign_key = f"referencia tabela {column['referenced_table']}, coluna {column['referenced_column']}"

            # Construindo a string para a coluna
            column_str = f"{column_name} - {column_type} - {is_nullable}"

            if is_primary_key:
                column_str += f" - {is_primary_key}"

            if is_foreign_key:
                column_str += f" - {is_foreign_key}"

            columns_str.append(column_str)

        # Adicionando a tabela e suas colunas ao resultado final
        result.append(f"Tabela {table_name}\nColunas:\n" + "\n".join(columns_str))

    return "\n\n".join(result)
