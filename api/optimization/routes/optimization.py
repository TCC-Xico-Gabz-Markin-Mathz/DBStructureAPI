from fastapi import APIRouter, Depends

from api.common.services.rag import RAGClient
from api.dependencies import get_mysql_instance, get_rag_client
from api.optimization.helpers.formatResult import (
    format_database_create,
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
    create_statements = format_database_create(response_create)

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
    for log in select_logs:
        print(f"Query: {log[0]}")
        print(f"Execution Time (s): {log[1]}")
        print(f"Timer Start: {log[2]}")
        print(f"No Index Used: {log[3]}")
        print(f"No Good Index Used: {log[4]}")
        print(f"CPU Time: {log[5]}")
        print(f"Max Total Memory: {log[6]}")
        print(f"Rows Sent: {log[7]}")
        print(f"Rows Examined: {log[8]}")
        print("-" * 40)

    # 9. Delete test instance
    mysql_instance.delete_instance()

    return {
        "optimized_queries": formatted_queries,
        "query_result": result,
    }
