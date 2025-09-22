import asyncio
import time
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

from models import (
    User, Product, Interaction, Session, GenerationRequest,
    GenerationResponse, StreamStatus
)
from data_generator import generator
from config import settings
from kafka_producer import kafka_producer_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_producer_manager.start()
    yield
    await kafka_producer_manager.stop()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-commerce clickstream data generator for recommendation systems",
    lifespan=lifespan
)

active_streams = {}
stream_stats = {
    "is_running": False,
    "start_time": None,
    "total_generated": 0,
    "current_rate": 0,
    "target_rate": 0,
    "active_streams": []
}

@app.get("/", tags=["Health"])
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "kafka_connected": await kafka_producer_manager.is_connected()
    }

@app.post("/generate/users", response_model=GenerationResponse, tags=["Generation"])
async def generate_users(request: GenerationRequest):
    start_time = time.time()

    try:
        users = generator.generate_users_batch(request.count)

        if request.stream:
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                stream_users_to_kafka,
                users,
                request.batch_size,
                request.rate or settings.generation_rate
            )
        else:
            await send_users_to_kafka(users, request.batch_size)

        generation_time = time.time() - start_time
        rate_per_second = request.count / generation_time if generation_time > 0 else 0

        return GenerationResponse(
            success=True,
            message=f"Generated {request.count} users successfully",
            count_generated=len(users),
            time_taken=generation_time,
            rate_per_second=rate_per_second
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate users: {str(e)}")

@app.post("/generate/products", response_model=GenerationResponse, tags=["Generation"])
async def generate_products(request: GenerationRequest):
    start_time = time.time()

    try:
        products = generator.generate_products_batch(request.count)

        if request.stream:
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                stream_products_to_kafka,
                products,
                request.batch_size,
                request.rate or settings.generation_rate
            )
        else:
            await send_products_to_kafka(products, request.batch_size)

        generation_time = time.time() - start_time
        rate_per_second = request.count / generation_time if generation_time > 0 else 0

        return GenerationResponse(
            success=True,
            message=f"Generated {request.count} products successfully",
            count_generated=len(products),
            time_taken=generation_time,
            rate_per_second=rate_per_second
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate products: {str(e)}")

@app.post("/generate/interactions", response_model=GenerationResponse, tags=["Generation"])
async def generate_interactions(request: GenerationRequest):
    start_time = time.time()

    try:
        interactions = generator.generate_interactions_batch(request.count)

        if request.stream:
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                stream_interactions_to_kafka,
                interactions,
                request.batch_size,
                request.rate or settings.generation_rate
            )
        else:
            await send_interactions_to_kafka(interactions, request.batch_size)

        generation_time = time.time() - start_time
        rate_per_second = request.count / generation_time if generation_time > 0 else 0

        return GenerationResponse(
            success=True,
            message=f"Generated {request.count} interactions successfully",
            count_generated=len(interactions),
            time_taken=generation_time,
            rate_per_second=rate_per_second
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate interactions: {str(e)}")

@app.post("/generate/sessions", response_model=GenerationResponse, tags=["Generation"])
async def generate_sessions(request: GenerationRequest):
    start_time = time.time()

    try:
        sessions = []
        for _ in range(request.count):
            user = generator.generate_user()
            session = generator.generate_session(user)
            sessions.append(session)

        if request.stream:
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                stream_sessions_to_kafka,
                sessions,
                request.batch_size,
                request.rate or settings.generation_rate
            )
        else:
            await send_sessions_to_kafka(sessions, request.batch_size)

        generation_time = time.time() - start_time
        rate_per_second = request.count / generation_time if generation_time > 0 else 0

        return GenerationResponse(
            success=True,
            message=f"Generated {request.count} sessions successfully",
            count_generated=len(sessions),
            time_taken=generation_time,
            rate_per_second=rate_per_second
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate sessions: {str(e)}")

@app.post("/stream/start", tags=["Streaming"])
async def start_streaming(
    data_type: str = "interactions",
    rate: int = settings.generation_rate,
    max_count: Optional[int] = None,
    duration: Optional[int] = None
):
    global stream_stats

    if data_type not in ["users", "products", "interactions", "sessions"]:
        raise HTTPException(status_code=400, detail="Invalid data type")

    if stream_stats["is_running"]:
        raise HTTPException(status_code=400, detail="Stream already running")

    stream_id = f"{data_type}_{int(time.time())}"
    active_streams[stream_id] = {
        "data_type": data_type,
        "rate": rate,
        "max_count": max_count,
        "duration": duration,
        "start_time": time.time(),
        "generated_count": 0
    }

    stream_stats.update({
        "is_running": True,
        "start_time": datetime.utcnow(),
        "current_rate": rate,
        "target_rate": rate,
        "active_streams": list(active_streams.keys())
    })

    asyncio.create_task(stream_data_continuously(stream_id))

    return {
        "stream_id": stream_id,
        "status": "started",
        "data_type": data_type,
        "rate": rate,
        "max_count": max_count,
        "duration": duration
    }

@app.post("/stream/stop/{stream_id}", tags=["Streaming"])
async def stop_streaming(stream_id: str):
    if stream_id not in active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")

    stream_info = active_streams.pop(stream_id)

    if not active_streams:
        stream_stats.update({
            "is_running": False,
            "start_time": None,
            "current_rate": 0,
            "target_rate": 0,
            "active_streams": []
        })
    else:
        stream_stats["active_streams"] = list(active_streams.keys())

    return {
        "stream_id": stream_id,
        "status": "stopped",
        "final_stats": stream_info
    }

@app.get("/stream/status", response_model=StreamStatus, tags=["Streaming"])
async def get_stream_status():
    return StreamStatus(**stream_stats)

@app.get("/stream/stats", tags=["Streaming"])
async def get_stream_stats():
    return {
        "global_stats": stream_stats,
        "active_streams": active_streams,
        "cache_stats": {
            "users_cached": len(generator.users_cache),
            "products_cached": len(generator.products_cache),
            "sessions_cached": len(generator.sessions_cache)
        }
    }

@app.get("/generate/sample/users", response_model=List[User], tags=["Sample Data"])
async def get_sample_users(count: int = 10):
    return generator.generate_users_batch(count)

@app.get("/generate/sample/products", response_model=List[Product], tags=["Sample Data"])
async def get_sample_products(count: int = 10):
    return generator.generate_products_batch(count)

@app.get("/generate/sample/interactions", response_model=List[Interaction], tags=["Sample Data"])
async def get_sample_interactions(count: int = 10):
    return generator.generate_interactions_batch(count)

async def send_users_to_kafka(users: List[User], batch_size: int):
    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]
        for user in batch:
            await kafka_producer_manager.send_user(user)

