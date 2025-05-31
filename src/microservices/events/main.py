import os
import asyncio
import logging
from fastapi import FastAPI, Request
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from pydantic import BaseModel
import json

app = FastAPI()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKERS", "kafka:9092")

# Топики
TOPIC_USER = "user-events"
TOPIC_PAYMENT = "payment-events"
TOPIC_MOVIE = "movie-events"

producer: AIOKafkaProducer = None

# === Pydantic Models ===
class UserEvent(BaseModel):
    user_id: int
    username: str
    action: str
    timestamp: str

class PaymentEvent(BaseModel):
    payment_id: int
    user_id: int
    amount: float
    status: str
    timestamp: str
    method_type: str

class MovieEvent(BaseModel):
    movie_id: int
    title: str
    action: str
    user_id: int

# === Kafka Producer ===
@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    for attempt in range(10):
        try:
            await producer.start()
            print("✅ Kafka connected.")
            break
        except Exception as e:
            print(f"Kafka not ready, retrying in 3s... ({attempt+1}/10)")
            await asyncio.sleep(3)
    else:
        raise RuntimeError("❌ Failed to connect to Kafka after 10 attempts")

    asyncio.create_task(consume_messages())

@app.on_event("shutdown")
async def shutdown_event():
    global producer
    if producer:
        await producer.stop()

# === Kafka Consumers (в фоне) ===
async def consume_messages():
    consumer = AIOKafkaConsumer(
        TOPIC_USER, TOPIC_PAYMENT, TOPIC_MOVIE,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="events-service-group"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            logging.info(f"Received from {msg.topic}: {msg.value.decode('utf-8')}")
    finally:
        await consumer.stop()

# === API Routes ===
@app.post("/api/events/user", status_code=201)  # Изменено с 200 на 201
async def send_user_event(event: UserEvent):
    await producer.send_and_wait(TOPIC_USER, json.dumps(event.dict()).encode("utf-8"))
    return {"status": "success"}

@app.post("/api/events/payment", status_code=201)  # Изменено с 200 на 201
async def send_payment_event(event: PaymentEvent):
    await producer.send_and_wait(TOPIC_PAYMENT, json.dumps(event.dict()).encode("utf-8"))
    return {"status": "success"}

@app.post("/api/events/movie", status_code=201)  # Изменено с 200 на 201
async def send_movie_event(event: MovieEvent):
    await producer.send_and_wait(TOPIC_MOVIE, json.dumps(event.dict()).encode("utf-8"))
    return {"status": "success"}

@app.get("/api/events/health")
async def health():
    return {"status": True}  # Изменено с "true" на True (булево значение)