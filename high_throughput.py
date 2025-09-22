import asyncio
import json
import time
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import uvicorn

from models import (
    User, Product, Interaction, Session, GenerationRequest,
    GenerationResponse, StreamStatus
)
from data_generator import generator
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("High-throughput data generator started")
    yield
    print("High-throughput data generator stopped")

app = FastAPI(
    title=f"{settings.app_name} - High Throughput",
    version=settings.app_version,
    description="High-throughput e-commerce data generator (10K+ msg/sec)",
    lifespan=lifespan
)

# Global performance metrics
performance_metrics = {
    "total_messages_generated": 0,
    "messages_per_second": 0,
    "start_time": time.time(),
    "last_metrics_update": time.time(),
    "active_streams": 0,
    "peak_throughput": 0
}

class HighThroughputGenerator:
    def __init__(self):
        self.generator = generator
        self.batch_size = 1000
        self.max_concurrent_streams = 10

    async def generate_interactions_batch(self, batch_size: int) -> List[dict]:
        """Generate a batch of interactions for high throughput"""
        interactions = []

        for _ in range(batch_size):
            if not self.generator.users_cache:
                self.generator.generate_users_batch(100)
            if not self.generator.products_cache:
                self.generator.generate_products_batch(200)

            user = self.generator.users_cache[len(self.generator.users_cache) % len(self.generator.users_cache)]
            product = self.generator.products_cache[len(self.generator.products_cache) % len(self.generator.products_cache)]

            session_id = list(self.generator.sessions_cache.keys())[0] if self.generator.sessions_cache else f"session_{int(time.time())}"
            if session_id not in self.generator.sessions_cache:
                session = self.generator.generate_session(user)
            else:
                session = self.generator.sessions_cache[session_id]

            interaction = self.generator.generate_interaction(user, product, session)
            interactions.append(interaction.dict())

        return interactions

    async def generate_users_batch(self, batch_size: int) -> List[dict]:
        """Generate a batch of users"""
        users = self.generator.generate_users_batch(batch_size)
        return [user.dict() for user in users]

    async def generate_products_batch(self, batch_size: int) -> List[dict]:
        """Generate a batch of products"""
        products = self.generator.generate_products_batch(batch_size)
        return [product.dict() for product in products]

    async def stream_data_sse(self, data_type: str, messages_per_second: int, max_messages: Optional[int] = None):
        """Server-Sent Events streaming endpoint"""
        global performance_metrics

        delay = 1.0 / messages_per_second if messages_per_second > 0 else 0.0001
        messages_sent = 0
        start_time = time.time()

        performance_metrics["active_streams"] += 1

        try:
            while max_messages is None or messages_sent < max_messages:
                # Generate batch of data
                if data_type == "interactions":
                    batch = await self.generate_interactions_batch(1)
                elif data_type == "users":
                    batch = await self.generate_users_batch(1)
                elif data_type == "products":
                    batch = await self.generate_products_batch(1)
                else:
                    break

                # Send as SSE event
                data_str = json.dumps(batch[0])
                yield f"data: {data_str}\n\n"

                messages_sent += 1
                performance_metrics["total_messages_generated"] += 1

                # Update metrics every second
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

                # Control message rate
                await asyncio.sleep(delay)

        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            performance_metrics["active_streams"] -= 1

    async def stream_data_http(self, data_type: str, messages_per_second: int, duration: int = 60):
        """HTTP streaming endpoint with newline-delimited JSON"""
        global performance_metrics

        delay = 1.0 / messages_per_second if messages_per_second > 0 else 0.0001
        messages_sent = 0
        start_time = time.time()
        end_time = start_time + duration

        performance_metrics["active_streams"] += 1

        try:
            while time.time() < end_time:
                # Generate batch of data
                batch_size = min(100, messages_per_second)  # Send in small batches

                if data_type == "interactions":
                    batch = await self.generate_interactions_batch(batch_size)
                elif data_type == "users":
                    batch = await self.generate_users_batch(batch_size)
                elif data_type == "products":
                    batch = await self.generate_products_batch(batch_size)
                else:
                    break

                # Send batch as newline-delimited JSON
                for data in batch:
                    yield json.dumps(data) + "\n"
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

                # Control message rate
                batch_delay = delay * batch_size
                await asyncio.sleep(batch_delay)

        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            performance_metrics["active_streams"] -= 1

