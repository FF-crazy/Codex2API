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

## First-Time Setup

### Easy Setup (Recommended)

For first-time users, we provide helper scripts to make setup easier:

```bash
# 🚀 Super simple setup (recommended)
python scripts/simple_auth.py

# 🔧 Or quick start with automatic setup
python scripts/start.py

# 📋 Or manual step-by-step setup
python scripts/setup_auth.py
python -m codex2api.main
```

### Authentication Setup Options

We provide three different setup methods:

#### 1. Simple Setup (Easiest) 🚀

```bash
python scripts/simple_auth.py
```

- ✅ Runs a local callback server
- ✅ Handles OAuth automatically
- ✅ No manual URL copying needed
- ✅ Works out of the box

#### 2. Manual Setup (Advanced) 📋

```bash
python scripts/setup_auth.py
```

- ✅ Step-by-step guidance
- ✅ Manual URL copying required
- ✅ More control over the process
- ✅ Works with any OAuth configuration

#### 3. Check Status 🔍

```bash
python scripts/check_auth.py
```

- ✅ Check existing tokens
- ✅ Validate authentication
- ✅ Show usage statistics
- ✅ Clean up expired sessions

All setup scripts will:

1. ✅ Check for existing tokens
2. 🌐 Open browser for OAuth login
3. 🔄 Exchange authorization code for tokens
4. 💾 Store tokens securely
5. 🧪 Test authentication
6. 📋 Show usage instructions

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

### Authentication Flow

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

#### Auth Endpoints

- `POST /v1/auth/login` - Start OAuth login
- `GET /v1/auth/status` - Check auth status
- `POST /v1/auth/logout` - Logout

### Reasoning Parameters

For o3-like models, you can control reasoning behavior using request parameters:

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
