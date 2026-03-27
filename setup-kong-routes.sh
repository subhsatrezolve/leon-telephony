#!/bin/bash

echo "Setting up Kong routes..."

# Wait for Kong to be ready
echo "Waiting for Kong to be ready..."
until curl -f http://localhost:8001/status >/dev/null 2>&1; do
    echo "Kong is not ready yet. Waiting..."
    sleep 3
done

echo "Kong is ready! Setting up routes..."

# Create service for API
echo "Creating hotel-api service..."
curl -i -X POST http://localhost:8001/services/ \
    --data "name=hotel-api" \
    --data "url=http://api:8000"

echo ""
echo "Creating /hotel-api route..."
curl -i -X POST http://localhost:8001/services/hotel-api/routes \
    --data "paths[]=/hotel-api" \
    --data "strip_path=true"

echo ""
echo "Routes configured! Testing..."

# Test the route
sleep 2
echo "Testing route: http://localhost:8080/hotel-api/health/"
curl -s http://localhost:8080/hotel-api/health/ | jq '.' || echo "Route test failed"

echo ""
echo "Kong setup complete!"
echo "API available at: http://localhost:8080/hotel-api/"
echo "Kong Admin: http://localhost:8001"
echo "Kong Manager: http://localhost:8002"