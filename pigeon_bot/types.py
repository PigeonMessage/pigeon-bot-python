from dataclasses import dataclass, field
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
    success: Optional[bool] = None 


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
class PhotoMedia:
    type: Literal["Photo"] = "Photo"
    file_id: str = ""
    file_url: str = ""
    width: int = 0
    height: int = 0
    file_size: int = 0
    thumbnail_url: Optional[str] = None
    spoiler: bool = False


@dataclass
class DocumentMedia:
    type: Literal["Document"] = "Document"
    file_id: str = ""
    file_url: str = ""
    file_name: str = ""
    mime_type: str = ""
    file_size: int = 0
    thumbnail_url: Optional[str] = None


@dataclass
class VideoMedia:
    type: Literal["Video"] = "Video"
    file_id: str = ""
    file_url: str = ""
    width: int = 0
    height: int = 0
    duration: Optional[float] = None
    file_size: int = 0
    thumbnail_url: Optional[str] = None
    supports_streaming: bool = True


@dataclass
class AudioMedia:
    type: Literal["Audio"] = "Audio"
    file_id: str = ""
    file_url: str = ""
    duration: Optional[float] = None
    file_name: Optional[str] = None
    mime_type: str = ""
    file_size: int = 0
    thumbnail_url: Optional[str] = None


@dataclass
class VoiceMedia:
    type: Literal["Voice"] = "Voice"
    file_id: str = ""
    file_url: str = ""
    duration: Optional[float] = None
    file_size: int = 0
    waveform: Optional[List[int]] = None


@dataclass
class GifMedia:
    type: Literal["Gif"] = "Gif"
    file_id: str = ""
    file_url: str = ""
    width: int = 0
    height: int = 0
    duration: Optional[float] = None
    file_size: int = 0
    preview_url: Optional[str] = None


@dataclass
class StickerMedia:
    type: Literal["Sticker"] = "Sticker"
    file_id: str = ""
    file_url: str = ""
    width: int = 0
    height: int = 0
    emoji: Optional[str] = None
    set_name: Optional[str] = None


@dataclass
class GeoMedia:
    type: Literal["Geo"] = "Geo"
    latitude: float = 0.0
    longitude: float = 0.0
    title: Optional[str] = None
    address: Optional[str] = None


@dataclass
class ContactMedia:
    type: Literal["Contact"] = "Contact"
    phone_number: str = ""
    first_name: str = ""
    last_name: Optional[str] = None
    vcard: Optional[str] = None


@dataclass
class PollOption:
    text: str
    id: Optional[int] = None
    poll_id: Optional[int] = None
    is_correct: Optional[bool] = None
    votes_count: Optional[int] = None
    voters: Optional[List[UserPublic]] = None


@dataclass
class PollMedia:
    type: Literal["Poll"] = "Poll"
    question: str = ""
    options: List[PollOption] = field(default_factory=list)
    allows_multiple: bool = False
    anonymous: bool = True
    is_quiz: bool = False
    has_voted: Optional[bool] = None
    user_voted_options: Optional[List[int]] = None
    explanation: Optional[str] = None
    close_period: Optional[int] = None
    correct_option_indexes: Optional[List[int]] = None
    allow_revote: bool = True


MessageMedia = Union[
    PhotoMedia,
    DocumentMedia,
    VideoMedia,
    AudioMedia,
    VoiceMedia,
    GifMedia,
    StickerMedia,
    GeoMedia,
    ContactMedia,
    PollMedia,
]


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
    media: Optional[List[MessageMedia]] = None
    is_edited: bool = False
    created_at: str = ""
    edited_at: Optional[str] = None
    reactions: Optional[List[MessageReaction]] = None
    new_chat_members: Optional[List[UserPublic]] = None
    left_chat_member: Optional[UserPublic] = None
    left_chat_member_id: Optional[int] = None
    new_chat_title: Optional[str] = None
    delete_chat_photo: Optional[bool] = None
    chat_created_type: Optional[str] = None
    migrate_to_chat_id: Optional[int] = None
    migrate_from_chat_id: Optional[int] = None
    pinned_message: Optional["Message"] = None


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
    "vote_poll",
    "unvote_poll",
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
