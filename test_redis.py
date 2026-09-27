from app.services.redis_service import redis_client


redis_client.set("test_key", "Hello Redis")

value = redis_client.get("test_key")

print("Redis value:", value)
print("Redis connection successful!")