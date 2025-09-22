import asyncio
import json
import time
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

from models import Interaction, User, Product, Session
from data_generator import generator
from config import settings

app = FastAPI(
    title="Simple Streaming API",
    description="Simple high-throughput streaming for testing"
)

# Initialize some cached data
@app.on_event("startup")
async def startup_event():
    print("Initializing data cache...")
    generator.generate_users_batch(1000)
    generator.generate_products_batch(2000)
    print("Data cache initialized")

@app.get("/")
async def root():
    return {
        "message": "Simple Streaming API",
        "version": "1.0.0",
        "endpoints": [
            "/stream/interactions",
            "/stream/users",
            "/metrics"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics")
async def metrics():
    return {
        "cached_users": len(generator.users_cache),
        "cached_products": len(generator.products_cache),
        "cached_sessions": len(generator.sessions_cache)
    }

async def generate_interaction_data():
    """Generate a single interaction with cached data"""
    if not generator.users_cache or not generator.products_cache:
        await startup_event()

    user = generator.users_cache[len(generator.users_cache) % len(generator.users_cache)]
    product = generator.products_cache[len(generator.products_cache) % len(generator.products_cache)]

    session_id = f"session_{int(time.time())}"
    if session_id not in generator.sessions_cache:
        session = generator.generate_session(user)
        generator.sessions_cache[session_id] = session
    else:
        session = generator.sessions_cache[session_id]

    interaction = generator.generate_interaction(user, product, session)
    return interaction.dict()

@app.get("/stream/interactions")
async def stream_interactions(
    rate: int = 1000,
    duration: int = 60,
    count: Optional[int] = None
):
    """Stream interactions at specified rate"""
    if rate > 50000:
        raise HTTPException(status_code=400, detail="Rate too high")

    delay = 1.0 / rate if rate > 0 else 0.001

    async def generate_stream():
        messages_sent = 0
        start_time = time.time()
        end_time = start_time + duration

        while (count is None or messages_sent < count) and time.time() < end_time:
            try:
                data = await generate_interaction_data()
                yield json.dumps(data) + "\n"
                messages_sent += 1

                # Control rate
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"Error generating data: {e}")
                break

    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )

@app.get("/stream/users")
async def stream_users(
    rate: int = 500,
    duration: int = 60,
    count: Optional[int] = None
):
    """Stream users at specified rate"""
    if rate > 5000:
        raise HTTPException(status_code=400, detail="Rate too high")

    delay = 1.0 / rate if rate > 0 else 0.001

    async def generate_stream():
        messages_sent = 0
        start_time = time.time()
        end_time = start_time + duration

        while (count is None or messages_sent < count) and time.time() < end_time:
            try:
                user = generator.generate_user()
                yield json.dumps(user.dict()) + "\n"
                messages_sent += 1

                # Control rate
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"Error generating data: {e}")
                break

    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )

if __name__ == "__main__":
    uvicorn.run("stream_simple:app", host="0.0.0.0", port=8000, reload=True)