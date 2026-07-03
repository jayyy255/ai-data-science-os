import os
import json
import redis

class RedisCacheService:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.in_memory_fallback = {}
        try:
            self.client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            self.client.ping()
            self.redis_enabled = True
            print(f"Redis Cache connected successfully at {redis_url}")
        except Exception as e:
            print(f"Redis connection failed (falling back to in-memory dictionary cache): {e}")
            self.redis_enabled = False

    def get(self, key: str):
        if self.redis_enabled:
            try:
                val = self.client.get(key)
                return json.loads(val) if val else None
            except Exception as e:
                print(f"Redis GET error for key '{key}': {e}")
        return self.in_memory_fallback.get(key)

    def set(self, key: str, value, expire_seconds: int = 3600):
        serialized_val = json.dumps(value)
        if self.redis_enabled:
            try:
                self.client.setex(key, expire_seconds, serialized_val)
                return
            except Exception as e:
                print(f"Redis SET error for key '{key}': {e}")
        self.in_memory_fallback[key] = value

    def get_cached_chat(self, project_id: str, question: str) -> str:
        key = f"chat:{project_id}:{question.strip().lower()}"
        return self.get(key)

    def set_cached_chat(self, project_id: str, question: str, answer: str):
        key = f"chat:{project_id}:{question.strip().lower()}"
        self.set(key, answer, expire_seconds=1800)  # cache queries for 30 minutes
        
    def get_cached_eda(self, project_id: str):
        key = f"eda:{project_id}"
        return self.get(key)

    def set_cached_eda(self, project_id: str, eda_data: dict):
        key = f"eda:{project_id}"
        self.set(key, eda_data, expire_seconds=7200)  # cache EDA profiles for 2 hours
