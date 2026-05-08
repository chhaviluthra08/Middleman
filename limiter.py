import redis
import time
import json

r = redis.Redis(host="localhost", port=6379, db=0)

DEFAULT_LIMIT = 10

def get_limit(ip: str) -> int:
    override = r.get(f"limit:{ip}")
    return int(override) if override else DEFAULT_LIMIT

def record_path(ip: str, path: str):
    key = f"paths:{ip}"
    r.rpush(key, path)
    r.ltrim(key, -20, -1)  # keep last 20 paths only
    r.expire(key, 300)

def get_paths(ip: str) -> list:
    return [p.decode() for p in r.lrange(f"paths:{ip}", 0, -1)]

def is_allowed(ip: str) -> tuple[bool, int]:
    key = f"rl:{ip}"
    now = int(time.time())
    window_start = now - 60

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now) + str(time.time_ns()): now})
    pipe.zcard(key)
    pipe.expire(key, 60)
    results = pipe.execute()

    count = results[2]
    limit = get_limit(ip)
    return count <= limit, count