# Codex2API

Modern OpenAI compatible API powered by ChatGPT.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for dependency management

## Quick Start

### Installation

#### Modern Way (Recommended - using uv)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that provides better dependency resolution, faster installs, and modern Python project management.

```bash
# Clone the repository
git clone https://github.com/your-username/Codex2API.git
cd Codex2API

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Activate virtual environment (optional - uv run handles this automatically)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Traditional Way (using pip)

```bash
# Clone the repository
git clone https://github.com/your-username/Codex2API.git
cd Codex2API

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```env
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_RELOAD=true

# Authentication (get client ID from OpenAI developer console)
AUTH_CLIENT_ID=your_openai_client_id_here
AUTH_REDIRECT_URI=http://localhost:8000/v1/auth/callback

# Application
ENVIRONMENT=development
DEBUG=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directory
DATA_DIR=./data
```

### Run the Server

#### Using uv (Recommended)

```bash
# Development mode with auto-reload
uv run python -m codex2api.main

# Or using uvicorn directly
uv run uvicorn codex2api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Traditional way

```bash
# Development mode
python -m codex2api.main

# Or using uvicorn directly
uvicorn codex2api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## Usage

### OpenAI Client Compatibility

Use any OpenAI client library by changing the base URL:

```python
import openai

# Configure client
client = openai.OpenAI(
    api_key="your-api-key",  # Will be handled by authentication
    base_url="http://localhost:8000/v1"
)

# Use as normal OpenAI client
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ]
)

print(response.choices[0].message.content)

# For reasoning models (o1), you can specify reasoning parameters
reasoning_response = client.chat.completions.create(
    model="o1",
    messages=[
        {"role": "user", "content": "Solve this complex problem step by step..."}
    ],
    reasoning_effort="high",  # User controls reasoning effort
    reasoning_summary="detailed"  # User controls summary format
)

print(reasoning_response.choices[0].message.content)
```

### Authentication

1. **Login**: POST `/v1/auth/login` to get OAuth URL
2. **Callback**: Complete OAuth flow at `/v1/auth/callback`
3. **Use API**: Include session cookie or bearer token in requests

### Available Endpoints

#### Chat Completions

- `POST /v1/chat/completions` - Create chat completion
- `GET /v1/chat/models` - List chat models

#### Models

- `GET /v1/models` - List all models
- `GET /v1/models/{model_id}` - Get model details

#### Authentication

- `POST /v1/auth/login` - Start OAuth login
- `GET /v1/auth/status` - Check auth status
- `POST /v1/auth/logout` - Logout

### Supported Models

- `gpt-4` - Most capable GPT-4 model
- `gpt-4-turbo` - Faster GPT-4 with larger context
- `gpt-4o` - Omni-modal GPT-4 with vision
- `gpt-4o-mini` - Smaller, faster GPT-4o
- `gpt-3.5-turbo` - Fast and efficient model
- `o1` - Advanced reasoning model (supports reasoning parameters)
- `o1-mini` - Smaller reasoning model (supports reasoning parameters)
- `o1-preview` - Preview reasoning model (supports reasoning parameters)

### Reasoning Parameters

For o1 models, you can control reasoning behavior using request parameters:

- `reasoning_effort`: Controls reasoning intensity (`"low"`, `"medium"`, `"high"`)
- `reasoning_summary`: Controls summary format (`"auto"`, `"concise"`, `"detailed"`, `"none"`)
- `reasoning_compat`: Compatibility mode (`"legacy"`, `"o3"`, `"think-tags"`, `"current"`)

**Important**: These are request parameters controlled by users, not server configuration.

### Example Requests

#### Chat Completion

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7
  }'
```

#### Reasoning Models (o1)

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "model": "o1",
    "messages": [
      {"role": "user", "content": "Solve this complex math problem..."}
    ],
    "reasoning_effort": "high",
    "reasoning_summary": "detailed"
  }'
```

#### List Models

```bash
curl -X GET "http://localhost:8000/v1/models" \
  -H "Authorization: Bearer your-token"
```

## Docker Deployment

### Using Docker

```bash
# Build image
docker build -t codex2api .

# Run container
docker run -d \
  --name codex2api \
  -p 8000:8000 \
  -e SERVER_HOST=0.0.0.0 \
  -e SERVER_PORT=8000 \
  codex2api
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  codex2api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8000
      - ENVIRONMENT=production
      - DEBUG=false
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

Run with:

```bash
docker-compose up -d
```

## Production Deployment

### Environment Variables

```env
# Production settings
ENVIRONMENT=production
DEBUG=false
SERVER_WORKERS=4
SERVER_RELOAD=false

# Security
AUTH_CLIENT_ID=your_production_client_id
AUTH_REDIRECT_URI=https://your-domain.com/v1/auth/callback

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs/codex2api.log

# Database
DB_URL=sqlite:///app/data/codex2api.db
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service

#### Using uv (Recommended)

Create `/etc/systemd/system/codex2api.service`:

```ini
[Unit]
Description=Codex2API Service
After=network.target

[Service]
Type=exec
User=codex2api
WorkingDirectory=/opt/codex2api
ExecStart=/usr/local/bin/uv run python -m codex2api.main
Restart=always
RestartSec=3
Environment=ENVIRONMENT=production

[Install]
WantedBy=multi-user.target
```

#### Traditional way

Create `/etc/systemd/system/codex2api.service`:

```ini
[Unit]
Description=Codex2API Service
After=network.target

[Service]
Type=exec
User=codex2api
WorkingDirectory=/opt/codex2api
Environment=PATH=/opt/codex2api/.venv/bin
ExecStart=/opt/codex2api/.venv/bin/python -m codex2api.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable codex2api
sudo systemctl start codex2api
```

## Health Check

Check if the service is running:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "version": "0.2.0",
  "timestamp": 1640995200.0
}
```

## API Documentation

When running in development mode, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
