from typing import Dict
from fastapi import APIRouter

from api.logs.services.mongodb.getLogs import get_db_logs


router = APIRouter(prefix="/db_logs", tags=["db_logs"])


def analyze_log(log: Dict):
    alerts = []

    for index in log.get("indexes_used", []):
        if index.get("possible_keys") == "ALL" or index.get("key") is None:
            alerts.append(f"Consider creating an index for table {index.get('table')}")
        if index.get("Extra") and "Using where" in index.get("Extra"):
            alerts.append(
                f"Query on table {index.get('table')} can be optimized with an index"
            )

    for join in log.get("join_performance", []):
        if join.get("rows_examined", 0) > 10 * join.get("rows_filtered", 1):
            alerts.append("rows_examined is significantly higher than rows_filtered")

    if not log.get("conditions") and len(log.get("tables_affected", [])) > 2:
        alerts.append(
            "Query affects multiple tables but has no conditions. Consider optimizing"
        )

    return alerts


@router.post("/")
def update_db_structure():
    logs = get_db_logs()
    analysis_results = []

    for log in logs:
        log_alerts = analyze_log(log)
        if log_alerts:
            analysis_results.append(
                {
                    "timestamp": log["timestamp"],
                    "query": log["sql_text"],
                    "alerts": log_alerts,
                }
            )

    return {"analysis": analysis_results}
