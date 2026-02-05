from .client import PigeonClient as Client
from .types import *
from .config import *
from .http import *
from .entities import *

__version__ = "0.1.0"
__all__ = [
    "Client",
    "ApiError",
    "ApiResponse",
    "UserPublic",
    "ChatType",
    "ChatMember",
    "Chat",
    "ChatPreview",
    "MessageAttachment",
    "MessageReaction",
    "Message",
    "WsMessageType",
    "WsEnvelope",
    "WsAuthenticatedData",
    "WsErrorData",
    "WsOnlineListUser",
    "WsOnlineListData",
    "ClientConfig",
    "DEFAULT_BASE_URL",
    "DEFAULT_API_PREFIX",
    "DEFAULT_WS_PATH",
    "resolve_base_url",
    "resolve_api_url",
    "resolve_ws_url",
    "HttpClient",
    "GetMessagesQuery",
    "BaseEntity",
    "MessageEntity",
    "UserEntity",
    "ChatEntity",
]