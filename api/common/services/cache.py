import redis

class CacheService:
    def __init__(self, host, port, db, password):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )

    def get_cached_or_generate(self, key, generator_func, use_cache: bool = True):
        """Busca no cache ou gera novo conteúdo, com a opção de ignorar o cache."""
        if not use_cache:
            return generator_func()

        cached = self.redis_client.get(key)
        if cached:
            return (
                cached.split("\n\n")
                if key.startswith("db_structure")
                else cached.splitlines()
            )

        result = generator_func()
        cache_value = (
            "\n\n".join(result) if key.startswith("db_structure") else "\n".join(result)
        )
        self.redis_client.set(key, cache_value)
        return result