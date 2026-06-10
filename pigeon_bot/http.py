from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode

import aiohttp

from .types import (
    ApiResponse,
    UserPublic,
    Chat,
    ChatMember,
    ChatPreview,
    Message,
    MessageMedia,
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
            qs = urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}?{qs}"

        headers = {"Content-Type": "application/json", **self._auth_headers()}
        async with self._session.request(
            method,
            url,
            headers=headers,
            json={"data": body} if body is not None else None,
        ) as response:
            if response.status == 204:
                return None
            resp_json = await response.json()

            error_msg = None
            if "error" in resp_json:
                err = resp_json["error"]
                if isinstance(err, dict):
                    error_msg = err.get("message", str(err))
                elif isinstance(err, str):
                    error_msg = err
                else:
                    error_msg = str(err)

            if error_msg:
                raise Exception(error_msg)

            if resp_json.get("success") is False:
                msg = resp_json.get("message", "Request failed")
                raise Exception(msg)

            if not response.ok:
                raise Exception(f"HTTP {response.status}: {response.reason}")

            return resp_json.get("data")

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
            data["members"] = [ChatMember(**m) for m in data["members"]]
        return Chat(**data)

    async def get_chat_members(self, chat_id: int) -> List[ChatMember]:
        data = await self._request("GET", f"/chats/{chat_id}/members")
        return [ChatMember(**m) for m in data]

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
        body = {}
        if role is not None:
            body["role"] = role
        if can_send_messages is not None:
            body["can_send_messages"] = can_send_messages
        if can_manage_messages is not None:
            body["can_manage_messages"] = can_manage_messages
        if can_manage_members is not None:
            body["can_manage_members"] = can_manage_members
        if can_manage_chat is not None:
            body["can_manage_chat"] = can_manage_chat
        await self._request("PUT", f"/chats/{chat_id}/members/{user_id}", body=body)

    async def remove_member(self, chat_id: int, user_id: int) -> None:
        """Remove member from the chat."""
        await self._request("DELETE", f"/chats/{chat_id}/members/{user_id}")

    # ========== MESSAGES ==========
    def _deserialize_media(self, media_dict: Dict[str, Any]) -> MessageMedia:
        """Convert media dict to corresponding dataclass based on 'type' field."""
        t = media_dict.get("type")
        if t == "Photo":
            return PhotoMedia(**media_dict)
        elif t == "Document":
            return DocumentMedia(**media_dict)
        elif t == "Video":
            return VideoMedia(**media_dict)
        elif t == "Audio":
            return AudioMedia(**media_dict)
        elif t == "Voice":
            return VoiceMedia(**media_dict)
        elif t == "Gif":
            return GifMedia(**media_dict)
        elif t == "Sticker":
            return StickerMedia(**media_dict)
        elif t == "Geo":
            return GeoMedia(**media_dict)
        elif t == "Contact":
            return ContactMedia(**media_dict)
        elif t == "Poll":
            if "options" in media_dict:
                opts = media_dict["options"]
                if isinstance(opts, list):
                    media_dict["options"] = [PollOption(**opt) if isinstance(opt, dict) else opt for opt in opts]
            return PollMedia(**media_dict)
        else:
            return media_dict

    def _deserialize_message(self, msg_dict: Dict[str, Any]) -> Message:
        md = dict(msg_dict)
        if md.get("media"):
            media_list = md["media"]
            if isinstance(media_list, list):
                md["media"] = [self._deserialize_media(m) for m in media_list]
        if md.get("reactions"):
            md["reactions"] = [MessageReaction(**r) for r in md["reactions"]]
        if md.get("new_chat_members"):
            md["new_chat_members"] = [UserPublic(**u) for u in md["new_chat_members"]]
        if md.get("left_chat_member"):
            md["left_chat_member"] = UserPublic(**md["left_chat_member"])
        if md.get("pinned_message"):
            md["pinned_message"] = self._deserialize_message(md["pinned_message"])
        return Message(**md)

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
        async with self._session.get(url, headers=self._auth_headers(), params=params) as resp:
            resp_json = await resp.json()
            api_resp = ApiResponse(**resp_json)
            if api_resp.error:
                raise Exception(api_resp.error.message or "Request failed")
            if not resp.ok:
                raise Exception(f"HTTP {resp.status}: {resp.reason}")
            messages = []
            for m in (api_resp.data or []):
                messages.append(self._deserialize_message(m))
            return messages

    async def upload_media(self, chat_id: int, form_data: aiohttp.FormData) -> MessageMedia:
        """Upload media to the chat."""
        await self._ensure_session()
        url = resolve_api_url(self.config, f"/chats/{chat_id}/upload")
        async with self._session.post(url, headers=self._auth_headers(), data=form_data) as resp:
            resp_json = await resp.json()
            api_resp = ApiResponse(**resp_json)
            if api_resp.error:
                raise Exception(api_resp.error.message or "Upload failed")
            if not resp.ok:
                raise Exception(f"HTTP {resp.status}: {resp.reason}")
            return api_resp.data