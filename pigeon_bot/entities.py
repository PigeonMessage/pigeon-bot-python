from abc import ABC
from typing import TYPE_CHECKING, List, Optional, Union

from .types import (
    UserPublic,
    Message,
    Chat,
    ChatPreview,
    ChatMember,
    MessageMedia,
    MessageReaction,
)

if TYPE_CHECKING:
    from .client import PigeonClient


class BaseEntity(ABC):
    """Base class for all entity classes."""

    def __init__(self, client: "PigeonClient"):
        self.client = client


class MessageEntity(BaseEntity):
    """Entity representing a message."""

    def __init__(self, client: "PigeonClient", data: Message):
        super().__init__(client)
        self._data = data

    @property
    def data(self) -> Message:
        """Get the raw message data."""
        return self._data

    @property
    def id(self) -> int:
        """Get the message ID."""
        return self._data.id

    @property
    def chat_id(self) -> int:
        """Get the chat ID."""
        return self._data.chat_id

    @property
    def sender_id(self) -> int:
        """Get the sender ID."""
        return self._data.sender_id

    @property
    def content(self) -> str:
        """Get the message content."""
        return self._data.content

    @property
    def reply_to_message_id(self) -> Optional[int]:
        """Get the ID of the message this reply is to."""
        return self._data.reply_to_message_id

    @property
    def media(self) -> Optional[List[MessageMedia]]:
        """Get the message media."""
        return self._data.media

    @property
    def reactions(self) -> Optional[List[MessageReaction]]:
        """Get the message reactions."""
        return self._data.reactions

    async def edit(self, content: str) -> None:
        """Edit the message content."""
        await self.client.edit_message(self.id, content)
        self._data.content = content
        self._data.is_edited = True

    async def delete(self) -> None:
        """Delete the message."""
        await self.client.delete_message(self.id)

    async def add_reaction(self, emoji: str) -> None:
        """Add a reaction to the message."""
        await self.client.add_reaction(self.id, emoji)

    async def remove_reaction(self, emoji: str) -> None:
        """Remove a reaction from the message."""
        await self.client.remove_reaction(self.id, emoji)

    async def reply(
        self, content: str, media: Optional[List[MessageMedia]] = None
    ) -> None:
        """Reply to this message."""
        await self.client.send_message(self.chat_id, content, self.id, media)


class UserEntity(BaseEntity):
    """Entity representing a user."""

    def __init__(self, client: "PigeonClient", data: UserPublic):
        super().__init__(client)
        self._data = data

    @property
    def id(self) -> int:
        """Get the user ID."""
        return self._data.id

    @property
    def data(self) -> UserPublic:
        """Get the raw user data."""
        return self._data

    async def fetch(self) -> "UserEntity":
        """Fetch fresh user data from the API."""
        fresh = await self.client.get_user(self.id)
        self._data = fresh
        return self


class ChatEntity(BaseEntity):
    """Entity representing a chat."""

    def __init__(self, client: "PigeonClient", data: Union[Chat, ChatPreview]):
        super().__init__(client)
        self._data = data

    @property
    def id(self) -> int:
        """Get the chat ID."""
        return self._data.id

    @property
    def data(self) -> Union[Chat, ChatPreview]:
        """Get the raw chat data."""
        return self._data

    async def fetch_full(self) -> "ChatEntity":
        """Fetch full chat data from the API."""
        chat = await self.client.get_chat(self.id)
        self._data = chat
        return self

    async def fetch_members(self) -> List[ChatMember]:
        """Fetch chat members."""
        return await self.client.get_chat_members(self.id)

    async def fetch_messages(
        self,
        limit: Optional[int] = None,
        before_id: Optional[int] = None,
        after_id: Optional[int] = None,
    ) -> List[Message]:
        """Fetch messages from the chat."""
        from .http import GetMessagesQuery
        query = GetMessagesQuery(limit=limit, before_id=before_id, after_id=after_id)
        return await self.client.get_messages(self.id, query)

    async def send_message(
        self,
        content: str,
        reply_to: Optional[int] = None,
        media: Optional[List[MessageMedia]] = None,
    ) -> None:
        """Send a message to the chat."""
        await self.client.send_message(self.id, content, reply_to, media)

    async def remove_member(self, user_id: int) -> None:
        """Remove a member from the chat."""
        await self.client.remove_member(self.id, user_id)

    async def upload_media(self, form_data) -> MessageMedia:
        """Upload a media."""
        return await self.client.upload_media(self.id, form_data)
