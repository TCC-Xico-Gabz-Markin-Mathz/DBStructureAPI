from typing import Dict, List


def analyze_log(log: Dict) -> List[str]:
    alerts = []

    indexes_used = log.get("indexes_used", [])
    for index in indexes_used:
        table = index.get("table", "unknown")
        key = index.get("key")
        possible_keys = index.get("possible_keys")
        extra = index.get("Extra", "")

        if possible_keys == "ALL" or key is None:
            alerts.append(
                f"🔍 Tabela '{table}' está fazendo full scan. Considere criar um índice."
            )

        if "Using where" in extra and not key:
            alerts.append(
                f"📌 Consulta na tabela '{table}' usa cláusula WHERE sem índice. Pode ser otimizada."
            )

    join_perf = log.get("join_performance", [])
    for join in join_perf:
        rows_examined = join.get("rows_examined", 0)
        rows_filtered = join.get("rows_filtered", 1)
        if rows_examined > 10 * rows_filtered:
            alerts.append(
                f"⚠️ Join examinou {rows_examined} linhas, mas filtrou apenas {rows_filtered}. Verifique condições de join ou índices."
            )

    tables_affected = log.get("tables_affected", [])
    conditions = log.get("conditions")

    if not conditions and len(tables_affected) > 2:
        alerts.append(
            f"📉 Consulta afeta {len(tables_affected)} tabelas sem condições. Pode causar desempenho ruim."
        )

    return alerts