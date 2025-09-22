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
    title="Working Streaming API",
    description="Working high-throughput streaming for testing"
)

# Global data cache
data_cache = {
    "users": [],
    "products": [],
    "initialized": False
}

def initialize_cache():
    """Initialize data cache"""
    if not data_cache["initialized"]:
        print("Initializing data cache...")
        data_cache["users"] = generator.generate_users_batch(1000)
        data_cache["products"] = generator.generate_products_batch(2000)
        data_cache["initialized"] = True
        print("Data cache initialized")

@app.get("/")
async def root():
    initialize_cache()
    return {
        "message": "Working Streaming API",
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
    initialize_cache()
    return {
        "cached_users": len(data_cache["users"]),
        "cached_products": len(data_cache["products"]),
        "initialized": data_cache["initialized"]
    }

def generate_interaction_data():
    """Generate a single interaction with cached data"""
    initialize_cache()

    user = data_cache["users"][int(time.time() * 100) % len(data_cache["users"])]
    product = data_cache["products"][int(time.time() * 100) % len(data_cache["products"])]

    session = generator.generate_session(user)
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
                data = generate_interaction_data()
                yield json.dumps(data) + "\n"
                messages_sent += 1

                # Control rate
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"Error generating data: {e}")
                yield json.dumps({"error": str(e)}) + "\n"
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
                yield json.dumps({"error": str(e)}) + "\n"
                break

    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )

# Test endpoint to verify streaming works
@app.get("/test-stream")
async def test_stream():
    """Test endpoint that returns a few lines"""
    async def test_generator():
        for i in range(5):
            data = {"test": i, "timestamp": time.time()}
            yield json.dumps(data) + "\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(
        test_generator(),
        media_type="application/x-ndjson"
    )

if __name__ == "__main__":
    uvicorn.run("stream_working:app", host="0.0.0.0", port=8000, reload=True)