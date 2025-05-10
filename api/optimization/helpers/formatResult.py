import re
import ast


def format_result(data):
    content = data.get("result", "")

    # Remove blocos de markdown
    clean_content = re.sub(
        r"```(?:python)?\n?|```", "", content, flags=re.IGNORECASE
    ).strip()

    # Primeira etapa: Normalizar as strings SQL
    def fix_sql_escaping(sql_string):
        # Remove sequências problemáticas como \'%\' e substitui por %
        sql_string = re.sub(r"\\\'\%\\\'", "%", sql_string)

        # Para padrões como \'%\'texto\'%\' -> '%texto%'
        sql_string = re.sub(r"\\\'\%(.*?)\%\\\'", r'"%\1%"', sql_string)

        # Para formato "%texto%" -> '%texto%'
        sql_string = re.sub(r'"%(.+?)%"', r"'%\1%'", sql_string)

        return sql_string

    try:
        queries_list = ast.literal_eval(clean_content)
        if isinstance(queries_list, list):
            fixed_queries = [fix_sql_escaping(q) for q in queries_list]
            return fixed_queries
    except Exception as e:
        print(f"Normalização direta falhou: {e}")

    # Tenta primeiro com ast.literal_eval diretamente
    try:
        queries = ast.literal_eval(clean_content)
        return [q.strip() for q in queries]
    except Exception as e:
        print(f"Primeiro método falhou: {e}")

        # Segunda tentativa: preprocessa o texto para lidar com aspas não escapadas
        try:
            # Substitui aspas duplas não escapadas dentro da string por aspas simples escapadas
            processed_content = re.sub(r'("%)(.+?)(%")', r"'%\2%'", clean_content)

            # Tenta novamente com o conteúdo processado
            queries = ast.literal_eval(processed_content)
            return [q.strip() for q in queries]
        except Exception as e:
            print(f"Segundo método falhou: {e}")

            # Terceira tentativa: Remove sequências problemáticas de escape
            try:
                # Remove sequências de escape problemáticas
                fixed_content = re.sub(r"\\\'\%\\\'", "'%'", clean_content)
                fixed_content = re.sub(r"\\\'\%(.*?)\%\\\'", r"'%\1%'", fixed_content)

                queries = ast.literal_eval(fixed_content)
                return [q.strip() for q in queries]
            except Exception as e:
                print(f"Terceiro método falhou: {e}")

                # Quarta tentativa: Extração manual de quotes
                try:
                    # Remove colchetes externos
                    content_no_brackets = clean_content.strip("[]")

                    # Divide com base em padrões de separação de string SQL
                    # Procura por coisas como: ', ' ou ", " que separam itens na lista
                    queries = []
                    current = ""
                    in_quote = False
                    quote_char = None
                    i = 0

                    while i < len(content_no_brackets):
                        char = content_no_brackets[i]

                        # Detecta começo/fim de string
                        if char in ['"', "'"]:
                            if not in_quote:
                                in_quote = True
                                quote_char = char
                            elif char == quote_char and (
                                i == 0 or content_no_brackets[i - 1] != "\\"
                            ):
                                in_quote = False

                        # Detecta separador de item quando não estiver dentro de aspas
                        if not in_quote and i < len(content_no_brackets) - 2:
                            if content_no_brackets[i : i + 2] in ["', ", '", ']:
                                if current:
                                    # Processa a query antes de adicioná-la
                                    current = current.strip().strip("'").strip('"')
                                    # Limpa sequências problemáticas de escape
                                    current = re.sub(r"\\\'\%\\\'", "%", current)
                                    current = re.sub(
                                        r"\\\'\%(.*?)\%\\\'", r"%\1%", current
                                    )
                                    queries.append(current)
                                    current = ""
                                    i += 2
                                    continue

                        current += char
                        i += 1

                    # Adiciona o último item
                    if current:
                        current = current.strip().strip("'").strip('"')
                        # Corrige os padrões de escape problemáticos
                        current = re.sub(r"\\\'\%\\\'", "%", current)
                        current = re.sub(r"\\\'\%(.*?)\%\\\'", r"%\1%", current)
                        # Corrige %texto%\' → %texto%
                        current = re.sub(r"%(.*?)%\\\'", r"%\1%", current)
                        # Remove possíveis vírgulas no final
                        if current.endswith(","):
                            current = current[:-1]
                        # Garante ponto e vírgula no final para SQL válido
                        if not current.endswith(";"):
                            current += ";"
                        queries.append(current)

                    return queries
                except Exception as e:
                    print(f"Quarta tentativa falhou: {e}")

                    # Como último recurso, usar uma abordagem simplificada de parsing
                    try:
                        content_no_brackets = clean_content.strip("[]")
                        # Tenta extrair strings baseadas em padrões de SQL
                        queries = []
                        for item in re.findall(
                            r"\'[^\']*(?:\'\'[^\']*)*\'|\"[^\"]*(?:\"\"[^\"]*)*\"",
                            content_no_brackets,
                        ):
                            item = item.strip("'").strip('"')
                            # Limpa sequências problemáticas
                            item = re.sub(r"\\\'\%\\\'", "%", item)
                            item = re.sub(r"\\\'\%(.*?)\%\\\'", r"%\1%", item)
                            queries.append(item)

                        if queries:
                            return queries
                        else:
                            # Última tentativa - dividir pelos delimitadores mais comuns
                            simple_split = content_no_brackets.split("', '")
                            queries = [
                                q.strip().strip("'").strip('"') for q in simple_split
                            ]
                            return queries
                    except Exception as e:
                        print(f"Todas as tentativas falharam: {e}")
                        return []


