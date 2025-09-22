import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "clickstream-datagenerator"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_users: str = "users"
    kafka_topic_products: str = "products"
    kafka_topic_interactions: str = "interactions"
    kafka_topic_sessions: str = "sessions"

    generation_rate: int = 100
    max_users: int = 100000
    max_products: int = 50000
    batch_size: int = 1000

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    class Config:
        env_file = ".env"

settings = Settings()