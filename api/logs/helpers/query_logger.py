import time
from pymongo import MongoClient
import re
from api.common.services.mysql.connection import MySQL

# Variável global para armazenar o último ID processado (ou tempo inicial)
last_timer_start = 0


def log_query_execution_times(exclude_connection_queries=True):
    """
    Registra as queries executadas nos últimos 5 minutos e seus tempos de execução,
    incluindo informações sobre o uso de índices, salvando cada query separada no MongoDB.

    Se exclude_connection_queries for True, as queries de configuração de conexão são ignoradas.
    """
    global last_timer_start

    mysql = MySQL()
    mysql.connect(database="teste")
    cursor = mysql.connection.cursor()

    # Conectar ao MongoDB
    mongo_client = MongoClient("mongodb://root:example@localhost:27017/")
    mongo_db = mongo_client["teste"]
    collection = mongo_db["queries"]

    try:
        # Consulta para pegar as queries recentes com base no TIMER_START
        cursor.execute(f"""
        SELECT 
            SQL_TEXT, 
            TIMER_WAIT / 1000000000000 AS EXECUTION_TIME_SECONDS,
            TIMER_START,
            NO_INDEX_USED,
            NO_GOOD_INDEX_USED,
            CPU_TIME,
            MAX_TOTAL_MEMORY
        FROM 
            performance_schema.events_statements_history
        WHERE 
            SQL_TEXT IS NOT NULL
            AND TIMER_START > {last_timer_start}
        ORDER BY 
            TIMER_START DESC;
        """)

        queries = cursor.fetchall()
        if queries:
            for row in queries:
                sql_text = row[0]
                execution_time = float(row[1])

                # Ignorar queries de configuração como SET autocommit e SET NAMES
                if exclude_connection_queries and sql_text.strip().upper().startswith(
                    ("SET", "BEGIN", "COMMIT", "ROLLBACK")
                ):
                    continue

                # Separar a query para identificar seus componentes
                query_type = identify_query_type(sql_text)
                query_details = extract_query_details(sql_text)

                # Obter informações do EXPLAIN para a query
                explain_info = []
                try:
                    cursor.execute(f"EXPLAIN {sql_text}")
                    explain_info = cursor.fetchall()
                except Exception as e:
                    explain_info = [{"error": f"Erro ao executar EXPLAIN: {str(e)}"}]

                # Preparar o log detalhado da query
                query_log = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "sql_text": normalize_sql(sql_text),
                    "query_type": query_type,
                    "execution_time_seconds": execution_time,
                    "execution_time_milliseconds": execution_time * 1000,
                    "tables_affected": query_details.get("tables", []),
                    "fields_affected": query_details.get("fields", []),
                    "conditions": query_details.get("conditions", []),
                    "indexes_used": extract_explain_info(explain_info),
                    "join_types": query_details.get("join_types", []),
                    "join_performance": extract_join_performance(explain_info),
                    "query_details": query_details,
                    "no_index_used": row[3],
                    "no_good_index_used": row[4],
                    "cpu_time": row[5],
                    "max_total_memory": row[6],
                }

                # Salvar a query detalhada no MongoDB
                collection.insert_one(query_log)

            # Atualizar o último TIMER_START processado
            last_timer_start = queries[0][2]

    except Exception as e:
        print(f"Erro ao consultar performance_schema: {str(e)}")

    finally:
        cursor.close()
        mysql.close_connection()
        mongo_client.close()


def normalize_sql(query: str) -> str:
    # Patterns para normalizar:
    patterns = [
        r"'(?:''|[^'])*'",             # strings entre aspas simples (com escape '')
        r'"(?:\\"|[^"])*"',            # strings entre aspas duplas (com escape \")
        r'\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)?\b',  # datas ISO 8601
        r'\b\d+\.\d+\b',               # números float
        r'\b\d+\b',                   # números inteiros
        r'\bTRUE\b|\bFALSE\b',         # booleanos
    ]
    
    for pattern in patterns:
        query = re.sub(pattern, '?', query, flags=re.IGNORECASE)
    
    return query


