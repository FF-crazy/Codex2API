'''
Unit tests for Codex2API data models.

Tests compatibility with original ChatMock dataclass models and validates
Pydantic model behavior.
'''

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from codex2api.models import (
    TokenData,
    AuthBundle,
    PkceCodes,
    AuthStatus,
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelsResponse,
    ModelInfo,
)


class TestAuthModels:
    '''
    Test authentication-related models.
    '''
    
    def test_token_data_creation(self) -> None:
        '''
        Test TokenData model creation and validation.
        '''
        token_data = TokenData(
            id_token='test_id_token',
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            account_id='test_account_id'
        )
        
        assert token_data.id_token == 'test_id_token'
        assert token_data.access_token == 'test_access_token'
        assert token_data.refresh_token == 'test_refresh_token'
        assert token_data.account_id == 'test_account_id'
    
    def test_token_data_validation(self) -> None:
        '''
        Test TokenData validation rules.
        '''
        # Test empty string validation
        with pytest.raises(ValidationError):
            TokenData(
                id_token='',
                access_token='test',
                refresh_token='test',
                account_id='test'
            )
    
    def test_auth_bundle_creation(self) -> None:
        '''
        Test AuthBundle model creation.
        '''
        token_data = TokenData(
            id_token='test_id',
            access_token='test_access',
            refresh_token='test_refresh',
            account_id='test_account'
        )
        
        auth_bundle = AuthBundle(
            api_key='test_api_key',
            token_data=token_data,
            last_refresh='2025-01-01T00:00:00Z'
        )
        
        assert auth_bundle.api_key == 'test_api_key'
        assert auth_bundle.token_data == token_data
        assert auth_bundle.last_refresh == '2025-01-01T00:00:00Z'
    
    def test_pkce_codes_creation(self) -> None:
        '''
        Test PkceCodes model creation and validation.
        '''
        pkce = PkceCodes(
            code_verifier='a' * 43,  # Minimum length
            code_challenge='b' * 43   # Minimum length
        )
        
        assert len(pkce.code_verifier) == 43
        assert len(pkce.code_challenge) == 43
        
        # Test length validation
        with pytest.raises(ValidationError):
            PkceCodes(
                code_verifier='short',
                code_challenge='also_short'
            )


class TestRequestModels:
    '''
    Test request-related models.
    '''
    
    def test_chat_message_creation(self) -> None:
        '''
        Test ChatMessage model creation.
        '''
        message = ChatMessage(
            role='user',
            content='Hello, world!'
        )
        
        assert message.role == 'user'
        assert message.content == 'Hello, world!'
        assert message.name is None
        assert message.tool_call_id is None
    
    def test_chat_completion_request(self) -> None:
        '''
        Test ChatCompletionRequest model creation.
        '''
        messages = [
            ChatMessage(role='system', content='You are a helpful assistant.'),
            ChatMessage(role='user', content='Hello!')
        ]
        
        request = ChatCompletionRequest(
            model='gpt-5',
            messages=messages,
            temperature=0.7,
            stream=False
        )
        
        assert request.model == 'gpt-5'
        assert len(request.messages) == 2
        assert request.temperature == 0.7
        assert request.stream is False
    
    def test_chat_completion_request_validation(self) -> None:
        '''
        Test ChatCompletionRequest validation.
        '''
        # Test empty messages list
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                model='gpt-5',
                messages=[]
            )
        
        # Test invalid temperature
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                model='gpt-5',
                messages=[ChatMessage(role='user', content='test')],
                temperature=3.0  # Too high
            )


class TestResponseModels:
    '''
    Test response-related models.
    '''
    
    def test_model_info_creation(self) -> None:
        '''
        Test ModelInfo model creation.
        '''
        model_info = ModelInfo(
            id='gpt-5',
            created=1640995200  # 2022-01-01 00:00:00 UTC
        )
        
        assert model_info.id == 'gpt-5'
        assert model_info.object == 'model'
        assert model_info.created == 1640995200
        assert model_info.owned_by == 'openai'
    
    def test_models_response_creation(self) -> None:
        '''
        Test ModelsResponse model creation.
        '''
        models = [
            ModelInfo(id='gpt-5', created=1640995200),
            ModelInfo(id='codex-mini', created=1640995200)
        ]
        
        response = ModelsResponse(data=models)
        
        assert response.object == 'list'
        assert len(response.data) == 2
        assert response.data[0].id == 'gpt-5'
        assert response.data[1].id == 'codex-mini'


class TestCompatibility:
    '''
    Test compatibility with original ChatMock models.
    '''
    
    def test_token_data_serialization(self) -> None:
        '''
        Test TokenData serialization compatibility.
        '''
        token_data = TokenData(
            id_token='test_id',
            access_token='test_access',
            refresh_token='test_refresh',
            account_id='test_account'
        )
        
        # Test JSON serialization
        json_data = token_data.model_dump()
        expected = {
            'id_token': 'test_id',
            'access_token': 'test_access',
            'refresh_token': 'test_refresh',
            'account_id': 'test_account'
        }
        
        assert json_data == expected
        
        # Test deserialization
        restored = TokenData.model_validate(json_data)
        assert restored == token_data
    
    def test_auth_bundle_json_compatibility(self) -> None:
        '''
        Test AuthBundle JSON format compatibility with original auth.json.
        '''
        # Simulate original auth.json structure
        auth_json = {
            'OPENAI_API_KEY': 'test_api_key',
            'tokens': {
                'id_token': 'test_id',
                'access_token': 'test_access',
                'refresh_token': 'test_refresh',
                'account_id': 'test_account'
            },
            'last_refresh': '2025-01-01T00:00:00Z'
        }
        
        # Convert to our model format
        token_data = TokenData(**auth_json['tokens'])
        auth_bundle = AuthBundle(
            api_key=auth_json['OPENAI_API_KEY'],
            token_data=token_data,
            last_refresh=auth_json['last_refresh']
        )
        
        # Verify conversion works
        assert auth_bundle.api_key == 'test_api_key'
        assert auth_bundle.token_data.id_token == 'test_id'
        assert auth_bundle.last_refresh == '2025-01-01T00:00:00Z'
