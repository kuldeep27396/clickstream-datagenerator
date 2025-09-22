import asyncio
import json
import time
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

from models import (
    User, Product, Interaction, Session, GenerationRequest,
    GenerationResponse, StreamStatus
)
from data_generator import generator
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to initialize Kafka, but don't fail if it's not available
    try:
        from kafka_producer import kafka_producer_manager
        await kafka_producer_manager.start()
        print("Kafka connected successfully")
    except Exception as e:
        print(f"Kafka not available: {e}")
        print("Running without Kafka streaming")
    yield
    try:
        from kafka_producer import kafka_producer_manager
        await kafka_producer_manager.stop()
    except:
        pass

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-commerce clickstream data generator for recommendation systems",
    lifespan=lifespan
)

# Performance metrics
performance_metrics = {
    "total_messages_generated": 0,
    "messages_per_second": 0,
    "start_time": time.time(),
    "last_metrics_update": time.time(),
    "active_streams": 0,
    "peak_throughput": 0
}

@app.get("/", tags=["Health"])
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running",
        "streaming": "Available",
        "throughput": "10K+ msg/sec"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    kafka_connected = False
    try:
        from kafka_producer import kafka_producer_manager
        kafka_connected = await kafka_producer_manager.is_connected()
    except:
        pass

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "kafka_connected": kafka_connected,
        "performance_metrics": performance_metrics
    }

# High-Throughput Streaming Endpoints
class HighThroughputStreamer:
    def __init__(self):
        self.generator = generator

    async def generate_interactions_stream(self, rate: int, duration: int = 60):
        """Generate interactions at specified rate"""
        delay = 1.0 / rate if rate > 0 else 0.0001
        messages_sent = 0
        start_time = time.time()
        end_time = start_time + duration

        performance_metrics["active_streams"] += 1

        try:
            while time.time() < end_time:
                # Pre-generate data for better performance
                if not self.generator.users_cache:
                    self.generator.generate_users_batch(1000)
                if not self.generator.products_cache:
                    self.generator.generate_products_batch(2000)

                user = self.generator.users_cache[messages_sent % len(self.generator.users_cache)]
                product = self.generator.products_cache[messages_sent % len(self.generator.products_cache)]

                # Get or create session
                session_id = f"session_{int(time.time())}"
                if session_id not in self.generator.sessions_cache:
                    session = self.generator.generate_session(user)
                    self.generator.sessions_cache[session_id] = session
                else:
                    session = self.generator.sessions_cache[session_id]

                interaction = self.generator.generate_interaction(user, product, session)

                # Send interaction
                yield json.dumps(interaction.dict()) + "\n"

                messages_sent += 1
                performance_metrics["total_messages_generated"] += 1

                # Update metrics
                current_time = time.time()
                if current_time - performance_metrics["last_metrics_update"] >= 1.0:
                    time_diff = current_time - performance_metrics["last_metrics_update"]
                    performance_metrics["messages_per_second"] = messages_sent / time_diff
                    performance_metrics["peak_throughput"] = max(
                        performance_metrics["peak_throughput"],
                        performance_metrics["messages_per_second"]
                    )
                    performance_metrics["last_metrics_update"] = current_time
                    messages_sent = 0

                await asyncio.sleep(delay)

        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            performance_metrics["active_streams"] -= 1

# Initialize streamer
streamer = HighThroughputStreamer()

# Original endpoints for backward compatibility
@app.post("/generate/users", response_model=GenerationResponse, tags=["Generation"])
async def generate_users(request: GenerationRequest):
    start_time = time.time()

    try:
        users = generator.generate_users_batch(request.count)

        # Try to send to Kafka if available
        try:
            from kafka_producer import kafka_producer_manager
            for user in users:
                await kafka_producer_manager.send_user(user)
            kafka_message = "Data sent to Kafka"
        except Exception as kafka_error:
            kafka_message = f"Kafka not available: {kafka_error}"

        generation_time = time.time() - start_time
        rate_per_second = request.count / generation_time if generation_time > 0 else 0

        return GenerationResponse(
            success=True,
            message=f"Generated {request.count} users successfully. {kafka_message}",
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

@app.get("/generate/sample/users", response_model=List[User], tags=["Sample Data"])
async def get_sample_users(count: int = 10):
    return generator.generate_users_batch(count)

@app.get("/generate/sample/products", response_model=List[Product], tags=["Sample Data"])
async def get_sample_products(count: int = 10):
    return generator.generate_products_batch(count)

@app.get("/generate/sample/interactions", response_model=List[Interaction], tags=["Sample Data"])
async def get_sample_interactions(count: int = 10):
    return generator.generate_interactions_batch(count)

# High-Throughput Streaming Endpoints
@app.get("/stream/interactions", tags=["High-Throughput Streaming"])
async def stream_interactions(
    rate: int = 10000,
    duration: int = 60,
    request: Request = None
):
    """High-throughput streaming of interactions (newline-delimited JSON)"""
    if rate > 50000:
        raise HTTPException(status_code=400, detail="Maximum rate is 50,000 messages/sec")

    if duration > 300:
        raise HTTPException(status_code=400, detail="Maximum duration is 300 seconds")

    return StreamingResponse(
        streamer.generate_interactions_stream(rate, duration),
        media_type="application/x-ndjson",
        headers={
            "Transfer-Encoding": "chunked",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@app.get("/stream/sse/interactions", tags=["High-Throughput Streaming"])
async def stream_interactions_sse(
    rate: int = 10000,
    max_messages: Optional[int] = None,
    request: Request = None
):
    """Server-Sent Events streaming of interactions"""
    if rate > 50000:
        raise HTTPException(status_code=400, detail="Maximum rate is 50,000 messages/sec")

    async def sse_generator():
        messages_sent = 0
        delay = 1.0 / rate if rate > 0 else 0.0001

        performance_metrics["active_streams"] += 1

        try:
            while max_messages is None or messages_sent < max_messages:
                if not generator.users_cache:
                    generator.generate_users_batch(1000)

                user = generator.users_cache[messages_sent % len(generator.users_cache)]
                product = generator.products_cache[messages_sent % len(generator.products_cache)] if generator.products_cache else generator.generate_product()

                session_id = f"session_{int(time.time())}"
                if session_id not in generator.sessions_cache:
                    session = generator.generate_session(user)
                    generator.sessions_cache[session_id] = session
                else:
                    session = generator.sessions_cache[session_id]

                interaction = generator.generate_interaction(user, product, session)

                data_str = json.dumps(interaction.dict())
                yield f"data: {data_str}\n\n"

                messages_sent += 1
                performance_metrics["total_messages_generated"] += 1

                # Update metrics
                current_time = time.time()
                if current_time - performance_metrics["last_metrics_update"] >= 1.0:
                    time_diff = current_time - performance_metrics["last_metrics_update"]
                    performance_metrics["messages_per_second"] = messages_sent / time_diff
                    performance_metrics["peak_throughput"] = max(
                        performance_metrics["peak_throughput"],
                        performance_metrics["messages_per_second"]
                    )
                    performance_metrics["last_metrics_update"] = current_time
                    messages_sent = 0

                await asyncio.sleep(delay)

        except Exception as e:
            print(f"SSE Stream error: {e}")
        finally:
            performance_metrics["active_streams"] -= 1

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# Performance monitoring
@app.get("/metrics", tags=["Performance"])
async def get_metrics():
    """Get current performance metrics"""
    return {
        **performance_metrics,
        "uptime_seconds": time.time() - performance_metrics["start_time"],
        "active_connections": performance_metrics["active_streams"],
        "current_throughput": f"{performance_metrics['messages_per_second']:.0f} msg/sec",
        "peak_throughput": f"{performance_metrics['peak_throughput']:.0f} msg/sec"
    }

@app.get("/benchmarks", tags=["Performance"])
async def run_benchmark():
    """Run a quick throughput benchmark"""
    start_time = time.time()
    test_duration = 10  # 10 seconds
    target_rate = 10000
    messages_received = 0

    async def count_messages():
        nonlocal messages_received
        async for chunk in streamer.generate_interactions_stream(target_rate, test_duration):
            messages_received += 1

    await count_messages()

    actual_duration = time.time() - start_time
    actual_rate = messages_received / actual_duration

    return {
        "target_rate": target_rate,
        "actual_rate": round(actual_rate, 2),
        "duration_seconds": round(actual_duration, 2),
        "total_messages": messages_received,
        "efficiency": f"{(actual_rate/target_rate)*100:.1f}%"
    }

@app.get("/kafka/status", tags=["Kafka"])
async def kafka_status():
    try:
        from kafka_producer import kafka_producer_manager
        is_connected = await kafka_producer_manager.is_connected()
        stats = kafka_producer_manager.get_producer_stats()
        return {
            "connected": is_connected,
            "stats": stats
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_production:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )