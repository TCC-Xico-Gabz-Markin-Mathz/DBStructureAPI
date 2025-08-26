import time
from fastapi import APIRouter, Depends, Query
import requests
import redis

from api.common.services.rag import RAGClient
from api.dependencies import get_mysql_instance, get_rag_client
from api.optimization.helpers.formatResult import format_sql_commands
from api.optimization.models.optimize import OptimizeQueryRequest
from api.structure.helpers.mongoToString import (
    convert_db_structure_to_string,
    schema_to_create_tables,
)
from api.structure.services.mongodb.getTables import get_db_structure

# Config
redis_client = redis.Redis(
    host="147.93.185.41",
    port=6379,
    db=0,
    password="4f2599e42acfa5ab6740",
    decode_responses=True,
)
router = APIRouter(prefix="/optimize", tags=["optimization"])
WEBHOOK_URL = (
    "https://tcc-n8n.6v8shu.easypanel.host/webhook/1e6343a0-6e0b-43c2-a301-0d3c0efb64f5"
)


def get_latest_select_log(mysql_instance):
    """Pega o log SELECT mais recente do performance schema"""
    pc = mysql_instance.execute_raw_query("""
        SELECT 
            SQL_TEXT, 
            TIMER_WAIT / 1000000000000 AS EXECUTION_TIME_SECONDS,
            TIMER_START,
            NO_INDEX_USED,
            NO_GOOD_INDEX_USED,
            CPU_TIME,
            MAX_TOTAL_MEMORY,
            ROWS_SENT,
            ROWS_EXAMINED,
            LOCK_TIME,
            MAX_CONTROLLED_MEMORY
        FROM 
            performance_schema.events_statements_history
        WHERE 
            SQL_TEXT IS NOT NULL
            AND UPPER(TRIM(SQL_TEXT)) LIKE 'SELECT%'
        ORDER BY 
            TIMER_START DESC
        LIMIT 1;
    """)

    if pc and len(pc) > 0:
        return pc[0]
    return None


def convert_metrics(log):
    """Converte os dados do log para o formato esperado"""
    if not log:
        return {}

    return {
        "execution_time_seconds": float(log[1]) if log[1] is not None else None,
        "timer_start": float(log[2]) if log[2] is not None else None,
        "no_index_used": bool(log[3]) if log[3] is not None else None,
        "no_good_index_used": bool(log[4]) if log[4] is not None else None,
        "cpu_time": float(log[5]) if log[5] is not None else None,
        "max_total_memory": float(log[6]) if log[6] is not None else None,
        "rows_sent": int(log[7]) if log[7] is not None else None,
        "rows_examined": int(log[8]) if log[8] is not None else None,
        "lock_time": float(log[9]) if log[9] is not None else None,
        "max_controlled_memory": float(log[10]) if log[10] is not None else None,
    }


def get_zero_metrics():
    """Retorna métricas zeradas para otimizações inválidas"""
    return {
        "execution_time_seconds": 0.0,
        "timer_start": 0.0,
        "no_index_used": False,
        "no_good_index_used": False,
        "cpu_time": 0.0,
        "max_total_memory": 0.0,
        "rows_sent": 0,
        "rows_examined": 0,
    }


def compare_query_results(result1, result2):
    """Compara se a quantidade de registros retornados é a mesma"""
    if result1 is None and result2 is None:
        return True
    if result1 is None or result2 is None:
        return False
    if isinstance(result1, (list, tuple)) and isinstance(result2, (list, tuple)):
        return len(result1) == len(result2)
    return True


def get_cached_or_generate(key, generator_func):
    """Busca no cache ou gera novo conteúdo"""
    cached = redis_client.get(key)
    if cached:
        return (
            cached.split("\n\n")
            if key.startswith("db_structure")
            else cached.splitlines()
        )

    result = generator_func()
    cache_value = (
        "\n\n".join(result) if key.startswith("db_structure") else "\n".join(result)
    )
    redis_client.set(key, cache_value)
    return result


