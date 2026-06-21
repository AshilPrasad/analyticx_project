"""
run.py — Start the FastAPI server with Uvicorn.

Usage:
    python run.py
    python run.py --port 8080

This is the entry point for running the app locally.
In production, the platform (Render/Railway) runs uvicorn directly.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",   # points to app/main.py → app object
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=True,      # auto-restart on code changes (dev only)
    )
