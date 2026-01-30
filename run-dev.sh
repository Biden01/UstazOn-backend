#!/bin/bash

# Development startup script for UstazOn backend
echo "Starting UstazOn backend in development mode..."

# Check if docker-compose is available
if ! [ -x "$(command -v docker-compose)" ]; then
  echo "Error: docker-compose is not installed." >&2
  exit 1
fi

# Start the development environment
echo "Starting services..."
docker-compose up --build