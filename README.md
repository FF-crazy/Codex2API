# Codex2API

Modern OpenAI compatible API powered by ChatGPT.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for dependency management

## Quick Start

### Installation


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


### Run the Server

```bash
# Development mode with auto-reload
uv run python -m codex2api.main

# Or using uvicorn directly
uv run uvicorn codex2api.main:app --host 0.0.0.0 --port 8000 --reload
```


The API will be available at `http://localhost:8000`

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

### Authentication Setup

You need a **ChatGPT Plus/Pro account** to use this service.

## Usage

### OpenAI Client Compatibility

Use any OpenAI client library by changing the base URL:

```python
import openai

# Configure client
client = openai.OpenAI(
    api_key="your-api-key",  # Will be set by yourself
    base_url="http://localhost:8000/v1"
)

# Use as normal OpenAI client
response = client.chat.completions.create(
    model="gpt-5",
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


### Available Endpoints

#### Chat Completions

- `POST /v1/chat/completions` - Create chat completion
- `GET /v1/chat/models` - List chat models

#### Models

- `GET /v1/models` - List all models
- `GET /v1/models/{model_id}` - Get model details

### Reasoning Parameters

For o3-like models, you can control reasoning behavior using request parameters:

- `reasoning_effort`: Controls reasoning intensity (`"low"`, `"medium"`, `"high"`)
- `reasoning_summary`: Controls summary format (`"auto"`, `"concise"`, `"detailed"`, `"none"`)
- `reasoning_compat`: Compatibility mode (`"legacy"`, `"o3"`, `"think-tags"`, `"current"`)

**Important**: These are request parameters controlled by users, not server configuration.

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

#### Reasoning Models (o3-like)

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "model": "o3",
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
