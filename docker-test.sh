#!/bin/bash

# Docker Test Script for Codex2API

set -e

echo "🐳 Codex2API Docker Test"
echo "========================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if auth.json exists
if [ ! -f "auth.json" ]; then
    echo "❌ auth.json not found. Please run 'uv run get_token.py' first."
    exit 1
fi

echo "🔨 Building Docker image..."
docker build -t codex2api-test .

echo "✅ Docker image built successfully"

echo "🚀 Testing Docker container..."
# Run container in detached mode
CONTAINER_ID=$(docker run -d \
  --name codex2api-test \
  -p 8001:8000 \
  -v $(pwd)/auth.json:/app/auth.json:ro \
  -v $(pwd)/models.json:/app/models.json:ro \
  codex2api-test)

echo "📋 Container ID: $CONTAINER_ID"

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 10

# Test health endpoint
echo "🔍 Testing health endpoint..."
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "📋 Container logs:"
    docker logs codex2api-test
fi

# Cleanup
echo "🧹 Cleaning up..."
docker stop codex2api-test > /dev/null 2>&1 || true
docker rm codex2api-test > /dev/null 2>&1 || true

echo "✅ Docker test completed"
