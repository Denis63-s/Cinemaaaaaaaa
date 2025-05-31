import os
import random
from fastapi import FastAPI, Request, Response
import httpx

app = FastAPI()

# Получаем значения переменных окружения
MONOLITH_URL = os.getenv("MONOLITH_URL", "http://monolith:8080")
MOVIES_SERVICE_URL = os.getenv("MOVIES_SERVICE_URL", "http://movies-service:8081")
EVENTS_SERVICE_URL = os.getenv("EVENTS_SERVICE_URL", "http://events-service:8082")
GRADUAL_MIGRATION = os.getenv("GRADUAL_MIGRATION", "false").lower() == "true"
MIGRATION_PERCENT = int(os.getenv("MOVIES_MIGRATION_PERCENT", "0"))

@app.get("/api/movies")
async def proxy_movies(request: Request):
    """
    Прокси для /api/movies: постепенно направляет трафик либо в монолит, либо в новый сервис
    """
    if GRADUAL_MIGRATION and random.randint(1, 100) <= MIGRATION_PERCENT:
        target_url = f"{MOVIES_SERVICE_URL}/api/movies"
    else:
        target_url = f"{MONOLITH_URL}/api/movies"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(target_url)
            filtered_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in {"content-length", "transfer-encoding"}
            }
            return Response(content=response.content, status_code=response.status_code, headers=filtered_headers)
        except httpx.RequestError as e:
            return {"error": f"Failed to connect to target: {e}"}

@app.get("/api/events")
async def proxy_events():
    return {"message": "Маршрут для events пока не реализован"}

@app.get("/api/users")
async def proxy_users():
    target_url = f"{MONOLITH_URL}/api/users"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(target_url)
            filtered_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in {"content-length", "transfer-encoding"}
            }
            return Response(content=response.content, status_code=response.status_code, headers=filtered_headers)
        except httpx.RequestError as e:
            return {"error": f"Failed to connect to monolith: {e}"}

@app.get("/health")
async def health():
    return {"status": "true"}
