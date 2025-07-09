from fastapi import APIRouter, Depends

from api.common.services.rag import RAGClient
from api.dependencies import get_mysql_instance, get_rag_client
from api.optimization.helpers.formatResult import (
    format_sql_commands,
)
from api.optimization.models.optimize import OptimizeQueryRequest
from api.structure.helpers.mongoToString import convert_db_structure_to_string
from api.structure.services.mongodb.getTables import get_db_structure


router = APIRouter(prefix="/optimize", tags=["optimization"])


@router.post("/")
def optimize_query(
    data: OptimizeQueryRequest,
    rag_client: RAGClient = Depends(get_rag_client),
    mysql_instance=Depends(get_mysql_instance),
):
    database_structure = get_db_structure("65ff3a7b8f1e4b23d4a9c1d2")
    string_structure = convert_db_structure_to_string(database_structure)

    # 1. ask to rag to generate the optimization
    payload_generate = {"database_structure": string_structure, "query": data.query}
    response_generate = rag_client.post("/optimizer/generate", payload_generate)
    formatted_queries = response_generate["result"]

    # 2. ask to rag to generate the command
    payload_create = {"database_structure": string_structure}
    response_create = rag_client.post("/optimizer/create-database", payload_create)
    create_statements = response_create["sql"]

    # 3. create the test instance
    mysql_instance.start_instance()
    mysql_instance.execute_sql_statements(create_statements)

    # 4. ask to rag and populate the db
    payload_populate = {"creation_command": string_structure, "number_insertions": 5}
    response_populate = rag_client.post("/optimizer/populate", payload_populate)
    populate_statements = format_sql_commands(response_populate["sql"])
    mysql_instance.execute_sql_statements(populate_statements)

    # 5. execute the original query
    result = mysql_instance.execute_raw_query(data.query)
    print("Resultado da query original:", result)

    # 6. execute optimizations and optimized query
    mysql_instance.execute_sql_statements(formatted_queries)

    # 7. Compare logs
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
            ROWS_EXAMINED
        FROM 
            performance_schema.events_statements_history
        WHERE 
            SQL_TEXT IS NOT NULL
        ORDER BY 
            TIMER_START ASC;
    """)
    select_logs = [log for log in pc if log[0].strip().lower().startswith("select")]

    if len(select_logs) >= 2:
        original_log = select_logs[0]
        optimized_log = select_logs[1]

        def convert_metrics(log):
            return {
                "execution_time_seconds": float(log[1]) if log[1] is not None else None,
                "timer_start": float(log[2]) if log[2] is not None else None,
                "no_index_used": bool(log[3]) if log[3] is not None else None,
                "no_good_index_used": bool(log[4]) if log[4] is not None else None,
                "cpu_time": float(log[5]) if log[5] is not None else None,
                "max_total_memory": float(log[6]) if log[6] is not None else None,
                "rows_sent": int(log[7]) if log[7] is not None else None,
                "rows_examined": int(log[8]) if log[8] is not None else None,
            }

        original_metrics = convert_metrics(original_log)
        optimized_metrics = convert_metrics(optimized_log)
        original_query = original_log[0]
        optimized_query = optimized_log[0]
    else:
        original_metrics = optimized_metrics = {}
        original_query = optimized_query = ""

    # 8. Analyse with RAG
    response_analyze = rag_client.post(
        "/optimizer/analyze",
        {
            "original_metrics": original_metrics,
            "optimized_metrics": optimized_metrics,
            "original_query": original_query,
            "optimized_query": optimized_query,
            "applied_indexes": formatted_queries
            if isinstance(formatted_queries, list)
            else [formatted_queries],
        },
    )

    # 9. Delete test instance
    mysql_instance.delete_instance()

    return {
        "analyze": response_analyze,
        "optimized_queries": formatted_queries,
        "query_result": result,
    }
