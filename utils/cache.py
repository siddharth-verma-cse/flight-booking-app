import hashlib
import json


def build_flight_cache_key(search) -> str:
    payload = json.dumps(search.model_dump(), sort_keys=True)

    return f"flight_search:{hashlib.md5(payload.encode()).hexdigest()}"