def format_database_create(data, debug=False):
    """
    Processa e formata comandos SQL CREATE TABLE a partir de blocos SQL em markdown.

    Args:
        data (dict): Dicionário contendo a chave 'sql' com comandos SQL em formato markdown
        debug (bool, optional): Flag para habilitar mensagens de debug. Padrão False.

    Returns:
        list: Lista de strings contendo os comandos CREATE TABLE formatados
    """
    content = data.get("sql", "")
    if debug:
        print("SQL original:", content)

    # Remove blocos de markdown SQL
    clean_content = re.sub(r"```sql\n?|```", "", content, flags=re.IGNORECASE).strip()

    # Divide os comandos CREATE TABLE pelo ponto e vírgula seguido de uma nova linha
    create_statements = []

    # Primeiro tenta encontrar padrões CREATE TABLE completos
    create_pattern = re.compile(
        r"CREATE\s+TABLE\s+\w+\s*\([^;]*\);", re.IGNORECASE | re.DOTALL
    )
    matches = create_pattern.findall(clean_content)

    if matches:
        # Se encontrou padrões completos, usa-os
        for match in matches:
            # Limpa e formata cada comando CREATE TABLE
            statement = match.strip()
            # Certifica-se de que termina com ponto e vírgula
            if not statement.endswith(";"):
                statement += ";"
            create_statements.append(statement)
    else:
        # Se não encontrou padrões completos, divide pelo ponto e vírgula
        raw_statements = clean_content.split(";")
        for stmt in raw_statements:
            stmt = stmt.strip()
            if stmt and stmt.upper().startswith("CREATE TABLE"):
                # Certifica-se de que termina com ponto e vírgula
                if not stmt.endswith(";"):
                    stmt += ";"
                create_statements.append(stmt)

    # Se ainda não encontrou nada, tenta uma abordagem mais simples
    if not create_statements:
        if debug:
            print("Tentando método alternativo de extração...")

        # Divide por CREATE TABLE e reconstrói cada comando
        parts = re.split(r"(CREATE\s+TABLE\s+)", clean_content, flags=re.IGNORECASE)
        current_statement = ""
        for i, part in enumerate(parts):
            if i > 0 and part.strip().upper() == "CREATE TABLE":
                if current_statement:
                    # Finaliza o comando anterior (se existir)
                    if not current_statement.endswith(";"):
                        current_statement += ";"
                    create_statements.append(current_statement.strip())
                current_statement = part
            else:
                current_statement += part

        # Adiciona o último comando (se existir)
        if current_statement and "CREATE TABLE" in current_statement.upper():
            if not current_statement.endswith(";"):
                current_statement += ";"
            create_statements.append(current_statement.strip())

    # Remove possíveis comandos vazios ou inválidos
    create_statements = [
        stmt
        for stmt in create_statements
        if stmt.strip() and "CREATE TABLE" in stmt.upper()
    ]

    return create_statements
