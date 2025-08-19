# Pydantic Models Migration

## Overview

This document describes the migration from dataclass-based models to Pydantic v2 models in Codex2API. The new models provide enhanced validation, serialization, and type safety while maintaining full backward compatibility with the original ChatMock dataclass models. All models are designed to be fully compatible with OpenAI API specifications.

## Models Structure

### Authentication Models (`src/codex2api/models/auth.py`)

#### TokenData

- **Purpose**: OAuth token data containing all authentication tokens
- **Compatibility**: Direct replacement for ChatMock's TokenData dataclass
- **Fields**:
  - `id_token`: OpenAI ID token for user identification
  - `access_token`: Access token for API authentication  
  - `refresh_token`: Refresh token for token renewal
  - `account_id`: ChatGPT account identifier
- **Validation**: All fields require minimum length of 1 character

#### AuthBundle

- **Purpose**: Complete authentication bundle containing tokens and metadata
- **Compatibility**: Direct replacement for ChatMock's AuthBundle dataclass
- **Fields**:
  - `api_key`: Optional OpenAI API key obtained through token exchange
  - `token_data`: TokenData instance
  - `last_refresh`: ISO timestamp of last token refresh

#### PkceCodes

- **Purpose**: PKCE (Proof Key for Code Exchange) codes for OAuth security
- **Compatibility**: Direct replacement for ChatMock's PkceCodes dataclass
- **Fields**:
  - `code_verifier`: PKCE code verifier (43-128 characters)
  - `code_challenge`: PKCE code challenge (43-128 characters)

#### API Models

- `AuthStatus`: Authentication status information for API responses
- `LoginRequest/Response`: OAuth login flow models
- `RefreshTokenRequest/Response`: Token refresh operation models

### Request Models (`src/codex2api/models/requests.py`)

#### ChatMessage

- **Purpose**: Individual chat message in a conversation
- **Fields**:
  - `role`: Message sender role (system, user, assistant, tool)
  - `content`: Message content (text or structured)
  - `name`: Optional sender name
  - `tool_call_id`: Tool call response ID
  - `tool_calls`: Assistant tool calls

#### ChatCompletionRequest

- **Purpose**: OpenAI chat completions API request
- **Features**:
  - Full OpenAI API compatibility
  - ChatGPT-specific parameters (reasoning_effort, reasoning_summary, etc.)
  - Comprehensive validation (temperature 0.0-2.0, top_p 0.0-1.0, etc.)
  - Support for tools and function calling

#### CompletionRequest

- **Purpose**: OpenAI text completions API request
- **Features**: Legacy completions API support with full parameter validation

### Response Models (`src/codex2api/models/responses.py`)

#### Core Response Models

- `Usage`: Token usage information
- `ToolCall`: Tool call information
- `ChatCompletionMessage`: Chat completion message in response
- `ChatCompletionChoice`: Individual choice in chat completion
- `ChatCompletionResponse`: Complete chat completion response
- `ChatCompletionChunk`: Streaming chunk for chat completions

#### Model Information

- `ModelInfo`: Information about a single model
- `ModelsResponse`: Models list API response
- `CompletionResponse`: Text completion response

#### Error Handling

- `ErrorResponse`: Standard error response model

## Key Features

### 1. Enhanced Validation

- **Type Safety**: Strict type checking with Pydantic v2
- **Field Validation**: Min/max length, numeric ranges, enum validation
- **Custom Validators**: Business logic validation rules
- **Error Messages**: Clear, actionable validation error messages

### 2. Serialization & Deserialization

- **JSON Compatibility**: Seamless JSON serialization/deserialization
- **Dict Conversion**: Easy conversion to/from Python dictionaries
- **Field Aliases**: Support for alternative field names
- **Exclude/Include**: Flexible field inclusion/exclusion

### 3. Configuration

- **Model Config**: Consistent configuration across all models
  - `str_strip_whitespace=True`: Automatic whitespace trimming
  - `validate_assignment=True`: Validation on field assignment
  - `extra='forbid'`: Prevent unexpected fields (configurable per model)

### 4. Backward Compatibility

- **ChatMock Compatibility**: Direct drop-in replacement for dataclass models
- **Field Names**: Identical field names and types
- **JSON Format**: Compatible with existing auth.json files
- **API Contracts**: Maintains existing API contracts

## Usage Examples

### Authentication

```python
from codex2api.models import TokenData, AuthBundle

# Create token data
token_data = TokenData(
    id_token="eyJ0eXAiOiJKV1Q...",
    access_token="sk-proj-abc123...",
    refresh_token="refresh_abc123...",
    account_id="user-abc123"
)

# Create auth bundle
auth_bundle = AuthBundle(
    api_key="sk-proj-xyz789...",
    token_data=token_data,
    last_refresh="2025-01-19T10:30:00Z"
)

# JSON serialization
auth_json = auth_bundle.model_dump()
```

### Chat Completion

```python
from codex2api.models import ChatCompletionRequest, ChatMessage

# Create chat request
request = ChatCompletionRequest(
    model="gpt-4",
    messages=[
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello!")
    ],
    temperature=0.7,
    max_tokens=150
)

# Validation happens automatically
request_json = request.model_dump()
```

## Migration Benefits

1. **Type Safety**: Catch errors at development time instead of runtime
2. **Validation**: Automatic input validation with clear error messages
3. **Documentation**: Self-documenting models with field descriptions
4. **IDE Support**: Better autocomplete and type hints
5. **Serialization**: Robust JSON handling with proper error handling
6. **Extensibility**: Easy to add new fields and validation rules
7. **Performance**: Optimized Pydantic v2 performance
8. **Standards**: Industry-standard data modeling approach
9. **OpenAI Compatibility**: Full compatibility with OpenAI API specifications

## Testing

All models have been thoroughly tested for:

- ✅ Basic creation and validation
- ✅ Field validation rules (min/max length, ranges, etc.)
- ✅ JSON serialization/deserialization
- ✅ ChatMock compatibility
- ✅ Error handling and validation messages
- ✅ Type safety and IDE support
- ✅ OpenAI API compatibility

## Next Steps

1. **Integration**: Update existing code to use new models
2. **API Endpoints**: Integrate models with FastAPI endpoints
3. **Documentation**: Generate OpenAPI schemas from models
4. **Testing**: Expand test coverage for edge cases
5. **Performance**: Benchmark and optimize model performance
