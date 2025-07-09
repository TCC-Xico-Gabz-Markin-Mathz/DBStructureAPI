def format_result(data):
    import re
    import ast

    content = data.get("result", "")

    # Se o conteúdo for uma string representando uma lista, tratamos diretamente
    if (
        isinstance(content, str)
        and content.strip().startswith("[")
        and content.strip().endswith("]")
    ):
        # Tratamento específico para o padrão que você compartilhou
        content_str = content.strip()

        # Divide pelo padrão específico que você mostrou
        # Exemplo: ["SQL1", "SQL2", "SQL3"]
        queries = []
        # Remove colchetes externos
        content_str = content_str.strip("[]")

        # Divide a string em pontos onde temos padrões de separação como ', ' ou '",
        pattern = r"(?:\'|\")(.*?)(?:\'|\")(?:,|\s|$)"
        matches = re.findall(pattern, content_str)

        if matches:
            for match in matches:
                query = match.strip()
                if query:
                    # Limpa padrões de escape e formatting
                    query = re.sub(r"\\\'\%\\\'", "%", query)
                    query = re.sub(r"\\\'\%(.*?)\%\\\'", r"%\1%", query)
                    query = query.replace("\\n", "\n").replace("\\t", "\t")

                    # Verifica se a query termina com ponto e vírgula
                    if not query.endswith(";"):
                        query += ";"

                    queries.append(query)

            # Se encontramos queries, retornamos diretamente
            if queries:
                return queries

    # Se não conseguimos tratar diretamente, continuamos com o algoritmo original

    # Remove blocos de markdown
    clean_content = re.sub(
        r"```(?:python)?\n?|```", "", content, flags=re.IGNORECASE
    ).strip()

    # Função para normalizar strings SQL
    def fix_sql_escaping(sql_string):
        # Remove sequências problemáticas como \'%\' e substitui por %
        sql_string = re.sub(r"\\\'\%\\\'", "%", sql_string)
        # Para padrões como \'%\'texto\'%\' -> '%texto%'
        sql_string = re.sub(r"\\\'\%(.*?)\%\\\'", r'"%\1%"', sql_string)
        # Para formato "%texto%" -> '%texto%'
        sql_string = re.sub(r'"%(.+?)%"', r"'%\1%'", sql_string)
        return sql_string

    # Trata o caso específico do exemplo que você mencionou
    if "SELECT posts.*, users.*, comments.*, likes.*" in clean_content:
        # Divide o conteúdo com base no padrão observado
        parts = clean_content.split("',")
        queries = []

        for part in parts:
            query = part.strip().strip("'").strip('"').strip()
            if query:
                # Limpa sequências problemáticas
                query = re.sub(r"\\\'\%\\\'", "%", query)
                query = re.sub(r"\\\'\%(.*?)\%\\\'", r"%\1%", query)
                # Adiciona ponto-e-vírgula se necessário
                if not query.endswith(";"):
                    query += ";"
                queries.append(query)

        # Verifica se obtivemos queries válidas
        if queries:
            # Trata especificamente o caso de "Verificando o status do container..." no final
            last_query = queries[-1]
            if "Verificando o status do container" in last_query:
                # Separa a query SQL da mensagem de status
                parts = last_query.split("Verificando")
                if parts[0].strip():
                    # Adiciona apenas a parte SQL
                    queries[-1] = parts[0].strip()
                    # Pode ser necessário adicionar novamente o ponto-e-vírgula
                    if not queries[-1].endswith(";"):
                        queries[-1] += ";"

            return queries

    # Tentativas usando ast.literal_eval
    try:
        queries_list = ast.literal_eval(clean_content)
        if isinstance(queries_list, list):
            return [fix_sql_escaping(q) for q in queries_list]
    except Exception as e:
        print(f"Normalização direta falhou: {e}")

    try:
        queries = ast.literal_eval(clean_content)
        return [q.strip() for q in queries]
    except Exception as e:
        print(f"Primeiro método falhou: {e}")

        try:
            processed_content = re.sub(r'("%)(.+?)(%")', r"'%\2%'", clean_content)
            queries = ast.literal_eval(processed_content)
            return [q.strip() for q in queries]
        except Exception as e:
            print(f"Segundo método falhou: {e}")

            try:
                fixed_content = re.sub(r"\\\'\%\\\'", "'%'", clean_content)
                fixed_content = re.sub(r"\\\'\%(.*?)\%\\\'", r"'%\1%'", fixed_content)
                queries = ast.literal_eval(fixed_content)
                return [q.strip() for q in queries]
            except Exception as e:
                print(f"Terceiro método falhou: {e}")

                # Extração manual de quotes
                try:
                    content_no_brackets = clean_content.strip("[]")
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

                    # Última tentativa com abordagem simplificada
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
                            # Dividir pelos delimitadores mais comuns
                            simple_split = content_no_brackets.split("', '")
                            return [
                                q.strip().strip("'").strip('"') for q in simple_split
                            ]
                    except Exception as e:
                        print(f"Todas as tentativas falharam: {e}")
                        return []


def format_sql_commands(sql_string):
    """
    Extrai apenas os comandos SQL de uma string que contém um array Python de comandos

    Args:
        sql_string (str): String contendo um array Python de comandos SQL

    Returns:
        list: Lista de comandos SQL prontos para execução
    """
    # Localiza o início e fim do array na string
    start_idx = sql_string.find("[")
    end_idx = sql_string.rfind("]")

    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        # Se não encontrar os delimitadores do array, retorna erro
        return ["-- Erro: Não foi possível identificar um array na string de entrada"]

    # Extrai apenas o conteúdo do array
    array_content = sql_string[start_idx : end_idx + 1]

    # Converte a string do array em uma lista real
    import ast

    try:
        sql_commands = ast.literal_eval(array_content)
    except (SyntaxError, ValueError) as e:
        return [f"-- Erro ao processar o array SQL: {str(e)}"]

    # Retorna os comandos limpos
    return [cmd.strip() for cmd in sql_commands if cmd.strip()]
