# Codex2API

Modern OpenAI compatible API powered by ChatGPT. This project converts Codex quota to OpenAI format API interface, allowing users to use API with just a Plus or Pro account without needing a developer platform account.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) for dependency management
- ChatGPT Plus/Pro account for authentication

## Quick Start

### Installation

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that provides better dependency resolution, faster installs, and modern Python project management.

```bash
# Clone the repository
git clone https://github.com/FF-crazy/Codex2API.git
cd Codex2API

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Activate virtual environment (optional - uv run handles this automatically)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Authentication Setup

Before running the server, you need to set up authentication with your ChatGPT Plus/Pro account:
Using Codex, after logging in your account, then run the following command:

1. Run the authentication script to get your token:

   ```bash
   uv run get_token.py
   ```

2. Follow the prompts to authenticate with your ChatGPT account

3. The authentication information will be saved to `auth.json`

### Run the Server

#### Option 1: Quick Start Script (Recommended)

```bash
# Make the script executable and run
chmod +x start.sh
./start.sh
```

The script will automatically:

- Install uv if not present
- Install dependencies
- Check for authentication
- Create .env file from template
- Start the server

#### Option 2: Manual Start

```bash
# Development mode
uv run main.py
```

The API will be available at `http://localhost:{PORT}`

## Docker Deployment

### Using Docker

```bash
# Build image
docker build -t codex2api .

# Run container (make sure auth.json exists)
docker run -d \
  --name codex2api \
  -p 11451:11451 \
  -v $(pwd)/auth.json:/app/auth.json:ro \
  -v $(pwd)/models.json:/app/models.json:ro \
  -v $(pwd)/.env:/app/.env:ro \
  -e HOST=0.0.0.0 \
  -e PORT=11451 \
  -e KEY=your-secure-api-key \
  codex2api
```

### Using Docker Compose

The project includes a `docker-compose.yml` file for easy deployment:

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

#### Docker Compose Configuration

The `docker-compose.yml` file includes:

- **Port mapping**: `11451:11451` (external:internal)
- **Environment variables**: Pre-configured with sensible defaults
- **Volume mounts**:
  - `auth.json` (required for authentication)
  - `models.json` (model configuration)
  - `.env` (optional environment overrides)
- **Health check**: Automatic container health monitoring
- **Restart policy**: `unless-stopped` for reliability

#### Environment Variables in Docker

You can override environment variables in several ways:

1. **Modify docker-compose.yml** (recommended for permanent changes)
2. **Use .env file** (mounted as volume)
3. **Command line override**:

   ```bash
   KEY=your-api-key docker-compose up -d
   ```

**Note**: Make sure you have completed the authentication setup and have `auth.json` file before running Docker containers.

### Testing Docker Setup

To test your Docker configuration:

```bash
# Make the test script executable and run
chmod +x docker-test.sh
./docker-test.sh
```

This script will:

- Build the Docker image
- Run a test container
- Test the health endpoint
- Clean up automatically

## Usage

### API Authentication

The API requires authentication using the `KEY` environment variable. By default, it's set to `sk-test`, but you should change this in production:

- **Development**: Use `sk-test` (default)
- **Production**: Set a secure API key in your environment variables

The API key should be provided in the `Authorization` header:

```http
Authorization: Bearer your-api-key
```

### OpenAI Client Compatibility

Use any OpenAI client library by changing the base URL:

```python
import openai

# Configure client
client = openai.OpenAI(
    api_key="sk-test",  # Use the KEY from your environment variables
    base_url="http://localhost:11451/v1"  # Note: Docker uses port 11451
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

## Configuration

### Environment Variables

You can configure the server using environment variables. Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

Available environment variables:

#### Server Configuration

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000, Docker uses 11451)
- `PYTHONPATH`: Python path for imports (default: /app in Docker)

#### API Security

- `KEY`: API key for authentication (default: sk-test)
  - **Important**: Change this to a secure key in production!

#### Reasoning Configuration

- `REASONING_EFFORT`: AI reasoning effort level (default: medium)
  - Options: `low`, `medium`, `high`
- `REASONING_SUMMARY`: Enable reasoning summary in responses (default: true)
  - Options: `true`, `false`
- `REASONING_COMPAT`: Reasoning compatibility mode (default: think-tags)
  - Options: `think-tags`, `openai-o1`

#### Optional Configuration

- `CHATGPT_LOCAL_HOME`: Custom directory for ChatGPT local files
- `CODEX_HOME`: Custom directory for Codex files

### Example .env file

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000

# API Security - CHANGE THIS IN PRODUCTION!
KEY=your-secure-api-key-here

# Reasoning Configuration
REASONING_EFFORT=medium
REASONING_SUMMARY=true
REASONING_COMPAT=think-tags
```

### Authentication

The server uses the authentication information stored in `auth.json`. This file is created when you run `get_token.py` and contains your ChatGPT session information.

To refresh your authentication token:

```bash
uv run refresh_auth.py
```

## Development

### Project Structure

```text
Codex2API/
├── codex2api/          # Main package
│   ├── __init__.py
│   ├── server.py       # FastAPI server
│   ├── models.py       # Data models
│   ├── request.py      # Request handling
│   └── utils.py        # Utility functions
├── main.py             # Entry point
├── start.sh            # Quick start script
├── docker-test.sh      # Docker testing script
├── get_token.py        # Authentication setup
├── refresh_auth.py     # Token refresh
├── auth.json           # Authentication data (created by get_token.py)
├── models.json         # Available models configuration
├── pyproject.toml      # Project configuration
├── .env.example        # Environment variables template
├── .dockerignore       # Docker ignore file
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose configuration
└── README.md           # This file
```

### Health Check

The server provides a health check endpoint at `/health` that returns the server status and timestamp.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test your changes
5. Submit a pull request

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.
