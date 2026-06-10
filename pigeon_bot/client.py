import asyncio
from typing import Optional, List, Callable, Any, Dict, Union

from .config import ClientConfig
from .http import HttpClient, GetMessagesQuery
from .websocket import WebSocketClient
from .types import (
    UserPublic,
    Chat,
    ChatMember,
    ChatPreview,
    Message,
    MessageMedia,
)
from .entities import MessageEntity, UserEntity, ChatEntity


class PigeonClient:
    """Main client for interacting with Pigeon Messenger."""

    def __init__(self, config: ClientConfig):
        if not config.token:
            raise ValueError("Bot token is required")
        self.config = config
        self.http = HttpClient(config)
        self.ws = WebSocketClient(config)
        self.ws._client = self
        self._closed = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self.ws.connected

    @property
    def authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self.ws.authenticated

    # ========== HTTP METHODS ==========
    async def get_user(self, id: int) -> UserPublic:
        """Get user by ID."""
        return await self.http.get_user(id)

    async def get_me(self) -> UserPublic:
        """Get the current bot user."""
        return await self.http.get_me()

    async def get_chat(self, id: int) -> Chat:
        """Get chat by ID."""
        return await self.http.get_chat(id)

    async def get_my_chats(self) -> List[ChatPreview]:
        """Get all chats for the current user."""
        return await self.http.get_my_chats()

    async def get_chat_members(self, chat_id: int) -> List[ChatMember]:
        """Get members of a chat."""
        return await self.http.get_chat_members(chat_id)

    async def update_member_permissions(
        self,
        chat_id: int,
        user_id: int,
        *,
        role: Optional[str] = None,
        can_send_messages: Optional[bool] = None,
        can_manage_messages: Optional[bool] = None,
        can_manage_members: Optional[bool] = None,
        can_manage_chat: Optional[bool] = None,
    ) -> None:
        """Update permissions of a member."""
        await self.http.update_member_permissions(
            chat_id, user_id,
            role=role,
            can_send_messages=can_send_messages,
            can_manage_messages=can_manage_messages,
            can_manage_members=can_manage_members,
            can_manage_chat=can_manage_chat,
        )

    async def get_messages(
        self, chat_id: int, query: Optional[GetMessagesQuery] = None
    ) -> List[Message]:
        """Get messages from a chat."""
        return await self.http.get_messages(chat_id, query)

    async def upload_media(self, chat_id: int, form_data) -> MessageMedia:
        """Upload a media to a chat."""
        return await self.http.upload_media(chat_id, form_data)

    async def remove_member(self, chat_id: int, user_id: int) -> None:
        """Remove a member from a chat."""
        await self.http.remove_member(chat_id, user_id)

    # ========== WEBSOCKET METHODS ==========
    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        await self.ws.connect()

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        await self.ws.disconnect()

    async def send_message(
        self,
        chat_id: int,
        content: str,
        reply_to: Optional[int] = None,
        media: Optional[List[MessageMedia]] = None,
    ) -> None:
        """Send a message."""
        await self.ws.send_message(chat_id, content, reply_to, media)

    async def edit_message(self, message_id: int, content: str) -> None:
        """Edit a message."""
        await self.ws.edit_message(message_id, content)

    async def delete_message(self, message_id: int) -> None:
        """Delete a message."""
        await self.ws.delete_message(message_id)

    async def add_reaction(self, message_id: int, emoji: str) -> None:
        """Add a reaction to a message."""
        await self.ws.add_reaction(message_id, emoji)

    async def remove_reaction(self, message_id: int, emoji: str) -> None:
        """Remove a reaction from a message."""
        await self.ws.remove_reaction(message_id, emoji)

    async def set_typing(self, chat_id: int, is_typing: bool = True) -> None:
        """Set typing status."""
        await self.ws.set_typing(chat_id, is_typing)

    async def get_online_list(self) -> List[dict]:
        """Get the list of online users."""
        return await self.ws.get_online_list()

    # ========== EVENT HANDLING ==========
    def on_event(self, event_name: str):
        """Decorator to register event handlers."""
        def decorator(func: Callable):
            self.ws.events.on(event_name)(func)
            return func
        return decorator

    def add_event_listener(self, event_name: str, handler: Callable) -> None:
        """Add an event listener."""
        self.ws.events.on(event_name)(handler)

    def remove_event_listener(self, event_name: str, handler: Callable) -> None:
        """Remove an event listener."""
        self.ws.events.remove_listener(event_name, handler)

    def remove_all_event_listeners(self, event_name: Optional[str] = None) -> None:
        """Remove all event listeners."""
        self.ws.events.remove_all_listeners(event_name)

    # ========== CONVENIENCE METHODS ==========
    def create_message_entity(self, message_data: Union[Message, Dict[str, Any]]) -> MessageEntity:
        """Create a MessageEntity from message data."""
        if isinstance(message_data, dict):
            from .types import Message as MessageType
            message_data = MessageType(**message_data)
        return MessageEntity(self, message_data)

    def create_user_entity(self, user_data: Union[UserPublic, Dict[str, Any]]) -> UserEntity:
        """Create a UserEntity from user data."""
        if isinstance(user_data, dict):
            user_data = UserPublic(**user_data)
        return UserEntity(self, user_data)

    def create_chat_entity(self, chat_data: Union[Chat, ChatPreview, Dict[str, Any]]) -> ChatEntity:
        """Create a ChatEntity from chat data."""
        if isinstance(chat_data, dict):
            if "members" in chat_data:
                chat_data = Chat(**chat_data)
            else:
                chat_data = ChatPreview(**chat_data)
        return ChatEntity(self, chat_data)

    async def start(self) -> None:
        """Start the client and connect."""
        await self.connect()

    async def close(self) -> None:
        """Close the client and clean up resources."""
        if self._closed:
            return
        try:
            await self.disconnect()
        except Exception:
            pass
        try:
            await self.http.close()
        except Exception:
            pass
        self._closed = True