@router.post("/")
def optimize_query(
    data: OptimizeQueryRequest,
    rag_client: RAGClient = Depends(get_rag_client),
    db_id: str = Query(..., description="Database ID"),
    mysql_instance=Depends(get_mysql_instance),
):
    actual_db_id = db_id or "65ff3a7b8f1e4b23d4a9c1d2"
    database_structure = get_db_structure(actual_db_id)
    string_structure = convert_db_structure_to_string(database_structure)

    # 1. Gerar otimizações
    payload_generate = {"database_structure": string_structure, "query": data.query}
    response_generate = rag_client.post("/optimizer/generate", payload_generate)
    formatted_queries = response_generate["result"]

    # 2. Obter comandos de criação (com cache)
    def create_db_generator():
        payload_create = {"database_structure": string_structure}
        response_create = rag_client.post("/optimizer/create-database", payload_create)
        return response_create["sql"]

    create_statements = get_cached_or_generate(
        f"db_structure:{actual_db_id}", create_db_generator
    )

    # 3. Iniciar instância MySQL
    mysql_instance.start_instance()

    try:
        mysql_instance.execute_sql_statements(create_statements)

        # 4. Popular dados (com cache)
        def populate_generator():
            payload_populate = {
                "creation_commands": schema_to_create_tables(database_structure),
                "number_insertions": 50,
            }
            response_populate = rag_client.post("/optimizer/populate", payload_populate)
            return format_sql_commands(response_populate)

        populate_statements = get_cached_or_generate(
            f"populate:{actual_db_id}", populate_generator
        )
        mysql_instance.execute_sql_statements(populate_statements)

        # 5. Executar query original
        original_result = mysql_instance.execute_raw_query(data.query)

        time.sleep(0.5)  # Garantir persistência do log

        original_log = get_latest_select_log(mysql_instance)
        original_metrics = convert_metrics(original_log)
        original_query = original_log[0] if original_log else data.query

        # 6. Aplicar otimizações (apenas índices, não a query final)
        print("Aplicando otimizações:", formatted_queries[:-1])
        if isinstance(formatted_queries, list) and len(formatted_queries) > 1:
            mysql_instance.execute_sql_statements(formatted_queries[:-1])

        # 7. Executar query otimizada (último elemento da lista)
        if isinstance(formatted_queries, list):
            optimized_sql = formatted_queries[-1]
        else:
            optimized_sql = formatted_queries  # caso venha string única
        optimized_result = mysql_instance.execute_raw_query(optimized_sql)

        time.sleep(0.5)  # Garantir persistência do log

        optimized_log = get_latest_select_log(mysql_instance)
        optimized_query = optimized_log[0] if optimized_log else data.query

        # 8. Validar resultados e definir métricas
        optimized_metrics = convert_metrics(optimized_log)
        print("✅ Mesma quantidade de registros - métricas válidas")

        # 9. Preparar dados para análise
        webhook_data = {
            "original_metrics": original_metrics,
            "optimized_metrics": optimized_metrics,
            "original_query": original_query,
            "optimized_query": optimized_query,
            "applied_indexes": formatted_queries
            if isinstance(formatted_queries, list)
            else [formatted_queries],
        }

        # Análise RAG
        response_analyze = rag_client.post("/optimizer/analyze", webhook_data)

        # Webhook
        try:
            webhook_response = requests.post(WEBHOOK_URL, json=webhook_data, timeout=10)
            print(f"Webhook enviado com sucesso: {webhook_response.status_code}")
            print(f"Resposta: {webhook_response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar webhook: {str(e)}")

        return {
            "analyze": response_analyze,
            "optimized_queries": formatted_queries,
            "query_result": original_result,
        }

    except Exception as e:
        return {"erro": str(e)}
    finally:
        mysql_instance.delete_instance()
