import time
import requests
from api.common.services.rag import RAGClient
from api.common.services.cache import CacheService
from api.optimization.helpers.query_helpers import get_latest_select_log, convert_metrics
from api.structure.helpers.mongoToString import (
    convert_db_structure_to_string,
    schema_to_create_tables,
)
from api.structure.services.mongodb.getTables import get_db_structure
from api.optimization.helpers.formatResult import format_sql_commands

class OptimizationService:
    def __init__(self, rag_client: RAGClient, cache_service: CacheService, webhook_url: str, default_db_id: str):
        self.rag_client = rag_client
        self.cache_service = cache_service
        self.webhook_url = webhook_url
        self.default_db_id = default_db_id

    def _get_database_structure_string(self, db_id: str) -> str:
        """Busca a estrutura do banco de dados e converte para string."""
        database_structure = get_db_structure(db_id)
        return convert_db_structure_to_string(database_structure)

    def _generate_optimizations(self, string_structure: str, query: str, model_name: str) -> list:
        """Gera otimizações para a query com base na estrutura do banco."""
        payload = {"database_structure": string_structure, "query": query}
        response = self.rag_client.post("/optimizer/generate", payload, model_name=model_name)
        return response["result"]

    def _get_create_statements(self, db_id: str, string_structure: str, model_name: str, use_cache: bool) -> list:
        """Obtém os comandos de criação do banco de dados (com cache)."""
        def generator():
            payload = {"database_structure": string_structure}
            response = self.rag_client.post("/optimizer/create-database", payload, model_name=model_name)
            return response["sql"]
        return self.cache_service.get_cached_or_generate(f"db_structure:{db_id}", generator, use_cache)

    def _get_populate_statements(self, db_id: str, database_structure: dict, model_name: str, use_cache: bool) -> list:
        """Obtém os comandos de população do banco de dados (com cache)."""
        def generator():
            payload = {
                "creation_commands": schema_to_create_tables(database_structure),
                "number_insertions": 50,
            }
            response = self.rag_client.post("/optimizer/populate", payload, model_name=model_name)
            return format_sql_commands(response)
        return self.cache_service.get_cached_or_generate(f"populate:{db_id}", generator, use_cache)

    def _prepare_database(self, db_id: str, string_structure: str, database_structure: dict, mysql_instance, model_name: str, use_cache: bool):
        """Prepara o banco de dados de teste, criando e populando as tabelas."""
        create_statements = self._get_create_statements(db_id, string_structure, model_name, use_cache)
        mysql_instance.execute_sql_statements(create_statements)

        populate_statements = self._get_populate_statements(db_id, database_structure, model_name, use_cache)
        mysql_instance.execute_sql_statements(populate_statements)

    def _execute_and_collect_metrics(self, query: str, mysql_instance) -> tuple:
        """Executa uma query e coleta suas métricas de performance."""
        result = mysql_instance.execute_raw_query(query)
        time.sleep(0.5)  # Garantir persistência do log
        log = get_latest_select_log(mysql_instance)
        metrics = convert_metrics(log)
        executed_query = log[0] if log else query
        return result, metrics, executed_query

    def _send_results_for_analysis(self, webhook_data: dict, model_name: str):
        """Envia os resultados para o webhook e para a análise do RAG."""
        try:
            requests.post(self.webhook_url, json=webhook_data, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar webhook: {str(e)}")

        return self.rag_client.post("/optimizer/analyze", webhook_data, model_name=model_name)


    def optimize_query_flow(self, db_id: str, query: str, mysql_instance, model_name: str = "hermes", use_cache: bool = True):
        actual_db_id = db_id or self.default_db_id
        
        database_structure = get_db_structure(actual_db_id)
        string_structure = convert_db_structure_to_string(database_structure)

        optimized_queries = self._generate_optimizations(string_structure, query, model_name)

        mysql_instance.start_instance()
        try:
            self._prepare_database(actual_db_id, string_structure, database_structure, mysql_instance, model_name, use_cache)

            original_result, original_metrics, original_query = self._execute_and_collect_metrics(query, mysql_instance)

            # Aplicar otimizações (apenas índices)
            if isinstance(optimized_queries, list) and len(optimized_queries) > 1:
                mysql_instance.execute_sql_statements(optimized_queries[:-1])

            optimized_sql = optimized_queries[-1] if isinstance(optimized_queries, list) else optimized_queries
            
            optimized_result, optimized_metrics, optimized_query = self._execute_and_collect_metrics(optimized_sql, mysql_instance)

            webhook_payload = {
                "original_metrics": original_metrics,
                "optimized_metrics": optimized_metrics,
                "original_query": original_query,
                "optimized_query": optimized_query,
                "applied_indexes": optimized_queries if isinstance(optimized_queries, list) else [optimized_queries],
            }

            analysis_result = self._send_results_for_analysis(webhook_payload, model_name)

            return {
                "analyze": analysis_result,
                "optimized_queries": optimized_queries,
                "query_result": original_result,
            }

        except Exception as e:
            return {"error": str(e)}
        finally:
            mysql_instance.delete_instance()