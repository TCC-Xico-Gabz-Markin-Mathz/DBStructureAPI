from api.logs.helpers.query_logger import log_query_execution_times

def analyse_logs():
    print("Creating logs...")
    log_query_execution_times(exclude_connection_queries=True)
    print("Logs created successfully!")
    return {"status": "ok"}