def identify_query_type(sql_text):
    """Identifica o tipo de query (SELECT, INSERT, UPDATE, DELETE)."""
    sql_text = sql_text.strip().upper()
    if sql_text.startswith("SELECT"):
        return "SELECT"
    elif sql_text.startswith("INSERT"):
        return "INSERT"
    elif sql_text.startswith("UPDATE"):
        return "UPDATE"
    elif sql_text.startswith("DELETE"):
        return "DELETE"
    elif sql_text.startswith("DROP"):
        return "DROP"
    else:
        return "UNKNOWN"


def extract_query_details(sql_text):
    """Extrai detalhes da query como tabelas, campos e condições."""
    details = {"tables": [], "fields": [], "conditions": [], "join_types": []}

    # Extrair tabelas (presumindo que estejam no formato `FROM table_name` ou `JOIN table_name`)
    tables = re.findall(r"(FROM|JOIN)\s+([^\s]+)", sql_text, re.IGNORECASE)
    details["tables"] = [table[1] for table in tables]

    # Extrair campos (presumindo que estejam no formato `SELECT field1, field2, ...`)
    fields = re.findall(r"SELECT\s+([^\s]+)", sql_text, re.IGNORECASE)
    details["fields"] = fields

    # Extrair condições (presumindo que estejam no formato `WHERE condition`)
    conditions = re.findall(r"WHERE\s+(.+)", sql_text, re.IGNORECASE)
    details["conditions"] = conditions

    # Extrair tipos de JOIN (INNER, LEFT, RIGHT, etc.)
    join_types = re.findall(
        r"(INNER|LEFT|RIGHT|OUTER|CROSS|)\s*JOIN", sql_text, re.IGNORECASE
    )
    details["join_types"] = [
        join_type if join_type else "INNER" for join_type in join_types
    ]

    return details


def extract_explain_info(explain_info):
    """Extrai e organiza as informações do EXPLAIN para análise mais detalhada."""
    explain_data = []

    for row in explain_info:
        if isinstance(row, tuple) and len(row) >= 12:
            # Organizando as colunas de EXPLAIN
            explain_details = {
                "id": row[0],
                "select_type": row[1],  # Tipo de seleção (SIMPLE, PRIMARY, etc.)
                "table": row[2],  # Nome da tabela
                "type": row[3],  # Tipo de junção (ALL, PRIMARY, etc.)
                "possible_keys": row[4],  # Chaves possíveis (índices sugeridos)
                "key": row[5],  # Chave/índice realmente utilizado
                "key_len": row[6],  # Tamanho da chave usada
                "ref": row[7],  # Referência para a chave (se houver)
                "rows": row[8],  # Número estimado de linhas processadas
                "filtered": row[9],  # Percentual de linhas filtradas
                "Extra": row[
                    11
                ],  # Informações extras (ex: "Using where", "Using index")
            }
            explain_data.append(explain_details)
        elif isinstance(row, dict):
            error_message = row.get("error")
            if error_message:
                explain_data.append(
                    {"error": f"Erro ao executar EXPLAIN: {error_message}"}
                )
    return explain_data


def extract_join_performance(explain_info):
    """Extrai e calcula a performance do JOIN com base em EXPLAIN."""
    join_performance = []

    for row in explain_info:
        if isinstance(row, dict):
            continue

        if len(row) >= 10:
            try:
                rows_examined = int(row[8]) if row[8] is not None else 0
                rows_filtered = int(row[9]) if row[9] is not None else 0
            except ValueError:
                rows_examined = 0
                rows_filtered = 0

            performance = {
                "rows_examined": rows_examined,
                "rows_filtered": rows_filtered,
            }
            join_performance.append(performance)

    return join_performance
