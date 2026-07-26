"""Entry point for the AML Analysis backend.

Usage::

    # Run the FastAPI development server
    python main.py

    # Or with uvicorn directly
    uvicorn app.api:app --reload
"""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