# Initialize high-throughput generator
ht_generator = HighThroughputGenerator()

@app.get("/", tags=["Health"])
async def root():
    return {
        "message": f"High-Throughput {settings.app_name}",
        "version": settings.app_version,
        "throughput": "10K+ messages/sec",
        "endpoints": [
            "/stream/sse/interactions?rate=10000",
            "/stream/http/interactions?rate=10000&duration=60",
            "/metrics"
        ]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "throughput_capable": True,
        "performance_metrics": performance_metrics
    }

@app.get("/metrics", tags=["Performance"])
async def get_metrics():
    """Get current performance metrics"""
    return {
        **performance_metrics,
        "uptime_seconds": time.time() - performance_metrics["start_time"],
        "active_connections": performance_metrics["active_streams"],
        "efficiency": f"{performance_metrics['messages_per_second']:.0f} msg/sec"
    }

@app.get("/stream/sse/interactions", tags=["Streaming"])
async def stream_interactions_sse(
    rate: int = 10000,
    max_messages: Optional[int] = None,
    request: Request = None
):
    """High-throughput SSE streaming of interactions"""
    if rate > 50000:
        raise HTTPException(status_code=400, detail="Maximum rate is 50,000 messages/sec")

    return StreamingResponse(
        ht_generator.stream_data_sse("interactions", rate, max_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/stream/sse/users", tags=["Streaming"])
async def stream_users_sse(
    rate: int = 5000,
    max_messages: Optional[int] = None,
    request: Request = None
):
    """SSE streaming of user data"""
    if rate > 20000:
        raise HTTPException(status_code=400, detail="Maximum rate is 20,000 messages/sec")

    return StreamingResponse(
        ht_generator.stream_data_sse("users", rate, max_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.get("/stream/http/interactions", tags=["Streaming"])
async def stream_interactions_http(
    rate: int = 10000,
    duration: int = 60,
    request: Request = None
):
    """High-throughput HTTP streaming of interactions (newline-delimited JSON)"""
    if rate > 50000:
        raise HTTPException(status_code=400, detail="Maximum rate is 50,000 messages/sec")

    if duration > 300:
        raise HTTPException(status_code=400, detail="Maximum duration is 300 seconds")

    return StreamingResponse(
        ht_generator.stream_data_http("interactions", rate, duration),
        media_type="application/x-ndjson",
        headers={
            "Transfer-Encoding": "chunked",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.get("/stream/http/users", tags=["Streaming"])
async def stream_users_http(
    rate: int = 5000,
    duration: int = 60,
    request: Request = None
):
    """HTTP streaming of user data"""
    if rate > 20000:
        raise HTTPException(status_code=400, detail="Maximum rate is 20,000 messages/sec")

    return StreamingResponse(
        ht_generator.stream_data_http("users", rate, duration),
        media_type="application/x-ndjson",
        headers={
            "Transfer-Encoding": "chunked",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.get("/benchmarks", tags=["Performance"])
async def run_benchmark():
    """Run a quick throughput benchmark"""
    start_time = time.time()
    test_duration = 10  # 10 seconds
    target_rate = 10000
    messages_received = 0

    async def count_messages():
        nonlocal messages_received
        async for chunk in ht_generator.stream_data_http("interactions", target_rate, test_duration):
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

if __name__ == "__main__":
    uvicorn.run(
        "high_throughput:app",
        host=settings.host,
        port=8001,  # Different port to avoid conflicts
        reload=settings.debug,
        workers=1  # FastAPI handles async, no need for multiple workers
    )