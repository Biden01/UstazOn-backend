# Development Setup for UstazOn Backend

This guide explains how to set up the development environment for the UstazOn backend.

## Prerequisites

- Docker and Docker Compose
- Python 3.13 (optional, for local development without Docker)

## Running in Development Mode

### Using Docker Compose (Recommended)

1. Make sure you have Docker and Docker Compose installed
2. Copy the `.env.example` file to `.env` and adjust the values as needed:
   ```bash
   cp .env.example .env
   ```
3. Run the development environment:
   ```bash
   docker-compose -f docker-compose.yml up --build
   ```

Or use the convenience script:
```bash
./run-dev.sh
```

### Development Features

- **Live Reload**: Changes to the Python code in the `src/` directory will automatically trigger a server restart
- **Exposed Services**: PostgreSQL (port 5432) and Redis (port 6379) are exposed for local debugging
- **Development CORS**: Includes common development origins like `http://localhost:5173`, `http://localhost:3000`, etc.
- **No Auto Restart**: The container won't restart automatically in case of crashes during development

### Environment Variables

The following environment variables are configured for development:

- `DATABASE_URL`: Points to the development PostgreSQL instance
- `REDIS_URL`: Points to the development Redis instance
- `SECRET_KEY`: Set to a development key (change in production!)
- `BACKEND_CORS_ORIGINS`: Includes common development origins
- `SMS_ENABLED`: Disabled by default in development

### Ports

The following ports are exposed in development mode:

- `8000`: Backend API
- `5432`: PostgreSQL database
- `6379`: Redis server

### Volumes

The following volumes are mounted for development:

- `./src:/app/src`: Source code with live reload
- `./media:/app/media`: Media files
- `./uploads:/app/uploads`: Upload files
- `./alembic:/app/alembic`: Alembic migrations

## Connecting Frontend

The backend is configured to accept connections from:

- `http://localhost:5173` (Vite default)
- `http://localhost:5174`
- `http://localhost:3000` (React/Create React App default)
- `http://localhost:3001`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:3000`
- `http://0.0.0.0:5173`
- `http://0.0.0.0:3000`

## Troubleshooting

If you encounter issues:

1. Make sure all ports are available
2. Check that Docker has enough resources allocated
3. Verify your `.env` file has the correct values
4. Check the Docker logs: `docker-compose logs -f`

## Stopping the Development Environment

Press `Ctrl+C` to stop the services, then run:
```bash
docker-compose down
```