async def send_products_to_kafka(products: List[Product], batch_size: int):
    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        for product in batch:
            await kafka_producer_manager.send_product(product)

async def send_interactions_to_kafka(interactions: List[Interaction], batch_size: int):
    for i in range(0, len(interactions), batch_size):
        batch = interactions[i:i + batch_size]
        for interaction in batch:
            await kafka_producer_manager.send_interaction(interaction)

async def send_sessions_to_kafka(sessions: List[Session], batch_size: int):
    for i in range(0, len(sessions), batch_size):
        batch = sessions[i:i + batch_size]
        for session in batch:
            await kafka_producer_manager.send_session(session)

async def stream_users_to_kafka(users: List[User], batch_size: int, rate: int):
    delay = 1.0 / rate if rate > 0 else 0.1

    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]
        for user in batch:
            await kafka_producer_manager.send_user(user)
            stream_stats["total_generated"] += 1
            await asyncio.sleep(delay)

async def stream_products_to_kafka(products: List[Product], batch_size: int, rate: int):
    delay = 1.0 / rate if rate > 0 else 0.1

    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        for product in batch:
            await kafka_producer_manager.send_product(product)
            stream_stats["total_generated"] += 1
            await asyncio.sleep(delay)

async def stream_interactions_to_kafka(interactions: List[Interaction], batch_size: int, rate: int):
    delay = 1.0 / rate if rate > 0 else 0.1

    for i in range(0, len(interactions), batch_size):
        batch = interactions[i:i + batch_size]
        for interaction in batch:
            await kafka_producer_manager.send_interaction(interaction)
            stream_stats["total_generated"] += 1
            await asyncio.sleep(delay)

async def stream_sessions_to_kafka(sessions: List[Session], batch_size: int, rate: int):
    delay = 1.0 / rate if rate > 0 else 0.1

    for i in range(0, len(sessions), batch_size):
        batch = sessions[i:i + batch_size]
        for session in batch:
            await kafka_producer_manager.send_session(session)
            stream_stats["total_generated"] += 1
            await asyncio.sleep(delay)

async def stream_data_continuously(stream_id: str):
    stream_info = active_streams.get(stream_id)
    if not stream_info:
        return

    data_type = stream_info["data_type"]
    rate = stream_info["rate"]
    max_count = stream_info["max_count"]
    duration = stream_info["duration"]

    start_time = time.time()
    generated_count = 0

    try:
        while stream_id in active_streams:
            current_time = time.time()

            if duration and (current_time - start_time) >= duration:
                break

            if max_count and generated_count >= max_count:
                break

            if data_type == "users":
                data = generator.generate_user()
                await kafka_producer_manager.send_user(data)
            elif data_type == "products":
                data = generator.generate_product()
                await kafka_producer_manager.send_product(data)
            elif data_type == "interactions":
                interactions = generator.generate_interactions_batch(1)
                for interaction in interactions:
                    await kafka_producer_manager.send_interaction(interaction)
                    data = interaction
            elif data_type == "sessions":
                user = generator.generate_user()
                data = generator.generate_session(user)
                await kafka_producer_manager.send_session(data)

            generated_count += 1
            stream_info["generated_count"] = generated_count
            stream_stats["total_generated"] += 1

            delay = 1.0 / rate if rate > 0 else 0.1
            await asyncio.sleep(delay)

    except Exception as e:
        print(f"Stream {stream_id} error: {e}")

    finally:
        if stream_id in active_streams:
            active_streams.pop(stream_id)

        if not active_streams:
            stream_stats.update({
                "is_running": False,
                "start_time": None,
                "current_rate": 0,
                "target_rate": 0,
                "active_streams": []
            })
        else:
            stream_stats["active_streams"] = list(active_streams.keys())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )