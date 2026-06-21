import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",   # points to app/main.py → app object
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=True,      # auto-restart on code changes (dev only)
    )
