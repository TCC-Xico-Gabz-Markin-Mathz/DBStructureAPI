# Processo de Otimização de Query SQL

Este documento detalha o funcionamento do endpoint de otimização de queries SQL, localizado em `api/optimization/routes/optimization.py`.

## Visão Geral

O módulo `optimization.py` define um endpoint API que permite aos usuários enviar uma query SQL e um ID de banco de dados para receber uma versão otimizada da query, juntamente com análises de performance. Ele utiliza serviços de RAG (Retrieval Augmented Generation), cache (Redis) e interação com instâncias MySQL para fornecer a otimização.

## Endpoint Principal

- **Caminho:** `/optimize`
- **Método:** `POST`
- **Sumário:** Otimiza uma query SQL.
- **Descrição:** Recebe uma query SQL e um ID de banco de dados, e retorna uma versão otimizada da query com análises de performance.

### Parâmetros da Requisição (Query Parameters)

- `db_id` (obrigatório): ID do banco de dados a ser usado para a otimização.
- `model_name` (opcional, padrão: `ModelName.GROQ.value`): Nome do modelo de linguagem a ser usado para a otimização.
- `use_cache` (opcional, padrão: `True`): Define se o cache de Redis deve ser utilizado para armazenar e recuperar resultados de otimização.

### Corpo da Requisição (Request Body)

O endpoint espera um objeto `OptimizeQueryRequest` no corpo da requisição, que contém:

- `query`: A query SQL original a ser otimizada.

### Respostas (Responses)

- **200 OK:**
    - **Descrição:** Query otimizada com sucesso.
    - **Conteúdo de Exemplo:**
        ```json
        {
            "analyze": {"analysis": "A query otimizada é mais performática..."},
            "optimized_queries": ["CREATE INDEX ...", "SELECT ..."],
            "query_result": [{"id": 1, "name": "John Doe"}]
        }
        ```
- **500 Internal Server Error:**
    - **Descrição:** Erro interno no servidor.
    - **Conteúdo de Exemplo:**
        ```json
        {
            "error": "Ocorreu um erro inesperado."
        }
        ```

## Fluxo de Otimização (`optimize_query_flow`)

A lógica central de otimização é orquestrada pelo método `optimize_query_flow` do `OptimizationService`. Embora os detalhes exatos da implementação estejam no serviço, o fluxo geral envolve:

1.  **Recebimento da Requisição:** O endpoint `optimize_query` recebe a query SQL, o `db_id` e outros parâmetros.
2.  **Injeção de Dependências:**
    - `mysql_instance`: Uma instância do cliente MySQL é injetada, permitindo a execução de queries no banco de dados especificado.
    - `optimization_service`: Uma instância do `OptimizationService` é injetada. Este serviço é responsável por coordenar o processo de otimização. Ele é inicializado com um `RAGClient` (para interação com modelos de linguagem), um `CacheService` (para gerenciar o cache Redis), e configurações como `WEBHOOK_URL` e `DEFAULT_DB_ID`.
3.  **Execução do Serviço de Otimização:** O método `optimize_query_flow` do `OptimizationService` é chamado com os dados da requisição. Este método encapsula a lógica para:
    - **Verificação de Cache:** Se `use_cache` for `True`, o serviço pode primeiro verificar se uma otimização para a query e `db_id` já existe no cache Redis.
    - **Geração de Otimização (via RAG):** Se não estiver em cache, o `RAGClient` é utilizado para interagir com o modelo de linguagem (especificado por `model_name`) para gerar a query otimizada e a análise de performance.
    - **Execução da Query Otimizada:** A query otimizada pode ser executada na `mysql_instance` para obter resultados ou validar a performance.
    - **Armazenamento em Cache:** Os resultados da otimização (query otimizada, análise, etc.) podem ser armazenados no cache Redis para futuras requisições.
    - **Retorno dos Resultados:** Os resultados processados são retornados ao cliente.

## Dependências Chave

- **`APIRouter` (FastAPI):** Para definir o endpoint da API.
- **`RAGClient` (`api.common.services.rag`):** Cliente para interagir com o modelo de linguagem (LLM) para a otimização da query.
- **`CacheService` (`api.common.services.cache`):** Serviço para gerenciar o cache de resultados de otimização usando Redis.
- **`OptimizationService` (`api.optimization.service.optimization_service`):** O serviço principal que orquestra o fluxo de otimização.
- **`get_mysql_instance` (`api.dependencies`):** Dependência que fornece uma instância do cliente MySQL para interagir com o banco de dados.
- **`get_rag_client` (`api.dependencies`):** Dependência que fornece uma instância do `RAGClient`.
- **`Config` (`api.config`):** Contém as configurações da aplicação, como detalhes do Redis e URL do webhook.
- **`OptimizeQueryRequest` (`api.optimization.models.optimize`):** Modelo Pydantic para validar o corpo da requisição.
- **`ModelName` (`api.optimization.models.optimize`):** Enumeração para os nomes dos modelos de linguagem suportados.

Este processo garante que as queries SQL possam ser otimizadas de forma eficiente, aproveitando modelos de linguagem avançados e um sistema de cache para melhorar a performance e a experiência do usuário.