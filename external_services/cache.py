import redis
from typing import Any
import json
import os


class RedisCache:
    def __init__(self, host: str, port: int):
        self.r = redis.Redis(host=host, port=port, db=0, decode_responses=True)

    def set(self, key: str, value: Any, exipiration_seconds: int = 300) -> bool:
        try:
            json_value = json.dumps(value)
            self.r.setex(key, exipiration_seconds, json_value)
            print(f"Cached key: {key} for {exipiration_seconds} seconds")
            return True
        except redis.exceptions.ConnectionError as e:
            print(f"Connection Error: {str(e)}")
            return False
        except Exception as e:
            print(f"Error while SET: {str(e)}")
            return False

    def get(self, key: str):
        try:
            value = self.r.get(key)
            if value is None:
                print(f"Key not found: {key}")
                return None
            print(f"Retrieved key: {key}")
            return json.loads(value)
        except redis.exceptions.ConnectionError as e:
            print(f"Connection Error: {str(e)}")
            return None
        except Exception as e:
            print(f"Error while GET: {str(e)}")
            return None


host = os.getenv("REDIS_HOST", "redis")
port = os.getenv("REDIS_PORT", 6379)
redis_cache = RedisCache(host, port)
