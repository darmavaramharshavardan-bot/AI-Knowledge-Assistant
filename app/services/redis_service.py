import os

import redis

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")


# ============================================================
# REDIS CLIENT
# ============================================================

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


# ============================================================
# SET CACHE
# ============================================================

def set_cache(
    key: str,
    value: str,
    expire: int = 3600
):
    try:

        redis_client.set(
            key,
            value,
            ex=expire
        )

        return True

    except Exception as error:

        print(
            f"Redis cache unavailable while setting key: {error}"
        )

        return False


# ============================================================
# GET CACHE
# ============================================================

def get_cache(key: str):

    try:

        return redis_client.get(key)

    except Exception as error:

        print(
            f"Redis cache unavailable while getting key: {error}"
        )

        return None


# ============================================================
# DELETE CACHE
# ============================================================

def delete_cache(key: str):

    try:

        redis_client.delete(key)

        return True

    except Exception as error:

        print(
            f"Redis cache unavailable while deleting key: {error}"
        )

        return False