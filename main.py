from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
import httpx
from limiter import is_allowed, record_path, get_paths, get_limit
from classifier import classify_user
import redis
from fastapi.responses import HTMLResponse


app = FastAPI()
TARGET_URL = "https://jsonplaceholder.typicode.com"
r = redis.Redis(host="localhost", port=6379, db=0)

@app.get("/__stats__")
def stats():
    keys = r.keys("rl:*")
    result = {}
    for key in keys:
        ip = key.decode().replace("rl:", "")
        count = r.zcard(key)
        limit = get_limit(ip)
        result[ip] = {
            "requests_last_minute": count,
            "current_limit": limit,
        }
    return result

@app.get("/__dashboard__")
def dashboard():
    with open("dashboard.html") as f:
        return HTMLResponse(f.read())

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    ip = request.client.host
    record_path(ip, path)

    allowed, count = is_allowed(ip)
    if not allowed:
        paths = get_paths(ip)
        try:
            result = classify_user(ip, count, paths)
            r.set(f"limit:{ip}", result["limit"], ex=300)
            reason = result["reason"]
            classification = result["classification"]
        except Exception:
            classification, reason = "UNKNOWN", "classifier error"

        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "classification": classification,
                "reason": reason,
                "requests_in_last_minute": count,
            }
        )

    url = f"{TARGET_URL}/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=await request.body(),
            params=request.query_params,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type"),
    )

@app.get("/__dashboard__")
def dashboard():
    with open("dashboard.html") as f:
        return HTMLResponse(f.read())