import os

import redis
from dotenv import load_dotenv


load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True
)


def set_cache(key: str, value: str, expire: int = 3600):
    redis_client.set(
        key,
        value,
        ex=expire
    )


def get_cache(key: str):
    return redis_client.get(key)