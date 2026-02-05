from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass
class ClientConfig:
    """
    Configuration for the Pigeon client.
    """
    token: str
    base_url: Optional[str] = None
    ws_url: Optional[str] = None
    auto_reconnect: bool = True
    reconnect_interval_ms: int = 5000


DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_API_PREFIX = "/api/v1"
DEFAULT_WS_PATH = "/ws"


def resolve_base_url(config: ClientConfig) -> str:
    """Resolve the base URL from config."""
    return (config.base_url or DEFAULT_BASE_URL).rstrip("/")


def resolve_api_url(config: ClientConfig, path: str) -> str:
    """Resolve the full API URL for a given path."""
    base = resolve_base_url(config)
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base}{DEFAULT_API_PREFIX}{normalized_path}"


def resolve_ws_url(config: ClientConfig) -> str:
    """Resolve the WebSocket URL from config."""
    if config.ws_url:
        return config.ws_url
    
    http_base = resolve_base_url(config)
    parsed = urlparse(http_base)
    protocol = "wss" if parsed.scheme == "https" else "ws"
    origin = f"{protocol}://{parsed.netloc}"
    return f"{origin}{DEFAULT_WS_PATH}"