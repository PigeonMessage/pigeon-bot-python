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
    MessageAttachment,
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
        self._wrappers_setup = False
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

    async def get_messages(
        self, chat_id: int, query: Optional[GetMessagesQuery] = None
    ) -> List[Message]:
        """Get messages from a chat."""
        return await self.http.get_messages(chat_id, query)

    async def upload_attachment(
        self, chat_id: int, form_data
    ) -> MessageAttachment:
        """Upload an attachment to a chat."""
        return await self.http.upload_attachment(chat_id, form_data)

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
        attachment_ids: Optional[List[int]] = None,
    ) -> None:
        """Send a message."""
        await self.ws.send_message(chat_id, content, reply_to, attachment_ids)

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
            from .types import UserPublic as UserPublicType
            user_data = UserPublicType(**user_data)
        return UserEntity(self, user_data)

    def create_chat_entity(self, chat_data: Union[Chat, ChatPreview, Dict[str, Any]]) -> ChatEntity:
        """Create a ChatEntity from chat data."""
        if isinstance(chat_data, dict):
            if "members" in chat_data:
                from .types import Chat as ChatType
                chat_data = ChatType(**chat_data)
            else:
                from .types import ChatPreview as ChatPreviewType
                chat_data = ChatPreviewType(**chat_data)
        return ChatEntity(self, chat_data)

    # ========== ENHANCED EVENT HANDLING ==========
    async def _setup_message_entity_wrapping(self):
        """Set up automatic wrapping of message data in MessageEntity."""
        if self._wrappers_setup:
            return

        async def message_wrapper(message_data, raw_data):
            message_entity = self.create_message_entity(message_data)
            self.ws.events.emit("new_message_entity", message_entity, raw_data)

        self.ws.events.on("new_message")(message_wrapper)

        async def edited_message_wrapper(message_data, raw_data):
            message_entity = self.create_message_entity(message_data)
            self.ws.events.emit("message_edited_entity", message_entity, raw_data)

        self.ws.events.on("message_edited")(edited_message_wrapper)
        
        self._wrappers_setup = True

    async def start(self) -> None:
        """Start the client and set up enhanced features."""
        await self._setup_message_entity_wrapping()
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