import redis.asyncio as redis

import config

# 初始化 Redis（默认 127.0.0.1:6379）
redis_client = redis.Redis(host=config.REDIS_HOST, port=6379, decode_responses=True)