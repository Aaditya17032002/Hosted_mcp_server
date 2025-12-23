"""
Hosted MCP server powered by FastMCP.

Designed for deployment on Render (or any Python 3.11 host) using HTTP/SSE
transport so it can be consumed by the mcp-runtime HttpSSETransport.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.context import Context
from starlette.requests import Request
from starlette.responses import JSONResponse

SERVER_NAME = os.getenv("MCP_SERVER_NAME", "Render Hosted MCP")
SERVER_VERSION = os.getenv("MCP_SERVER_VERSION", "1.0.0")
DATA_ROOT = Path(os.getenv("MCP_DATA_ROOT", "./data")).resolve()
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")


@asynccontextmanager
async def _lifespan(_: Context) -> Any:
    """FastMCP lifespan hook to prepare local data."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    sample = DATA_ROOT / "hello.txt"
    if not sample.exists():
        sample.write_text("Hello from the hosted MCP server!\n", encoding="utf-8")
    yield


mcp = FastMCP(
    name=SERVER_NAME,
    version=SERVER_VERSION,
    instructions=(
        "Provide safe utility tools for arithmetic, echoing text, simple status "
        "checks, and access to demo files. Never read outside the configured data "
        "directory."
    ),
    website_url="https://render.com/",
    lifespan=_lifespan,
)


def _ensure_data_root() -> None:
    """Create the data directory with a sample file if missing."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    sample = DATA_ROOT / "hello.txt"
    if not sample.exists():
        sample.write_text("Hello from the hosted MCP server!\n", encoding="utf-8")


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    """Lightweight health endpoint for Render/uptime checks."""
    return JSONResponse(
        {
            "status": "ok",
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "time": datetime.utcnow().isoformat() + "Z",
        }
    )


@mcp.tool()
def calculator(operation: str, a: float, b: float) -> dict[str, Any]:
    """Perform arithmetic on two numbers."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None,
    }

    if operation not in operations:
        return {"error": f"Unknown operation: {operation}", "result": None}

    try:
        result = operations[operation](a, b)
        return {"result": result, "operation": operation, "a": a, "b": b}
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": str(exc), "result": None}


@mcp.tool()
def echo(text: str, repeat: int = 1, uppercase: bool = False) -> dict[str, Any]:
    """Echo text with optional repetition and casing."""
    repeated_text = " ".join([text] * repeat)
    if uppercase:
        repeated_text = repeated_text.upper()
    return {"text": text, "repeated": repeated_text, "count": repeat}


@mcp.tool()
def server_status() -> dict[str, Any]:
    """Return basic server metadata for quick diagnostics."""
    return {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "data_root": str(DATA_ROOT),
        "time": datetime.utcnow().isoformat() + "Z",
    }


@mcp.resource("file://{relative_path}")
def read_local_file(relative_path: str) -> dict[str, Any]:
    """Read a file within the data directory."""
    _ensure_data_root()
    target = (DATA_ROOT / relative_path).resolve()

    if DATA_ROOT not in target.parents and target != DATA_ROOT:
        return {"error": "Access denied: path must be inside data root."}

    if not target.exists() or not target.is_file():
        return {"error": f"File not found: {relative_path}"}

    contents = target.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(target.relative_to(DATA_ROOT)),
        "size": len(contents),
        "contents": contents,
    }


@mcp.prompt()
def greeting(name: str, language: str = "en") -> list[dict[str, Any]]:
    """Return a simple greeting prompt."""
    greetings = {
        "en": f"Hello, {name}! How can I help you today?",
        "es": f"¡Hola, {name}! ¿Cómo puedo ayudarte hoy?",
        "fr": f"Bonjour, {name}! Comment puis-je vous aider aujourd'hui?",
    }
    message = greetings.get(language, greetings["en"])
    return [
        {
            "role": "user",
            "content": [{"type": "text", "text": message}],
        }
    ]


if __name__ == "__main__":
    # Configure SSE paths to match the runtime's HttpSSETransport defaults.
    # Paths can be overridden with FASTMCP_MESSAGE_PATH / FASTMCP_SSE_PATH env vars.
    message_path = os.getenv("FASTMCP_MESSAGE_PATH", "/message")
    sse_path = os.getenv("FASTMCP_SSE_PATH", "/sse")

    mcp._deprecated_settings.message_path = message_path  # type: ignore[attr-defined]
    mcp._deprecated_settings.sse_path = sse_path  # type: ignore[attr-defined]

    mcp.run(
        transport="sse",
        host=HOST,
        port=PORT,
        path=sse_path,
        json_response=False,
    )

