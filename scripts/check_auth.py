#!/usr/bin/env python3
"""
Codex2API Authentication Status Checker

This script checks the status of stored authentication tokens.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codex2api.auth import get_token_manager, get_session_manager
from codex2api.core import setup_logging, get_logger


class AuthChecker:
    """Tool for checking authentication status."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.token_manager = get_token_manager()
        self.session_manager = get_session_manager()
    
    def print_banner(self):
        """Print banner."""
        print("=" * 50)
        print("🔍 Codex2API Authentication Status")
        print("=" * 50)
    
    async def check_tokens(self):
        """Check stored tokens."""
        print("\n📋 Token Status:")
        print("-" * 30)
        
        users = self.token_manager.list_users()
        
        if not users:
            print("❌ No tokens found.")
            print("   Run 'python scripts/setup_auth.py' to set up authentication.")
            return False
        
        print(f"✅ Found tokens for {len(users)} user(s):")
        
        valid_users = 0
        for user_id in users:
            print(f"\n👤 User: {user_id}")
            
            try:
                # Get tokens
                auth_bundle = self.token_manager.get_tokens(user_id)
                if not auth_bundle:
                    print("   ❌ No auth bundle found")
                    continue
                
                # Check if tokens need refresh
                needs_refresh = self.token_manager._needs_refresh(auth_bundle)
                
                print(f"   📅 Last refresh: {auth_bundle.last_refresh}")
                print(f"   🔄 Needs refresh: {'Yes' if needs_refresh else 'No'}")
                
                # Try to get valid tokens (will refresh if needed)
                valid_bundle = await self.token_manager.get_valid_tokens(user_id)
                if valid_bundle:
                    print("   ✅ Tokens are valid")
                    valid_users += 1
                    
                    # Show token info (masked)
                    access_token = valid_bundle.token_data.access_token
                    refresh_token = valid_bundle.token_data.refresh_token
                    
                    print(f"   🔑 Access token: {access_token[:20]}...{access_token[-10:]}")
                    print(f"   🔄 Refresh token: {'Available' if refresh_token else 'Not available'}")
                    
                    if valid_bundle.api_key:
                        api_key = valid_bundle.api_key
                        print(f"   🗝️  API key: {api_key[:20]}...{api_key[-10:]}")
                else:
                    print("   ❌ Failed to get valid tokens")
                    
            except Exception as e:
                print(f"   ❌ Error checking tokens: {str(e)}")
        
        return valid_users > 0
    
    def check_sessions(self):
        """Check active sessions."""
        print("\n📋 Session Status:")
        print("-" * 30)
        
        try:
            stats = self.session_manager.get_session_stats()
            
            print(f"📊 Session Statistics:")
            print(f"   Total sessions: {stats['total_sessions']}")
            print(f"   Active sessions: {stats['active_sessions']}")
            print(f"   Expired sessions: {stats['expired_sessions']}")
            print(f"   Unique users: {stats['unique_users']}")
            
            if stats['active_sessions'] > 0:
                print(f"   Oldest session: {stats['oldest_session']}")
                print(f"   Newest session: {stats['newest_session']}")
            
            # Clean up expired sessions
            expired_count = self.session_manager.cleanup_expired_sessions()
            if expired_count > 0:
                print(f"🧹 Cleaned up {expired_count} expired sessions")
                
        except Exception as e:
            print(f"❌ Error checking sessions: {str(e)}")
    
    def show_usage_tips(self):
        """Show usage tips."""
        print("\n💡 Usage Tips:")
        print("-" * 30)
        print("1. Start the server:")
        print("   python -m codex2api.main")
        print()
        print("2. Test with curl:")
        print("   curl http://localhost:8000/health")
        print()
        print("3. Check API documentation:")
        print("   http://localhost:8000/docs")
        print()
        print("4. Re-run authentication setup:")
        print("   python scripts/setup_auth.py")
        print()
        print("5. Check logs:")
        print("   tail -f data/logs/codex2api.log")
    
    async def run(self):
        """Run the authentication check."""
        try:
            self.print_banner()
            
            # Check tokens
            has_valid_tokens = await self.check_tokens()
            
            # Check sessions
            self.check_sessions()
            
            # Show usage tips
            self.show_usage_tips()
            
            if has_valid_tokens:
                print("\n🎉 Authentication is ready!")
                print("   You can start using the Codex2API server.")
            else:
                print("\n⚠️  No valid authentication found.")
                print("   Please run 'python scripts/setup_auth.py' first.")
                
        except Exception as e:
            print(f"\n❌ Check failed: {str(e)}")
            self.logger.error("Auth check failed", error=str(e))


async def main():
    """Main entry point."""
    # Setup logging
    setup_logging()
    
    # Run checker
    checker = AuthChecker()
    await checker.run()


if __name__ == "__main__":
    asyncio.run(main())
