# Clickstream Data Generator

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/kuldeep27396/clickstream-datagenerator)

A FastAPI-based service for generating realistic e-commerce recommendation data including user profiles, products, interactions, and sessions with Kafka integration.

## Features

- **Realistic Data Generation**: Uses Faker library to generate realistic e-commerce data
- **Multiple Data Types**: Users, Products, Interactions (views/clicks/purchases), Sessions
- **Kafka Integration**: Stream data to Kafka topics for real-time processing
- **Configurable Rates**: Adjustable generation rates up to 100K+ messages per second
- **User Segments**: Casual, Regular, Power, and Premium user segments with realistic behaviors
- **Product Categories**: 10 different product categories with realistic pricing and attributes
- **Streaming Endpoints**: Real-time data streaming with configurable parameters
- **Railway Deployment**: Ready-to-deploy configuration files

## Quick Start

### Local Development

1. Clone and setup the repository:
```bash
git clone <repository-url>
cd clickstream-datagenerator
pip install -r requirements.txt
```

2. Start with Docker Compose (includes Kafka, Redis, Kafka UI):
```bash
docker-compose up -d
```

3. Start the FastAPI application:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

Copy `.env.example` to `.env` and configure:
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers
- `GENERATION_RATE`: Default generation rate (messages/second)
- `MAX_USERS`: Maximum number of users to cache
- `MAX_PRODUCTS`: Maximum number of products to cache

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health status including Kafka connectivity

### Data Generation
- `POST /generate/users` - Generate user profiles
- `POST /generate/products` - Generate product catalog
- `POST /generate/interactions` - Generate user interactions
- `POST /generate/sessions` - Generate user sessions

### Streaming
- `POST /stream/start` - Start continuous data streaming
- `POST /stream/stop/{stream_id}` - Stop a streaming session
- `GET /stream/status` - Get current streaming status
- `GET /stream/stats` - Get detailed streaming statistics

### Sample Data
- `GET /generate/sample/users` - Get sample user data
- `GET /generate/sample/products` - Get sample product data
- `GET /generate/sample/interactions` - Get sample interaction data

## Data Models

### User
- User segments: Casual, Regular, Power, Premium
- Realistic spending patterns and behavior
- Age, location, preferences, device information

### Product
- 10 product categories (Electronics, Clothing, Home, etc.)
- Realistic pricing per category
- Brand, rating, popularity scores, tags

### Interaction
- View, Click, Add to Cart, Purchase, Wishlist, etc.
- Session-based tracking
- Duration, quantity, revenue metrics

### Session
- User session tracking
- Device and browser information
- Interaction counts and revenue totals

## Example Usage

### Generate 1000 users with streaming to Kafka
```bash
curl -X POST "http://localhost:8000/generate/users" \
  -H "Content-Type: application/json" \
  -d '{
    "count": 1000,
    "stream": true,
    "rate": 100,
    "batch_size": 100
  }'
```

### Start continuous interaction streaming
```bash
curl -X POST "http://localhost:8000/stream/start" \
  -H "Content-Type: application/json" \
  -d '{
    "data_type": "interactions",
    "rate": 1000,
    "duration": 3600
  }'
```

### Get streaming status
```bash
curl -X GET "http://localhost:8000/stream/status"
```

## Performance

The application can generate:
- **100K+ messages/second** on modern hardware
- **Realistic behavioral patterns** based on user segments
- **Configurable batching** for optimal Kafka throughput
- **Memory-efficient caching** for users and products

## Railway Deployment

### One-Click Deployment

Click the button above to deploy instantly on Railway, or follow these manual steps:

### Manual Deployment

1. Push your code to GitHub
2. Connect your repository to Railway
3. Configure environment variables in Railway dashboard:
   - `KAFKA_BOOTSTRAP_SERVERS`: Your Kafka bootstrap servers
   - `GENERATION_RATE`: Default generation rate (default: 100)
   - `MAX_USERS`: Maximum cached users (default: 100000)
   - `MAX_PRODUCTS`: Maximum cached products (default: 50000)
4. Deploy with one click

The included `railway.toml` and `Dockerfile` handle all deployment configuration.

### Environment Variables on Railway

```bash
# Required for Kafka streaming
KAFKA_BOOTSTRAP_SERVERS=your-kafka-cluster:9092

# Optional configuration
GENERATION_RATE=1000
MAX_USERS=100000
MAX_PRODUCTS=50000
BATCH_SIZE=1000

# Redis for session tracking (optional)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_DB=0
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │     Kafka       │    │      Redis      │
│                 │    │                 │    │                 │
│  • Data Gen     │───▶│  • Users        │    │  • Session      │
│  • REST API     │    │  • Products     │    │    Cache        │
│  • Streaming    │    │  • Interactions │    │                 │
│  • Config       │    │  • Sessions     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Monitoring

- **Kafka UI**: Available at `http://localhost:8080` (with docker-compose)
- **FastAPI Docs**: Available at `http://localhost:8000/docs`
- **Health Checks**: `/health` endpoint for monitoring
- **Streaming Stats**: `/stream/stats` for real-time metrics

## Configuration

All aspects are configurable:
- Generation rates and limits
- Kafka topics and servers
- User segment weights
- Product pricing ranges
- Interaction probabilities
- Session behaviors

## License

MIT License