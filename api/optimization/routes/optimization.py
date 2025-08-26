import time
from fastapi import APIRouter, Depends, Query
import requests

from api.dependencies import get_mysql_instance, get_rag_client
from api.optimization.helpers.formatResult import format_sql_commands
from api.optimization.models.optimize import ModelName, OptimizeQueryRequest
from api.optimization.service.mySqlInstance import MySQLTestInstance
from api.structure.helpers.mongoToString import (
    convert_db_structure_to_string,
    schema_to_create_tables,
)
from api.structure.services.mongodb.getTables import get_db_structure
import redis


# Connect to Redis (adjust host/port/db as needed)
redis_client = redis.Redis(
    host="147.93.185.41",
    port=6379,
    db=0,
    password="4f2599e42acfa5ab6740",
    decode_responses=True,
)
router = APIRouter(prefix="/optimize", tags=["optimization"])

# Options are in the ModelName enum
MODEL_NAME = ModelName.GROQ.value


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
        "lock_time": int(log[9]) if log[9] is not None else None,
        "max_controlled_memory": float(log[10]) if log[10] is not None else None,
    }


@router.post("/")
def optimize_query(
    data: OptimizeQueryRequest,
    db_id: str = Query(..., description="Database ID"),
    mysql_instance: MySQLTestInstance = Depends(get_mysql_instance),
    model_name: ModelName = Query(MODEL_NAME, description="LLM Model Name"),
    rag_client=Depends(get_rag_client),
):
    # Use db_id or fallback to default if None/empty to get structure
    actual_db_id = db_id or "65ff3a7b8f1e4b23d4a9c1d2"
    database_structure = get_db_structure(actual_db_id)
    string_structure = convert_db_structure_to_string(database_structure)

    # 1. ask to rag to generate the optimization
    payload_generate = {"database_structure": string_structure, "query": data.query}
    response_generate = rag_client.post(
        "/optimizer/generate" + "?model_name=" + model_name, payload_generate
    )
    formatted_queries = response_generate["result"]

    # 2. ask to rag to generate the command

    # Use Redis for db_structure_file
    db_structure_key = f"db_structure:{actual_db_id}"
    create_statements_str = redis_client.get(db_structure_key)
    if create_statements_str:
        create_statements = [
            stmt.strip() for stmt in create_statements_str.split("\n\n") if stmt.strip()
        ]
    else:
        payload_create = {"database_structure": string_structure}
        response_create = rag_client.post(
            "/optimizer/create-database" + "?model_name=" + model_name, payload_create
        )
        create_statements = response_create["sql"]
        redis_client.set(db_structure_key, create_statements_str)
        create_statements = response_create["sql"]

    # 3. create the test instance
    mysql_instance.start_instance()

    try:
        mysql_instance.execute_sql_statements(create_statements)
        time.sleep(10)

        # 4. ask to rag and populate the db
        payload_populate = {
            "creation_commands": schema_to_create_tables(database_structure),
            "number_insertions": 1000,
        }
        populate_key = f"populate:{actual_db_id}"
        populate_statements_str = redis_client.get(populate_key)
        if populate_statements_str:
            populate_statements = populate_statements_str.splitlines()
        else:
            response_populate = rag_client.post("/optimizer/populate", payload_populate)
            populate_statements = format_sql_commands(response_populate)
            redis_client.set(populate_key, "\n".join(populate_statements))
        mysql_instance.execute_sql_statements(populate_statements)

        # 5. execute the original query and capture its log
        result = mysql_instance.execute_raw_query(data.query)
        print("Resultado da query original:", result)

        # Pequena pausa para garantir que o log seja persistido
        time.sleep(0.5)

        # Captura o log da query original
        original_log = get_latest_select_log(mysql_instance)
        original_metrics = convert_metrics(original_log)
        original_query = original_log[0] if original_log else data.query

        # 6. execute optimizations (índices)
        mysql_instance.execute_sql_statements(formatted_queries)

        # Pequena pausa para garantir que o log seja persistido
        time.sleep(0.5)

        # Captura o log da query otimizada
        optimized_log = get_latest_select_log(mysql_instance)
        optimized_metrics = convert_metrics(optimized_log)
        optimized_query = optimized_log[0] if optimized_log else data.query

        # 8. Analyse with RAG
        webhook_data = {
            "original_metrics": original_metrics,
            "optimized_metrics": optimized_metrics,
            "original_query": original_query,
            "optimized_query": optimized_query,
            "applied_indexes": formatted_queries
            if isinstance(formatted_queries, list)
            else [formatted_queries],
        }

        response_analyze = rag_client.post(
            "/optimizer/analyze" + "?model_name=" + model_name, webhook_data
        )

        try:
            webhook_response = requests.post(
                "https://tcc-n8n.6v8shu.easypanel.host/webhook/1e6343a0-6e0b-43c2-a301-0d3c0efb64f5",
                json=webhook_data,
                timeout=10,
            )
            print(f"Webhook enviado com sucesso: {webhook_response.status_code}")
            print(f"Resposta: {webhook_response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar webhook: {str(e)}")

        response_analyze = rag_client.post("/optimizer/analyze", webhook_data)

        return {
            "analyze": response_analyze,
            "optimized_queries": formatted_queries,
            "query_result": result,
        }

    except Exception as e:
        return {"erro": str(e)}

    finally:
        mysql_instance.delete_instance()
