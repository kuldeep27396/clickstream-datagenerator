#!/bin/bash

# Setup script for Kafka topics and configuration

set -e

KAFKA_BOOTSTRAP=${KAFKA_BOOTSTRAP_SERVERS:-"localhost:9092"}
TOPICS=("users" "products" "interactions" "sessions")

echo "Setting up Kafka topics..."

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
until nc -z localhost 9092; do
    echo "Kafka not ready yet..."
    sleep 2
done

echo "Kafka is ready. Creating topics..."

# Create topics if they don't exist
for topic in "${TOPICS[@]}"; do
    echo "Creating topic: $topic"
    kafka-topics --create \
        --bootstrap-server $KAFKA_BOOTSTRAP \
        --replication-factor 1 \
        --partitions 3 \
        --topic $topic \
        --if-not-exists || true
done

echo "Topics created successfully!"

# List all topics
echo "Available topics:"
kafka-topics --list --bootstrap-server $KAFKA_BOOTSTRAP

echo "Kafka setup complete!"