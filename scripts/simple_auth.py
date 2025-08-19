#!/usr/bin/env python3
"""
Simple Authentication Setup for Codex2API

This script provides a simpler way to set up authentication by running
a temporary local server to handle the OAuth callback.
"""

import asyncio
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codex2api.auth import OAuthClient, get_token_manager
from codex2api.core import get_settings, setup_logging, get_logger
from codex2api.models import PkceCodes


class SimpleAuthSetup:
    """Simple authentication setup with local callback server."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.token_manager = get_token_manager()
        
        # Use a local callback server
        self.callback_port = 3000
        self.callback_uri = f"http://localhost:{self.callback_port}/callback"
        
        # Store OAuth state
        self.oauth_state = None
        self.pkce_codes = None
        self.received_code = None
        self.received_state = None
        self.received_error = None
        
        # Create FastAPI app for callback
        self.app = FastAPI()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup callback routes."""
        
        @self.app.get("/callback")
        async def oauth_callback(request: Request):
            """Handle OAuth callback."""
            query_params = dict(request.query_params)
            
            self.received_code = query_params.get("code")
            self.received_state = query_params.get("state")
            self.received_error = query_params.get("error")
            
            if self.received_error:
                return HTMLResponse(f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h1>❌ Authentication Error</h1>
                    <p>Error: {self.received_error}</p>
                    <p>Description: {query_params.get('error_description', 'Unknown error')}</p>
                    <p>You can close this window and check the terminal.</p>
                </body>
                </html>
                """)
            
            if self.received_code:
                return HTMLResponse("""
                <html>
                <head><title>Authentication Successful</title></head>
                <body>
                    <h1>✅ Authentication Successful!</h1>
                    <p>Authorization code received. You can close this window.</p>
                    <p>Check the terminal for next steps.</p>
                </body>
                </html>
                """)
            else:
                return HTMLResponse("""
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>❌ Authentication Failed</h1>
                    <p>No authorization code received.</p>
                    <p>You can close this window and try again.</p>
                </body>
                </html>
                """)
    
    def print_banner(self):
        """Print banner."""
        print("=" * 60)
        print("🚀 Simple Codex2API Authentication Setup")
        print("=" * 60)
        print()
        print("This tool will:")
        print("1. Start a local callback server")
        print("2. Open your browser for OAuth login")
        print("3. Automatically handle the callback")
        print("4. Store your tokens securely")
        print()
    
    async def start_callback_server(self):
        """Start the callback server in background."""
        config = uvicorn.Config(
            self.app,
            host="localhost",
            port=self.callback_port,
            log_level="error"  # Suppress uvicorn logs
        )
        server = uvicorn.Server(config)
        
        # Start server in background
        task = asyncio.create_task(server.serve())
        
        # Wait a moment for server to start
        await asyncio.sleep(1)
        
        return task, server
    
    async def run_oauth_flow(self):
        """Run the OAuth flow."""
        print("🔐 Starting OAuth flow...")
        
        async with OAuthClient() as oauth_client:
            # Override redirect URI to use our local server
            oauth_client.auth_config.redirect_uri = self.callback_uri
            
            # Generate auth URL
            auth_url, pkce_codes, state = oauth_client.generate_auth_url(no_browser=False)
            
            # Store for later use
            self.oauth_state = state
            self.pkce_codes = pkce_codes
            
            print(f"✅ Authorization URL: {auth_url}")
            print("🌐 Browser should open automatically...")
            print("⏳ Waiting for OAuth callback...")
            
            return auth_url
    
    async def wait_for_callback(self, timeout=300):
        """Wait for OAuth callback."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if self.received_code or self.received_error:
                break
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                print("⏰ Timeout waiting for OAuth callback.")
                return False
            
            await asyncio.sleep(1)
        
        if self.received_error:
            print(f"❌ OAuth error: {self.received_error}")
            return False
        
        if not self.received_code:
            print("❌ No authorization code received.")
            return False
        
        if self.received_state != self.oauth_state:
            print("❌ State parameter mismatch.")
            return False
        
        print("✅ Authorization code received!")
        return True
    
    async def exchange_tokens(self):
        """Exchange authorization code for tokens."""
        print("🔄 Exchanging authorization code for tokens...")
        
        try:
            async with OAuthClient() as oauth_client:
                # Override redirect URI
                oauth_client.auth_config.redirect_uri = self.callback_uri
                
                # Exchange code for tokens
                token_data = await oauth_client.exchange_code_for_tokens(
                    authorization_code=self.received_code,
                    pkce_codes=self.pkce_codes,
                    state=self.oauth_state,
                    received_state=self.received_state
                )
                
                # Store tokens
                auth_bundle = self.token_manager.store_tokens(token_data)
                
                print("✅ Tokens obtained and stored successfully!")
                print(f"   User ID: {token_data.account_id}")
                print(f"   Access token: {token_data.access_token[:20]}...")
                
                return True
                
        except Exception as e:
            print(f"❌ Failed to exchange tokens: {str(e)}")
            return False
    
    async def test_authentication(self):
        """Test authentication."""
        print("🧪 Testing authentication...")
        
        try:
            users = self.token_manager.list_users()
            if not users:
                return False
            
            user_id = users[0]
            auth_bundle = await self.token_manager.get_valid_tokens(user_id)
            
            if not auth_bundle:
                return False
            
            # Test with userinfo endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://auth0.openai.com/userinfo",
                    headers={"Authorization": f"Bearer {auth_bundle.token_data.access_token}"}
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    print("✅ Authentication test successful!")
                    print(f"   Email: {user_info.get('email', 'N/A')}")
                    return True
                else:
                    print(f"❌ Authentication test failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Authentication test failed: {str(e)}")
            return False
    
    def show_usage(self):
        """Show usage instructions."""
        print("\n🎉 Setup complete!")
        print("=" * 40)
        print("Now you can start the Codex2API server:")
        print()
        print("  python -m codex2api.main")
        print("  # or")
        print("  uv run python -m codex2api.main")
        print()
        print("API will be available at: http://localhost:8000")
        print("Documentation: http://localhost:8000/docs")
        print()
    
    async def run(self):
        """Run the complete setup process."""
        try:
            self.print_banner()
            
            # Start callback server
            print("🖥️  Starting local callback server...")
            server_task, server = await self.start_callback_server()
            print(f"✅ Callback server running on http://localhost:{self.callback_port}")
            
            try:
                # Run OAuth flow
                await self.run_oauth_flow()
                
                # Wait for callback
                if not await self.wait_for_callback():
                    print("❌ OAuth flow failed.")
                    return
                
                # Exchange tokens
                if not await self.exchange_tokens():
                    print("❌ Token exchange failed.")
                    return
                
                # Test authentication
                if await self.test_authentication():
                    self.show_usage()
                else:
                    print("⚠️  Setup completed but authentication test failed.")
                    print("   You may still be able to use the API.")
                
            finally:
                # Stop callback server
                print("\n🛑 Stopping callback server...")
                server.should_exit = True
                await server_task
                
        except KeyboardInterrupt:
            print("\n⚠️  Setup interrupted by user.")
        except Exception as e:
            print(f"\n❌ Setup failed: {str(e)}")


async def main():
    """Main entry point."""
    setup_logging()
    
    setup = SimpleAuthSetup()
    await setup.run()


if __name__ == "__main__":
    asyncio.run(main())
