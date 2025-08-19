#!/usr/bin/env python3
"""
Main entry point for Codex2API server.
"""

import os
import uvicorn
from dotenv import load_dotenv
from codex2api.server import create_app

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print(f"🚀 Starting Codex2API server on {host}:{port}")
    print(f"📖 API documentation available at http://{host}:{port}/docs")
    print(f"🔧 Environment variables loaded from .env file")

    # Create and run the app
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=True)
