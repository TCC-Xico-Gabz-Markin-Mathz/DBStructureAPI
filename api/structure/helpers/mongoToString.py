import json


def convert_db_structure_to_string(db_structure):
    """
    Converte a estrutura do banco de dados para um dicionário Python
    pronto para ser serializado em JSON.
    """
    output_tables = []

    # Lista de chaves primárias para aprimorar a lógica de ordenação
    primary_keys = {}
    for table in db_structure["tables"]:
        table_name = table["table_name"]
        primary_keys[table_name] = [
            col["name"] for col in table["columns"] if col.get("is_primary_key")
        ]

    for table in db_structure["tables"]:
        table_name = table["table_name"]
        columns_data = []

        for column in table["columns"]:
            column_info = {
                "name": column["name"],
                "type": column["type"],
                "nullable": column["is_nullable"],
            }

            if column.get("is_primary_key"):
                # Se for uma chave primária composta, o LLM vai precisar de todas as colunas
                # para gerar a PRIMARY KEY (col1, col2)
                if len(primary_keys[table_name]) > 1:
                    column_info["is_composite_primary_key"] = True
                else:
                    column_info["is_primary_key"] = True

            if "auto_increment" in column.get("extra", "").lower():
                column_info["auto_increment"] = True

            if column.get("is_foreign_key"):
                column_info["foreign_key"] = {
                    "referenced_table": column["referenced_table"],
                    "referenced_column": column["referenced_column"],
                }

            columns_data.append(column_info)

        output_tables.append({"table_name": table_name, "columns": columns_data})

    return json.dumps({"tables": output_tables}, indent=2)


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
