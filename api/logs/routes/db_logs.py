from fastapi import APIRouter
from api.logs.helpers.query_logger import log_query_execution_times


router = APIRouter(prefix="/db_logs", tags=["db_logs"])


@router.get("/")
def analyse_logs():
    log_query_execution_times(exclude_connection_queries=True)
    return {"status": "ok"}

# @router.get("/")
# def analyse_logs():
#     logs = get_db_logs()
#     analysis_results = []
#
#     for log in logs:
#         log_alerts = analyze_log(log)
#         if log_alerts:
#             analysis_results.append(
#                 {
#                     "timestamp": log["timestamp"],
#                     "query": log["sql_text"],
#                     "alerts": log_alerts,
#                 }
#             )
#
#     return {"analysis": analysis_results}
