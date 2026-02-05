from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urlencode

import aiohttp

from .types import (
    ApiResponse,
    UserPublic,
    Chat,
    ChatMember,
    ChatPreview,
    Message,
    MessageAttachment,
    MessageReaction,
)
from .config import ClientConfig, resolve_api_url


@dataclass
class GetMessagesQuery:
    limit: Optional[int] = None
    before_id: Optional[int] = None
    after_id: Optional[int] = None


class HttpClient:
    """HTTP client for the Pigeon API."""

    def __init__(self, config: ClientConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return {"Authorization": f"Bot {self.config.token}"}

    async def _ensure_session(self):
        """Ensure a session exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        body: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an HTTP request to the API."""
        await self._ensure_session()
        url = resolve_api_url(self.config, path)
        
        if params:
            query_string = urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}?{query_string}"

        headers = {"Content-Type": "application/json", **self._auth_headers()}

        async with self._session.request(
            method,
            url,
            headers=headers,
            json={"data": body} if body is not None else None,
        ) as response:
            if response.status == 204:
                return None

            response_data = await response.json()
            api_response = ApiResponse(**response_data)

            if api_response.error:
                raise Exception(api_response.error.message or "Request failed")

            if not response.ok:
                raise Exception(f"HTTP {response.status}: {response.reason}")

            return api_response.data

    # ========== USERS ==========
    async def get_user(self, id: int) -> UserPublic:
        """Get user by ID."""
        data = await self._request("GET", f"/users/{id}")
        return UserPublic(**data)

    async def get_me(self) -> UserPublic:
        """Get the current bot user."""
        data = await self._request("GET", "/users/me")
        return UserPublic(**data)

    # ========== CHATS ==========
    async def get_chat(self, id: int) -> Chat:
        """Get chat by ID."""
        data = await self._request("GET", f"/chats/{id}")
        if data.get("members"):
            data["members"] = [ChatMember(**member) for member in data["members"]]
        return Chat(**data)

    async def get_my_chats(self) -> List[ChatPreview]:
        """Get all chats for the current user."""
        data = await self._request("GET", "/chats")
        chats = []
        for chat in data:
            chat_data = dict(chat)
            
            if chat_data.get("last_message"):
                chat_data["last_message"] = self._deserialize_message(chat_data["last_message"])
            
            if chat_data.get("last_user"):
                chat_data["last_user"] = UserPublic(**chat_data["last_user"])
            
            if chat_data.get("other_user"):
                chat_data["other_user"] = UserPublic(**chat_data["other_user"])
            
            chats.append(ChatPreview(**chat_data))
        return chats

    async def get_chat_members(self, chat_id: int) -> List[ChatMember]:
        """Get members of a chat."""
        data = await self._request("GET", f"/chats/{chat_id}/members")
        return [ChatMember(**member) for member in data]

    async def remove_member(self, chat_id: int, user_id: int) -> None:
        """Remove a member from a chat."""
        await self._request("DELETE", f"/chats/{chat_id}/members/{user_id}")

    # ========== MESSAGES ==========
    def _deserialize_message(self, message_dict: Dict[str, Any]) -> Message:
        """Deserialize a message dictionary to Message object."""
        msg_data = dict(message_dict)
        
        if msg_data.get("attachments"):
            msg_data["attachments"] = [
                MessageAttachment(**attachment) for attachment in msg_data["attachments"]
            ]
        
        if msg_data.get("reactions"):
            msg_data["reactions"] = [
                MessageReaction(**reaction) for reaction in msg_data["reactions"]
            ]
        
        return Message(**msg_data)

    async def get_messages(
        self, chat_id: int, query: Optional[GetMessagesQuery] = None
    ) -> List[Message]:
        """Get messages from a chat."""
        await self._ensure_session()
        
        if query is None:
            query = GetMessagesQuery()

        params = {}
        if query.limit is not None:
            params["limit"] = query.limit
        if query.before_id is not None:
            params["before_id"] = query.before_id
        if query.after_id is not None:
            params["after_id"] = query.after_id

        url = resolve_api_url(self.config, f"/chats/{chat_id}/messages")
        
        async with self._session.get(
            url, headers=self._auth_headers(), params=params
        ) as response:
            response_data = await response.json()
            api_response = ApiResponse(**response_data)

            if api_response.error:
                raise Exception(api_response.error.message or "Request failed")
            if not response.ok:
                raise Exception(f"HTTP {response.status}: {response.reason}")

            messages = []
            for msg in (api_response.data or []):
                messages.append(self._deserialize_message(msg))
            return messages

    # ========== ATTACHMENTS ==========
    async def upload_attachment(
        self, chat_id: int, form_data: aiohttp.FormData
    ) -> MessageAttachment:
        """Upload an attachment to a chat."""
        await self._ensure_session()
        url = resolve_api_url(self.config, f"/chats/{chat_id}/attachments")

        async with self._session.post(
            url, headers=self._auth_headers(), data=form_data
        ) as response:
            response_data = await response.json()
            api_response = ApiResponse(**response_data)

            if api_response.error:
                raise Exception(api_response.error.message or "Upload failed")
            if not response.ok:
                raise Exception(f"HTTP {response.status}: {response.reason}")

            return MessageAttachment(**api_response.data)