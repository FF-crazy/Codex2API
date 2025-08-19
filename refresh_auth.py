#!/usr/bin/env python3
"""
Script to help refresh authentication tokens.
"""

import json
import os
from datetime import datetime

def check_auth_status():
    """Check current authentication status."""
    auth_paths = [
        "auth.json",
        os.path.expanduser("~/.chatgpt-local/auth.json"),
        os.path.expanduser("~/.codex/auth.json"),
    ]
    
    for path in auth_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                auth = json.load(f)
                tokens = auth.get("tokens", {})
                last_refresh = auth.get("last_refresh", "unknown")
                
                print(f"📁 Auth file: {path}")
                print(f"🔑 Access token: {'✅ Present' if tokens.get('access_token') else '❌ Missing'}")
                print(f"👤 Account ID: {tokens.get('account_id', 'missing')}")
                print(f"🕒 Last refresh: {last_refresh}")
                
                # Check if token might be expired (older than 1 hour)
                try:
                    if last_refresh != "unknown":
                        refresh_time = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
                        now = datetime.now(refresh_time.tzinfo)
                        age = now - refresh_time
                        print(f"⏰ Token age: {age}")
                        
                        if age.total_seconds() > 3600:  # 1 hour
                            print("⚠️  Token might be expired (older than 1 hour)")
                        else:
                            print("✅ Token seems fresh")
                except Exception as e:
                    print(f"❓ Could not parse refresh time: {e}")
                
                return True
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"❌ Error reading {path}: {e}")
            continue
    
    print("❌ No valid auth file found")
    return False

def main():
    """Main function."""
    print("🔍 Checking authentication status...")
    print()
    
    if not check_auth_status():
        print()
        print("💡 To fix authentication issues:")
        print("1. Make sure you have a valid ChatGPT Plus/Pro account")
        print("2. Use the original ChatMock project to re-authenticate:")
        print("   - Run the original chatmock.py")
        print("   - Complete the OAuth flow")
        print("   - Copy the generated auth.json to this project")
        print("3. Or manually update the auth.json file with fresh tokens")
        return
    
    print()
    print("💡 If you're getting 403 errors:")
    print("1. The access token might be expired - re-authenticate")
    print("2. ChatGPT might be detecting automated requests")
    print("3. Try using a different User-Agent or request headers")
    print("4. Check if your ChatGPT account is still active")

if __name__ == "__main__":
    main()
