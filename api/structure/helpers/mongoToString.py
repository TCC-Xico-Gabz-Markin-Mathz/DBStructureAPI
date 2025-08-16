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
            is_autoincrement = ""

            if column["is_foreign_key"]:
                is_foreign_key = f"referencia tabela {column['referenced_table']}, coluna {column['referenced_column']}"

            # Verificando auto increment
            if column.get("extra") and "auto_increment" in column["extra"].lower():
                is_autoincrement = "auto increment"

            # Construindo a string para a coluna
            column_str = f"{column_name} - {column_type} - {is_nullable}"

            if is_primary_key:
                column_str += f" - {is_primary_key}"

            if is_autoincrement:
                column_str += f" - {is_autoincrement}"

            if is_foreign_key:
                column_str += f" - {is_foreign_key}"

            columns_str.append(column_str)

        # Adicionando a tabela e suas colunas ao resultado final
        result.append(f"Tabela {table_name}\nColunas:\n" + "\n".join(columns_str))

    return "\n\n".join(result)


def schema_to_create_tables(schema_obj):
    """
    Converte um objeto de schema de banco de dados em uma lista de comandos SQL CREATE TABLE.

    Args:
        schema_obj (dict): Objeto contendo informações do schema com tabelas e colunas

    Returns:
        list: Lista de strings contendo os comandos CREATE TABLE
    """
    create_statements = []

    # Percorre cada tabela no schema
    for table in schema_obj.get("tables", []):
        table_name = table["table_name"]
        columns = table["columns"]

        # Inicia o comando CREATE TABLE
        create_sql = f"CREATE TABLE {table_name} (\n"

        # Lista para armazenar definições de colunas e constraints
        column_definitions = []
        foreign_keys = []
        composite_primary_keys = []

        # Processa cada coluna
        for column in columns:
            name = column["name"]
            col_type = column["type"]
            is_nullable = column["is_nullable"]
            default = column["default"]
            extra = column["extra"]
            is_primary_key = column["is_primary_key"]
            is_foreign_key = column["is_foreign_key"]
            referenced_table = column.get("referenced_table")
            referenced_column = column.get("referenced_column")

            # Monta a definição da coluna
            col_def = f"    {name} {col_type.upper()}"

            # Para primary key simples, adiciona inline
            if is_primary_key:
                # Verifica se é uma primary key composta (conta quantas colunas são PK)
                pk_count = sum(1 for col in columns if col["is_primary_key"])
                if pk_count == 1:
                    col_def += " PRIMARY KEY"
                else:
                    composite_primary_keys.append(name)

            # Adiciona NOT NULL se necessário
            if not is_nullable:
                col_def += " NOT NULL"

            # Adiciona AUTO_INCREMENT se presente
            if extra and "auto_increment" in extra.lower():
                col_def += " AUTO_INCREMENT"

            # Adiciona DEFAULT se presente
            if default is not None:
                if isinstance(default, str):
                    col_def += f" DEFAULT '{default}'"
                else:
                    col_def += f" DEFAULT {default}"

            column_definitions.append(col_def)

            # Coleta foreign keys
            if is_foreign_key and referenced_table and referenced_column:
                fk_constraint = f"    FOREIGN KEY ({name}) REFERENCES {referenced_table}({referenced_column})"
                foreign_keys.append(fk_constraint)

        # Adiciona PRIMARY KEY constraint apenas se for composta
        if composite_primary_keys:
            pk_constraint = f"    PRIMARY KEY ({', '.join(composite_primary_keys)})"
            column_definitions.append(pk_constraint)

        # Adiciona FOREIGN KEY constraints
        column_definitions.extend(foreign_keys)

        # Finaliza o comando CREATE TABLE
        create_sql += ",\n".join(column_definitions)
        create_sql += "\n);"

        create_statements.append(create_sql)

    return create_statements
