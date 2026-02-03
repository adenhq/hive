#!/usr/bin/env python3
"""
Aden Tools MCP Server

Exposes all tools via Model Context Protocol using FastMCP.

Usage:
    # Run with HTTP transport (requires authentication)
    export MCP_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
    python mcp_server.py

    # Run with custom port
    python mcp_server.py --port 8001

    # Run with STDIO transport (for local testing, no auth required)
    python mcp_server.py --stdio

Environment Variables:
    MCP_PORT              - Server port (default: 4001)
    MCP_API_KEY           - Required for HTTP mode (generate with secrets.token_urlsafe(32))
    ANTHROPIC_API_KEY     - Required at startup for testing/LLM nodes
    BRAVE_SEARCH_API_KEY  - Required for web_search tool (validated at agent load time)

Security:
    HTTP mode requires API key authentication via MCP_API_KEY environment variable.
    STDIO mode runs without authentication (single-process, no network exposure).
"""
import argparse
import os
import sys
import secrets

# Suppress FastMCP banner in STDIO mode
if "--stdio" in sys.argv:
    # Monkey-patch rich Console to redirect to stderr
    import rich.console
    _original_console_init = rich.console.Console.__init__

    def _patched_console_init(self, *args, **kwargs):
        kwargs['file'] = sys.stderr  # Force all rich output to stderr
        _original_console_init(self, *args, **kwargs)

    rich.console.Console.__init__ = _patched_console_init

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from aden_tools.credentials import CredentialManager, CredentialError
from aden_tools.tools import register_all_tools


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce API key authentication for HTTP mode."""
    
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key
    
    async def dispatch(self, request: Request, call_next):
        # Allow health check and root without auth
        if request.url.path in ["/health", "/"]:
            return await call_next(request)
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {
                    "error": "Unauthorized",
                    "message": "Missing or invalid Authorization header. Use: Authorization: Bearer <MCP_API_KEY>"
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        provided_key = auth_header[7:]  # Remove "Bearer " prefix
        
        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_key, self.api_key):
            return JSONResponse(
                {
                    "error": "Forbidden",
                    "message": "Invalid API key"
                },
                status_code=403
            )
        
        # Authentication successful
        return await call_next(request)


# Create credential manager
credentials = CredentialManager()

# Tier 1: Validate startup-required credentials (if any)
try:
    credentials.validate_startup()
    print("[MCP] Startup credentials validated")
except CredentialError as e:
    # Non-fatal - tools will validate their own credentials when called
    print(f"[MCP] Warning: {e}", file=sys.stderr)

mcp = FastMCP("tools")

# Register all tools with the MCP server, passing credential manager
tools = register_all_tools(mcp, credentials=credentials)
# Only print to stdout in HTTP mode (STDIO mode requires clean stdout for JSON-RPC)
if "--stdio" not in sys.argv:
    print(f"[MCP] Registered {len(tools)} tools: {tools}")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """Health check endpoint for container orchestration."""
    return PlainTextResponse("OK")


@mcp.custom_route("/", methods=["GET"])
async def index(request: Request) -> PlainTextResponse:
    """Landing page for browser visits."""
    return PlainTextResponse("Aden MCP Server - Authentication Required")


def main() -> None:
    """Entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="Aden Tools MCP Server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "4001")),
        help="HTTP server port (default: 4001)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",  # ✅ Localhost by default for security
        help="HTTP server host (default: 127.0.0.1 for security)",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Use STDIO transport instead of HTTP (no authentication required)",
    )
    args = parser.parse_args()

    if args.stdio:
        # STDIO mode: only JSON-RPC messages go to stdout
        print("[MCP] Starting STDIO mode (no authentication required)", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        # HTTP mode: require API key authentication
        api_key = os.getenv("MCP_API_KEY")
        
        if not api_key:
            print("[MCP] ERROR: MCP_API_KEY environment variable required for HTTP mode", file=sys.stderr)
            print("", file=sys.stderr)
            print("Generate a secure API key with:", file=sys.stderr)
            print("  export MCP_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')", file=sys.stderr)
            print("", file=sys.stderr)
            print("Then start the server:", file=sys.stderr)
            print("  python tools/mcp_server.py", file=sys.stderr)
            print("", file=sys.stderr)
            print("Clients must authenticate with:", file=sys.stderr)
            print("  Authorization: Bearer $MCP_API_KEY", file=sys.stderr)
            print("", file=sys.stderr)
            print("For local development without authentication, use STDIO mode:", file=sys.stderr)
            print("  python tools/mcp_server.py --stdio", file=sys.stderr)
            sys.exit(1)
        
        # Validate API key strength (minimum 32 characters)
        if len(api_key) < 32:
            print("[MCP] WARNING: MCP_API_KEY is too short (< 32 characters)", file=sys.stderr)
            print("[MCP] Generate a stronger key with:", file=sys.stderr)
            print("  export MCP_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')", file=sys.stderr)
            print("", file=sys.stderr)
        
        # Warn if binding to 0.0.0.0
        if args.host == "0.0.0.0":
            print("[MCP] WARNING: Binding to 0.0.0.0 exposes server to network", file=sys.stderr)
            print("[MCP] Ensure firewall rules are properly configured", file=sys.stderr)
            print("[MCP] For local development, use --host 127.0.0.1", file=sys.stderr)
            print("", file=sys.stderr)
        
        print(f"[MCP] Starting HTTP server on {args.host}:{args.port}")
        print("[MCP] Authentication: API Key required (MCP_API_KEY)")
        
        # Add authentication middleware
        middleware = [
            Middleware(APIKeyAuthMiddleware, api_key=api_key)
        ]
        
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            middleware=middleware
        )


if __name__ == "__main__":
    main()
