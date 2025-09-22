import time
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from models import (
    User, Product, Interaction, Session, GenerationRequest,
    GenerationResponse, StreamStatus
)
from data_generator import generator
from config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-commerce clickstream data generator for recommendation systems"
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
        "kafka_connected": False
    }

@app.post("/generate/users", response_model=GenerationResponse, tags=["Generation"])
async def generate_users(request: GenerationRequest):
    start_time = time.time()

    try:
        users = generator.generate_users_batch(request.count)

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

@app.get("/generate/sample/users", response_model=List[User], tags=["Sample Data"])
async def get_sample_users(count: int = 10):
    return generator.generate_users_batch(count)

@app.get("/generate/sample/products", response_model=List[Product], tags=["Sample Data"])
async def get_sample_products(count: int = 10):
    return generator.generate_products_batch(count)

@app.get("/generate/sample/interactions", response_model=List[Interaction], tags=["Sample Data"])
async def get_sample_interactions(count: int = 10):
    return generator.generate_interactions_batch(count)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_simple:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )