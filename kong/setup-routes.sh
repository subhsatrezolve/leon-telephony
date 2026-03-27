#!/bin/bash

# Wait for Kong to be ready
echo "Waiting for Kong to be ready..."
until curl -f http://kong:8001/status >/dev/null 2>&1; do
    echo "Kong is not ready yet. Waiting..."
    sleep 5
done

echo "Kong is ready! Setting up routes..."

# Create service for API
echo "Creating hotel-api service..."
SERVICE_RESPONSE=$(curl -s -X POST http://kong:8001/services/ \
    --data "name=hotel-api" \
    --data "url=http://api:8000")
echo "Service response: $SERVICE_RESPONSE"

# Create route for hotel-api path
echo "Creating /hotel-api route..."
ROUTE_RESPONSE=$(curl -s -X POST http://kong:8001/services/hotel-api/routes \
    --data "paths[]=/hotel-api" \
    --data "strip_path=true")
echo "Route response: $ROUTE_RESPONSE"

# Wait a moment for configuration to propagate
sleep 2

echo "Kong routes configured successfully!"

# Show configured services and routes
echo "=== Services ==="
curl -s http://kong:8001/services/ | jq -r '.data[] | "Name: \(.name), URL: \(.url)"'

echo "=== Routes ==="
curl -s http://kong:8001/routes/ | jq -r '.data[] | "Path: \(.paths[]), Service: \(.service.name)"'

echo "=== Testing route ==="
curl -s http://kong:8000/hotel-api/health/ || echo "Route test failed"