# server.py
import contextlib
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware

from mcp.server.fastmcp import FastMCP
from tools.wikipedia import search_wikipedia
from prompts.greeting import greet_user

# ---- MCP server ----
mcp = FastMCP("Demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool()
def wikipedia_search(query: str) -> list[str]:
    """Search Wikipedia for articles matching the query."""
    return search_wikipedia(query)

@mcp.prompt()
def greet_user_prompt(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt for someone."""
    return greet_user(name, style)

# ---- Lifespan: start/stop MCP session manager ----
@asynccontextmanager
async def mcp_lifespan(_app):
    async with contextlib.AsyncExitStack() as stack:
        # This is the key bit you were missing:
        await stack.enter_async_context(mcp.session_manager.run())
        yield  # app is live
        # exit stack will shut it down cleanly

# Optional: health endpoint for probes
async def healthz(_req):
    return JSONResponse({"status": "ok"})

# ---- Parent Starlette app with MCP mounted ----
app = Starlette(
    lifespan=mcp_lifespan,  # << wire in the MCP lifespan
    routes=[
        Route("/healthz", endpoint=healthz),
        # Mount at "/" if you want MCP at root; otherwise use "/mcp"
        Mount("/", app=mcp.streamable_http_app()),
        Mount("/mcp", app=mcp.streamable_http_app()),  # alt path
    ],
)

# Add CORS middleware - must be added AFTER app creation but order matters
app = CORSMiddleware(
    app=app,
    allow_origins=["*"],  # In production, specify the Inspector's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id", "content-type"],
)