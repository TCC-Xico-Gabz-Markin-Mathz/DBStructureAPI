
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
