from dataclasses import dataclass
from typing import Optional, List, Any, Union, Literal
from enum import Enum


@dataclass
class ApiError:
    code: int
    message: str


@dataclass
class ApiResponse:
    data: Optional[Any] = None
    error: Optional[ApiError] = None


@dataclass
class UserPublic:
    id: int
    username: str
    name: str
    is_bot: bool
    bio: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    last_seen_at: Optional[str]


ChatType = Literal["DM", "GROUP", "CHANNEL"]


@dataclass
class ChatMember:
    chat_id: int
    user_id: int
    role: str
    custom_nickname: Optional[str]
    can_send_messages: bool
    can_manage_messages: bool
    can_manage_members: bool
    can_manage_chat: bool
    joined_at: str
    last_read_message_id: Optional[int]


@dataclass
class Chat:
    id: int
    chat_type: str
    name: Optional[str]
    description: Optional[str]
    avatar_url: Optional[str]
    owner_id: Optional[int]
    is_public: bool
    created_at: str
    updated_at: str
    members: List[ChatMember]
    member_count: int


@dataclass
class ChatPreview:
    id: int
    chat_type: str
    name: Optional[str]
    description: Optional[str]
    avatar_url: Optional[str]
    is_public: bool
    member_count: int
    last_message: Optional["Message"]
    last_user: Optional[UserPublic]
    other_user: Optional[UserPublic]
    last_read_message_id: Optional[int]
    unread_count: int


@dataclass
class MessageAttachment:
    id: int
    chat_id: int
    uploaded_by: int
    file_type: str
    file_url: str
    file_name: str
    file_size: int
    mime_type: str
    thumbnail_url: Optional[str]
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int]
    created_at: str


@dataclass
class MessageReaction:
    id: int
    message_id: int
    user_id: int
    emoji: str
    created_at: str


@dataclass
class Message:
    id: int
    chat_id: int
    sender_id: int
    reply_to_message_id: Optional[int]
    content: str
    is_edited: bool
    created_at: str
    edited_at: Optional[str]
    attachments: Optional[List[MessageAttachment]]
    reactions: Optional[List[MessageReaction]]


WsMessageType = Literal[
    # client -> server
    "ping",
    "authenticate",
    "subscribe",
    "unsubscribe",
    "send_message",
    "edit_message",
    "delete_message",
    "add_reaction",
    "remove_reaction",
    "mark_as_read",
    "mark_all_as_read",
    "typing",
    "get_online_list",
    # server -> client
    "pong",
    "authenticated",
    "error",
    "new_message",
    "message_edited",
    "message_deleted",
    "reaction_added",
    "reaction_removed",
    "user_online",
    "user_offline",
    "user_typing",
    "message_read",
    "all_messages_read",
    "poll_created",
    "poll_voted",
    "poll_closed",
    "online_list",
]


@dataclass
class WsEnvelope:
    type: Union[WsMessageType, str]
    data: Any


@dataclass
class WsAuthenticatedData:
    user_id: int


@dataclass
class WsErrorData:
    message: str


@dataclass
class WsOnlineListUser:
    id: int


@dataclass
class WsOnlineListData:
    users: List[WsOnlineListUser]
