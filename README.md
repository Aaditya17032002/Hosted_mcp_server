# Hosted MCP Server (FastMCP + Render)

This folder contains a lightweight MCP server built with **FastMCP** for HTTP/SSE
transport. It is configured to deploy on Render using Python 3.11.

## Features
- Tools: `calculator`, `echo`, `server_status`
- Resource: `file://{relative_path}` reads files inside the `data/` directory
- Prompt: `greeting`
- HTTP routes: `/health` for uptime checks
- SSE transport paths aligned with `runtime.transport.http_sse.HttpSSETransport`

## Local setup
```bash
cd hosted_mcp_server
python -m venv .venv
. .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

The server listens on `http://0.0.0.0:8000` by default. Update ports via `PORT`.

## Render deployment
The root `render.yaml` blueprint is preconfigured:
- Build: `pip install -r requirements.txt`
- Start: `python main.py`
- Paths: `FASTMCP_MESSAGE_PATH=/message`, `FASTMCP_SSE_PATH=/sse`

Steps:
1. Push this repo to GitHub.
2. In Render, create a new **Web Service** from the repo and select the blueprint.
3. Confirm environment `python` and **Python 3.11** runtime.
4. Deploy. Health check: `https://<service>.onrender.com/health`.

## Using with mcp-runtime
```python
from runtime.runtime import MCPRuntime
from runtime.adapter.gemini import GeminiAdapter
from runtime.transport.http_sse import HttpSSETransport

transport = HttpSSETransport("https://<service>.onrender.com")
adapter = GeminiAdapter()
runtime = MCPRuntime(transport, adapter)
await runtime.start({"name": "runtime-http-demo", "version": "1.0.0"})
```

Ensure the base URL matches your Render service; the transport automatically uses
`/message` and `/sse`.

## Notes
- Data files live in `./data` (auto-created with `hello.txt`).
- To change server identity, set `MCP_SERVER_NAME` / `MCP_SERVER_VERSION`.
- Keep paths inside `data/`—the resource blocks access outside that directory.

